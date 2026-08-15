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
Byte-identity replay tests (round-two independent review, finding
R2-N3/R2-F3): "isolated replay of seed 1028331701 differs from the
committed artifact only at ch6.W1.plain.poisoned_mean_abs_value_delta:
committed 2.3614615384615383, replayed 2.361461538461538 -- a one-ULP
delta." The root cause was contamination.py's `sum(deltas) / len(deltas)`,
a naive float summation whose bit-exact result depends on the order
`deltas` happens to be built in -- unlike Python's `statistics.mean`
(already order-independent via exact fraction arithmetic internally),
plain `sum()` is not. Fixed by switching to `math.fsum` over explicitly
sorted inputs everywhere a mean or absolute-delta aggregate is computed
(contamination.py's `mean_delta`, sweep.py's `mean_ci95`).

Two seeds are replayed here: 26313 (first registered seed) and
1028331701 (the specific seed the round-two review's replay audit
flagged). Each is run TWICE against the same in-process sim/engines and
asserted byte-identical via canonical (sort_keys) JSON serialization --
this reproduces the exact class of bug the review caught without
depending on any previously-committed checkpoint file being present or
current.

This module builds the real simulation and engines once per test
session (~15-20s per run_seed call x 4 calls) -- expensive, but this is
exactly the reproduction the round-two review performed and the task
explicitly asks to guard against.

SEED = 26313 and 1028331701 (both registered in prereg/seeds.json)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner import build_engines
from suite_sim import RetailSimulation
from sweep import run_seed

REPLAY_SEEDS = [26313, 1028331701]


@pytest.fixture(scope="module")
def engines():
    sim = RetailSimulation("data/open_retail_daily.csv")
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    return sim, dq_spec, sarc_spec, green_engines


def _canonical(result: dict) -> str:
    return json.dumps(result, sort_keys=True)


@pytest.mark.parametrize("seed", REPLAY_SEEDS)
def test_seed_replay_is_byte_identical(engines, seed):
    sim, dq_spec, sarc_spec, green_engines = engines
    first = run_seed(sim, dq_spec, sarc_spec, green_engines, seed)
    second = run_seed(sim, dq_spec, sarc_spec, green_engines, seed)
    assert _canonical(first) == _canonical(second)


def test_seed_1028331701_poisoned_mean_abs_value_delta_is_stable():
    """The exact field the round-two review's replay audit named:
    ch6.W1.plain.poisoned_mean_abs_value_delta must be bit-identical
    across two replays of seed 1028331701, not merely equal up to
    display rounding."""
    sim = RetailSimulation("data/open_retail_daily.csv")
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    first = run_seed(sim, dq_spec, sarc_spec, green_engines, 1028331701)
    second = run_seed(sim, dq_spec, sarc_spec, green_engines, 1028331701)
    a = first["ch6"]["W1"]["plain"]["poisoned_mean_abs_value_delta"]
    b = second["ch6"]["W1"]["plain"]["poisoned_mean_abs_value_delta"]
    assert a.hex() == b.hex()  # bit-exact, not just ==, which float already guarantees here too


@pytest.mark.slow
def test_seed_1028331701_fresh_run_matches_committed_artifact():
    """Guards against exactly the staleness class this repo already hit
    once, silently: `make sweep`'s own checkpoint logic
    (`if seed_path.exists(): ... skipping`) means a code fix that
    changes a seed's computed values does NOT, by itself, regenerate an
    already-committed per-seed artifact -- the stale value only gets
    replaced by an explicit `rm` + rerun. After the R2-F3 order-stable
    summation fix landed, this repo's own committed
    out/results/sweep/seed_1028331701.json still held the pre-fix value
    (2.3614615384615383) through an entire `make all` run, because the
    checkpoint file already existed and the sweep step skipped it --
    only test_seed_replay_is_byte_identical's two in-process replays
    (which never touch the checkpoint file) stayed green throughout,
    masking the drift completely.

    Unlike that test -- which only proves two fresh replays agree with
    EACH OTHER, and would stay green even if both sides were quietly
    stale relative to history -- this test compares a fresh replay
    against the COMMITTED out/results/sweep/seed_1028331701.json on
    disk: the actual artifact `make sweep` left behind and that ships
    in this repo's history. Marked slow (real ~10k-decision simulation,
    not the two-line unit checks elsewhere in this file) so it can be
    deselected with `-m "not slow"` if ever needed, but it is NOT
    excluded from the default `make test` run -- staleness like this
    must be caught by the standard suite, not an opt-in extra."""
    committed_path = Path("out/results/sweep/seed_1028331701.json")
    if not committed_path.exists():
        pytest.skip(f"{committed_path} not present -- run make sweep first")
    committed = json.loads(committed_path.read_text())

    sim = RetailSimulation("data/open_retail_daily.csv")
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    fresh = run_seed(sim, dq_spec, sarc_spec, green_engines, 1028331701)

    assert _canonical(fresh) == _canonical(committed)
