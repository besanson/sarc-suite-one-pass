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
    _buffer_write_eid,
    _dq_buffer_key,
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


def _clean_evidence(ctx):
    """A well-formed evidence record matching ctx's own numbers -- used
    by the audit_executed tests below that exercise cap/budget/role
    violations (not evidence content itself), so any clean, schema-valid
    record does the job. Independent review finding F4: composition.py's
    audit_executed itself no longer builds this kind of record internally
    (see runner.py's exec_evidence threading) -- this is a TEST fixture
    only."""
    unit_cost = ctx.order_value / ctx.proposed_qty if ctx.proposed_qty else 0.0
    return [
        EvidenceRecord(
            record_id=f"{ctx.sku}-audit-fixture",
            payload={"sku": ctx.sku, "unit_cost": unit_cost, "currency": "GBP"},
            metadata=RecordMetadata(source="erp.pricing", as_of_day=ctx.day, retrieved_day=ctx.day, version=2, lineage=("supplier_feed:SKU",)),
        )
    ]


# ---------------------------------------------------------------------------
# audit_executed: must correctly detect violations, not just correctly
# report "clean" on already-compliant decisions (the property test in
# test_properties.py only exercises the clean/no-violation path).
# ---------------------------------------------------------------------------


def test_audit_executed_detects_over_cap_violation():
    engine = _engine()
    exec_ctx = _ctx(qty=100.0, cost=TRUE_COST)  # order_value = 1000.0
    violated = engine.audit_executed(exec_ctx, _clean_evidence(exec_ctx), ("agent-replenish",), 10.0, LOOSE, LOOSE)
    assert violated is True


def test_audit_executed_detects_over_budget_violation():
    engine = _engine()
    exec_ctx = _ctx(qty=100.0, cost=TRUE_COST)
    violated = engine.audit_executed(exec_ctx, _clean_evidence(exec_ctx), ("agent-replenish",), LOOSE, 0.001, LOOSE)
    assert violated is True


def test_audit_executed_detects_unauthorised_role_violation():
    engine = _engine()
    exec_ctx = _ctx(role="agent-intruder")
    violated = engine.audit_executed(exec_ctx, _clean_evidence(exec_ctx), ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert violated is True


def test_audit_executed_clean_on_compliant_decision():
    engine = _engine()
    exec_ctx = _ctx()
    violated = engine.audit_executed(exec_ctx, _clean_evidence(exec_ctx), ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert violated is False


def test_audit_executed_detects_violation_in_the_exact_evidence_itself():
    """Independent review finding F4: the audit must catch a violation
    that lives in the EXACT executed evidence, not just in ctx/budget/role
    -- a synthetic reconstruction from ctx's own numbers could never
    exercise this path, because it always looks clean by construction."""
    engine = _engine()
    exec_ctx = _ctx()
    dirty_evidence = [
        EvidenceRecord(
            record_id=f"{SKU}-audit-fixture",
            payload={"sku": SKU, "unit_cost": TRUE_COST},  # missing "currency"
            metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
        )
    ]
    violated = engine.audit_executed(exec_ctx, dirty_evidence, ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert violated is True


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
    line, _, _ = engine.remediate_regate(0, ctx, [record], ("agent-replenish",), LOOSE, 123.0, 456.0)
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
    line, _, _ = engine.single_pass(0, ctx, [record], ("agent-replenish",), LOOSE, 123.0, 456.0)
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
    line, exec_ctx, _ = engine.remediate_regate(
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
    line, _, _ = engine.remediate_regate(
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
    line, exec_ctx, _ = engine.single_pass(
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
    line, exec_ctx, _ = engine.remediate_regate(
        0, ctx, [stale], ("agent-replenish",), LOOSE, tight_budget, LOOSE, workflow="W2",
    )
    assert line["remediation"]["evidence_substitution"] is not None
    assert line["remediation"]["downroute"] is not None
    assert line["remediation"]["order_applied"] == ["evidence_substitution", "downroute"]
    assert line["final"]["admitted"] is True


# ---------------------------------------------------------------------------
# Evidence Set provenance (independent review finding F2, schema v2):
# pre_evidence_ids and substitute_source in remediation.evidence_substitution.
# ---------------------------------------------------------------------------


def test_buffer_write_eid_is_content_addressed():
    a = _buffer_write_eid("SKU1", 10.0)
    b = _buffer_write_eid("SKU1", 10.0)
    assert a == b  # identical (key, value) -> identical id

    different_value = _buffer_write_eid("SKU1", 10.5)
    assert different_value != a

    different_key = _buffer_write_eid("SKU2", 10.0)
    assert different_key != a


def test_dq_buffer_key_matches_evidence_payload_sku():
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    assert _dq_buffer_key([record]) == SKU


def test_remediate_regate_evidence_substitution_carries_provenance_fields():
    engine = _engine()
    ctx = _ctx()
    stale = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST * 0.7, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY - 60, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _, _ = engine.remediate_regate(0, ctx, [stale], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    sub = line["remediation"]["evidence_substitution"]
    assert sub is not None
    assert sub["pre_evidence_ids"] == [stale.evidence_id()]
    assert sub["substitute_source"]["buffer_key"] == SKU
    assert sub["substitute_source"]["buffer_write_eid"] == _buffer_write_eid(SKU, sub["substituted_value"])
    assert line["schema_version"] == 2


def test_single_pass_evidence_substitution_carries_provenance_fields():
    engine = _engine()
    ctx = _ctx()
    stale = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST * 0.7, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY - 60, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _, _ = engine.single_pass(0, ctx, [stale], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    sub = line["remediation"]["evidence_substitution"]
    assert sub is not None
    assert sub["pre_evidence_ids"] == [stale.evidence_id()]
    assert sub["substitute_source"]["buffer_key"] == SKU
    assert sub["substitute_source"]["buffer_write_eid"] == _buffer_write_eid(SKU, sub["substituted_value"])
    assert line["schema_version"] == 2


def test_no_substitution_means_no_provenance_fields_needed():
    engine = _engine()
    ctx = _ctx()
    clean = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _, _ = engine.remediate_regate(0, ctx, [clean], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert line["remediation"]["evidence_substitution"] is None
    assert line["schema_version"] == 2


def test_provenance_fields_validate_against_schema_v2():
    import json

    import jsonschema

    schema = json.loads(open("schemas/evidence_line.schema.json").read())
    engine = _engine()
    ctx = _ctx()
    stale = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST * 0.7, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY - 60, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _, _ = engine.remediate_regate(0, ctx, [stale], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    jsonschema.validate(line, schema)
