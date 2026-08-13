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
Canonical generator for prereg/weights.json (the CH5 grid). Run ONCE; the
output is frozen and committed.

Weight vectors: every (w_dq, w_sarc, w_green) on the 3-simplex with step
0.1 — i.e. every (a, b, c) of non-negative integers with a + b + c = 10,
weight = (a/10, b/10, c/10). There are C(12, 2) = 66 such vectors.

Score encoding (per gate response): admit=1.0, substitute=0.75,
degrade=0.5, escalate=0.25, block=0.0.

Thresholds: tau in {0.5, 0.6, 0.7, 0.8}. The weighted aggregator admits a
decision iff sum_i w_i * score_i >= tau.
"""
import json

STEP_DENOMINATOR = 10
SCORE_ENCODING = {
    "admit": 1.0,
    "substitute": 0.75,
    "degrade": 0.5,
    "escalate": 0.25,
    "block": 0.0,
}
THRESHOLDS = [0.5, 0.6, 0.7, 0.8]
GATES = ["dq", "sarc", "green"]


def generate_weight_vectors():
    vectors = []
    for a in range(STEP_DENOMINATOR + 1):
        for b in range(STEP_DENOMINATOR + 1 - a):
            c = STEP_DENOMINATOR - a - b
            vectors.append({
                "dq": a / STEP_DENOMINATOR,
                "sarc": b / STEP_DENOMINATOR,
                "green": c / STEP_DENOMINATOR,
            })
    return vectors


if __name__ == "__main__":
    vectors = generate_weight_vectors()
    assert len(vectors) == 66, f"expected 66 simplex points, got {len(vectors)}"
    for v in vectors:
        assert abs(sum(v.values()) - 1.0) < 1e-9
    out = {
        "step": 1.0 / STEP_DENOMINATOR,
        "gates": GATES,
        "score_encoding": SCORE_ENCODING,
        "thresholds": THRESHOLDS,
        "weight_vectors": vectors,
    }
    print(json.dumps(out, indent=2))
