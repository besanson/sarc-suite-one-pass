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
SARC Suite Composition: three-gate orchestration with min semantics.

This module composes the THREE PUBLISHED ENGINES directly — it holds no
gate-internal defect logic of its own:

- Evidence gate:  sarc_dq.gate.PreActionGate + sarc_dq.dq_spec.load_spec()
- Authority gate: sarc_governance ConstraintSpec loaded from specs/authority.yaml,
                   evaluated via ConstraintSpec.at(PAG) + Constraint.predicate(ctx)
                   — the same loop GovernanceToolset.call_tool runs internally at
                   PAG (sarc_governance/governance.py L182-204). We do not wrap the
                   full async GovernanceToolset because there is no async
                   ToolsetProtocol tool here to call: this is a synchronous
                   decision-stream simulation, not an agent tool-call framework.
                   See ADR-001 "Repair" section for the full rationale.
- Resource gate:  green_sarc.PreActionGate + ColdStartEstimator against a
                   per-SKU TableCostModel/TableCarbonModel (declared field
                   mapping, see ADR-001).

SEED = 26313
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import sarc_governance as sg
from sarc_governance.predicates import register as register_sg_predicate

from sarc_dq.gate import GovernedBuffer, PreActionGate as DQPreActionGate
from sarc_dq.records import EvidenceRecord, RecordMetadata

from green_sarc import (
    Action as GreenAction,
    Budget as GreenBudget,
    ColdStartEstimator,
    GovernanceContext as GreenGovernanceContext,
    ModelProfile,
    PreActionGate as GreenPreActionGate,
    TableCarbonModel,
    TableCostModel,
)


# ---------------------------------------------------------------------------
# Composed response lattice (Definition 1/2): admit < substitute < degrade <
# escalate < block; the join is max() over this order; lowercase everywhere.
# ---------------------------------------------------------------------------


class Response(Enum):
    ADMIT = 0
    SUBSTITUTE = 1
    DEGRADE = 2
    ESCALATE = 3
    BLOCK = 4

    def __lt__(self, other: "Response") -> bool:
        if not isinstance(other, Response):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "Response") -> bool:
        if not isinstance(other, Response):
            return NotImplemented
        return self.value <= other.value


RESPONSE_NAME: Dict[Response, str] = {
    Response.ADMIT: "admit",
    Response.SUBSTITUTE: "substitute",
    Response.DEGRADE: "degrade",
    Response.ESCALATE: "escalate",
    Response.BLOCK: "block",
}

EXEC_RESPONSES = (Response.ADMIT, Response.SUBSTITUTE, Response.DEGRADE)


def compute_restrictiveness_join(responses: List[Response]) -> Response:
    """Definition 2: the composed response is the join r* = max_i r_i."""
    if not responses:
        return Response.ADMIT
    return max(responses, key=lambda r: r.value)


def is_executed(response: Response) -> bool:
    return response in EXEC_RESPONSES


@dataclass(frozen=True)
class ActionContext:
    agent_id: str
    role: str
    sku: str
    day: int
    proposed_qty: float
    order_value: float
    est_cost_eur: float
    est_carbon_g: float


# ---------------------------------------------------------------------------
# Authority gate (sarc-governance): custom predicates registered into the
# engine's own registry, resolved by name when specs/authority.yaml loads.
# The cap/allowed-roles are per-decision data, so predicates read them out of
# ctx["args"] rather than closing over scenario state — this keeps the
# predicates pure, reusable, and identical to how a real caller would author
# them against sarc_governance.predicates.register().
# ---------------------------------------------------------------------------


def _role_unauthorised(ctx: Dict[str, Any]) -> bool:
    """Fires (True) exactly when the acting role is NOT in the allowed set."""
    args = ctx.get("args", {})
    return args.get("role") not in args.get("allowed_roles", ())


def _order_value_over_cap(ctx: Dict[str, Any]) -> bool:
    """Fires (True) exactly when order_value exceeds the per-decision cap."""
    args = ctx.get("args", {})
    return float(args.get("order_value", 0.0)) > float(args.get("order_value_cap", float("inf")))


