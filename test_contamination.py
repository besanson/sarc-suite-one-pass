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
CH6 tests (prereg/contamination.md): the two buffer-mitigation adapters
in isolation, the poisoned-substitution metric against a synthetic
ground-truth fixture, and an end-to-end check on the registered SEED that
plain contamination occurs and both mitigations strictly reduce it.

SEED = 26313
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from contamination import (
    MedianOf3Buffer,
    QuarantineWindowBuffer,
    compute_poisoned_substitutions,
)
from runner import build_contamination_scenarios, build_engines, run_scenario
from suite_sim import SEED, RetailSimulation

SKU = "S1"


# ---------------------------------------------------------------------------
# QuarantineWindowBuffer
# ---------------------------------------------------------------------------


def test_quarantine_window_seeded_value_is_immediately_eligible():
    buf = QuarantineWindowBuffer(values={SKU: 10.0})
    assert buf.substitute(SKU) == 10.0


def test_quarantine_window_single_write_not_yet_eligible():
    buf = QuarantineWindowBuffer()
    buf.put(SKU, 25.0)
    assert buf.substitute(SKU) is None


def test_quarantine_window_becomes_eligible_after_k_consistent_writes():
    buf = QuarantineWindowBuffer()
    buf.put(SKU, 25.0)
    buf.put(SKU, 25.0)
    assert buf.substitute(SKU) is None  # only 2 so far
    buf.put(SKU, 25.0)
    assert buf.substitute(SKU) == 25.0  # 3rd consistent write


def test_quarantine_window_inconsistent_write_resets_streak():
    buf = QuarantineWindowBuffer()
    buf.put(SKU, 25.0)
    buf.put(SKU, 25.0)
    buf.put(SKU, 999.0)  # breaks the streak
    assert buf.substitute(SKU) is None
    buf.put(SKU, 999.0)
    assert buf.substitute(SKU) is None
    buf.put(SKU, 999.0)
    assert buf.substitute(SKU) == 999.0


def test_quarantine_window_single_spurious_write_never_reaches_eligibility():
    """A lone poisoned write (the common case at INJECTION_PROBABILITY=0.02)
    can never itself become substitutable — it would need two more
    identical corrupted writes in a row first."""
    buf = QuarantineWindowBuffer(values={SKU: 10.0})
    buf.put(SKU, 25.0)  # one poisoned write
    assert buf.substitute(SKU) == 10.0  # falls back to the prior eligible value
    buf.put(SKU, 10.0)
    buf.put(SKU, 10.0)
    assert buf.substitute(SKU) == 10.0


# ---------------------------------------------------------------------------
# MedianOf3Buffer
# ---------------------------------------------------------------------------


def test_median_of_3_no_history_returns_none():
    buf = MedianOf3Buffer()
    assert buf.substitute(SKU) is None


def test_median_of_3_seeded_single_value():
    buf = MedianOf3Buffer(values={SKU: 10.0})
    assert buf.substitute(SKU) == 10.0


def test_median_of_3_smooths_a_single_outlier():
    buf = MedianOf3Buffer(values={SKU: 10.0})
    buf.put(SKU, 10.0)
    buf.put(SKU, 25.0)  # one poisoned write among three
    assert buf.substitute(SKU) == 10.0


def test_median_of_3_keeps_only_last_three():
    buf = MedianOf3Buffer()
    for v in (1.0, 2.0, 3.0, 4.0, 5.0):
        buf.put(SKU, v)
    # history is now [3.0, 4.0, 5.0]; median = 4.0
    assert buf.substitute(SKU) == 4.0


def test_median_of_3_consecutive_poisoning_defeats_the_mitigation():
    """Documented limitation: three poisoned writes IN A ROW still poison
    the median — the mitigation reduces, not eliminates, exposure."""
    buf = MedianOf3Buffer(values={SKU: 10.0})
    buf.put(SKU, 25.0)
    buf.put(SKU, 25.0)
    assert buf.substitute(SKU) == 25.0  # median(10, 25, 25) = 25


# ---------------------------------------------------------------------------
# compute_poisoned_substitutions: synthetic ground-truth fixture.
# ---------------------------------------------------------------------------


@dataclass
class _FakePlanEntry:
    decision_id: int
    sku: str
    injected_defect: Optional[str]
    true_cost: float = 10.0
    read_cost: float = 10.0


def _sub_line(triggered_value):
    return {
        "remediation": {"evidence_substitution": {"triggered": True, "substituted_value": triggered_value}},
        "gates": {"dq": {"verdict": "substitute"}},
    }


def _admit_line():
    return {
        "remediation": {"evidence_substitution": None},
        "gates": {"dq": {"verdict": "admit"}},
    }


def test_no_poisoning_when_traced_write_is_clean():
    plan = [
        _FakePlanEntry(0, SKU, None),           # clean admit, writes true_cost=10.0
        _FakePlanEntry(1, SKU, "stale_master_data"),  # substitutes the clean value (10.0)
    ]
    lines = [_admit_line(), _sub_line(10.0)]
    result = compute_poisoned_substitutions(plan, lines)
    assert result["substitutions"] == 1
    assert result["poisoned_substitutions"] == 0


