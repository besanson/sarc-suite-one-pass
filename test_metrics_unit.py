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
Fast, synthetic-data unit tests for metrics.py's pure aggregation
functions — deliberately independent of the expensive real suite_run
fixture (which runs 4 scenarios x 2 modes x ~10k decisions each) so this
file stays fast enough to be the primary target for mutation testing
(Phase 2, V5) without paying that cost per mutant.

SEED = 26313
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import metrics


@dataclass
class _FakePlanEntry:
    decision_id: int
    injected_defect: Optional[str]
    true_cost: float = 10.0
    proposed_qty: float = 5.0


def _line(decision_id, dq_verdict="admit", sarc_verdict="admit", green_verdict="admit",
          final_response="admit", admitted=True, winner_gate="none", detected=False,
          phase1=None, order_value_cap=1e12, order_qty=5.0, order_value=50.0):
    return {
        "decision_id": decision_id,
        "context": {"order_value_cap": order_value_cap},
        "gates": {
            "dq": {"verdict": dq_verdict, "detected": detected},
            "sarc": {"verdict": sarc_verdict},
            "green": {"verdict": green_verdict},
        },
        "remediation": {"evidence_substitution": phase1, "downroute": None, "order_applied": []},
        "final": {"admitted": admitted, "response": final_response, "winner_gate": winner_gate},
        "action": {"order_qty": order_qty, "order_value": order_value},
    }


def _scenario(lines, plan, audit_violations=0, audit_flags=None):
    return {
        "scenario": None,  # aggregate_scenario_block type-annotates but never reads this
        "plan": plan,
        "results": {
            "remediate_regate": {
                "lines": lines, "audit_violations": audit_violations,
                "audit_flags": audit_flags or {},
            },
            "single_pass": {
                "lines": lines, "audit_violations": audit_violations,
                "audit_flags": audit_flags or {},
            },
        },
    }


def _all_results(**overrides):
    base = {
        s: _scenario([], []) for s in metrics.SCENARIO_ORDER
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _ch1_violations
# ---------------------------------------------------------------------------


def test_ch1_violations_sums_across_all_scenarios():
    all_results = _all_results(
        S1=_scenario([], [], audit_violations=1),
        S2=_scenario([], [], audit_violations=2),
        S3=_scenario([], [], audit_violations=0),
        S4=_scenario([], [], audit_violations=3),
    )
    assert metrics._ch1_violations(all_results) == 6


def test_ch1_violations_zero_when_all_clean():
    all_results = _all_results()
    assert metrics._ch1_violations(all_results) == 0


# ---------------------------------------------------------------------------
# _ch2
# ---------------------------------------------------------------------------


def test_ch2_no_divergence_when_responses_match():
    rtr_lines = [_line(0, final_response="admit")]
    sp_lines = [_line(0, final_response="admit")]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, None)]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    divergent, label_only, directions = metrics._ch2(all_results)
    assert divergent == 0
    assert label_only == 0
    assert directions["single_pass_admits_then_violates"] == 0
    assert directions["single_pass_holds_remediated_compliant"] == 0


def test_ch2_admits_then_violates_direction():
    rtr_lines = [_line(0, final_response="escalate", admitted=False)]
    sp_lines = [_line(0, final_response="substitute", admitted=True)]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, "stale_master_data")]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    all_results["S4"]["results"]["single_pass"]["audit_flags"] = {0: True}
    divergent, label_only, directions = metrics._ch2(all_results)
    assert divergent == 1
    assert label_only == 0
    assert directions["single_pass_admits_then_violates"] == 1
    assert directions["single_pass_holds_remediated_compliant"] == 0


def test_ch2_holds_remediated_compliant_direction():
    rtr_lines = [_line(0, final_response="admit", admitted=True)]
    sp_lines = [_line(0, final_response="escalate", admitted=False)]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, "stale_master_data")]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    divergent, label_only, directions = metrics._ch2(all_results)
    assert divergent == 1
    assert label_only == 0
    assert directions["single_pass_admits_then_violates"] == 0
    assert directions["single_pass_holds_remediated_compliant"] == 1


def test_ch2_no_audit_flag_means_not_admits_then_violates():
    rtr_lines = [_line(0, final_response="escalate", admitted=False)]
    sp_lines = [_line(0, final_response="substitute", admitted=True)]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, "stale_master_data")]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    all_results["S4"]["results"]["single_pass"]["audit_flags"] = {0: False}
    divergent, label_only, directions = metrics._ch2(all_results)
    # Class change alone (escalate/held vs substitute/exec) still makes
    # this divergent under rule 1, even with no audit violation.
    assert divergent == 1
    assert directions["single_pass_admits_then_violates"] == 0