register_sg_predicate("role_unauthorised", _role_unauthorised)
register_sg_predicate("order_value_over_cap", _order_value_over_cap)


_SG_RESPONSE_MAP: Dict[sg.Response, Response] = {
    sg.Response.BLOCK: Response.BLOCK,
    sg.Response.BLOCK_OR_ESCALATE: Response.BLOCK,
    sg.Response.SUSPEND_ROUTE_DEFAULT_DENY: Response.BLOCK,
    sg.Response.ESCALATE: Response.ESCALATE,
    sg.Response.THROTTLE_LOG: Response.DEGRADE,
    sg.Response.LOG: Response.ADMIT,
}


def load_sarc_spec(path: str) -> sg.ConstraintSpec:
    """Load the authority ConstraintSpec via the real YAML loader (R2)."""
    return sg.load_spec(path)


def evaluate_sarc_pag(
    spec: sg.ConstraintSpec,
    role: str,
    allowed_roles: Tuple[str, ...],
    order_value: float,
    order_value_cap: float,
) -> Tuple[Response, Dict[str, Any]]:
    """Evaluate the authority spec at PAG.

    Mirrors sarc_governance.governance.GovernanceToolset.call_tool's own PAG
    loop: iterate ``spec.at(EnforcementPoint.PAG)`` and call each
    ``Constraint.predicate(ctx)``. No local rule logic lives here — the
    predicates are registered engine-side and the Constraint/Response objects
    are the engine's own types.
    """
    ctx = {
        "tool": "replenish_order",
        "args": {
            "role": role,
            "allowed_roles": tuple(allowed_roles),
            "order_value": order_value,
            "order_value_cap": order_value_cap,
        },
    }
    pag_constraints = spec.at(sg.EnforcementPoint.PAG)
    fired = [c for c in pag_constraints if bool(c.predicate(ctx))]
    detail = {
        "constraints_evaluated": {c.id: (c in fired) for c in pag_constraints},
        "fired_ids": [c.id for c in fired],
    }
    if not fired:
        return Response.ADMIT, detail
    mapped = [_SG_RESPONSE_MAP.get(c.response, Response.BLOCK) for c in fired]
    return compute_restrictiveness_join(mapped), detail


# ---------------------------------------------------------------------------
# Evidence gate (sarc_dq): thin wrapper over the real PreActionGate.
# ---------------------------------------------------------------------------


_DQ_RESPONSE_MAP: Dict[str, Response] = {
    "admit": Response.ADMIT,
    "quarantine_substitute": Response.SUBSTITUTE,
    "degrade": Response.DEGRADE,
    "escalate": Response.ESCALATE,
    "block": Response.BLOCK,
}


def _dq_buffer_key(evidence: List[EvidenceRecord]) -> str:
    """Mirrors sarc_dq.gate.PreActionGate.evaluate's own site-key
    derivation (site_field="sku" by default) so provenance recording
    (substitute_source.buffer_key) uses exactly the same key the real
    engine consulted, not an assumed equivalent."""
    primary = evidence[0]
    return str(primary.payload.get("sku", primary.record_id))


def _record_buffer_write(write_log: List[Dict[str, Any]], key: str, value: float, day: Optional[int]) -> str:
    """Appends one durable, run-scoped write-log event and returns its
    content-addressed event id (independent review round-two finding
    R2-F6(a), replacing the old key+value-only `_buffer_write_eid`).
    Hashing write_seq together with key/value/day means repeated
    identical (key, value) writes -- common, since many SKUs' governed
    cost doesn't change often -- get DISTINCT ids instead of collapsing
    to the same one (the exact bug the review's provenance probe found:
    3,478 substitution occurrences resolving to only 62 unique ids).
    write_seq is write_log's own length before the append, so ids are
    stable regardless of what gets logged later. day=None marks a
    genesis entry seeded from the buffer's initial (pre-run) known-good
    values -- see `_seed_genesis_writes` -- rather than a write produced
    by an actual admitted decision during this run."""
    write_seq = len(write_log)
    event_id = hashlib.sha256(f"{write_seq}\x00{key}\x00{value!r}\x00{day!r}".encode()).hexdigest()
    write_log.append({"write_seq": write_seq, "key": key, "value": value, "day": day, "event_id": event_id})
    return event_id


