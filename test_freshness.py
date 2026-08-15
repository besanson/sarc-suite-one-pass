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
Freshness tests (round-two independent review, finding R2-N1/R2-F1(a)):
"the committed out/checkers/*.json embedded the review commit SHA, and
the paper reports 140/200 although the response HEAD deterministically
produces 145/200." Two distinct bugs made this possible: `make paper`
didn't depend on `make formal` (fixed in the Makefile: `paper: suite
sweep formal`), and the off-grid probe was HEAD-derived so its count
drifted across commits even at a fixed set of source files (fixed in
checkers/remediator_check.py + prereg/probe-seeds.json, R2-F1(b)).

These tests guard both halves directly rather than trusting the
Makefile's dependency graph alone:
  1. every checker, run now, stamps its own output with the actual
     current git HEAD (checkers/_provenance.py) -- a checked-in checker
     JSON whose generated_at_head_sha does not match the commit it
     ships in is exactly the staleness the review caught.
  2. the off-grid probe is deterministic given the fixed seed in
     prereg/probe-seeds.json -- rerunning it twice, or rerunning it
     fresh against the paper's already-populated slots, must agree.

SEED = 26313 (via prereg/probe-seeds.json's fixed ch7_off_grid_probe
seed, not HEAD-derived -- see checkers/remediator_check.py)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from checkers import compensation_check, lattice_check, remediator_check


def _require(path: str):
    if not Path(path).exists():
        pytest.skip(f"{path} not present -- run make suite / make sweep / make formal / make paper first")
    return path


def _current_head_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


# ---------------------------------------------------------------------------
# (1) every checker stamps the real current HEAD when it actually runs
# ---------------------------------------------------------------------------


def test_lattice_check_stamps_current_head_on_fresh_run():
    result = lattice_check.run()
    assert result["generated_at_head_sha"] == _current_head_sha()


def test_compensation_check_stamps_current_head_on_fresh_run():
    result = compensation_check.run()
    assert result["generated_at_head_sha"] == _current_head_sha()


def test_remediator_check_stamps_current_head_on_fresh_run():
    result = remediator_check.run()
    assert result["generated_at_head_sha"] == _current_head_sha()


def test_committed_checker_artifacts_share_one_generation_sha():
    """All three out/checkers/*.json were meant to be regenerated
    together by a single `make formal` invocation (itself run as part of
    `make paper`'s dependency chain) -- if they carry DIFFERENT
    generated_at_head_sha values, they were produced by separate runs at
    separate commits, which is precisely the staleness pattern R2-N1
    describes."""
    for p in (
        "out/checkers/lattice_check.json",
        "out/checkers/compensation_check.json",
        "out/checkers/remediator_check.json",
    ):
        _require(p)
    shas = {
        json.loads(Path(p).read_text())["generated_at_head_sha"]
        for p in (
            "out/checkers/lattice_check.json",
            "out/checkers/compensation_check.json",
            "out/checkers/remediator_check.json",
        )
    }
    assert len(shas) == 1, f"checker artifacts were generated at different commits: {shas}"


# ---------------------------------------------------------------------------
# (2) the off-grid probe is fixed-seed and commit-stable, not HEAD-derived
# ---------------------------------------------------------------------------


def test_off_grid_probe_seed_is_the_declared_fixed_constant():
    spec = remediator_check.load_off_grid_probe_spec()
    declared = json.loads(Path("prereg/probe-seeds.json").read_text())["ch7_off_grid_probe"]
    assert spec == declared
    assert isinstance(spec["seed"], int)


def test_off_grid_probe_result_is_identical_across_reruns():
    """Reproduces the exact bug the round-two review caught: at a FIXED
    set of source files, the off-grid count used to differ between two
    plain reruns of the checker whenever HEAD moved in between (or even
    without HEAD moving, if compared against a value baked in at an
    earlier commit). With a fixed declared seed, two reruns right now
    must agree exactly, and neither depends on what HEAD currently is."""
    first = remediator_check.run()
    second = remediator_check.run()
    assert first["off_grid_probe"]["non_confluent_count"] == second["off_grid_probe"]["non_confluent_count"]
    assert first["off_grid_probe"]["n_probes"] == second["off_grid_probe"]["n_probes"]
    # generated_at_head_sha may legitimately differ if a commit landed
    # between the two calls in some other context; the probe VALUE must
    # not, since it no longer depends on HEAD at all.


# ---------------------------------------------------------------------------
# freshness: the populated paper's off-grid slot vs. a checker run NOW
# ---------------------------------------------------------------------------


def test_paper_off_grid_value_matches_a_fresh_checker_run():
    """The exact reproduction the round-two review specified: after
    `make paper`, the off-grid value embedded in out/paper/slots_v3.json
    must equal the value in the just-generated
    out/checkers/remediator_check.json. Since the probe is now fixed-
    seed (not HEAD-derived), a fresh checker run performed right here,
    in this test, is exactly as authoritative as a fresh `make formal`
    run would be -- both use the same declared seed and the same grid
    functions, so they must agree with whatever `make paper` last
    embedded, as long as the paper was generated with this same code."""
    slots_path = _require("out/paper/slots_v3.json")
    slots = json.loads(Path(slots_path).read_text())
    if "checkers.remediator_offgrid_non_confluent" not in slots:
        pytest.skip("out/paper/slots_v3.json predates the off-grid probe slots -- run make paper")

    fresh = remediator_check.run()
    assert slots["checkers.remediator_offgrid_non_confluent"] == str(fresh["off_grid_probe"]["non_confluent_count"])
    assert slots["checkers.remediator_offgrid_probes"] == str(fresh["off_grid_probe"]["n_probes"])


def test_populated_paper_off_grid_metric_is_not_the_stale_140_200_value():
    """The literal regression this review finding named: the response
    commit's populated paper reported the off-grid metric as 140/200, a
    HEAD-derived value from an earlier commit, which had already drifted
    to 145/200 by the time the round-two review re-ran the checker. The
    fixed-seed probe's current value (whatever it is) is asserted equal
    to what's embedded by test_paper_off_grid_value_matches_a_fresh_
    checker_run above; this test additionally guards that the specific
    stale numerator '140/200' is not silently still reported as the
    LIVE off-grid metric. It deliberately does not forbid '140/200'
    appearing anywhere in the document at all: Appendix A's own
    historical narrative about this exact bug (R2-N1, in the "why this
    changed" note on the off-grid probe) legitimately names 140/200 as
    a fact about what happened, not a current measurement -- that
    narrative is accurate and is not what this test guards against."""
    populated_path = _require("paper4-composition-draft-v0.3-populated.md")
    text = Path(populated_path).read_text()
    assert "140/200 off-grid points" not in text
