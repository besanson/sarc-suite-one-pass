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
Phase 4 / V2 gate: exhaustive check of the compensation lemma / CH5
("compensation admits vetoed actions") over CH5's discrete encoding
(prereg/weights.json), rather than only the empirical sample
ch5_aggregator.py checks against whatever decisions the simulation
happened to produce.

Restated per independent review finding F1 (review/REVIEW.md): the
original Proposition 1 claimed a universal continuous-domain veto
theorem for any strictly increasing aggregator, which the review refuted
with a concrete counterexample (f(s)=s1+s2+s3, tau=2.5: admissible but
veto-preserving). appendix-a-proofs.md now states the precise linear-
family lemma this checker verifies: for f(s) = sum_i w_i s_i with
w_i >= 0, a vetoed profile is admitted by f iff tau <= L*, where
L* = W - min_i(w_i) is the largest "leave-one-out" weight sum. This
checker verifies that characterization against brute-force ground truth
-- not just the discrete grid's existence claim, the Lemma's exact
threshold condition -- over the declared 66x4 grid plus 200 HEAD-derived
random positive-weight vectors (same methodology the independent review
used for its own off-grid probes).

The discrete state space is exactly the 5x5x5 = 125 per-gate verdict
combinations (composition.Response over dq/sarc/green), scored via
weights.json's score_encoding. This is small enough to enumerate
completely: this checker is the exhaustive, machine-checked counterpart
to ch5_aggregator.py's empirical (sample-dependent) harness -- it proves
the existence claim over the FULL discrete space, not just whatever
verdicts a given run's seed happened to produce.

SEED = 26313 (not used here -- this checker is exhaustive/HEAD-derived,
not seeded from the registered seed list)
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

from checkers._provenance import head_sha, inputs_hash
from composition import Response, compute_restrictiveness_join, is_executed

GATES = ("dq", "sarc", "green")
OUT_PATH = Path("out/checkers/compensation_check.json")
N_RANDOM_PROBES = 200

# Round-three response (finding R3-F1): this checker's own generating
# inputs. prereg/weights.json is the declared grid/score_encoding this
# checker actually reads (load_weights); prereg/probe-seeds.json and
# engines.lock are included uniformly across every checker's stamp (see
# checkers/_provenance.py's inputs_hash docstring), even though neither
# is this checker's own random-probe seed source -- that source is
# deliberately HEAD-derived (random_positive_weight_vectors), an
# existing, unchanged-by-round-three methodological choice, and
# inputs_hash intentionally does NOT include HEAD, so a fresh commit
# that touches none of these files stays "fresh" even though the
# checker's own probe vectors would differ if actually rerun.
INPUT_FILES = [
    Path("checkers/compensation_check.py"),
    Path("checkers/_provenance.py"),
    Path("composition.py"),
    Path("prereg/weights.json"),
    Path("prereg/probe-seeds.json"),
    Path("engines.lock"),
]


def load_weights(path: str = "prereg/weights.json") -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def _response_name(r: Response) -> str:
    return r.name.lower()


def all_held_profiles() -> List[Dict[str, str]]:
    """Every one of the 125 (dq, sarc, green) verdict combinations whose
    min-join composed response is Held under Definition 3's Exec/Held
    partition ({escalate, block}, via composition.is_executed) -- the
    same boundary ch5_aggregator.py's empirical harness uses
    (final.admitted), so the exhaustive and empirical CH5 checks agree on
    what counts as "held". This is CH5's own population (unchanged by
    the F1 restatement) -- max_violations / proposition_1_holds_exhaustively
    below are computed over this set, as they always have been.
    """
    held = []
    for combo in itertools.product(list(Response), repeat=3):
        joined = compute_restrictiveness_join(list(combo))
        if not is_executed(joined):
            held.append({gate: _response_name(v) for gate, v in zip(GATES, combo)})
    return held


def all_vetoed_profiles() -> List[Dict[str, str]]:
    """Every profile with at least one gate scored EXACTLY 0 under
    score_encoding -- i.e. at least one "block" verdict. This is the
    Lemma's own "vetoed" population (s_j = 0 for some j), which is a
    STRICT SUBSET of all_held_profiles(): score_encoding gives "escalate"
    a nonzero score (0.25), so an escalate-only-held profile is Held
    under Definition 3 but is NOT "vetoed" in the Lemma's s_j=0 sense --
    conflating the two was exactly the bug this checker's own random
    probes caught during the review response (an escalate-containing
    profile can clear a threshold the Lemma's L* would predict it
    couldn't, because escalate contributes 0.25 * w_j, not 0). The Lemma
    is verified against this population, not all_held_profiles().
    """
    vetoed = []
    for combo in itertools.product(list(Response), repeat=3):
        names = [_response_name(v) for v in combo]
        if "block" in names:
            vetoed.append(dict(zip(GATES, names)))
    return vetoed


def leave_one_out_max(weight_vector: Dict[str, float]) -> float:
    """L* = max_j (sum_{i != j} w_i) = W - min_i(w_i): the largest score
    the linear aggregator can assign to any profile holding one
    coordinate at 0 -- the exact threshold appendix-a-proofs.md's Lemma
    (linear family) is stated around."""
    total = sum(weight_vector[g] for g in GATES)
    return total - min(weight_vector[g] for g in GATES)