def _seed_genesis_writes(write_log: List[Dict[str, Any]], initial_buffer_values: Dict[str, float]) -> None:
    """One genesis write-log entry per SKU the buffer was constructed
    with (runner.py's `buffer_factory(values=dict(sku_true_cost))`),
    with day=None. Without this, a decision that substitutes before any
    real admit has ever been logged for its SKU -- entirely possible,
    since a stale/corrupt read can be the very first decision the
    simulation draws for that SKU -- would resolve to no write-log entry
    at all, because the buffer's pre-run seed value was never itself an
    observed `put()` call."""
    for key, value in sorted(initial_buffer_values.items()):
        _record_buffer_write(write_log, key, value, day=None)


def _resolve_buffer_write_event(write_log: List[Dict[str, Any]], key: str, value: float) -> Optional[str]:
    """The event id of the MOST RECENT prior write to `key` whose value
    equals `value` -- the exact write a substitution actually drew from,
    resolved against this run's own durable write history, not
    recomputed as a bare content hash of (key, value) alone. Same
    backward-scan-for-most-recent-match technique
    contamination.py's compute_poisoned_substitutions already uses for
    its own provenance tracing. Returns None only if no matching prior
    write exists at all (including no genesis entry), which should not
    happen for a real substitution -- the buffer must have had SOME
    value to substitute."""
    for entry in reversed(write_log):
        if entry["key"] == key and entry["value"] == value:
            return entry["event_id"]
    return None


def evaluate_dq(
    gate: DQPreActionGate,
    evidence: List[EvidenceRecord],
    write_log: Optional[List[Dict[str, Any]]] = None,
    day: Optional[int] = None,
):
    """Evaluate the real sarc_dq PreActionGate; refresh the governed buffer
    on a clean admit (downstream-only remediation, per Appendix B). A
    response of "admit" means the real schema_conformant/complete
    predicates already validated unit_cost/sku, so no further type check
    is needed here. write_log, when given, records this write as a
    durable run-scoped event (independent review round-two finding
    R2-F6(a)) -- callers that don't care about write provenance (e.g.
    audit_executed's independent re-evaluation, which never produces its
    own evidence_substitution record) simply omit it."""
    decision = gate.evaluate(evidence)
    if decision.response == "admit":
        primary = evidence[0]
        key = str(primary.payload["sku"])
        value = float(primary.payload["unit_cost"])
        gate.buffer.put(key, value)
        if write_log is not None:
            _record_buffer_write(write_log, key, value, day)
    return _DQ_RESPONSE_MAP[decision.response], decision


def evaluate_paa_lineage(dq_spec, evidence: List[EvidenceRecord]) -> bool:
    """PAA lineage_present flag — never gates the verdict (Appendix B)."""
    for constraint, result in dq_spec.evaluate(evidence, verif="PAA"):
        if constraint.id == "c_lineage" and not result.passed:
            return True
    return False


# ---------------------------------------------------------------------------
# Resource gate (green_sarc): real ColdStartEstimator + PreActionGate.
# ---------------------------------------------------------------------------


_GREEN_VERDICT_MAP: Dict[str, Response] = {
    "admit": Response.ADMIT,
    "reject": Response.BLOCK,
    "downroute": Response.DEGRADE,
    "escalate": Response.ESCALATE,
}

GREEN_REGION = "declared"


@dataclass
class GreenEngines:
    """Per-SKU cost/carbon model built once from the real economics constants.

    Declared field mapping (ADR-001): Action.max_tokens carries the predicted
    order cost (prompt_tokens=0), so ColdStartEstimator's cost_hat equals
    est_cost_eur exactly. Each SKU gets its own ModelProfile so that
    carbon_hat, computed by the engine's own carbon_for_tokens() pipeline,
    equals est_carbon_g exactly, given a flat declared carbon_intensity of
    1.0 gCO2e/kWh for the single declared region. Both coefficients are
    derived once from the simulation's real, constant-per-SKU economics
    (true unit cost, cost multiplier, carbon-per-unit) — not fitted per
    decision.
    """

    estimator: ColdStartEstimator


