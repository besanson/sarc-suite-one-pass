# Copyright 2026 SARC Suite Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
SARC Suite Runner: build the real engines once, run S1-S4 in both
composition modes over the SAME per-scenario decision plan, audit every
executed action with the real gates, and aggregate metrics.

SEED = 26313
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sarc_governance as sg
from sarc_dq.dq_spec import load_spec as load_dq_spec
from sarc_dq.gate import GovernedBuffer, PreActionGate as DQPreActionGate
from sarc_dq.records import EvidenceRecord, RecordMetadata

from composition import (
    ActionContext,
    CompositionEngine,
    Response,
    RESPONSE_NAME,
    build_green_engines,
    is_executed,
    load_sarc_spec,
)
from suite_sim import (
    CARBON_PER_UNIT,
    COST_MULTIPLIER,
    DEFECT_CLASSES,
    RetailSimulation,
    SEED,
)

AUTHORITY_SPEC_PATH = "specs/authority.yaml"


@dataclass
class ScenarioConfig:
    name: str
    label: str
    authorized_roles: List[str]
    unauthorized_role_rate: float
    order_value_cap: float
    daily_cost_budget: float
    daily_carbon_budget: float
    apply_s4_kappa: bool = False
    workflow: str = "W1"
    commitment_period_days: int = 1
    seed: int = SEED


def _fresh_dq_gate(dq_spec, sku_true_cost: Dict[str, float], buffer_factory=GovernedBuffer) -> DQPreActionGate:
    buffer = buffer_factory(values=dict(sku_true_cost))
    return DQPreActionGate(spec=dq_spec, buffer=buffer)


def _engine(dq_spec, sarc_spec, green_engines, sku_true_cost, buffer_factory=GovernedBuffer) -> CompositionEngine:
    return CompositionEngine(
        dq_gate=_fresh_dq_gate(dq_spec, sku_true_cost, buffer_factory),
        sarc_spec=sarc_spec,
        green_engines=green_engines,
        carbon_per_unit=CARBON_PER_UNIT,
        cost_multiplier=COST_MULTIPLIER,
        # Same dict just used to seed the buffer above (buffer_factory's
        # values= kwarg) -- passed again so the engine's own write-log
        # (independent review round-two finding R2-F6(a)) can seed a
        # genesis entry per SKU, matching the buffer's real initial
        # state exactly rather than guessing at it after the fact.
        initial_buffer_values=sku_true_cost,
    )


def _context_from_plan(p) -> ActionContext:
    order_value = p.proposed_qty * p.read_cost
    return ActionContext(
        agent_id=f"agent-{p.sku}",
        role=p.role,
        sku=p.sku,
        day=p.day,
        proposed_qty=p.proposed_qty,
        order_value=order_value,
        est_cost_eur=order_value * COST_MULTIPLIER,
        est_carbon_g=p.proposed_qty * CARBON_PER_UNIT,
    )


def _compute_s4_kappa(dq_spec, sku_true_cost, plan) -> Dict[int, float]:
    """Peek-evaluate DQ Phase I on a throwaway gate to find which decisions
    substitute, then compute kappa = (V_pre + V_post) / 2 for each (S4,
    Proposition 3's construction)."""
    peek_gate = _fresh_dq_gate(dq_spec, sku_true_cost)
    kappa: Dict[int, float] = {}
    for p in plan:
        decision = peek_gate.evaluate(p.evidence_records)
        if decision.response == "admit":
            primary = p.evidence_records[0]
            cost = primary.payload.get("unit_cost")
            if isinstance(cost, (int, float)):
                peek_gate.buffer.put(p.sku, float(cost))
        if decision.response == "quarantine_substitute" and decision.substituted_value is not None:
            v_pre = p.proposed_qty * p.read_cost
            v_post = p.proposed_qty * decision.substituted_value
            kappa[p.decision_id] = (min(v_pre, v_post) + max(v_pre, v_post)) / 2
    return kappa


