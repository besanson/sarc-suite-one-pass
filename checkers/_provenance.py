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
Shared provenance helpers for checkers/.

`head_sha()` (round-two independent review, finding R2-N1/R2-F1(a)):
every checker's output JSON is stamped with the git HEAD commit at
generation time, under the key "generated_at_head_sha". This remains an
informational stamp -- useful for a human skimming a JSON file -- but as
of round three it is no longer what freshness is defined by (see
`inputs_hash` below): a HEAD-based check flags every "publication-only"
commit (README edits, unrelated files, this very docstring) as staleness
even when nothing the checker actually reads has changed, which is
exactly the round-three finding R3-F1 caught (the response commit's
formal artifacts legitimately carried an earlier HEAD because no
generating input had changed since).

`inputs_hash()` (round-three independent review, finding R3-F1): a
sha256 over the literal bytes of the checker's own declared generating
inputs -- its source module(s), any config file it reads, and the
repository-wide `prereg/probe-seeds.json` and `engines.lock` every
checker's stamp includes uniformly per the round-three response's own
fix design, even for a checker (lattice_check.py) that does not read
either file today: if either ever starts mattering to a checker's
result, every checker's freshness stamp already covers it, rather than
only the checker where the review happened to notice.
FRESHNESS IS DEFINED BY inputs_hash, not generated_at_head_sha: a
checker artifact is fresh if and only if recomputing inputs_hash from
the CURRENT tree reproduces the hash the committed artifact already
carries -- see test_freshness.py. This is testable at any commit,
including ones that never touched a checker's inputs at all, and is
exactly the property generated_at_head_sha alone could not express.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Iterable


def head_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def inputs_hash(paths: Iterable[Path]) -> str:
    """sha256 over the literal bytes of every path in `paths`, each
    length-delimited by its own (repo-relative, forward-slash) path
    string so that a byte-identical file under a different name, or a
    boundary shift between two files' content, cannot collide. Paths are
    sorted before hashing so caller-supplied ordering never affects the
    result."""
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda p: p.as_posix()):
        name = p.as_posix().encode("utf-8")
        data = p.read_bytes()
        h.update(len(name).to_bytes(8, "big"))
        h.update(name)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()
