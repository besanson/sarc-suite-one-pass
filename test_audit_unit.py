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
    _dq_buffer_key,
    _maybe_downroute,
    _record_buffer_write,
    _resolve_buffer_write_event,
    _seed_genesis_writes,
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
    return CompositionEngine(
        dq_gate, sarc_spec, green_engines, CARBON_PER_UNIT, COST_MULTIPLIER,
        initial_buffer_values={SKU: TRUE_COST},
    )


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


def test_record_buffer_write_gives_each_event_a_distinct_id_even_when_repeated():
    """Round-two independent review finding R2-F6(a): the old
    key+value-only hash gave every identical (key, value) write the SAME
    id, which is exactly why 3,478 real substitution occurrences
    resolved to only 62 unique ids. write_seq makes every event distinct
    regardless of whether its (key, value) repeats a prior write."""
    log = []
    first = _record_buffer_write(log, "SKU1", 10.0, day=1)
    second = _record_buffer_write(log, "SKU1", 10.0, day=2)  # identical (key, value), different write
    assert first != second
    assert len(log) == 2
    assert log[0] == {"write_seq": 0, "key": "SKU1", "value": 10.0, "day": 1, "event_id": first}
    assert log[1] == {"write_seq": 1, "key": "SKU1", "value": 10.0, "day": 2, "event_id": second}


def test_resolve_buffer_write_event_finds_the_most_recent_matching_write():
    log = []
    older = _record_buffer_write(log, "SKU1", 10.0, day=1)
    _record_buffer_write(log, "SKU1", 11.0, day=2)
    newer = _record_buffer_write(log, "SKU1", 10.0, day=3)  # same value as `older`, later write
    assert _resolve_buffer_write_event(log, "SKU1", 10.0) == newer
    assert _resolve_buffer_write_event(log, "SKU1", 10.0) != older
    assert _resolve_buffer_write_event(log, "SKU1", 999.0) is None  # no matching write at all


def test_seed_genesis_writes_covers_the_buffers_initial_state():
    """A substitution whose value equals the buffer's pre-run seed value
    (never itself an observed put()) must still resolve to exactly one
    write-log entry -- the genesis entry -- not None."""
    log = []
    _seed_genesis_writes(log, {"SKU1": 10.0, "SKU2": 20.0})
    assert len(log) == 2
    assert all(entry["day"] is None for entry in log)  # genesis, not a real decision day
    assert _resolve_buffer_write_event(log, "SKU1", 10.0) is not None
    assert _resolve_buffer_write_event(log, "SKU2", 20.0) is not None


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
    # Snapshot BEFORE the call: remediate_regate's own Phase II re-admits
    # the now-clean remediated evidence, which appends a SECOND write
    # (same value, later write_seq) to the log after the substitution's
    # own provenance was already resolved against the FIRST (genesis)
    # entry -- resolving again against the post-call log would find that
    # later write instead, a look-ahead mismatch, not a bug in the code
    # under test. Comparing against the pre-call snapshot avoids that.
    genesis_id = engine.write_log[-1]["event_id"]
    assert len(engine.write_log) == 1  # only the SKU genesis entry exists yet

    line, _, _ = engine.remediate_regate(0, ctx, [stale], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    sub = line["remediation"]["evidence_substitution"]
    assert sub is not None
    assert sub["pre_evidence_ids"] == [stale.evidence_id()]
    assert sub["substitute_source"]["buffer_key"] == SKU
    # Round-two independent review finding R2-F6(a): the substitution
    # traces to exactly the genesis write it actually read from.
    assert sub["substitute_source"]["buffer_write_eid"] == genesis_id
    matches = [e for e in engine.write_log if e["event_id"] == genesis_id]
    assert len(matches) == 1  # exactly one durable write event, never zero or ambiguous
    # Phase II then re-admits the clean remediated evidence, appending
    # its own (later, distinct) write event for the same governed value
    # -- expected, and itself individually resolvable.
    assert len(engine.write_log) == 2
    assert engine.write_log[-1]["event_id"] != genesis_id
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
    resolved = _resolve_buffer_write_event(engine.write_log, SKU, sub["substituted_value"])
    assert sub["substitute_source"]["buffer_write_eid"] == resolved
    assert resolved is not None
    assert line["schema_version"] == 2


def test_repeated_identical_writes_stay_individually_resolvable():
    """The exact regression the round-two review's provenance probe
    found: 3,478 real substitution occurrences resolved to only 62
    unique buffer_write_eid values, because the old id was a pure
    function of (key, value) and the same true cost gets written
    repeatedly across many decisions/days. Simulates that pattern
    directly: several admits at the SAME (key, value), then a
    substitution -- the substitution's event id must match exactly ONE
    write-log entry, and that entry must be the most recent of the
    repeated writes, not an ambiguous merge of all of them."""
    engine = _engine()
    admit_ctx = _ctx()
    clean = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    # Repeated admits at the identical (key, value) -- the same true cost
    # read cleanly on several different days.
    for decision_id in range(5):
        engine.remediate_regate(decision_id, admit_ctx, [clean], ("agent-replenish",), LOOSE, LOOSE, LOOSE)

    # genesis (1) + 5 repeated identical admits = 6 write-log entries,
    # every one with a DISTINCT event id despite identical (key, value).
    same_value_entries = [e for e in engine.write_log if e["key"] == SKU and e["value"] == TRUE_COST]
    assert len(same_value_entries) == 6
    assert len({e["event_id"] for e in same_value_entries}) == 6  # all distinct

    stale = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": TRUE_COST * 0.7, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY - 60, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, _, _ = engine.remediate_regate(5, admit_ctx, [stale], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    sub = line["remediation"]["evidence_substitution"]
    assert sub is not None
    resolved_id = sub["substitute_source"]["buffer_write_eid"]
    matches = [e for e in engine.write_log if e["event_id"] == resolved_id]
    assert len(matches) == 1  # exactly one durable write event, not zero, not several
    assert matches[0] == same_value_entries[-1]  # the MOST RECENT of the repeated writes


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
