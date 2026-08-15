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

ALLOWED is deliberately small and closed: only the statuses this
pipeline is entitled to assign. "proven" is intentionally absent -- if it
ever appears in a linted file, that is a lint failure, not a fourth
allowed value to add to this set.

"checked-scope-only" was added per the independent review's proof-tag
policy (review/REVIEW.md Section 3): a statement whose largest certified
scope is narrower than its general prose claim is tagged
"checked-scope-only (REVIEW.md)" and its wording narrowed to exactly
that certified scope -- distinct from "pending-human-review" (general
claim, no scope-narrowing needed yet) and from "machine-checked" (the
full general claim is exhaustively verified).

Round-two independent review finding R2-N2 (review-r2/REVIEW-R2.md):
"machine-checked" tags were found attached to general, unbounded-domain
statements (an arbitrary-n continuous theorem, an arbitrary-gate/
arbitrary-action-space theorem) when only a finite instantiation was
actually executable-verified. `find_machine_checked_scope_violations`
below is the mechanical fix: every "machine-checked" tag's own paragraph
must name either (a) an executable checker module under `checkers/`
(a `checkers/*.py` path) or (b) a structural tautology argued directly
from the code that produces the number (the taxonomy's own stated
alternative, for claims like Proposition 5's coverage-union identity
that are true by construction rather than by exhaustive search) --
AND an enumerated domain: a concrete count, grid size, or state-space
size, not just an unquantified assertion of completeness. A
"machine-checked" tag whose paragraph names neither is a lint failure,
the same as an unlisted tag value.

SEED = 26313 (not applicable -- this is a static text lint, not a
simulation)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

ALLOWED = {"machine-checked", "pending-human-review", "checked-scope-only"}
TAG_PATTERN = re.compile(r"PROOF-STATUS:\s*([A-Za-z][A-Za-z \-]*[A-Za-z])")

CHECKER_MODULE_PATTERN = re.compile(r"checkers/[A-Za-z0-9_]+\.py")
TAUTOLOGY_PATTERN = re.compile(r"tautolog\w*", re.IGNORECASE)
ENUMERATED_DOMAIN_PATTERN = re.compile(r"\b\d{1,3}(?:,\d{3})*\b")

DEFAULT_TARGETS = ["appendix-a-proofs.md"]


def find_tags(text: str) -> List[str]:
    return [m.group(1).strip() for m in TAG_PATTERN.finditer(text)]


def find_machine_checked_scope_violations(text: str) -> List[Dict[str, Any]]:
    """For every 'machine-checked' tag, look at its own paragraph (up to
    the next blank line) and require it to name a verification source
    (an executable checker module, or an explicit structural-tautology
    argument) plus an enumerated domain. Returns one entry per tag whose
    paragraph is missing either -- an empty list means every
    machine-checked tag names its scope, per round-two review finding
    R2-N2."""
    violations = []
    for m in TAG_PATTERN.finditer(text):
        if m.group(1).strip() != "machine-checked":
            continue
        paragraph_end = text.find("\n\n", m.start())
        if paragraph_end == -1:
            paragraph_end = len(text)
        scope_text = text[m.start():paragraph_end]
        has_source = bool(CHECKER_MODULE_PATTERN.search(scope_text)) or bool(TAUTOLOGY_PATTERN.search(scope_text))
        has_domain = bool(ENUMERATED_DOMAIN_PATTERN.search(scope_text))
        if not (has_source and has_domain):
            violations.append({
                "excerpt": scope_text[:200],
                "has_checker_or_tautology_reference": has_source,
                "has_enumerated_domain": has_domain,
            })
    return violations


def lint_file(path: str) -> Dict[str, object]:
    text = Path(path).read_text()
    tags = find_tags(text)
    forbidden = sorted({t for t in tags if t not in ALLOWED})
    scope_violations = find_machine_checked_scope_violations(text)
    return {
        "path": path,
        "tag_count": len(tags),
        "tags": tags,
        "forbidden_values_found": forbidden,
        "machine_checked_scope_violations": scope_violations,
        "clean": len(forbidden) == 0 and len(scope_violations) == 0,
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
