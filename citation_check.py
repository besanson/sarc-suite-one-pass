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
V4 gate: citation verification.

Per the task spec: "a citation may enter the paper only after it is
verified by fetching its source page and recording url, title, first
author, year into verified-citations.json." verified-citations.json
holds exactly that record for each of this artifact's four citations
(fetched live via WebFetch against arxiv.org / archive.ics.uci.edu, see
each entry's verified_via field) -- this pipeline never fabricates a
citation to fill a gap. A literature claim this artifact cannot yet back
with a verified source stays an honest `[CITE: ...]` placeholder
(Section 10's stubs, unchanged in spirit from v0.1's Section 9) and is
counted, not invented -- the count is one of the numbers Phase 6 prints
in the human release checklist.

Every citation-shaped token (an arXiv ID or a DOI) appearing in a paper
draft must match an entry's arxiv_id/doi here.

SEED = 26313 (not applicable -- this is a static text check)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

CITATIONS_PATH = "verified-citations.json"

ARXIV_PATTERN = re.compile(r"arXiv[:\s]+(\d{4}\.\d{5})", re.IGNORECASE)
DOI_PATTERN = re.compile(r"\bdoi[:\s]+(10\.\d{4,9}/[^\s,)\]]+)", re.IGNORECASE)
CITE_PLACEHOLDER_PATTERN = re.compile(r"\[CITE[-:][^\]]*\]")


REQUIRED_FIELDS = ("url", "title", "first_author", "year")


def load_whitelist(path: str = CITATIONS_PATH) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def verify_whitelist_schema(path: str = CITATIONS_PATH) -> Dict[str, Any]:
    """Every entry must carry what the task spec requires a verified
    citation to record: url, title, first_author, year -- not just the
    machine-matchable arxiv_id/doi token."""
    whitelist = load_whitelist(path)
    incomplete = []
    for citation in whitelist["citations"]:
        missing = [f for f in REQUIRED_FIELDS if f not in citation]
        if missing:
            incomplete.append({"id": citation.get("id"), "missing": missing})
    return {"total": len(whitelist["citations"]), "incomplete": incomplete, "clean": not incomplete}


def check(paper_path: str, whitelist_path: str = CITATIONS_PATH) -> Dict[str, Any]:
    text = Path(paper_path).read_text()
    whitelist = load_whitelist(whitelist_path)
    allowed_arxiv = {c["arxiv_id"] for c in whitelist["citations"] if "arxiv_id" in c}
    allowed_doi = {c["doi"] for c in whitelist["citations"] if "doi" in c}

    found_arxiv = set(ARXIV_PATTERN.findall(text))
    found_doi = {m.rstrip(".") for m in DOI_PATTERN.findall(text)}
    unverified_arxiv = sorted(found_arxiv - allowed_arxiv)
    unverified_doi = sorted(found_doi - allowed_doi)
    placeholder_count = len(CITE_PLACEHOLDER_PATTERN.findall(text))

    return {
        "paper_path": paper_path,
        "found_arxiv_ids": sorted(found_arxiv),
        "found_dois": sorted(found_doi),
        "unverified_arxiv_ids": unverified_arxiv,
        "unverified_dois": unverified_doi,
        "cite_needed_placeholder_count": placeholder_count,
        "clean": not unverified_arxiv and not unverified_doi,
    }


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "paper4-composition-draft-v0.3.md"
    result = check(target)
    print(json.dumps(result, indent=2))
    if not result["clean"]:
        raise SystemExit(1)
