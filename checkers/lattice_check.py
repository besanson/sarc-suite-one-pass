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
Phase 4 / V2 gate: exhaustive check of the join-semilattice laws
(Definition 1/2, Proposition 2 in paper4-composition-draft-v0.1.md) over
the real composed response lattice `composition.Response`.

`compute_restrictiveness_join` is the real join used by every scenario
run in this artifact -- this module does not reimplement it, it exhausts
it. Laws checked, for every tuple length k = 1..4 (k=4 already exceeds
the 3 real gates in this artifact, so k<=3 is fully realistic and k=4 is
margin):

- idempotence: join(r, r, ..., r) == r
- commutativity: join is invariant under any permutation of its inputs
- associativity: join(join(a, b), c) == join(a, join(b, c))
- monotone hardening: adding an extra response to a tuple never makes the
  join more permissive (Proposition 2's "adding a gate never increases
  permissiveness")
- duplication invariance: repeating a response already in the tuple
  never changes the join (the artifact's duplication-invariance claim)

|Response| = 5, so exhaustive coverage over k in {1,2,3,4} is
5 + 25 + 125 + 625 = 780 tuples plus the derived checks below -- small
enough to brute force completely rather than sample.

SEED = 26313 (not used here -- this checker is exhaustive, not sampled)
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Dict, List

from checkers._provenance import head_sha
from composition import Response, compute_restrictiveness_join

MAX_K = 4
OUT_PATH = Path("out/checkers/lattice_check.json")


def _all_tuples(k: int):
    return itertools.product(list(Response), repeat=k)


def check_idempotence() -> Dict[str, Any]:
    checked = 0
    for r in Response:
        for k in range(1, MAX_K + 1):
            checked += 1
            joined = compute_restrictiveness_join([r] * k)
            if joined != r:
                return {"law": "idempotence", "holds": False, "checked": checked,
                        "counterexample": {"response": r.name, "k": k, "joined": joined.name}}
    return {"law": "idempotence", "holds": True, "checked": checked}


def check_commutativity() -> Dict[str, Any]:
    checked = 0
    for k in range(2, MAX_K + 1):
        for tup in _all_tuples(k):
            baseline = compute_restrictiveness_join(list(tup))
            for perm in itertools.permutations(tup):
                checked += 1
                if compute_restrictiveness_join(list(perm)) != baseline:
                    return {"law": "commutativity", "holds": False, "checked": checked,
                            "counterexample": {"tuple": [r.name for r in tup], "perm": [r.name for r in perm]}}
    return {"law": "commutativity", "holds": True, "checked": checked}


def check_associativity() -> Dict[str, Any]:
    checked = 0
    for a, b, c in _all_tuples(3):
        checked += 1
        left = compute_restrictiveness_join([compute_restrictiveness_join([a, b]), c])
        right = compute_restrictiveness_join([a, compute_restrictiveness_join([b, c])])
        if left != right:
            return {"law": "associativity", "holds": False, "checked": checked,
                     "counterexample": {"a": a.name, "b": b.name, "c": c.name, "left": left.name, "right": right.name}}
    return {"law": "associativity", "holds": True, "checked": checked}


def check_monotone_hardening() -> Dict[str, Any]:
    """Proposition 2: adding a response to a tuple never decreases the
    join (never makes the composed verdict more permissive)."""
    checked = 0
    for k in range(1, MAX_K):
        for tup in _all_tuples(k):
            before = compute_restrictiveness_join(list(tup))
            for extra in Response:
                checked += 1
                after = compute_restrictiveness_join(list(tup) + [extra])
                if after < before:
                    return {"law": "monotone_hardening", "holds": False, "checked": checked,
                             "counterexample": {"tuple": [r.name for r in tup], "extra": extra.name,
                                                 "before": before.name, "after": after.name}}
    return {"law": "monotone_hardening", "holds": True, "checked": checked}


def check_duplication_invariance() -> Dict[str, Any]:
    checked = 0
    for k in range(1, MAX_K):
        for tup in _all_tuples(k):
            baseline = compute_restrictiveness_join(list(tup))
            for dup in tup:
                checked += 1
                with_dup = compute_restrictiveness_join(list(tup) + [dup])
                if with_dup != baseline:
                    return {"law": "duplication_invariance", "holds": False, "checked": checked,
                             "counterexample": {"tuple": [r.name for r in tup], "dup": dup.name}}
    return {"law": "duplication_invariance", "holds": True, "checked": checked}


def check_empty_is_admit() -> Dict[str, Any]:
    joined = compute_restrictiveness_join([])
    return {"law": "empty_join_is_admit", "holds": joined == Response.ADMIT, "checked": 1}


LAWS = [
    check_idempotence,
    check_commutativity,
    check_associativity,
    check_monotone_hardening,
    check_duplication_invariance,
    check_empty_is_admit,
]


def run() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = [law() for law in LAWS]
    result = {
        "max_k": MAX_K,
        "response_count": len(list(Response)),
        "laws": results,
        "all_hold": all(r["holds"] for r in results),
        "total_checks": sum(r["checked"] for r in results),
        "generated_at_head_sha": head_sha(),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
