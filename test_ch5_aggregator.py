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
CH5 tests (prereg/hypotheses.md, prereg/weights.json): the weighted-score
aggregator harness against a synthetic held-decision fixture, plus an
end-to-end check on the registered SEED that the pre-registered grid does
in fact find at least one compensation violation.

SEED = 26313
"""
from __future__ import annotations

from ch5_aggregator import evaluate_ch5, load_weights, weighted_score
from runner import build_engines, build_scenarios, run_scenario
from suite_sim import SEED, RetailSimulation

WEIGHTS = load_weights()


def _line(dq="admit", sarc="admit", green="admit", admitted=True):
    return {
        "gates": {
            "dq": {"verdict": dq},
            "sarc": {"verdict": sarc},
            "green": {"verdict": green},
        },
        "final": {"admitted": admitted},
    }


def test_weighted_score_is_the_weighted_sum_of_per_gate_scores():
    line = _line(dq="admit", sarc="degrade", green="block")
    wv = {"dq": 0.5, "sarc": 0.3, "green": 0.2}
    score = weighted_score(line, wv, WEIGHTS["score_encoding"])
    expected = 0.5 * 1.0 + 0.3 * 0.5 + 0.2 * 0.0
    assert score == expected


def test_grid_loads_with_registered_shape():
    assert WEIGHTS["thresholds"] == [0.5, 0.6, 0.7, 0.8]
    assert len(WEIGHTS["weight_vectors"]) == 66
    for wv in WEIGHTS["weight_vectors"]:
        assert abs(sum(wv.values()) - 1.0) < 1e-9


def test_min_join_admits_zero_of_held_decisions_by_construction():
    # Sanity check on the harness's own premise: any line it classifies as
    # "held" has final.admitted False, i.e. min join admitted none of them.
    lines = [_line(green="block", admitted=False), _line(admitted=True)]
    result = evaluate_ch5(lines, WEIGHTS)
    assert result["held_decisions"] == 1


def test_pure_green_veto_is_not_compensated_by_pure_green_weight():
    """A weight vector that puts ALL weight on the vetoing gate itself
    can never compensate: green=block scores 0.0, so weight_vector
    {green: 1.0} always yields 0.0, below every threshold."""
    lines = [_line(dq="admit", sarc="admit", green="block", admitted=False)]
    result = evaluate_ch5(lines, WEIGHTS)
    pure_green_cells = [c for c in result["surface"] if c["weights"]["green"] == 1.0]
    assert all(c["violations"] == 0 for c in pure_green_cells)


def test_low_weight_on_the_vetoing_gate_lets_other_scores_compensate():
    """The CH5 mechanism itself: two clean gates and one veto, with the
    veto's own weight diluted to near zero, lets the aggregate clear even
    the highest registered threshold — while the min join still holds the
    decision (final.admitted is False)."""
    lines = [_line(dq="admit", sarc="admit", green="block", admitted=False)]
    result = evaluate_ch5(lines, WEIGHTS)
    assert result["ch5_supported"] is True
    # weights dq=0.5 sarc=0.5 green=0.0 -> score = 1.0, clears every threshold
    matching = [
        c for c in result["surface"]
        if c["weights"] == {"dq": 0.5, "sarc": 0.5, "green": 0.0} and c["threshold"] == 0.8
    ]
    assert matching and matching[0]["violations"] == 1


def test_no_held_decisions_means_ch5_not_supported():
    lines = [_line(admitted=True), _line(admitted=True)]
    result = evaluate_ch5(lines, WEIGHTS)
    assert result["held_decisions"] == 0
    assert result["max_violations"] == 0
    assert result["ch5_supported"] is False


# ---------------------------------------------------------------------------
# End-to-end: real engines, registered SEED, pooled S1-S4.
# ---------------------------------------------------------------------------


def test_ch5_supported_on_real_pooled_s1_to_s4_registered_seed():
    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenarios = build_scenarios(sim)
    pooled_lines = []
    for name in ("S1", "S2", "S3", "S4"):
        result = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenarios[name])
        pooled_lines.extend(result["results"]["remediate_regate"]["lines"])

    ch5 = evaluate_ch5(pooled_lines, WEIGHTS)
    assert ch5["held_decisions"] > 0
    assert ch5["ch5_supported"] is True
