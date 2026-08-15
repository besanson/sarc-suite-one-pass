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
Phase 4 / V2 gate tests: the three exhaustive checkers actually verify
what they claim to, and their registered verdicts are exercised here so a
future code change that silently breaks a law is caught by the test
suite, not just by re-running the checker by hand.

SEED = 26313
"""
from __future__ import annotations

from checkers import compensation_check, lattice_check, remediator_check
from composition import Response, compute_restrictiveness_join


# ---------------------------------------------------------------------------
# lattice_check
# ---------------------------------------------------------------------------


def test_lattice_all_laws_hold():
    result = lattice_check.run()
    assert result["all_hold"] is True
    for law in result["laws"]:
        assert law["holds"] is True, law


def test_lattice_check_idempotence_catches_a_broken_join():
    # Sanity check on the checker itself: a join that is NOT idempotent
    # must be caught, not silently reported as holding.
    def broken_join(responses):
        # always returns BLOCK regardless of input -- not idempotent for
        # any response other than BLOCK itself.
        return Response.BLOCK

    real_join = lattice_check.compute_restrictiveness_join
    lattice_check.compute_restrictiveness_join = broken_join
    try:
        result = lattice_check.check_idempotence()
    finally:
        lattice_check.compute_restrictiveness_join = real_join
    assert result["holds"] is False
    assert result["counterexample"]["response"] == "ADMIT"


def test_lattice_check_writes_output_file(tmp_path, monkeypatch):
    out = tmp_path / "lattice_check.json"
    monkeypatch.setattr(lattice_check, "OUT_PATH", out)
    lattice_check.run()
    assert out.exists()


# ---------------------------------------------------------------------------
# compensation_check
# ---------------------------------------------------------------------------


def test_compensation_check_held_profiles_use_the_paper_exec_held_partition():
    held = compensation_check.all_held_profiles()
    # Every held profile's join must be escalate or block (Definition 3),
    # never admit/substitute/degrade.
    for profile in held:
        joined = compute_restrictiveness_join([Response[p.upper()] for p in profile.values()])
        assert joined in (Response.ESCALATE, Response.BLOCK)


def test_compensation_check_proposition_1_holds_exhaustively():
    result = compensation_check.run()
    assert result["proposition_1_holds_exhaustively"] is True
    assert result["max_violations"] >= 1
    assert result["held_profiles_count"] > 0
    # The witness must genuinely be a held profile compensated by weight.
    witness = result["witness_profile"]
    joined = compute_restrictiveness_join([Response[witness[g].upper()] for g in ("dq", "sarc", "green")])
    assert joined in (Response.ESCALATE, Response.BLOCK)


def test_all_vetoed_profiles_is_strict_subset_of_all_held_profiles():
    """The Lemma's "vetoed" (s_j=0, i.e. a block verdict) is narrower
    than CH5's own "Held" (escalate-or-block) -- conflating the two was
    the bug the random probe caught during the review response."""
    vetoed = compensation_check.all_vetoed_profiles()
    held = compensation_check.all_held_profiles()
    assert len(vetoed) == 61
    assert len(held) == 98
    vetoed_set = {tuple(sorted(p.items())) for p in vetoed}
    held_set = {tuple(sorted(p.items())) for p in held}
    assert vetoed_set < held_set  # strict subset


def test_all_vetoed_profiles_always_contain_a_block():
    for profile in compensation_check.all_vetoed_profiles():
        assert "block" in profile.values()


def test_leave_one_out_max_matches_reviewer_counterexample():
    # w=(1,1,1): L* = 3 - 1 = 2, exactly the boundary the reviewer's
    # tau=2.5 sits above (no vetoed profile admitted).
    wv = {"dq": 1.0, "sarc": 1.0, "green": 1.0}
    assert compensation_check.leave_one_out_max(wv) == 2.0
    assert compensation_check.lemma_predicts_compensation(wv, 2.5) is False
    assert compensation_check.lemma_predicts_compensation(wv, 2.0) is True


def test_lemma_verification_agrees_on_declared_grid_and_random_probe():
    result = compensation_check.run()
    lv = result["lemma_verification"]
    assert lv["declared_grid"]["all_agree"] is True
    assert lv["head_derived_random_probe"]["all_agree"] is True
    assert lv["lemma_holds_on_all_checked_cases"] is True
    assert lv["n_random_probes"] == 200
    assert lv["total_checked"] == 264 + 200 * 4


def test_random_positive_weight_vectors_are_deterministic_and_strictly_positive():
    vectors_a = compensation_check.random_positive_weight_vectors(50, "fixed-seed-material")
    vectors_b = compensation_check.random_positive_weight_vectors(50, "fixed-seed-material")
    assert vectors_a == vectors_b  # same seed material -> identical draws
    for v in vectors_a:
        assert all(w > 0 for w in v.values())
        assert abs(sum(v.values()) - 1.0) < 1e-9

    vectors_c = compensation_check.random_positive_weight_vectors(50, "different-seed-material")
    assert vectors_a != vectors_c  # different seed material -> different draws


def test_compensation_check_pure_green_weight_never_compensates_a_green_block():
    """A weight vector putting all weight on the SAME gate that vetoed can
    never compensate a block from that gate -- block scores exactly 0
    under the score encoding, and 0 clears no positive threshold. (An
    escalate veto scores 0.25, so it CAN clear the lowest registered
    threshold under pure self-weight -- that is a real, distinct
    violation, not a bug in this claim.)"""
    weights_spec = compensation_check.load_weights()
    held = compensation_check.all_held_profiles()
    green_blocks = [p for p in held if p["green"] == "block"]
    assert green_blocks  # sanity: such profiles exist
    score_encoding = weights_spec["score_encoding"]
    for profile in green_blocks:
        score = sum(
            {"dq": 0.0, "sarc": 0.0, "green": 1.0}[gate] * score_encoding[verdict]
            for gate, verdict in profile.items()
        )
        assert score == 0.0


# ---------------------------------------------------------------------------
# remediator_check (CH7)
# ---------------------------------------------------------------------------


def test_remediator_check_runs_and_reports_a_verdict():
    result = remediator_check.run()
    assert result["ch7_registered_outcome"] in ("confluent", "non_confluent")
    assert result["grid_points_checked"] > 0


def test_remediator_check_non_confluent_counterexample_is_reproducible():
    """This artifact's remediators are expected to be non-confluent (the
    downroute budget check depends on whichever unit cost is current at
    the time it runs) -- verify the checker's own sample counterexample
    actually reproduces under direct re-computation, not just trust the
    checker's self-report."""
    result = remediator_check.run()
    assert result["confluent"] is False
    ce = result["sample_counterexample"]
    a = remediator_check._order_a_substitute_then_downroute(
        ce["qty"], ce["corrupted_unit_cost"], ce["governed_unit_cost"], ce["cost_budget"], ce["carbon_budget"],
    )
    b = remediator_check._order_b_downroute_then_substitute(
        ce["qty"], ce["corrupted_unit_cost"], ce["governed_unit_cost"], ce["cost_budget"], ce["carbon_budget"],
    )
    assert not remediator_check._close(a.proposed_qty, b.proposed_qty) or not remediator_check._close(
        a.order_value, b.order_value
    )