def run_scenario(
    sim: RetailSimulation,
    dq_spec,
    sarc_spec,
    green_engines,
    scenario: ScenarioConfig,
    buffer_factory=GovernedBuffer,
    modes: Tuple[str, ...] = ("remediate_regate", "single_pass"),
) -> Dict[str, object]:
    """buffer_factory selects the DQ gate's governed-buffer implementation
    for the scenario's own run engine (plain GovernedBuffer, or one of
    contamination.py's mitigation adapters — CH6, prereg/contamination.md).
    The post-hoc audit engine below always uses the plain GovernedBuffer:
    the audit is an idealized independent re-check, not itself subject to
    whichever mitigation is under test.

    modes restricts which composition protocol(s) actually run — the
    30-seed sweep's contamination scenarios (sweep.py) only ever read
    remediate_regate lines, so they pass modes=("remediate_regate",) to
    skip single_pass's redundant compute entirely. Every other caller
    keeps the default (both modes), unchanged."""
    plan = sim.generate_plan(
        seed=scenario.seed,
        unauthorized_role_rate=scenario.unauthorized_role_rate,
        authorized_roles=scenario.authorized_roles,
        workflow=scenario.workflow,
        commitment_period_days=scenario.commitment_period_days,
    )

    kappa_by_decision: Dict[int, float] = {}
    if scenario.apply_s4_kappa:
        kappa_by_decision = _compute_s4_kappa(dq_spec, sim.sku_true_cost, plan)

    results: Dict[str, Dict[str, object]] = {}
    for mode in modes:
        engine = _engine(dq_spec, sarc_spec, green_engines, sim.sku_true_cost, buffer_factory)
        lines: List[Dict[str, object]] = []
        exec_ctxs: Dict[int, Tuple[ActionContext, float, List[Any]]] = {}
        for p in plan:
            ctx = _context_from_plan(p)
            cap = kappa_by_decision.get(p.decision_id, scenario.order_value_cap)
            if mode == "remediate_regate":
                line, exec_ctx, exec_evidence = engine.remediate_regate(
                    p.decision_id, ctx, p.evidence_records,
                    tuple(scenario.authorized_roles), cap,
                    scenario.daily_cost_budget, scenario.daily_carbon_budget,
                    workflow=scenario.workflow,
                )
            else:
                line, exec_ctx, exec_evidence = engine.single_pass(
                    p.decision_id, ctx, p.evidence_records,
                    tuple(scenario.authorized_roles), cap,
                    scenario.daily_cost_budget, scenario.daily_carbon_budget,
                    workflow=scenario.workflow,
                )
            lines.append(line)
            if line["final"]["admitted"]:
                exec_ctxs[p.decision_id] = (exec_ctx, cap, exec_evidence)

        # Post-hoc audit: fresh engine so the audit never perturbs the run's
        # buffer. Independent review finding F4: audits the EXACT executed
        # evidence records (exec_evidence), not a synthetic reconstruction.
        audit_engine = _engine(dq_spec, sarc_spec, green_engines, sim.sku_true_cost)
        audit_flags: Dict[int, bool] = {}
        exec_evidence_by_decision: Dict[int, List[Any]] = {}
        for decision_id, (exec_ctx, cap, exec_evidence) in exec_ctxs.items():
            audit_flags[decision_id] = audit_engine.audit_executed(
                exec_ctx, exec_evidence, tuple(scenario.authorized_roles), cap,
                scenario.daily_cost_budget, scenario.daily_carbon_budget,
            )
            exec_evidence_by_decision[decision_id] = exec_evidence

        results[mode] = {
            "lines": lines,
            "audit_flags": audit_flags,
            "audit_violations": sum(audit_flags.values()),
            "exec_evidence_by_decision": exec_evidence_by_decision,
            # The live run's own durable governed-buffer write log
            # (independent review round-two finding R2-F6(a)) -- NOT
            # audit_engine's, which never produces its own
            # evidence_substitution to resolve provenance for.
            "buffer_writes": engine.write_log,
        }

    return {"scenario": scenario, "plan": plan, "results": results}


