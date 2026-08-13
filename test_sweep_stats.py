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
Fast unit tests for sweep.py's pure statistics helper (mean_ci95) and
seed-list loading, independent of the expensive 30-seed sweep run itself.

SEED = 26313
"""
from __future__ import annotations

from sweep import load_seeds, mean_ci95


def test_load_seeds_matches_registered_count_and_first_seed():
    seeds = load_seeds()
    assert len(seeds) == 30
    assert seeds[0] == 26313
    assert len(set(seeds)) == 30  # no duplicates


def test_mean_ci95_empty_is_all_zero():
    result = mean_ci95([])
    assert result == {"mean": 0.0, "ci95_low": 0.0, "ci95_high": 0.0, "n": 0}


def test_mean_ci95_single_value_is_a_degenerate_point_interval():
    result = mean_ci95([5.0])
    assert result["mean"] == 5.0
    assert result["ci95_low"] == 5.0
    assert result["ci95_high"] == 5.0
    assert result["n"] == 1


def test_mean_ci95_constant_values_have_zero_width_interval():
    result = mean_ci95([3.0] * 30)
    assert result["mean"] == 3.0
    assert result["ci95_low"] == 3.0
    assert result["ci95_high"] == 3.0


def test_mean_ci95_interval_is_symmetric_around_the_mean():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    result = mean_ci95(values)
    assert result["mean"] == 5.5
    lower_gap = result["mean"] - result["ci95_low"]
    upper_gap = result["ci95_high"] - result["mean"]
    assert abs(lower_gap - upper_gap) < 1e-9
    assert result["ci95_low"] < result["mean"] < result["ci95_high"]


def test_mean_ci95_wider_spread_gives_wider_interval():
    tight = mean_ci95([10.0, 10.1, 9.9, 10.0, 10.05])
    wide = mean_ci95([0.0, 20.0, 5.0, 15.0, 10.0])
    tight_width = tight["ci95_high"] - tight["ci95_low"]
    wide_width = wide["ci95_high"] - wide["ci95_low"]
    assert wide_width > tight_width
