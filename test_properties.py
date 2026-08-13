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
Phase 2 (V5 groundwork) property-based tests: join laws over random
response tuples, the audit invariant under remediate_regate on randomly
generated admitted contexts, and schema validation of randomly sampled
Evidence Set lines.

SEED = 26313
"""
from __future__ import annotations

import json

import jsonschema
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from composition import (
    ActionContext,
    CompositionEngine,
    Response,
    build_green_engines,
    compute_restrictiveness_join,
    load_sarc_spec,
)
from sarc_dq.dq_spec import load_spec as load_dq_spec
from sarc_dq.gate import GovernedBuffer, PreActionGate as DQPreActionGate
from sarc_dq.records import EvidenceRecord, RecordMetadata
from suite_sim import CARBON_PER_UNIT, COST_MULTIPLIER

RESPONSES = list(Response)
response_st = st.sampled_from(RESPONSES)
response_tuple_st = st.lists(response_st, min_size=1, max_size=6)

SCHEMA = json.load(open("schemas/evidence_line.schema.json"))


# ---------------------------------------------------------------------------
# Join laws (Definition 1/2): the join is max() over the restrictiveness
# order, so these are properties of max() — verified over the ACTUAL
# Response values and compute_restrictiveness_join, not re-derived.
# ---------------------------------------------------------------------------


@given(response_tuple_st)
def test_join_idempotent_on_repetition(responses):
    once = compute_restrictiveness_join(responses)
    twice = compute_restrictiveness_join(responses + responses)
    assert once == twice


@given(response_st, response_st)
def test_join_commutative_pairwise(a, b):
    assert compute_restrictiveness_join([a, b]) == compute_restrictiveness_join([b, a])


@given(response_st, response_st, response_st)
def test_join_associative(a, b, c):
    left = compute_restrictiveness_join([compute_restrictiveness_join([a, b]), c])
    right = compute_restrictiveness_join([a, compute_restrictiveness_join([b, c])])
    assert left == right


@given(response_tuple_st, response_st)
def test_join_monotone_hardening(responses, extra):
    """Adding another gate's response never DECREASES the composed
    restrictiveness (Proposition 2: adding a gate never increases
    permissiveness)."""
    before = compute_restrictiveness_join(responses)
    after = compute_restrictiveness_join(responses + [extra])
    assert after.value >= before.value


@given(response_st)
def test_join_single_response_is_identity(r):
    assert compute_restrictiveness_join([r]) == r


def test_join_empty_is_admit():
    assert compute_restrictiveness_join([]) == Response.ADMIT


def test_response_le_matches_lt_or_equal():
    for a in RESPONSES:
        for b in RESPONSES:
            assert (a <= b) == (a.value <= b.value)
            assert (a < b) == (a.value < b.value)
    assert Response.ADMIT <= Response.ADMIT
    assert not (Response.BLOCK <= Response.ADMIT)


# ---------------------------------------------------------------------------
# Audit invariant: for randomly generated admitted decisions under
# remediate_regate, the post-hoc audit is clean (Theorem 1, empirically,
# complementing the exhaustive Phase 4 checker).
# ---------------------------------------------------------------------------

SKU = "PROPSKU"


def _engine_and_true_cost(true_cost: float) -> CompositionEngine:
    dq_spec = load_dq_spec()
    sarc_spec = load_sarc_spec("specs/authority.yaml")
    green_engines = build_green_engines({SKU: true_cost}, CARBON_PER_UNIT, COST_MULTIPLIER)
    buffer = GovernedBuffer(values={SKU: true_cost})
    dq_gate = DQPreActionGate(spec=dq_spec, buffer=buffer)
    return CompositionEngine(dq_gate, sarc_spec, green_engines, CARBON_PER_UNIT, COST_MULTIPLIER)


@given(
    true_cost=st.floats(min_value=0.5, max_value=500.0, allow_nan=False, allow_infinity=False),
    qty=st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False),
    stale_days=st.integers(min_value=0, max_value=200),
    cost_multiplier_drift=st.floats(min_value=0.5, max_value=1.5, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_audit_invariant_random_admitted_decisions_are_clean(
    true_cost, qty, stale_days, cost_multiplier_drift
):
    engine = _engine_and_true_cost(true_cost)
    read_cost = true_cost * cost_multiplier_drift
    order_value = qty * read_cost
    ctx = ActionContext(
        agent_id="agent-prop", role="agent-replenish", sku=SKU, day=300,
        proposed_qty=qty, order_value=order_value,
        est_cost_eur=order_value * COST_MULTIPLIER, est_carbon_g=qty * CARBON_PER_UNIT,
    )
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload={"sku": SKU, "unit_cost": read_cost, "currency": "GBP"},
        metadata=RecordMetadata(
            source="erp.pricing", as_of_day=300 - stale_days, retrieved_day=300,
            version=2, lineage=("supplier_feed:SKU",),
        ),
    )
    allowed_roles = ("agent-replenish",)
    cap = 1e12
    daily_cost_budget = 1e12
    daily_carbon_budget = 1e12

    line, exec_ctx = engine.remediate_regate(
        0, ctx, [record], allowed_roles, cap, daily_cost_budget, daily_carbon_budget
    )
    if not line["final"]["admitted"]:
        return  # audit invariant only claims something about EXECUTED decisions

    violated = engine.audit_executed(
        exec_ctx, allowed_roles, cap, daily_cost_budget, daily_carbon_budget
    )
    assert not violated, (
        f"audit found a violation on an admitted remediate_regate decision: {line}"
    )


# ---------------------------------------------------------------------------
# Schema validation of randomly sampled Evidence Set lines.
# ---------------------------------------------------------------------------


@given(
    true_cost=st.floats(min_value=0.5, max_value=500.0, allow_nan=False, allow_infinity=False),
    qty=st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False),
    role=st.sampled_from(["agent-replenish", "agent-intruder"]),
    unit_cost_kind=st.sampled_from(["numeric", "string", "same"]),
    drop_currency=st.booleans(),
    stale_days=st.integers(min_value=0, max_value=200),
    mode=st.sampled_from(["remediate_regate", "single_pass"]),
)
@settings(max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_randomly_sampled_lines_validate_against_schema_v1(
    true_cost, qty, role, unit_cost_kind, drop_currency, stale_days, mode
):
    engine = _engine_and_true_cost(true_cost)
    order_value = qty * true_cost
    ctx = ActionContext(
        agent_id="agent-prop", role=role, sku=SKU, day=300,
        proposed_qty=qty, order_value=order_value,
        est_cost_eur=order_value * COST_MULTIPLIER, est_carbon_g=qty * CARBON_PER_UNIT,
    )
    payload = {"sku": SKU, "unit_cost": true_cost}
    if unit_cost_kind == "string":
        payload["unit_cost"] = str(true_cost)
    if not drop_currency:
        payload["currency"] = "GBP"
    record = EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload=payload,
        metadata=RecordMetadata(
            source="erp.pricing", as_of_day=300 - stale_days, retrieved_day=300,
            version=2, lineage=("supplier_feed:SKU",),
        ),
    )
    allowed_roles = ("agent-replenish",)
    cap = 1e12
    method = engine.remediate_regate if mode == "remediate_regate" else engine.single_pass
    line, _ = method(0, ctx, [record], allowed_roles, cap, 1e12, 1e12)
    jsonschema.validate(line, SCHEMA)