def lemma_predicts_compensation(weight_vector: Dict[str, float], threshold: float) -> bool:
    return threshold <= leave_one_out_max(weight_vector)


def _violations(weight_vector: Dict[str, float], threshold: float, held_profiles, held_scores) -> Tuple[int, Dict[str, Any]]:
    scores = [sum(weight_vector[g] * s[g] for g in GATES) for s in held_scores]
    violating = [p for p, s in zip(held_profiles, scores) if s >= threshold]
    witness = violating[0] if violating else {}
    return len(violating), witness


def random_positive_weight_vectors(n: int, seed_material: str) -> List[Dict[str, float]]:
    """n vectors on the 3-gate simplex (weights > 0, sum to 1), sampled
    uniformly via normalized exponentials (a standard Dirichlet(1,1,1)
    construction), deterministically seeded from seed_material -- HEAD's
    commit sha by default, so a re-run at the same commit reproduces the
    identical probe set, and a new commit draws a fresh one, matching the
    independent review's own "HEAD-derived" probe methodology."""
    seed_int = int(hashlib.sha256(seed_material.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed_int)
    vectors = []
    for _ in range(n):
        # exponential(1) draws normalized to sum 1 are uniform over the
        # simplex; -log(uniform) is the standard inverse-CDF exponential
        # sampler. random() draws from [0, 1), so guard the (probability
        # zero, but not impossible) exact-0.0 draw to keep every weight
        # strictly positive.
        draws = [-math.log(rng.random() or 1e-300) for _ in GATES]
        total = sum(draws)
        vectors.append({g: d / total for g, d in zip(GATES, draws)})
    return vectors


def verify_lemma(
    weight_vectors: List[Dict[str, float]], thresholds: List[float], held_profiles, held_scores, label: str
) -> Dict[str, Any]:
    checked = 0
    mismatches: List[Dict[str, Any]] = []
    for wv in weight_vectors:
        for threshold in thresholds:
            checked += 1
            actual_count, _ = _violations(wv, threshold, held_profiles, held_scores)
            actual_compensated = actual_count >= 1
            predicted = lemma_predicts_compensation(wv, threshold)
            if actual_compensated != predicted:
                mismatches.append(
                    {"weights": wv, "threshold": threshold, "predicted": predicted, "actual_compensated": actual_compensated}
                )
    return {"label": label, "checked": checked, "mismatches": mismatches, "all_agree": not mismatches}


def run(weights_path: str = "prereg/weights.json") -> Dict[str, Any]:
    weights_spec = load_weights(weights_path)
    score_encoding = weights_spec["score_encoding"]
    thresholds = weights_spec["thresholds"]
    weight_vectors = weights_spec["weight_vectors"]

    held_profiles = all_held_profiles()
    held_scores = [{gate: score_encoding[verdict] for gate, verdict in profile.items()} for profile in held_profiles]

    max_violations = 0
    max_cell: Dict[str, Any] = {}
    witness_profile: Dict[str, Any] = {}
    surface_size = 0
    for wv in weight_vectors:
        for threshold in thresholds:
            surface_size += 1
            count, witness = _violations(wv, threshold, held_profiles, held_scores)
            if count > max_violations:
                max_violations = count
                max_cell = {"weights": wv, "threshold": threshold}
                witness_profile = witness

    # The Lemma's own population: profiles with s_j = 0 (a "block"
    # verdict), a strict subset of held_profiles -- see
    # all_vetoed_profiles()'s docstring.
    vetoed_profiles = all_vetoed_profiles()
    vetoed_scores = [{gate: score_encoding[verdict] for gate, verdict in profile.items()} for profile in vetoed_profiles]

    sha = head_sha()
    random_vectors = random_positive_weight_vectors(N_RANDOM_PROBES, sha)
    grid_lemma_check = verify_lemma(weight_vectors, thresholds, vetoed_profiles, vetoed_scores, "declared_grid")
    probe_lemma_check = verify_lemma(random_vectors, thresholds, vetoed_profiles, vetoed_scores, "head_derived_random_probe")

    result = {
        "discrete_state_space_size": len(list(Response)) ** 3,
        "held_profiles_count": len(held_profiles),
        "grid_cells_checked": surface_size,
        "max_violations": max_violations,
        "max_violation_cell": max_cell,
        "witness_profile": witness_profile,
        "proposition_1_holds_exhaustively": max_violations >= 1,
        "generated_at_head_sha": sha,
        "inputs_hash": inputs_hash(INPUT_FILES),
        "lemma_verification": {
            "head_sha": sha,
            "vetoed_profiles_count": len(vetoed_profiles),
            "n_random_probes": N_RANDOM_PROBES,
            "declared_grid": grid_lemma_check,
            "head_derived_random_probe": probe_lemma_check,
            "total_checked": grid_lemma_check["checked"] + probe_lemma_check["checked"],
            "lemma_holds_on_all_checked_cases": grid_lemma_check["all_agree"] and probe_lemma_check["all_agree"],
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