def aggregate_scenario_block(scenario_result: Dict[str, object]) -> Dict[str, object]:
    scenario: ScenarioConfig = scenario_result["scenario"]
    lines = scenario_result["results"]["remediate_regate"]["lines"]
    plan = scenario_result["plan"]

    decisions = len(lines)
    veto_counts = {"dq": 0, "sarc": 0, "green": 0}
    winner_dist: Dict[str, int] = defaultdict(int)
    executed_value = 0.0
    held_clean_value = 0.0
    executed_count = 0
    held_count = 0

    for line, p in zip(lines, plan):
        final = line["final"]
        winner_dist[final["winner_gate"]] += 1
        for gate in ("dq", "sarc", "green"):
            if line["gates"][gate]["verdict"] != "admit":
                veto_counts[gate] += 1
        clean_value = p.proposed_qty * p.true_cost
        if final["admitted"]:
            executed_value += line["action"]["order_value"]
            executed_count += 1
        else:
            held_clean_value += clean_value
            held_count += 1

    return {
        "decisions": decisions,
        "veto_counts": veto_counts,
        "winner_gate_distribution": dict(winner_dist),
        "executed_vs_held_loss": {
            "executed_count": executed_count,
            "executed_order_value": executed_value,
            "held_count": held_count,
            "held_clean_value_foregone": held_clean_value,
        },
    }


def data_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build_engines(sim: RetailSimulation):
    dq_spec = load_dq_spec()
    sarc_spec = load_sarc_spec(AUTHORITY_SPEC_PATH)
    green_engines = build_green_engines(sim.sku_true_cost, CARBON_PER_UNIT, COST_MULTIPLIER)
    return dq_spec, sarc_spec, green_engines


def build_scenarios(sim: RetailSimulation) -> Dict[str, ScenarioConfig]:
    """Calibrate S1/S2/S3 budgets and caps from the real order-economics
    distribution (generated, not guessed) so S1 is genuinely loose."""
    loose_plan = sim.generate_plan(seed=SEED, unauthorized_role_rate=0.0, authorized_roles=["agent-replenish"])
    stats = sim.calibrate(loose_plan)

    # Loose enough for S1/S4: 10x the observed maximum (which already
    # includes the plausible_outlier 2.5x worst case, since read_cost
    # reflects whatever the injector corrupted the payload to).
    loose_cap = stats["max_order_value"] * 10
    loose_cost_budget = stats["max_est_cost"] * 10
    loose_carbon_budget = stats["max_est_carbon"] * 10

    tight_cost_budget = stats["median_est_cost"]
    tight_carbon_budget = stats["median_est_carbon"]

    low_cap = stats["median_order_value"]

    return {
        "S1": ScenarioConfig(
            name="S1", label="baseline: loose budgets, all roles authorised",
            authorized_roles=["agent-replenish"], unauthorized_role_rate=0.0,
            order_value_cap=loose_cap, daily_cost_budget=loose_cost_budget,
            daily_carbon_budget=loose_carbon_budget,
        ),
        "S2": ScenarioConfig(
            name="S2", label="tight-budget day",
            authorized_roles=["agent-replenish"], unauthorized_role_rate=0.0,
            order_value_cap=loose_cap, daily_cost_budget=tight_cost_budget,
            daily_carbon_budget=tight_carbon_budget,
        ),
        "S3": ScenarioConfig(
            name="S3", label="unauthorised burst",
            authorized_roles=["agent-replenish"], unauthorized_role_rate=0.05,
            order_value_cap=low_cap, daily_cost_budget=loose_cost_budget,
            daily_carbon_budget=loose_carbon_budget,
        ),
        "S4": ScenarioConfig(
            name="S4", label="constructive counterexample (Proposition 3)",
            authorized_roles=["agent-replenish"], unauthorized_role_rate=0.0,
            order_value_cap=loose_cap, daily_cost_budget=loose_cost_budget,
            daily_carbon_budget=loose_carbon_budget, apply_s4_kappa=True,
        ),
    }


W2_ROLE = "agent-w2-replenish"  # distinct from W1's "agent-replenish" (prereg/w2-workflow.md)
W2_UNAUTHORIZED_ROLE = "agent-w2-unauthorized"
W2_COMMITMENT_PERIOD_DAYS = 7


