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
CH5 (prereg/hypotheses.md, prereg/weights.json): the weighted-score
compensatory aggregator, compared against the min-join composed result
already present on each Evidence Set line.

Decision rule (prereg/hypotheses.md, verbatim): "over the declared weight
grid, there exists at least one weight vector whose weighted-score
aggregator admits at least one decision that a member gate held, while
the min join admits zero such decisions." The min join admits zero of a
"held" decision by construction (held means final.admitted is False), so
this reduces to: does any (weight_vector, threshold) cell in the
pre-registered grid have at least one held decision whose weighted score
reaches the threshold?

SEED = 26313
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

GATES = ("dq", "sarc", "green")


def load_weights(path: str = "prereg/weights.json") -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def weighted_score(
    line: Dict[str, Any], weight_vector: Dict[str, float], score_encoding: Dict[str, float]
) -> float:
    return sum(
        weight_vector[gate] * score_encoding[line["gates"][gate]["verdict"]] for gate in GATES
    )


def evaluate_ch5(lines: List[Dict[str, Any]], weights_spec: Dict[str, Any]) -> Dict[str, Any]:
    """lines: Evidence Set lines (any scenario/mode mix the caller chooses
    to pool — the harness itself is scenario-agnostic).

    Returns the full violation-count surface over the pre-registered grid
    plus max_violations, whose value >= 1 IS CH5's registered decision
    rule (ch5_supported).
    """
    score_encoding = weights_spec["score_encoding"]
    thresholds = weights_spec["thresholds"]
    weight_vectors = weights_spec["weight_vectors"]

    held_lines = [line for line in lines if not line["final"]["admitted"]]
    held_scores = [
        {gate: score_encoding[line["gates"][gate]["verdict"]] for gate in GATES}
        for line in held_lines
    ]

    surface: List[Dict[str, Any]] = []
    max_violations = 0
    max_cell: Dict[str, Any] = {}
    for wv in weight_vectors:
        scores = [sum(wv[gate] * s[gate] for gate in GATES) for s in held_scores]
        for threshold in thresholds:
            violations = sum(1 for s in scores if s >= threshold)
            cell = {"weights": wv, "threshold": threshold, "violations": violations}
            surface.append(cell)
            if violations > max_violations:
                max_violations = violations
                max_cell = cell

    return {
        "decisions": len(lines),
        "held_decisions": len(held_lines),
        "max_violations": max_violations,
        "max_violation_cell": max_cell,
        "ch5_supported": max_violations >= 1,
        "surface": surface,
    }
