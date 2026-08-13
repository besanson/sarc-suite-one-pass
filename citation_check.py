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

Every citation-shaped token (an arXiv ID or a DOI) appearing in a paper
draft must already be in the verified whitelist (citations.json) -- this
pipeline never fabricates a citation to fill a gap. A literature claim
this artifact cannot yet back with a verified source stays an honest
`[CITE: ...]` placeholder (Section 9's stubs, unchanged from v0.1) and is
counted, not invented -- the count is one of the numbers Phase 6 prints
in the human release checklist.

SEED = 26313 (not applicable -- this is a static text check)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

CITATIONS_PATH = "citations.json"

ARXIV_PATTERN = re.compile(r"arXiv[:\s]+(\d{4}\.\d{5})", re.IGNORECASE)
DOI_PATTERN = re.compile(r"\bdoi[:\s]+(10\.\d{4,9}/[^\s,)\]]+)", re.IGNORECASE)
CITE_PLACEHOLDER_PATTERN = re.compile(r"\[CITE[-:][^\]]*\]")


def load_whitelist(path: str = CITATIONS_PATH) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


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