def build_w2_scenarios(sim: RetailSimulation, seed: int = SEED) -> Dict[str, ScenarioConfig]:
    """W2's weekly-commitment workflow: calibrated the same generated way
    as W1's scenarios, from the real weekly order-economics distribution
    (not W1's daily one — a week's worth of quantity is ~7x a day's)."""
    loose_plan = sim.generate_plan(
        seed=seed, unauthorized_role_rate=0.0, authorized_roles=[W2_ROLE],
        workflow="W2", commitment_period_days=W2_COMMITMENT_PERIOD_DAYS,
    )
    stats = sim.calibrate(loose_plan)

    loose_cap = stats["max_order_value"] * 10
    loose_cost_budget = stats["max_est_cost"] * 10
    loose_carbon_budget = stats["max_est_carbon"] * 10

    # Tight enough that downroute has real work to do on a meaningful
    # subset (median order implies roughly half of decisions exceed it),
    # loose enough that feasible_qty > 0 for virtually all of them.
    downroute_cost_budget = stats["median_est_cost"]
    downroute_carbon_budget = stats["median_est_carbon"]

    return {
        "W2-S1": ScenarioConfig(
            name="W2-S1", label="W2 baseline: loose weekly budgets, all roles authorised",
            authorized_roles=[W2_ROLE], unauthorized_role_rate=0.0,
            order_value_cap=loose_cap, daily_cost_budget=loose_cost_budget,
            daily_carbon_budget=loose_carbon_budget,
            workflow="W2", commitment_period_days=W2_COMMITMENT_PERIOD_DAYS, seed=seed,
        ),
        "W2-S2": ScenarioConfig(
            name="W2-S2", label="W2 tight weekly budgets: exercises downroute",
            authorized_roles=[W2_ROLE], unauthorized_role_rate=0.0,
            order_value_cap=loose_cap, daily_cost_budget=downroute_cost_budget,
            daily_carbon_budget=downroute_carbon_budget,
            workflow="W2", commitment_period_days=W2_COMMITMENT_PERIOD_DAYS, seed=seed,
        ),
    }


def build_contamination_scenarios(sim: RetailSimulation, seed: int = SEED) -> Dict[str, ScenarioConfig]:
    """CH6 (prereg/contamination.md): loose-budget scenarios for both
    workflows — the poisoned-substitution study exercises the evidence
    buffer, not the resource budgets, so budgets/caps are calibrated the
    same generated-loose way as S1/W2-S1. Run once per buffer strategy
    (plain=GovernedBuffer, quarantine=QuarantineWindowBuffer,
    median_of_3=MedianOf3Buffer) by passing the matching buffer_factory
    to run_scenario."""
    w1_plan = sim.generate_plan(seed=seed, unauthorized_role_rate=0.0, authorized_roles=["agent-replenish"])
    w1_stats = sim.calibrate(w1_plan)
    w2_plan = sim.generate_plan(
        seed=seed, unauthorized_role_rate=0.0, authorized_roles=[W2_ROLE],
        workflow="W2", commitment_period_days=W2_COMMITMENT_PERIOD_DAYS,
    )
    w2_stats = sim.calibrate(w2_plan)
    return {
        "CONTAM-W1": ScenarioConfig(
            name="CONTAM-W1", label="contamination study: loose budgets, W1",
            authorized_roles=["agent-replenish"], unauthorized_role_rate=0.0,
            order_value_cap=w1_stats["max_order_value"] * 10,
            daily_cost_budget=w1_stats["max_est_cost"] * 10,
            daily_carbon_budget=w1_stats["max_est_carbon"] * 10,
            seed=seed,
        ),
        "CONTAM-W2": ScenarioConfig(
            name="CONTAM-W2", label="contamination study: loose weekly budgets, W2",
            authorized_roles=[W2_ROLE], unauthorized_role_rate=0.0,
            order_value_cap=w2_stats["max_order_value"] * 10,
            daily_cost_budget=w2_stats["max_est_cost"] * 10,
            daily_carbon_budget=w2_stats["max_est_carbon"] * 10,
            workflow="W2", commitment_period_days=W2_COMMITMENT_PERIOD_DAYS, seed=seed,
        ),
    }


def run_all_scenarios(data_path: str = "data/open_retail_daily.csv"):
    sim = RetailSimulation(data_path)
    sha_before = data_sha256(data_path)

    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenarios = build_scenarios(sim)

    all_results = {}
    for name in ("S1", "S2", "S3", "S4"):
        print(f"Running {name}: {scenarios[name].label}")
        all_results[name] = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenarios[name])
        for mode in ("remediate_regate", "single_pass"):
            n = len(all_results[name]["results"][mode]["lines"])
            print(f"  {mode}: {n} decisions")

    sha_after = data_sha256(data_path)
    assert sha_before == sha_after, "source data file was modified during the run"

    return sim, all_results, sha_before == sha_after


