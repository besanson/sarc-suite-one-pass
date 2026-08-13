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


def evaluate_dq(gate: DQPreActionGate, evidence: List[EvidenceRecord]):
    """Evaluate the real sarc_dq PreActionGate; refresh the governed buffer
    on a clean admit (downstream-only remediation, per Appendix B). A
    response of "admit" means the real schema_conformant/complete
    predicates already validated unit_cost/sku, so no further type check
    is needed here."""
    decision = gate.evaluate(evidence)
    if decision.response == "admit":
        primary = evidence[0]
        gate.buffer.put(str(primary.payload["sku"]), float(primary.payload["unit_cost"]))
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


def _audit_clean_evidence_record(exec_ctx: ActionContext) -> EvidenceRecord:
    """The clean, structurally-valid evidence record standing in for
    "what the executed action's evidence would look like" during the
    post-hoc audit (R4). unit_cost is recovered as order_value /
    proposed_qty — the audit re-derives it from the executed action's own
    numbers rather than trusting any external state, so a decision with
    proposed_qty == 0 (never produced by the real newsvendor rule, but
    guarded here rather than dividing by zero) falls back to 0.0."""
    unit_cost = exec_ctx.order_value / exec_ctx.proposed_qty if exec_ctx.proposed_qty else 0.0
    return EvidenceRecord(
        record_id=f"{exec_ctx.sku}-audit",
        payload={"sku": exec_ctx.sku, "unit_cost": unit_cost, "currency": "GBP"},
        metadata=RecordMetadata(
            source="governed_buffer",
            as_of_day=exec_ctx.day,
            retrieved_day=exec_ctx.day,
            version=1,
            lineage=("governed_buffer:SKU",),
        ),
    )


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
    ) -> None:
        self.dq_gate = dq_gate
        self.sarc_spec = sarc_spec
        self.green_engines = green_engines
        self.carbon_per_unit = carbon_per_unit
        self.cost_multiplier = cost_multiplier

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
    ) -> Tuple[Dict[str, Any], ActionContext]:
        dq_resp1, dq_decision1 = evaluate_dq(self.dq_gate, evidence_records)

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
            evidence_substitution = {
                "triggered": True,
                "pre_order_value": context.order_value,
                "post_order_value": remediated_ctx.order_value,
                "substituted_value": sub_cost,
            }

        if remediated_evidence is evidence_records:
            # No remediation occurred: Phase II would re-evaluate DQ on the
            # identical evidence and get the identical (deterministic)
            # result, so reuse Phase I's decision instead of re-running the
            # real gate (its evidence_id() hashing is the dominant cost).
            dq_resp2, dq_decision2 = dq_resp1, dq_decision1
        else:
            dq_resp2, dq_decision2 = evaluate_dq(self.dq_gate, remediated_evidence)
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
            "decision_id": decision_id,
            "day": context.day,
            "sku": context.sku,
            "workflow": workflow,
            "context": _context_dict(context, order_value_cap, allowed_roles),
            "remediation": {
                "evidence_substitution": evidence_substitution,
                "downroute": None,  # W2-only (Phase 3); always null under W1
                "order_applied": ["evidence_substitution"] if evidence_substitution else [],
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
        return line, remediated_ctx

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
    ) -> Tuple[Dict[str, Any], ActionContext]:
        dq_resp, dq_decision = evaluate_dq(self.dq_gate, evidence_records)
        sarc_resp, sarc_detail = evaluate_sarc_pag(
            self.sarc_spec, context.role, allowed_roles, context.order_value, order_value_cap
        )
        green_resp, green_decision = evaluate_green(
            self.green_engines, context.sku, context.est_cost_eur, daily_cost_budget, daily_carbon_budget
        )

        final_resp = compute_restrictiveness_join([dq_resp, sarc_resp, green_resp])
        winner = _find_winner_gate(dq_resp, sarc_resp, green_resp, final_resp)
        paa_flag = evaluate_paa_lineage(self.dq_gate.spec, evidence_records)

        # The executed action still uses the remediated value when DQ
        # substituted, even though sarc/green judged the ORIGINAL value —
        # this is the single-pass unsoundness mechanism (Proposition 3).
        exec_ctx = context
        evidence_substitution: Optional[Dict[str, Any]] = None
        if dq_resp == Response.SUBSTITUTE and dq_decision.substituted_value is not None:
            exec_ctx = _remediated_context(
                context, dq_decision.substituted_value, self.carbon_per_unit, self.cost_multiplier
            )
            evidence_substitution = {
                "triggered": True,
                "pre_order_value": context.order_value,
                "post_order_value": exec_ctx.order_value,
                "substituted_value": dq_decision.substituted_value,
            }

        line = {
            "decision_id": decision_id,
            "day": context.day,
            "sku": context.sku,
            "workflow": workflow,
            "context": _context_dict(context, order_value_cap, allowed_roles),
            "remediation": {
                "evidence_substitution": evidence_substitution,
                "downroute": None,  # W2-only (Phase 3); always null under W1
                "order_applied": ["evidence_substitution"] if evidence_substitution else [],
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
        return line, exec_ctx

    # -- post-hoc audit (CH1 mechanic) --------------------------------------

    def audit_executed(
        self,
        exec_ctx: ActionContext,
        allowed_roles: Tuple[str, ...],
        order_value_cap: float,
        daily_cost_budget: float,
        daily_carbon_budget: float,
    ) -> bool:
        """Re-evaluate all three real gates on the executed action, its
        recomputed context, and the state in force at execution. Returns
        True iff any gate would NOT admit/substitute/degrade it — i.e. a
        soundness violation (R4)."""
        clean_evidence = [_audit_clean_evidence_record(exec_ctx)]
        dq_resp, _ = evaluate_dq(self.dq_gate, clean_evidence)
        sarc_resp, _ = evaluate_sarc_pag(
            self.sarc_spec, exec_ctx.role, allowed_roles, exec_ctx.order_value, order_value_cap
        )
        green_resp, _ = evaluate_green(
            self.green_engines, exec_ctx.sku, exec_ctx.est_cost_eur, daily_cost_budget, daily_carbon_budget
        )
        return not (is_executed(dq_resp) and is_executed(sarc_resp) and is_executed(green_resp))
