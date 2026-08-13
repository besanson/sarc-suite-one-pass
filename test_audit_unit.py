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
Fast, targeted tests for composition.py's audit machinery and the
budget_state/predicates fields mutmut found under-covered in Phase 2's
first mutation-testing pass (composition.audit_executed and the
gates.green.budget_state dict keys).

SEED = 26313
"""
from __future__ import annotations

from composition import (
    ActionContext,
    CompositionEngine,
    _audit_clean_evidence_record,
    _maybe_downroute,
    build_green_engines,
    load_sarc_spec,
)
from sarc_dq.dq_spec import load_spec as load_dq_spec
from sarc_dq.gate import GovernedBuffer, PreActionGate as DQPreActionGate
from sarc_dq.records import EvidenceRecord, RecordMetadata
from suite_sim import CARBON_PER_UNIT, COST_MULTIPLIER

SKU = "AUDITSKU"
TRUE_COST = 10.0
DAY = 200
LOOSE = 1e12


def _engine() -> CompositionEngine:
    dq_spec = load_dq_spec()
    sarc_spec = load_sarc_spec("specs/authority.yaml")
    green_engines = build_green_engines({SKU: TRUE_COST}, CARBON_PER_UNIT, COST_MULTIPLIER)
    buffer = GovernedBuffer(values={SKU: TRUE_COST})
    dq_gate = DQPreActionGate(spec=dq_spec, buffer=buffer)
    return CompositionEngine(dq_gate, sarc_spec, green_engines, CARBON_PER_UNIT, COST_MULTIPLIER)


def _ctx(qty=5.0, cost=TRUE_COST, role="agent-replenish"):
    order_value = qty * cost
    return ActionContext(
        agent_id="agent-test", role=role, sku=SKU, day=DAY,
        proposed_qty=qty, order_value=order_value,
        est_cost_eur=order_value * COST_MULTIPLIER, est_carbon_g=qty * CARBON_PER_UNIT,
    )


# ---------------------------------------------------------------------------
# _audit_clean_evidence_record: the helper extracted from audit_executed
# so its unit_cost recomputation can be tested directly.
# ---------------------------------------------------------------------------


def test_audit_clean_evidence_record_recovers_unit_cost_via_division():
    ctx = _ctx(qty=5.0, cost=12.5)  # order_value = 62.5
    record = _audit_clean_evidence_record(ctx)
    assert record.payload["unit_cost"] == 12.5  # 62.5 / 5.0, NOT 62.5 * 5.0
    assert record.payload["sku"] == SKU
    assert record.payload["currency"] == "GBP"
    assert record.record_id == f"{SKU}-audit"


def test_audit_clean_evidence_record_zero_qty_falls_back_to_zero_cost():
    ctx = _ctx(qty=0.0, cost=TRUE_COST)
    record = _audit_clean_evidence_record(ctx)
    assert record.payload["unit_cost"] == 0.0


def test_audit_clean_evidence_record_is_structurally_clean():
    ctx = _ctx()
    record = _audit_clean_evidence_record(ctx)
    assert record.metadata.source == "governed_buffer"
    assert record.metadata.age_days == 0
    assert record.metadata.lineage == ("governed_buffer:SKU",)


# ---------------------------------------------------------------------------
# audit_executed: must correctly detect violations, not just correctly
# report "clean" on already-compliant decisions (the property test in
# test_properties.py only exercises the clean/no-violation path).
# ---------------------------------------------------------------------------


def test_audit_executed_detects_over_cap_violation():
    engine = _engine()
    exec_ctx = _ctx(qty=100.0, cost=TRUE_COST)  # order_value = 1000.0
    violated = engine.audit_executed(exec_ctx, ("agent-replenish",), 10.0, LOOSE, LOOSE)
    assert violated is True


def test_audit_executed_detects_over_budget_violation():
    engine = _engine()
    exec_ctx = _ctx(qty=100.0, cost=TRUE_COST)
    violated = engine.audit_executed(exec_ctx, ("agent-replenish",), LOOSE, 0.001, LOOSE)
    assert violated is True


def test_audit_executed_detects_unauthorised_role_violation():
    engine = _engine()
    exec_ctx = _ctx(role="agent-intruder")
    violated = engine.audit_executed(exec_ctx, ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert violated is True


def test_audit_executed_clean_on_compliant_decision():
    engine = _engine()
    exec_ctx = _ctx()
    violated = engine.audit_executed(exec_ctx, ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert violated is False


# ---------------------------------------------------------------------------
# budget_state dict keys — not previously asserted anywhere.
# ---------------------------------------------------------------------------


def test_remediate_regate_budget_state_keys():
    engine = _engine()
    ctx = _ctx()
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _ = engine.remediate_regate(0, ctx, [record], ("agent-replenish",), LOOSE, 123.0, 456.0)
    budget_state = line["gates"]["green"]["budget_state"]
    assert budget_state["daily_cost_budget"] == 123.0
    assert budget_state["daily_carbon_budget"] == 456.0


def test_single_pass_budget_state_keys():
    engine = _engine()
    ctx = _ctx()
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _ = engine.single_pass(0, ctx, [record], ("agent-replenish",), LOOSE, 123.0, 456.0)
    budget_state = line["gates"]["green"]["budget_state"]
    assert budget_state["daily_cost_budget"] == 123.0
    assert budget_state["daily_carbon_budget"] == 456.0


# ---------------------------------------------------------------------------
# W2 / downroute (Phase 3, prereg/w2-workflow.md): the second remediator.
# ---------------------------------------------------------------------------


def test_downroute_triggers_under_w2_tight_budget():
    engine = _engine()
    ctx = _ctx(qty=100.0)  # order_value = 1000.0, est_cost_eur = 1200.0
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    tight_budget = 360.0  # feasible qty = 360 / (10 * 1.2) = 30
    line, exec_ctx = engine.remediate_regate(
        0, ctx, [record], ("agent-replenish",), LOOSE, tight_budget, LOOSE, workflow="W2",
    )
    assert line["remediation"]["downroute"] == {
        "triggered": True, "pre_qty": 100.0, "post_qty": 30.0, "cap_used": tight_budget,
    }
    assert line["remediation"]["order_applied"] == ["downroute"]
    assert line["final"]["admitted"] is True
    assert exec_ctx.proposed_qty == 30.0
    assert line["action"]["order_qty"] == 30.0


def test_downroute_never_triggers_under_w1_even_with_same_tight_budget():
    engine = _engine()
    ctx = _ctx(qty=100.0)
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _ = engine.remediate_regate(
        0, ctx, [record], ("agent-replenish",), LOOSE, 360.0, LOOSE, workflow="W1",
    )
    assert line["remediation"]["downroute"] is None
    assert line["final"]["response"] == "block"
    assert line["final"]["winner_gate"] == "green"


def test_single_pass_w2_downroute_reflected_in_executed_action_not_verdict():
    engine = _engine()
    ctx = _ctx(qty=100.0)
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    tight_budget = 360.0
    line, exec_ctx = engine.single_pass(
        0, ctx, [record], ("agent-replenish",), LOOSE, tight_budget, LOOSE, workflow="W2",
    )
    # single_pass judges the ORIGINAL (pre-downroute) action: green sees
    # qty=100 against a budget that only fits 30, so the JOIN still blocks...
    assert line["gates"]["green"]["verdict"] == "block"
    assert line["final"]["response"] == "block"
    assert line["final"]["admitted"] is False
    # ...but the executed action (what "action" reports) is downrouted.
    assert line["remediation"]["downroute"]["post_qty"] == 30.0
    assert line["action"]["order_qty"] == 30.0
    assert exec_ctx.proposed_qty == 30.0


# ---------------------------------------------------------------------------
# _maybe_downroute in isolation: closed-form quantity scaling, both binding
# constraints, and the no-op paths.
# ---------------------------------------------------------------------------


def test_maybe_downroute_w1_is_always_a_noop():
    ctx = _ctx(qty=100.0)
    new_ctx, info = _maybe_downroute(ctx, 1.0, 1.0, CARBON_PER_UNIT, COST_MULTIPLIER, "W1")
    assert new_ctx is ctx
    assert info is None


def test_maybe_downroute_zero_qty_is_a_noop():
    ctx = _ctx(qty=0.0)
    new_ctx, info = _maybe_downroute(ctx, 1.0, 1.0, CARBON_PER_UNIT, COST_MULTIPLIER, "W2")
    assert new_ctx is ctx
    assert info is None


def test_maybe_downroute_already_feasible_is_a_noop():
    ctx = _ctx(qty=10.0, cost=TRUE_COST)  # est_cost_eur = 100 * COST_MULTIPLIER
    huge = 1e12
    new_ctx, info = _maybe_downroute(ctx, huge, huge, CARBON_PER_UNIT, COST_MULTIPLIER, "W2")
    assert new_ctx is ctx
    assert info is None


def test_maybe_downroute_cost_bound_is_the_binding_constraint():
    ctx = _ctx(qty=100.0, cost=TRUE_COST)  # est_cost_eur=1200, est_carbon_g=50
    # cost budget forces qty<=30; a huge carbon budget never binds.
    tight_cost = 30.0 * TRUE_COST * COST_MULTIPLIER
    new_ctx, info = _maybe_downroute(ctx, tight_cost, 1e12, CARBON_PER_UNIT, COST_MULTIPLIER, "W2")
    assert info["triggered"] is True
    assert info["cap_used"] == tight_cost
    assert new_ctx.proposed_qty == 30.0


def test_maybe_downroute_carbon_bound_is_the_binding_constraint():
    ctx = _ctx(qty=100.0, cost=TRUE_COST)  # est_cost_eur=1200, est_carbon_g=50
    # carbon budget forces qty<=20; a huge cost budget never binds.
    tight_carbon = 20.0 * CARBON_PER_UNIT
    new_ctx, info = _maybe_downroute(ctx, 1e12, tight_carbon, CARBON_PER_UNIT, COST_MULTIPLIER, "W2")
    assert info["triggered"] is True
    assert info["cap_used"] == tight_carbon
    assert new_ctx.proposed_qty == 20.0
    assert new_ctx.order_value == 20.0 * TRUE_COST
    assert new_ctx.est_cost_eur == new_ctx.order_value * COST_MULTIPLIER
    assert new_ctx.est_carbon_g == 20.0 * CARBON_PER_UNIT


def test_w2_evidence_substitution_and_downroute_can_both_trigger_in_order():
    engine = _engine()
    ctx = _ctx(qty=100.0, cost=TRUE_COST)
    stale = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST * 0.7, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY - 60, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    tight_budget = 360.0
    line, exec_ctx = engine.remediate_regate(
        0, ctx, [stale], ("agent-replenish",), LOOSE, tight_budget, LOOSE, workflow="W2",
    )
    assert line["remediation"]["evidence_substitution"] is not None
    assert line["remediation"]["downroute"] is not None
    assert line["remediation"]["order_applied"] == ["evidence_substitution", "downroute"]
    assert line["final"]["admitted"] is True