HONESTY_BANNER = (
    "Mechanism demonstration on open payload data with a declared synthetic "
    "metadata layer. Not a live GIGO-Bench release; live cells come only from "
    "the official harness. Not the proprietary Suite: no connectors, evidence "
    "vault, identity, or hosting. plausible_outlier is injected and not "
    "caught, by design: declared uncovered. S4 is a constructed "
    "counterexample scenario, declared as such."
)


# Short form used in output filenames only (prereg/renaming.md): the mode
# value inside each Evidence Set line stays the full "remediate_regate".
_MODE_FILE_PREFIX = {"remediate_regate": "rtr", "single_pass": "single_pass"}


def _serialize_evidence_record(record) -> Dict[str, object]:
    """Full payload + metadata (record.full_view(), which explicitly
    excludes ground_truth per the standing invariant), plus the record's
    own content-addressed evidence_id -- independent review finding F4's
    "exact Phase II evidence records, content-addressed, persisted"."""
    view = record.full_view()
    view["record_id"] = record.record_id
    view["evidence_id"] = record.evidence_id()
    return view


def _deserialize_evidence_record(view: Dict[str, object]) -> EvidenceRecord:
    """Inverse of _serialize_evidence_record (independent review
    round-two finding R2-F6(b), persisted-evidence reload audit):
    reconstructs a real EvidenceRecord from its persisted JSONL view.
    age_days is dropped -- it's a RecordMetadata @property
    (retrieved_day - as_of_day), not a constructor field, so passing it
    back in would be a TypeError, not a no-op. ground_truth is never in
    the persisted view (full_view() excludes it by design), so the
    reloaded record legitimately has the same empty ground_truth any
    gate is allowed to see."""
    m = view["metadata"]
    metadata = RecordMetadata(
        source=m["source"], as_of_day=m["as_of_day"], retrieved_day=m["retrieved_day"],
        version=m["version"], lineage=tuple(m["lineage"]),
    )
    return EvidenceRecord(record_id=view["record_id"], payload=dict(view["payload"]), metadata=metadata)


def _reconstruct_exec_ctx_and_params(
    line: Dict[str, object],
) -> Tuple[ActionContext, Tuple[str, ...], float, float, float]:
    """Rebuilds exactly the (exec_ctx, allowed_roles, order_value_cap,
    daily_cost_budget, daily_carbon_budget) audit_executed needs, from
    ONE persisted evidence line alone (independent review round-two
    finding R2-F6(b)): context.{agent_id,role,sku,day} never change
    under remediation; action.{order_qty,order_value} are the EXECUTED,
    post-remediation values (composition.py writes them from
    remediated_ctx/exec_ctx, never the pre-remediation context);
    est_cost_eur/est_carbon_g are recomputed with the same formulas
    composition.py itself uses to build every ActionContext
    (order_value * COST_MULTIPLIER, order_qty * CARBON_PER_UNIT); cap
    and allowed_roles are exactly what Phase I/II were actually judged
    against (context.order_value_cap, context.allowed_roles); the daily
    budgets are read back from gates.green.budget_state, the same
    values evaluate_green was actually called with for this decision."""
    ctx = line["context"]
    action = line["action"]
    budget_state = line["gates"]["green"]["budget_state"]
    exec_ctx = ActionContext(
        agent_id=ctx["agent_id"], role=ctx["role"], sku=ctx["sku"], day=ctx["day"],
        proposed_qty=action["order_qty"], order_value=action["order_value"],
        est_cost_eur=action["order_value"] * COST_MULTIPLIER,
        est_carbon_g=action["order_qty"] * CARBON_PER_UNIT,
    )
    return (
        exec_ctx, tuple(ctx["allowed_roles"]), ctx["order_value_cap"],
        budget_state["daily_cost_budget"], budget_state["daily_carbon_budget"],
    )