def build_green_engines(
    sku_true_costs: Dict[str, float], carbon_per_unit: float, cost_multiplier: float
) -> GreenEngines:
    profiles: Dict[str, ModelProfile] = {}
    for sku, true_cost in sku_true_costs.items():
        # energy_per_token_kwh * carbon_intensity(=1.0) must equal
        # est_carbon_g / est_cost_eur = (qty*carbon_per_unit) / (qty*true_cost*cost_multiplier)
        energy_per_token_kwh = carbon_per_unit / (true_cost * cost_multiplier)
        profiles[sku] = ModelProfile(
            energy_per_token_kwh=energy_per_token_kwh, usd_per_completion_token=1.0
        )
    cost_model = TableCostModel(profiles=profiles, strict=True)
    carbon_model = TableCarbonModel(intensities={GREEN_REGION: 1.0}, strict=True)
    estimator = ColdStartEstimator(cost_model, carbon_model)
    return GreenEngines(estimator=estimator)


def evaluate_green(
    engines: GreenEngines,
    sku: str,
    est_cost_eur: float,
    daily_cost_budget: float,
    daily_carbon_budget: float,
) -> Tuple[Response, Any]:
    action = GreenAction(
        kind="replenish_order",
        model=sku,
        region=GREEN_REGION,
        prompt_tokens=0,
        max_tokens=est_cost_eur,
    )
    budget = GreenBudget(
        token_budget=daily_cost_budget, carbon_ceiling=daily_carbon_budget, delta=0.05
    )
    gate = GreenPreActionGate(engines.estimator)
    decision = gate.evaluate(action, GreenGovernanceContext(budget=budget))
    return _GREEN_VERDICT_MAP[decision.verdict.value], decision


# ---------------------------------------------------------------------------
# Unified Evidence Set line + composition protocols
# ---------------------------------------------------------------------------


def _find_winner_gate(
    dq: Response, sarc: Response, green: Response, final: Response
) -> str:
    if final == Response.ADMIT:
        return "none"
    for name, resp in (("dq", dq), ("sarc", sarc), ("green", green)):
        if resp == final:
            return name
    return "unknown"  # pragma: no cover - unreachable given join semantics


def _context_dict(ctx: ActionContext, order_value_cap: float, allowed_roles: Tuple[str, ...]) -> Dict[str, Any]:
    return {
        "agent_id": ctx.agent_id,
        "role": ctx.role,
        "sku": ctx.sku,
        "day": ctx.day,
        "proposed_qty": ctx.proposed_qty,
        "order_value": ctx.order_value,
        "est_cost_eur": ctx.est_cost_eur,
        "est_carbon_g": ctx.est_carbon_g,
        "allowed_roles": list(allowed_roles),
        "order_value_cap": order_value_cap,
    }


def _remediated_context(ctx: ActionContext, substituted_cost: float, carbon_per_unit: float, cost_multiplier: float) -> ActionContext:
    new_value = ctx.proposed_qty * substituted_cost
    return replace(
        ctx,
        order_value=new_value,
        est_cost_eur=new_value * cost_multiplier,
        est_carbon_g=ctx.proposed_qty * carbon_per_unit,
    )