def test_ch2_same_class_different_string_clean_audit_is_label_only():
    """The core fix (prereg/ch2-semantics.md): both protocols execute
    (same Exec class), the response strings differ only because
    remediate_regate's Phase II re-reads "admit" post-substitution, and
    the audit finds nothing wrong -- this must NOT count toward
    ch2_divergent_decisions."""
    rtr_lines = [_line(0, final_response="admit", admitted=True)]
    sp_lines = [_line(0, final_response="substitute", admitted=True)]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, "stale_master_data")]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    all_results["S4"]["results"]["single_pass"]["audit_flags"] = {0: False}
    divergent, label_only, directions = metrics._ch2(all_results)
    assert divergent == 0
    assert label_only == 1
    assert directions["single_pass_admits_then_violates"] == 0
    assert directions["single_pass_holds_remediated_compliant"] == 0


def test_ch2_same_class_audited_violation_counts_as_divergent_not_label_only():
    """Same Exec class, differing response strings, AND the audit flags
    single_pass's executed action -- rule 2 fires, so this is a genuine
    divergence, not a label-only difference."""
    rtr_lines = [_line(0, final_response="admit", admitted=True)]
    sp_lines = [_line(0, final_response="substitute", admitted=True)]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, "stale_master_data")]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    all_results["S4"]["results"]["single_pass"]["audit_flags"] = {0: True}
    divergent, label_only, directions = metrics._ch2(all_results)
    assert divergent == 1
    assert label_only == 0
    assert directions["single_pass_admits_then_violates"] == 1


# ---------------------------------------------------------------------------
# _ch3_false_hold
# ---------------------------------------------------------------------------


def test_ch3_zero_when_no_clean_authorised_inbudget_decisions():
    all_results = _all_results()
    assert metrics._ch3_false_hold(all_results) == 0.0


def test_ch3_rate_computed_over_clean_authorised_inbudget_population():
    plan = [_FakePlanEntry(0, None), _FakePlanEntry(1, None)]
    lines = [
        _line(0, sarc_verdict="admit", green_verdict="admit", admitted=True),
        _line(1, sarc_verdict="admit", green_verdict="admit", admitted=False, final_response="escalate"),
    ]
    all_results = _all_results(S1=_scenario(lines, plan))
    rate = metrics._ch3_false_hold(all_results)
    assert rate == 0.5


def test_ch3_excludes_unauthorised_or_over_budget_decisions_from_population():
    plan = [_FakePlanEntry(0, None)]
    # unauthorised (sarc != admit) — must NOT count toward the ch3 population
    lines = [_line(0, sarc_verdict="block", admitted=False, final_response="block")]
    all_results = _all_results(S1=_scenario(lines, plan))
    assert metrics._ch3_false_hold(all_results) == 0.0


def test_ch3_excludes_dirty_decisions_from_population():
    plan = [_FakePlanEntry(0, "schema_drift")]
    lines = [_line(0, dq_verdict="block", admitted=False, final_response="block")]
    all_results = _all_results(S1=_scenario(lines, plan))
    assert metrics._ch3_false_hold(all_results) == 0.0


# ---------------------------------------------------------------------------
# _ch4_matrix
# ---------------------------------------------------------------------------


def test_ch4_matrix_rates_and_union_ok():
    plan = [
        _FakePlanEntry(0, "stale_master_data"),
        _FakePlanEntry(1, "stale_master_data"),
        _FakePlanEntry(2, "plausible_outlier"),
    ]
    lines = [
        _line(0, detected=True, winner_gate="none"),
        _line(1, detected=False, winner_gate="none"),
        _line(2, detected=False, winner_gate="none"),
    ]
    all_results = _all_results(S1=_scenario(lines, plan))
    matrix = metrics._ch4_matrix(all_results)
    assert matrix["stale_master_data"]["dq"] == 0.5
    assert matrix["plausible_outlier"]["dq"] == 0.0
    assert matrix["plausible_outlier"]["sarc"] == 0.0
    assert matrix["plausible_outlier"]["green"] == 0.0
    assert matrix["union_ok"] is True
    assert matrix["source_scenario"] == "S1"