def reload_and_reaudit(
    dq_spec, sarc_spec, green_engines, sku_true_cost: Dict[str, float], out_dir: Path = Path("out")
) -> Dict[str, Dict[str, Dict[int, bool]]]:
    """Independent review round-two finding R2-F6(b): "audit_executed
    runs before _write_outputs ... the round-two requirement for a
    persisted-evidence replay remains unmet." This function IS that
    replay: for every scenario/mode, it loads the JUST-WRITTEN
    {prefix}-evidence.jsonl and {prefix}-exec-evidence.jsonl back from
    disk, reconstructs real EvidenceRecord objects and ActionContexts
    from that persisted representation alone (never the in-memory
    objects the run itself produced), and reruns audit_executed on a
    fresh engine -- exactly the same audit the live run performed, but
    driven entirely by what actually made it to disk. Must be called
    AFTER the evidence/exec-evidence files exist (i.e. after the first
    write pass in _write_outputs)."""
    reloaded: Dict[str, Dict[str, Dict[int, bool]]] = {}
    for name in ("S1", "S2", "S3", "S4"):
        reloaded[name] = {}
        scenario_dir = out_dir / name
        for mode in ("remediate_regate", "single_pass"):
            prefix = _MODE_FILE_PREFIX[mode]
            lines_by_decision = {
                json.loads(l)["decision_id"]: json.loads(l)
                for l in (scenario_dir / f"{prefix}-evidence.jsonl").read_text().splitlines()
            }
            audit_engine = _engine(dq_spec, sarc_spec, green_engines, sku_true_cost)
            flags: Dict[int, bool] = {}
            exec_evidence_path = scenario_dir / f"{prefix}-exec-evidence.jsonl"
            for raw in exec_evidence_path.read_text().splitlines():
                entry = json.loads(raw)
                decision_id = entry["decision_id"]
                exec_evidence = [_deserialize_evidence_record(v) for v in entry["evidence"]]
                line = lines_by_decision[decision_id]
                exec_ctx, allowed_roles, cap, cost_budget, carbon_budget = _reconstruct_exec_ctx_and_params(line)
                flags[decision_id] = audit_engine.audit_executed(
                    exec_ctx, exec_evidence, allowed_roles, cap, cost_budget, carbon_budget,
                )
            reloaded[name][mode] = flags
    return reloaded


def _write_outputs(sim, all_results, sha_unchanged: bool, dq_spec=None, sarc_spec=None, green_engines=None) -> Path:
    """dq_spec/sarc_spec/green_engines are optional and, if omitted,
    rebuilt via build_engines(sim) -- but build_engines loads
    specs/authority.yaml relative to the CURRENT working directory, so
    any caller that changes directory (e.g. a test isolating its output
    under tmp_path) MUST build them beforehand, in the original
    directory, and pass them in here rather than relying on the
    default."""
    from metrics import build_metrics

    if dq_spec is None or sarc_spec is None or green_engines is None:
        dq_spec, sarc_spec, green_engines = build_engines(sim)

    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    # Pass 1: write evidence, exec-evidence, and buffer-writes for every
    # scenario/mode. reload_and_reaudit (pass 2 below) depends on these
    # files actually existing on disk -- it is a genuine reload, not a
    # relabeled in-memory recheck.
    for name in ("S1", "S2", "S3", "S4"):
        scenario_dir = out_dir / name
        scenario_dir.mkdir(exist_ok=True)
        for mode in ("remediate_regate", "single_pass"):
            result = all_results[name]["results"][mode]
            prefix = _MODE_FILE_PREFIX[mode]
            evidence_path = scenario_dir / f"{prefix}-evidence.jsonl"
            with open(evidence_path, "w") as f:
                for line in result["lines"]:
                    f.write(json.dumps(line) + "\n")
            exec_evidence_path = scenario_dir / f"{prefix}-exec-evidence.jsonl"
            with open(exec_evidence_path, "w") as f:
                for decision_id, records in sorted(result["exec_evidence_by_decision"].items()):
                    entry = {
                        "decision_id": decision_id,
                        "evidence": [_serialize_evidence_record(r) for r in records],
                    }
                    f.write(json.dumps(entry) + "\n")
            # Durable governed-buffer write log (independent review
            # round-two finding R2-F6(a)): one line per write event, in
            # write_seq order, next to this mode's evidence lines --
            # substitute_source.buffer_write_eid in {prefix}-evidence.jsonl
            # resolves to exactly one entry here.
            buffer_writes_path = scenario_dir / f"{prefix}-buffer-writes.jsonl"
            with open(buffer_writes_path, "w") as f:
                for entry in result["buffer_writes"]:
                    f.write(json.dumps(entry) + "\n")

    # Pass 2 (independent review round-two finding R2-F6(b)): reload the
    # just-written evidence back from disk, reconstruct real
    # EvidenceRecord/ActionContext objects from that persisted
    # representation, and rerun the audit on them -- never the in-memory
    # objects the run itself produced. Assert it agrees with the
    # in-memory audit_flags (the strong claim: the SAME violation/clean
    # verdicts are reachable from disk alone, not just from what the run
    # happened to hold in memory), then make the reloaded flags
    # authoritative for CH1 and the runlog -- "CH1 is reported from the
    # reloaded audit."
    reloaded = reload_and_reaudit(dq_spec, sarc_spec, green_engines, sim.sku_true_cost, out_dir)
    for name in ("S1", "S2", "S3", "S4"):
        for mode in ("remediate_regate", "single_pass"):
            result = all_results[name]["results"][mode]
            reloaded_flags = reloaded[name][mode]
            if reloaded_flags != result["audit_flags"]:
                raise AssertionError(
                    f"persisted-evidence reload audit disagrees with the in-memory audit "
                    f"for {name}/{mode}: reloaded={reloaded_flags} in_memory={result['audit_flags']}"
                )
            result["audit_flags"] = reloaded_flags
            result["audit_violations"] = sum(reloaded_flags.values())

    for name in ("S1", "S2", "S3", "S4"):
        scenario_dir = out_dir / name
        for mode in ("remediate_regate", "single_pass"):
            result = all_results[name]["results"][mode]
            plan = all_results[name]["plan"]
            prefix = _MODE_FILE_PREFIX[mode]
            runlog_path = scenario_dir / f"{prefix}-runlog.jsonl"
            with open(runlog_path, "w") as f:
                for line, p in zip(result["lines"], plan):
                    entry = {
                        "decision_id": p.decision_id,
                        "day": p.day,
                        "sku": p.sku,
                        "ground_truth": {
                            "injected_defect": p.injected_defect,
                            "true_cost": p.true_cost,
                            "read_cost": p.read_cost,
                        },
                        "verdict": line["final"]["response"],
                        "winner_gate": line["final"]["winner_gate"],
                        "audit_violation": result["audit_flags"].get(p.decision_id, False),
                    }
                    f.write(json.dumps(entry) + "\n")

    metrics = build_metrics(sim, all_results, sha_unchanged)
    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    return metrics_path