def _maybe_downroute(
    ctx: ActionContext,
    daily_cost_budget: float,
    daily_carbon_budget: float,
    carbon_per_unit: float,
    cost_multiplier: float,
    workflow: str,
) -> Tuple[ActionContext, Optional[Dict[str, Any]]]:
    """The second remediation operator (prereg/w2-workflow.md): scale the
    committed quantity down to the largest quantity whose predicted cost
    AND carbon both fit the remaining budget, recompute context. Only
    ever applies under W2 (Green SARC's PreActionGate.evaluate never
    itself returns Verdict.DOWNROUTE; this repo realizes the downroute
    *response* as a remediation strategy the same way evidence
    substitution is realized via the real governed buffer — the gate
    supplies the verdict, this function supplies what to do about it).
    W1 is untouched: returns (ctx, None) unconditionally, so W1's
    behavior (and every byte-identical-output guarantee already locked
    in by earlier tests) is unaffected.

    cost_hat and carbon_hat are both exactly linear in proposed_qty for a
    fixed unit_cost (the declared Greensarc field mapping in ADR-001), so
    the budget-feasible maximum quantity has a closed form — no search.
    """
    if workflow != "W2" or ctx.proposed_qty <= 0:
        return ctx, None

    unit_cost = ctx.order_value / ctx.proposed_qty
    max_qty_by_cost = (
        daily_cost_budget / (unit_cost * cost_multiplier)
        if unit_cost > 0 and cost_multiplier > 0
        else ctx.proposed_qty
    )
    max_qty_by_carbon = (
        daily_carbon_budget / carbon_per_unit if carbon_per_unit > 0 else ctx.proposed_qty
    )
    feasible_qty = max(0.0, min(ctx.proposed_qty, max_qty_by_cost, max_qty_by_carbon))

    if feasible_qty >= ctx.proposed_qty:
        return ctx, None  # already budget-feasible; nothing to downroute

    cap_used = daily_cost_budget if max_qty_by_cost <= max_qty_by_carbon else daily_carbon_budget
    new_value = feasible_qty * unit_cost
    new_ctx = replace(
        ctx,
        proposed_qty=feasible_qty,
        order_value=new_value,
        est_cost_eur=new_value * cost_multiplier,
        est_carbon_g=feasible_qty * carbon_per_unit,
    )
    info = {
        "triggered": True,
        "pre_qty": ctx.proposed_qty,
        "post_qty": feasible_qty,
        "cap_used": cap_used,
    }
    return new_ctx, info


def _remediated_evidence(primary: EvidenceRecord, sku: str, day: int, substituted_cost: float) -> List[EvidenceRecord]:
    """Clean, governed-buffer-sourced evidence for Phase II / the audit —
    admitted by construction (Lemma 1: idempotent substitution)."""
    return [
        EvidenceRecord(
            record_id=primary.record_id,
            payload={"sku": sku, "unit_cost": substituted_cost, "currency": "GBP"},
            metadata=RecordMetadata(
                source="governed_buffer",
                as_of_day=day,
                retrieved_day=day,
                version=primary.metadata.version + 1,
                lineage=("governed_buffer:SKU",),
            ),
        )
    ]


