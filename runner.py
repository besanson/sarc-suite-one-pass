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


def _fresh_dq_gate(dq_spec, sku_true_cost: Dict[str, float]) -> DQPreActionGate:
    buffer = GovernedBuffer(values=dict(sku_true_cost))
    return DQPreActionGate(spec=dq_spec, buffer=buffer)


def _engine(dq_spec, sarc_spec, green_engines, sku_true_cost) -> CompositionEngine:
    return CompositionEngine(
        dq_gate=_fresh_dq_gate(dq_spec, sku_true_cost),
        sarc_spec=sarc_spec,
        green_engines=green_engines,
        carbon_per_unit=CARBON_PER_UNIT,
        cost_multiplier=COST_MULTIPLIER,
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
) -> Dict[str, object]:
    plan = sim.generate_plan(
        seed=SEED,
        unauthorized_role_rate=scenario.unauthorized_role_rate,
        authorized_roles=scenario.authorized_roles,
    )

    kappa_by_decision: Dict[int, float] = {}
    if scenario.apply_s4_kappa:
        kappa_by_decision = _compute_s4_kappa(dq_spec, sim.sku_true_cost, plan)

    results: Dict[str, Dict[str, object]] = {}
    for mode in ("two_phase", "single_pass"):
        engine = _engine(dq_spec, sarc_spec, green_engines, sim.sku_true_cost)
        lines: List[Dict[str, object]] = []
        exec_ctxs: Dict[int, Tuple[ActionContext, float]] = {}
        for p in plan:
            ctx = _context_from_plan(p)
            cap = kappa_by_decision.get(p.decision_id, scenario.order_value_cap)
            if mode == "two_phase":
                line, exec_ctx = engine.two_phase(
                    p.decision_id, ctx, p.evidence_records,
                    tuple(scenario.authorized_roles), cap,
                    scenario.daily_cost_budget, scenario.daily_carbon_budget,
                )
            else:
                line, exec_ctx = engine.single_pass(
                    p.decision_id, ctx, p.evidence_records,
                    tuple(scenario.authorized_roles), cap,
                    scenario.daily_cost_budget, scenario.daily_carbon_budget,
                )
            lines.append(line)
            if line["final"]["admitted"]:
                exec_ctxs[p.decision_id] = (exec_ctx, cap)

        # Post-hoc audit: fresh engine so the audit never perturbs the run's buffer.
        audit_engine = _engine(dq_spec, sarc_spec, green_engines, sim.sku_true_cost)
        audit_flags: Dict[int, bool] = {}
        for decision_id, (exec_ctx, cap) in exec_ctxs.items():
            audit_flags[decision_id] = audit_engine.audit_executed(
                exec_ctx, tuple(scenario.authorized_roles), cap,
                scenario.daily_cost_budget, scenario.daily_carbon_budget,
            )

        results[mode] = {
            "lines": lines,
            "audit_flags": audit_flags,
            "audit_violations": sum(audit_flags.values()),
        }

    return {"scenario": scenario, "plan": plan, "results": results}


def aggregate_scenario_block(scenario_result: Dict[str, object]) -> Dict[str, object]:
    scenario: ScenarioConfig = scenario_result["scenario"]
    lines = scenario_result["results"]["two_phase"]["lines"]
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


def run_all_scenarios(data_path: str = "data/open_retail_daily.csv"):
    sim = RetailSimulation(data_path)
    sha_before = data_sha256(data_path)

    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenarios = build_scenarios(sim)

    all_results = {}
    for name in ("S1", "S2", "S3", "S4"):
        print(f"Running {name}: {scenarios[name].label}")
        all_results[name] = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenarios[name])
        for mode in ("two_phase", "single_pass"):
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


def _write_outputs(sim, all_results, sha_unchanged: bool) -> Path:
    from metrics import build_metrics

    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    for name in ("S1", "S2", "S3", "S4"):
        scenario_dir = out_dir / name
        scenario_dir.mkdir(exist_ok=True)
        for mode in ("two_phase", "single_pass"):
            result = all_results[name]["results"][mode]
            plan = all_results[name]["plan"]
            evidence_path = scenario_dir / f"{mode}-evidence.jsonl"
            with open(evidence_path, "w") as f:
                for line in result["lines"]:
                    f.write(json.dumps(line) + "\n")
            runlog_path = scenario_dir / f"{mode}-runlog.jsonl"
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
    print("SCENARIO SUMMARIES (two_phase)")
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
        f"direction_counts={metrics['ch2_direction_counts']} | "
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