def test_remediator_check_agreeing_orders_are_not_flagged():
    """When corrupted and governed costs are equal, substitution is a
    no-op, so both orders must trivially agree -- confirms the checker
    doesn't over-report false counterexamples."""
    a = remediator_check._order_a_substitute_then_downroute(100.0, 10.0, 10.0, 1e12, 1e12)
    b = remediator_check._order_b_downroute_then_substitute(100.0, 10.0, 10.0, 1e12, 1e12)
    assert remediator_check._close(a.proposed_qty, b.proposed_qty)
    assert remediator_check._close(a.order_value, b.order_value)


# ---------------------------------------------------------------------------
# remediator_check off-grid probe (promoted per independent review, CH7)
# ---------------------------------------------------------------------------


def test_random_off_grid_points_are_deterministic_and_strictly_off_grid():
    """Same seed must give the same points (reproducibility), and no
    point may land exactly on a declared grid coordinate (that would
    make it a grid point, not an off-grid probe). Seeding is now a
    fixed declared int (prereg/probe-seeds.json), not HEAD-derived --
    round-two review finding R2-N1/R2-F1(b)."""
    points_a = remediator_check.random_off_grid_points(50, 26313)
    points_b = remediator_check.random_off_grid_points(50, 26313)
    assert points_a == points_b
    for p in points_a:
        assert p["qty"] not in remediator_check.QTY_GRID
        assert p["corrupted_unit_cost"] not in remediator_check.CORRUPTED_COST_GRID
        assert p["governed_unit_cost"] not in remediator_check.GOVERNED_COST_GRID


def test_random_off_grid_points_differ_across_seeds():
    points_a = remediator_check.random_off_grid_points(20, 1)
    points_b = remediator_check.random_off_grid_points(20, 2)
    assert points_a != points_b


def test_off_grid_probe_reports_a_non_confluent_count():
    """This artifact's remediators are already known non-confluent on the
    declared grid (86/243) -- the off-grid probe is expected to also find
    non-confluent points, strengthening CH7 per the independent review's
    own finding (review/REVIEW.md: 144/200 HEAD-derived off-grid points
    non-confluent)."""
    spec = remediator_check.load_off_grid_probe_spec()
    points = remediator_check.random_off_grid_points(spec["n_probes"], spec["seed"])
    probe = remediator_check._off_grid_probe(points)
    assert probe["n_probes"] == spec["n_probes"]
    assert probe["non_confluent_count"] > 0
    assert probe["confluent_count"] + probe["non_confluent_count"] == spec["n_probes"]


def test_remediator_check_run_includes_off_grid_probe_block():
    result = remediator_check.run()
    off_grid = result["off_grid_probe"]
    spec = remediator_check.load_off_grid_probe_spec()
    assert off_grid["n_probes"] == spec["n_probes"]
    assert off_grid["seed"] == spec["seed"]
    assert off_grid["non_confluent_count"] >= 0
    assert "generated_at_head_sha" in result