def main():
    print("=" * 70)
    print("SARC SUITE ONE-PASS DEMO: suite run")
    print("=" * 70)

    sim, all_results, sha_unchanged = run_all_scenarios()
    metrics_path = _write_outputs(sim, all_results, sha_unchanged)
    metrics = json.loads(metrics_path.read_text())

    print("\n" + "=" * 70)
    print("SCENARIO SUMMARIES (remediate_regate)")
    print("=" * 70)
    for s in ("S1", "S2", "S3", "S4"):
        block = metrics[s]
        loss = block["executed_vs_held_loss"]
        print(
            f"{s}: decisions={block['decisions']} executed={loss['executed_count']} "
            f"held={loss['held_count']} veto_counts={block['veto_counts']} "
            f"winner_gate_distribution={block['winner_gate_distribution']}"
        )

    print("\n" + "=" * 70)
    print("CH1-CH4")
    print("=" * 70)
    print(
        f"CH1 ch1_violations={metrics['ch1_violations']} | "
        f"CH2 ch2_divergent_decisions={metrics['ch2_divergent_decisions']} "
        f"direction_counts={metrics['ch2_direction_counts']} "
        f"label_only_differences={metrics['label_only_differences']} | "
        f"CH3 ch3_false_hold={metrics['ch3_false_hold']:.6f} | "
        f"CH4 union_ok={metrics['ch4_matrix']['union_ok']}"
    )

    print("\n" + "=" * 70)
    print(f"CH4 PER-CLASS MATRIX (source: {metrics['ch4_matrix']['source_scenario']})")
    print("=" * 70)
    for cls in DEFECT_CLASSES:
        row = metrics["ch4_matrix"][cls]
        print(
            f"  {cls:28s} dq={row['dq']:.3f} sarc={row['sarc']:.3f} "
            f"green={row['green']:.3f} winner_gate_counts={row['winner_gate_counts']}"
        )

    print("\n" + "=" * 70)
    print("HONESTY BANNER")
    print("=" * 70)
    print(HONESTY_BANNER)

    print(f"\nsource_sha256_unchanged={metrics['source_sha256_unchanged']}")
    print(f"\nArtifact: {metrics_path}")


if __name__ == "__main__":
    main()