def test_poisoning_when_traced_write_is_uncovered_defect():
    plan = [
        _FakePlanEntry(0, SKU, "plausible_outlier", read_cost=25.0),  # DQ admits it (uncovered), writes 25.0
        _FakePlanEntry(1, SKU, "stale_master_data"),  # substitutes the poisoned value (25.0)
    ]
    lines = [_admit_line(), _sub_line(25.0)]
    result = compute_poisoned_substitutions(plan, lines)
    assert result["substitutions"] == 1
    assert result["poisoned_substitutions"] == 1
    event = result["poisoned_events"][0]
    assert event["poisoning_decision_id"] == 0
    assert event["poisoning_defect"] == "plausible_outlier"
    assert event["abs_value_delta"] == 15.0  # |25.0 - 10.0|
    assert result["poisoned_mean_abs_value_delta"] == 15.0


def test_poisoning_traces_by_value_not_simply_the_most_recent_write():
    """A mitigation buffer can return a value used earlier in the write
    history (e.g. a stale quarantined value, or a median), not simply the
    single most recent write — the trace-back must follow the VALUE, not
    position."""
    plan = [
        _FakePlanEntry(0, SKU, "plausible_outlier_high", read_cost=25.0),  # poisoned write, 25.0
        _FakePlanEntry(1, SKU, None),                      # clean write, 10.0 (more recent)
        _FakePlanEntry(2, SKU, "stale_master_data"),        # substitutes 25.0 -- a MITIGATION
        # buffer could still be returning the stale poisoned value here even
        # though a clean write happened since (e.g. quarantine's streak
        # hasn't re-qualified the newer clean value yet).
    ]
    lines = [_admit_line(), _admit_line(), _sub_line(25.0)]
    result = compute_poisoned_substitutions(plan, lines)
    assert result["poisoned_substitutions"] == 1
    assert result["poisoned_events"][0]["poisoning_decision_id"] == 0


def test_no_poisoning_when_mitigation_returns_the_older_clean_value():
    plan = [
        _FakePlanEntry(0, SKU, None),                      # clean write, 10.0
        _FakePlanEntry(1, SKU, "plausible_outlier", read_cost=25.0),        # poisoned write, 25.0 (more recent)
        _FakePlanEntry(2, SKU, "stale_master_data"),        # substitutes 10.0 -- mitigation
        # correctly avoided the poisoned value even though it is the most
        # recent raw write.
    ]
    lines = [_admit_line(), _admit_line(), _sub_line(10.0)]
    result = compute_poisoned_substitutions(plan, lines)
    assert result["poisoned_substitutions"] == 0


def test_substitution_with_no_prior_write_is_not_poisoned():
    plan = [_FakePlanEntry(0, SKU, "stale_master_data")]
    lines = [_sub_line(10.0)]
    result = compute_poisoned_substitutions(plan, lines)
    assert result["substitutions"] == 1
    assert result["poisoned_substitutions"] == 0


def test_distinct_skus_do_not_cross_contaminate():
    plan = [
        _FakePlanEntry(0, "SKU-A", "plausible_outlier", read_cost=25.0),
        _FakePlanEntry(1, "SKU-B", "stale_master_data"),  # different SKU, no prior write at all
    ]
    lines = [_admit_line(), _sub_line(10.0)]
    result = compute_poisoned_substitutions(plan, lines)
    assert result["poisoned_substitutions"] == 0


# ---------------------------------------------------------------------------
# End-to-end: real engines, registered SEED, both workflows.
# ---------------------------------------------------------------------------


def _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, buffer_factory):
    result = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenario, buffer_factory=buffer_factory)
    lines = result["results"]["remediate_regate"]["lines"]
    plan = result["plan"]
    return compute_poisoned_substitutions(plan, lines)


def test_plain_buffer_produces_at_least_one_poisoned_substitution_on_registered_seed():
    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_contamination_scenarios(sim, seed=SEED)["CONTAM-W1"]
    from sarc_dq.gate import GovernedBuffer

    stats = _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, GovernedBuffer)
    assert stats["poisoned_substitutions"] >= 1


def test_both_mitigations_strictly_reduce_poisoning_w1_registered_seed():
    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_contamination_scenarios(sim, seed=SEED)["CONTAM-W1"]
    from sarc_dq.gate import GovernedBuffer

    plain = _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, GovernedBuffer)
    quarantine = _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, QuarantineWindowBuffer)
    median3 = _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, MedianOf3Buffer)

    assert quarantine["poisoned_substitutions"] < plain["poisoned_substitutions"]
    assert median3["poisoned_substitutions"] < plain["poisoned_substitutions"]


def test_both_mitigations_strictly_reduce_poisoning_w2_registered_seed():
    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_contamination_scenarios(sim, seed=SEED)["CONTAM-W2"]
    from sarc_dq.gate import GovernedBuffer

    plain = _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, GovernedBuffer)
    quarantine = _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, QuarantineWindowBuffer)
    median3 = _poisoned_count(sim, dq_spec, sarc_spec, green_engines, scenario, MedianOf3Buffer)

    assert quarantine["poisoned_substitutions"] < plain["poisoned_substitutions"]
    assert median3["poisoned_substitutions"] < plain["poisoned_substitutions"]
