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
Phase 4 / V2 gate: exhaustive check of Proposition 1 / CH5 ("compensation
admits vetoed actions") over CH5's discrete encoding (prereg/weights.json),
rather than only the empirical sample ch5_aggregator.py checks against
whatever decisions the simulation happened to produce.

Proposition 1 (paper4-composition-draft-v0.1.md, Section 3): a strictly
increasing aggregator f with f(s) >= tau admissible violates veto -- there
exists a held profile (some s_j = 0) with f(s) >= tau. CH5's decision rule
restates this over the artifact's own three-gate, five-response,
pre-registered weight/threshold grid: does any (weight_vector, threshold)
pair admit at least one profile the min join holds?

The discrete state space is exactly the 5x5x5 = 125 per-gate verdict
combinations (composition.Response over dq/sarc/green), scored via
weights.json's score_encoding. This is small enough to enumerate
completely: this checker is the exhaustive, machine-checked counterpart
to ch5_aggregator.py's empirical (sample-dependent) harness -- it proves
the existence claim over the FULL discrete space, not just whatever
verdicts a given run's seed happened to produce.

SEED = 26313 (not used here -- this checker is exhaustive, not sampled)
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Dict, List

from composition import Response, compute_restrictiveness_join, is_executed

GATES = ("dq", "sarc", "green")
OUT_PATH = Path("out/checkers/compensation_check.json")


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
    what counts as "held"."""
    held = []
    for combo in itertools.product(list(Response), repeat=3):
        joined = compute_restrictiveness_join(list(combo))
        if not is_executed(joined):
            held.append({gate: _response_name(v) for gate, v in zip(GATES, combo)})
    return held


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
        scores = [sum(wv[gate] * s[gate] for gate in GATES) for s in held_scores]
        for threshold in thresholds:
            surface_size += 1
            violating = [p for p, s in zip(held_profiles, scores) if s >= threshold]
            if len(violating) > max_violations:
                max_violations = len(violating)
                max_cell = {"weights": wv, "threshold": threshold}
                witness_profile = violating[0]

    result = {
        "discrete_state_space_size": len(list(Response)) ** 3,
        "held_profiles_count": len(held_profiles),
        "grid_cells_checked": surface_size,
        "max_violations": max_violations,
        "max_violation_cell": max_cell,
        "witness_profile": witness_profile,
        "proposition_1_holds_exhaustively": max_violations >= 1,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