class CompositionEngine:
    """Orchestrates the three real gates with remediate-regate ("rtr") /
    single-pass protocols."""

    def __init__(
        self,
        dq_gate: DQPreActionGate,
        sarc_spec: sg.ConstraintSpec,
        green_engines: GreenEngines,
        carbon_per_unit: float,
        cost_multiplier: float,
        initial_buffer_values: Optional[Dict[str, float]] = None,
    ) -> None:
        self.dq_gate = dq_gate
        self.sarc_spec = sarc_spec
        self.green_engines = green_engines
        self.carbon_per_unit = carbon_per_unit
        self.cost_multiplier = cost_multiplier
        # Durable, run-scoped governed-buffer write log (independent
        # review round-two finding R2-F6(a)) -- every real evaluate_dq
        # admit that writes to dq_gate.buffer also appends here, plus one
        # genesis entry per SKU the buffer was seeded with at
        # construction, so every substitution's provenance resolves to
        # exactly one durable write event, never a bare content hash
        # that repeated identical writes could collapse together.
        self.write_log: List[Dict[str, Any]] = []
        if initial_buffer_values:
            _seed_genesis_writes(self.write_log, initial_buffer_values)

    # -- remediate-regate (sound) -------------------------------------------
    # Renamed from "two_phase" per prereg/renaming.md: avoids the reader
    # collision with two-phase-commit (there is no coordinator/participant
    # handshake here). "rtr" is the short form used in identifiers/outputs.

    def remediate_regate(
        self,
        decision_id: int,
        context: ActionContext,
        evidence_records: List[EvidenceRecord],
        allowed_roles: Tuple[str, ...],
        order_value_cap: float,
        daily_cost_budget: float,
        daily_carbon_budget: float,
        workflow: str = "W1",
    ) -> Tuple[Dict[str, Any], ActionContext, List[EvidenceRecord]]:
        """Returns (line, executed context, executed evidence records) --
        the third element is the EXACT evidence Phase II relied on
        (independent review finding F4): the original evidence_records if
        nothing was substituted, or the real remediated records if it was
        -- never a synthetic reconstruction."""
        dq_resp1, dq_decision1 = evaluate_dq(self.dq_gate, evidence_records, self.write_log, context.day)

        remediated_ctx = context
        remediated_evidence = evidence_records
        evidence_substitution: Optional[Dict[str, Any]] = None
        if dq_resp1 == Response.SUBSTITUTE and dq_decision1.substituted_value is not None:
            sub_cost = dq_decision1.substituted_value
            remediated_ctx = _remediated_context(
                context, sub_cost, self.carbon_per_unit, self.cost_multiplier
            )
            remediated_evidence = _remediated_evidence(
                evidence_records[0], context.sku, context.day, sub_cost
            )
            buffer_key = _dq_buffer_key(evidence_records)
            evidence_substitution = {
                "triggered": True,
                "pre_order_value": context.order_value,
                "post_order_value": remediated_ctx.order_value,
                "substituted_value": sub_cost,
                "pre_evidence_ids": list(dq_decision1.evidence_ids),
                "substitute_source": {
                    "buffer_key": buffer_key,
                    "buffer_write_eid": _resolve_buffer_write_event(self.write_log, buffer_key, sub_cost),
                },
            }

        # Second remediator (W2 only, fixed order per prereg/w2-workflow.md:
        # evidence gate first, then resource gate): peek at whether green
        # would reject the (possibly evidence-remediated) action outright
        # for being over budget, and if so, downroute the quantity to the
        # budget-feasible maximum before Phase II's real gate evaluation.
        downroute: Optional[Dict[str, Any]] = None
        if workflow == "W2":
            peek_green_resp, _ = evaluate_green(
                self.green_engines, remediated_ctx.sku, remediated_ctx.est_cost_eur,
                daily_cost_budget, daily_carbon_budget,
            )
            if peek_green_resp == Response.BLOCK:
                remediated_ctx, downroute = _maybe_downroute(
                    remediated_ctx, daily_cost_budget, daily_carbon_budget,
                    self.carbon_per_unit, self.cost_multiplier, workflow,
                )

        if remediated_evidence is evidence_records:
            # No remediation occurred: Phase II would re-evaluate DQ on the
            # identical evidence and get the identical (deterministic)
            # result, so reuse Phase I's decision instead of re-running the
            # real gate (its evidence_id() hashing is the dominant cost).
            dq_resp2, dq_decision2 = dq_resp1, dq_decision1
        else:
            dq_resp2, dq_decision2 = evaluate_dq(self.dq_gate, remediated_evidence, self.write_log, context.day)
        sarc_resp, sarc_detail = evaluate_sarc_pag(
            self.sarc_spec, remediated_ctx.role, allowed_roles, remediated_ctx.order_value, order_value_cap
        )
        green_resp, green_decision = evaluate_green(
            self.green_engines, remediated_ctx.sku, remediated_ctx.est_cost_eur, daily_cost_budget, daily_carbon_budget
        )

        final_resp = compute_restrictiveness_join([dq_resp2, sarc_resp, green_resp])
        winner = _find_winner_gate(dq_resp2, sarc_resp, green_resp, final_resp)
        paa_flag = evaluate_paa_lineage(self.dq_gate.spec, evidence_records)

        line = {
            "schema_version": 2,
            "decision_id": decision_id,
            "day": context.day,
            "sku": context.sku,
            "workflow": workflow,
            "context": _context_dict(context, order_value_cap, allowed_roles),
            "remediation": {
                "evidence_substitution": evidence_substitution,
                "downroute": downroute,
                "order_applied": (
                    (["evidence_substitution"] if evidence_substitution else [])
                    + (["downroute"] if downroute else [])
                ),
            },
            "gates": {
                "sarc": {"constraints_evaluated": sarc_detail["constraints_evaluated"], "verdict": RESPONSE_NAME[sarc_resp]},
                "green": {
                    "predicted_cost": green_decision.forecast.cost_hat,
                    "predicted_carbon": green_decision.forecast.carbon_hat,
                    "budget_state": {
                        "daily_cost_budget": daily_cost_budget,
                        "daily_carbon_budget": daily_carbon_budget,
                    },
                    "verdict": RESPONSE_NAME[green_resp],
                },
                "dq": {
                    # Phase I firing/detection — Phase II re-evaluates DQ on
                    # the remediated (clean) evidence, so "verdict" below
                    # reflects the post-remediation state and normally reads
                    # "admit" even when Phase I substituted. "detected" and
                    # "phase1_predicates" preserve what Phase I actually saw.
                    "detected": dq_decision1.detected,
                    "phase1_predicates": list(dq_decision1.firing),
                    "predicates": list(dq_decision2.firing),
                    "verdict": RESPONSE_NAME[dq_resp2],
                    "substituted_value": dq_decision2.substituted_value,
                    "evidence_ids": list(dq_decision2.evidence_ids),
                    "paa_lineage_flag": paa_flag,
                },
            },
            "final": {
                "admitted": is_executed(final_resp),
                "response": RESPONSE_NAME[final_resp],
                "winner_gate": winner,
                "mode": "remediate_regate",
            },
            "action": {
                "order_qty": remediated_ctx.proposed_qty,
                "order_value": remediated_ctx.order_value,
            },
        }
        return line, remediated_ctx, remediated_evidence

    # -- single-pass (measurement only) ------------------------------------

    def single_pass(
        self,
        decision_id: int,
        context: ActionContext,
        evidence_records: List[EvidenceRecord],
        allowed_roles: Tuple[str, ...],
        order_value_cap: float,
        daily_cost_budget: float,
        daily_carbon_budget: float,
        workflow: str = "W1",
    ) -> Tuple[Dict[str, Any], ActionContext, List[EvidenceRecord]]:
        """Returns (line, executed context, executed evidence records) --
        see remediate_regate's docstring for the third element's meaning.
        single_pass never re-evaluates DQ on the substituted evidence (by
        design -- that is the unsoundness mechanism), but the executed
        evidence is still the real substituted records when substitution
        triggered, not a synthetic reconstruction."""
        dq_resp, dq_decision = evaluate_dq(self.dq_gate, evidence_records, self.write_log, context.day)
        sarc_resp, sarc_detail = evaluate_sarc_pag(
            self.sarc_spec, context.role, allowed_roles, context.order_value, order_value_cap
        )
        green_resp, green_decision = evaluate_green(
            self.green_engines, context.sku, context.est_cost_eur, daily_cost_budget, daily_carbon_budget
        )

        final_resp = compute_restrictiveness_join([dq_resp, sarc_resp, green_resp])
        winner = _find_winner_gate(dq_resp, sarc_resp, green_resp, final_resp)
        paa_flag = evaluate_paa_lineage(self.dq_gate.spec, evidence_records)

        # The executed action still uses the remediated value(s) even
        # though sarc/green judged the ORIGINAL (pre-remediation) value —
        # this is the single-pass unsoundness mechanism (Proposition 3),
        # now extended to both remediators under W2.
        exec_ctx = context
        exec_evidence = evidence_records
        evidence_substitution: Optional[Dict[str, Any]] = None
        if dq_resp == Response.SUBSTITUTE and dq_decision.substituted_value is not None:
            exec_ctx = _remediated_context(
                context, dq_decision.substituted_value, self.carbon_per_unit, self.cost_multiplier
            )
            exec_evidence = _remediated_evidence(
                evidence_records[0], context.sku, context.day, dq_decision.substituted_value
            )
            buffer_key = _dq_buffer_key(evidence_records)
            evidence_substitution = {
                "triggered": True,
                "pre_order_value": context.order_value,
                "post_order_value": exec_ctx.order_value,
                "substituted_value": dq_decision.substituted_value,
                "pre_evidence_ids": list(dq_decision.evidence_ids),
                "substitute_source": {
                    "buffer_key": buffer_key,
                    "buffer_write_eid": _resolve_buffer_write_event(self.write_log, buffer_key, dq_decision.substituted_value),
                },
            }

        downroute: Optional[Dict[str, Any]] = None
        if workflow == "W2":
            peek_green_resp, _ = evaluate_green(
                self.green_engines, exec_ctx.sku, exec_ctx.est_cost_eur,
                daily_cost_budget, daily_carbon_budget,
            )
            if peek_green_resp == Response.BLOCK:
                exec_ctx, downroute = _maybe_downroute(
                    exec_ctx, daily_cost_budget, daily_carbon_budget,
                    self.carbon_per_unit, self.cost_multiplier, workflow,
                )

        line = {
            "schema_version": 2,
            "decision_id": decision_id,
            "day": context.day,
            "sku": context.sku,
            "workflow": workflow,
            "context": _context_dict(context, order_value_cap, allowed_roles),
            "remediation": {
                "evidence_substitution": evidence_substitution,
                "downroute": downroute,
                "order_applied": (
                    (["evidence_substitution"] if evidence_substitution else [])
                    + (["downroute"] if downroute else [])
                ),
            },
            "gates": {
                "sarc": {"constraints_evaluated": sarc_detail["constraints_evaluated"], "verdict": RESPONSE_NAME[sarc_resp]},
                "green": {
                    "predicted_cost": green_decision.forecast.cost_hat,
                    "predicted_carbon": green_decision.forecast.carbon_hat,
                    "budget_state": {
                        "daily_cost_budget": daily_cost_budget,
                        "daily_carbon_budget": daily_carbon_budget,
                    },
                    "verdict": RESPONSE_NAME[green_resp],
                },
                "dq": {
                    "detected": dq_decision.detected,
                    # single_pass has only one evaluation, so "phase1" and
                    # final predicates are the same by construction.
                    "phase1_predicates": list(dq_decision.firing),
                    "predicates": list(dq_decision.firing),
                    "verdict": RESPONSE_NAME[dq_resp],
                    "substituted_value": dq_decision.substituted_value,
                    "evidence_ids": list(dq_decision.evidence_ids),
                    "paa_lineage_flag": paa_flag,
                },
            },
            "final": {
                "admitted": is_executed(final_resp),
                "response": RESPONSE_NAME[final_resp],
                "winner_gate": winner,
                "mode": "single_pass",
            },
            "action": {
                "order_qty": exec_ctx.proposed_qty,
                "order_value": exec_ctx.order_value,
            },
        }
        return line, exec_ctx, exec_evidence

    # -- post-hoc audit (CH1 mechanic) --------------------------------------

    def audit_executed(
        self,
        exec_ctx: ActionContext,
        exec_evidence: List[EvidenceRecord],
        allowed_roles: Tuple[str, ...],
        order_value_cap: float,
        daily_cost_budget: float,
        daily_carbon_budget: float,
    ) -> bool:
        """Re-evaluate all three real gates on the executed action, its
        EXACT executed evidence, and the state in force at execution.
        Returns True iff any gate would NOT admit/substitute/degrade it --
        i.e. a soundness violation (R4).

        Independent review finding F4 (review/REVIEW.md): this used to
        re-derive a synthetic "clean" evidence record from exec_ctx's own
        numbers (order_value / proposed_qty), which by construction always
        looked freshly clean to the DQ gate regardless of what actually
        happened upstream. It now audits exec_evidence, the real Phase II
        evidence records the decision was executed on -- the original
        evidence_records if nothing was substituted, the real remediated
        records if it was (see remediate_regate/single_pass's third
        return value). A fresh CompositionEngine/buffer is still used for
        this call (runner.py), so the audit never perturbs the run's own
        buffer state. write_log is intentionally omitted here: the audit
        never produces its own evidence_substitution record (it only
        returns a violated/clean bool), so it has no provenance to
        resolve against a write-log entry -- this call's own
        self.write_log stays empty and unused, harmlessly."""
        dq_resp, _ = evaluate_dq(self.dq_gate, exec_evidence)
        sarc_resp, _ = evaluate_sarc_pag(
            self.sarc_spec, exec_ctx.role, allowed_roles, exec_ctx.order_value, order_value_cap
        )
        green_resp, _ = evaluate_green(
            self.green_engines, exec_ctx.sku, exec_ctx.est_cost_eur, daily_cost_budget, daily_carbon_budget
        )
        return not (is_executed(dq_resp) and is_executed(sarc_resp) and is_executed(green_resp))
