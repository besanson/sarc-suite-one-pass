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
Phase 4 / V2 gate: the PROOF-STATUS linter.

"Clearing any PROOF-STATUS tag to proven" is on the task's human-only
list -- this repo's own pipeline must never write that value. This is a
standing invariant, not a one-time check: it is re-run by the test suite
on every change to appendix-a-proofs.md (or any future paper draft that
carries PROOF-STATUS tags), so a future edit cannot silently cross the
human-only line.

ALLOWED is deliberately small and closed: only the two statuses this
pipeline is entitled to assign. "proven" is intentionally absent -- if it
ever appears in a linted file, that is a lint failure, not a third
allowed value to add to this set.

SEED = 26313 (not applicable -- this is a static text lint, not a
simulation)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

ALLOWED = {"machine-checked", "pending-human-review"}
TAG_PATTERN = re.compile(r"PROOF-STATUS:\s*([A-Za-z][A-Za-z \-]*[A-Za-z])")

DEFAULT_TARGETS = ["appendix-a-proofs.md"]


def find_tags(text: str) -> List[str]:
    return [m.group(1).strip() for m in TAG_PATTERN.finditer(text)]


def lint_file(path: str) -> Dict[str, object]:
    text = Path(path).read_text()
    tags = find_tags(text)
    forbidden = sorted({t for t in tags if t not in ALLOWED})
    return {
        "path": path,
        "tag_count": len(tags),
        "tags": tags,
        "forbidden_values_found": forbidden,
        "clean": len(forbidden) == 0,
    }


def lint(paths: List[str] = None) -> Dict[str, object]:
    paths = paths if paths is not None else DEFAULT_TARGETS
    results = [lint_file(p) for p in paths if Path(p).exists()]
    return {
        "files": results,
        "total_tags": sum(r["tag_count"] for r in results),
        "all_clean": all(r["clean"] for r in results),
    }


if __name__ == "__main__":
    import json

    result = lint()
    print(json.dumps(result, indent=2))
    if not result["all_clean"]:
        raise SystemExit(1)