def test_ch4_matrix_zero_n_class_reads_all_zero_rates():
    all_results = _all_results()
    matrix = metrics._ch4_matrix(all_results)
    for cls in metrics.DEFECT_CLASSES:
        assert matrix[cls]["dq"] == 0.0
        assert matrix[cls]["sarc"] == 0.0
        assert matrix[cls]["green"] == 0.0


# ---------------------------------------------------------------------------
# _s4_divergent_decisions
# ---------------------------------------------------------------------------


def test_s4_divergent_decisions_extracts_pre_post_and_cap():
    rtr_lines = [_line(
        0, final_response="escalate", admitted=False, order_value_cap=67.3,
        phase1={"pre_order_value": 62.6, "post_order_value": 72.0, "substituted_value": 14.4},
    )]
    sp_lines = [_line(0, final_response="substitute", admitted=True)]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, "stale_master_data")]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    divs = metrics._s4_divergent_decisions(all_results)
    assert len(divs) == 1
    d = divs[0]
    assert d["decision_id"] == 0
    assert d["remediate_regate_response"] == "escalate"
    assert d["single_pass_response"] == "substitute"
    assert d["pre_order_value"] == 62.6
    assert d["post_order_value"] == 72.0
    assert d["cap"] == 67.3


def test_s4_divergent_decisions_none_when_no_substitution():
    rtr_lines = [_line(0, final_response="admit", admitted=True)]
    sp_lines = [_line(0, final_response="block", admitted=False)]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, "schema_drift")]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    divs = metrics._s4_divergent_decisions(all_results)
    assert divs[0]["pre_order_value"] is None
    assert divs[0]["post_order_value"] is None


def test_s4_divergent_decisions_empty_when_no_divergence():
    rtr_lines = [_line(0, final_response="admit")]
    sp_lines = [_line(0, final_response="admit")]
    all_results = _all_results(S4=_scenario(rtr_lines, [_FakePlanEntry(0, None)]))
    all_results["S4"]["results"]["single_pass"]["lines"] = sp_lines
    assert metrics._s4_divergent_decisions(all_results) == []


# ---------------------------------------------------------------------------
# build_metrics: exercises the top-level orchestration directly (mutmut
# found this entirely untested — 31 "no tests" mutants on this function
# alone before this test existed).
# ---------------------------------------------------------------------------


def test_build_metrics_assembles_all_required_top_level_keys():
    plan0 = [_FakePlanEntry(0, None)]
    lines0 = [_line(0, final_response="admit")]
    all_results = _all_results(
        S1=_scenario(lines0, plan0, audit_violations=0),
        S4=_scenario(lines0, plan0, audit_violations=0),
    )
    all_results["S4"]["results"]["single_pass"]["lines"] = lines0

    result = metrics.build_metrics(sim=None, all_results=all_results, source_sha256_unchanged=True)

    assert set(result.keys()) == {
        "ch1_violations", "ch2_divergent_decisions", "ch2_direction_counts",
        "label_only_differences", "ch3_false_hold", "ch4_matrix",
        "S1", "S2", "S3", "S4", "source_sha256_unchanged",
    }
    assert result["ch1_violations"] == 0
    assert result["source_sha256_unchanged"] is True
    assert result["S4"]["decisions"] == 1
    assert "divergent_decisions" in result["S4"]


def test_build_metrics_propagates_source_sha256_unchanged_false():
    plan0 = [_FakePlanEntry(0, None)]
    lines0 = [_line(0, final_response="admit")]
    all_results = _all_results(S1=_scenario(lines0, plan0))
    all_results["S4"]["results"]["single_pass"]["lines"] = all_results["S4"]["results"]["remediate_regate"]["lines"]

    result = metrics.build_metrics(sim=None, all_results=all_results, source_sha256_unchanged=False)
    assert result["source_sha256_unchanged"] is False


def test_build_metrics_ch1_violations_reflects_all_scenarios():
    plan0 = [_FakePlanEntry(0, None)]
    lines0 = [_line(0, final_response="admit")]
    all_results = _all_results(
        S1=_scenario(lines0, plan0, audit_violations=2),
        S2=_scenario(lines0, plan0, audit_violations=1),
    )
    all_results["S4"]["results"]["single_pass"]["lines"] = all_results["S4"]["results"]["remediate_regate"]["lines"]

    result = metrics.build_metrics(sim=None, all_results=all_results, source_sha256_unchanged=True)
    assert result["ch1_violations"] == 3
