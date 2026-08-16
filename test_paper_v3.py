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
Phase 5 (v0.3 paper) tests: citation_check.py's whitelist enforcement,
paper_tables_v3.py's slot generation, and an end-to-end check that the
v0.3 template populates with zero unfilled slots against this repo's own
already-committed out/metrics.json + out/results/sweep_summary.json +
out/checkers/*.json (no expensive re-run of the suite/sweep needed here —
those are covered by their own test files).

SEED = 26313
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from citation_check import check as check_citations


def _require(path: str):
    if not Path(path).exists():
        pytest.skip(f"{path} not present -- run make suite / make sweep / make formal first")
    return path


# ---------------------------------------------------------------------------
# citation_check.py
# ---------------------------------------------------------------------------


def test_known_citations_are_whitelisted(tmp_path):
    paper = tmp_path / "p.md"
    paper.write_text(
        "SARC (arXiv 2605.07728), Green SARC (arXiv 2606.15954), "
        "SARC-DQ (arXiv 2607.26313), doi 10.24432/C5BW33."
    )
    result = check_citations(str(paper))
    assert result["clean"] is True
    assert result["unverified_arxiv_ids"] == []
    assert result["unverified_dois"] == []


def test_unwhitelisted_arxiv_id_is_flagged(tmp_path):
    paper = tmp_path / "p.md"
    paper.write_text("A fabricated citation (arXiv 9999.99999).")
    result = check_citations(str(paper))
    assert result["clean"] is False
    assert "9999.99999" in result["unverified_arxiv_ids"]


def test_unwhitelisted_doi_is_flagged(tmp_path):
    paper = tmp_path / "p.md"
    paper.write_text("doi 10.9999/fabricated")
    result = check_citations(str(paper))
    assert result["clean"] is False
    assert "10.9999/fabricated" in result["unverified_dois"]


def test_cite_needed_placeholders_are_counted_not_fabricated(tmp_path):
    paper = tmp_path / "p.md"
    paper.write_text("[CITE: some literature] and [CITE-NEEDED: another gap]")
    result = check_citations(str(paper))
    assert result["clean"] is True  # placeholders are honest, not violations
    assert result["cite_needed_placeholder_count"] == 2


def test_verified_citations_file_has_url_title_author_year():
    from citation_check import verify_whitelist_schema

    result = verify_whitelist_schema()
    assert result["clean"] is True
    assert result["total"] == 15  # 4 engine/data + 6 F5 + 5 v0.4-final-feedback related-work citations


def test_url_only_citation_is_verified_by_exact_url_match(tmp_path):
    """perspectives-tofu (Wendlandt et al. 2008) predates DOI assignment
    for USENIX proceedings -- verified_whitelist_schema still requires it
    to carry url/title/first_author/year, and citation_check.check()
    verifies it by exact url presence instead of arxiv_id/doi."""
    paper = tmp_path / "p.md"
    paper.write_text(
        "Trust-on-first-use (Wendlandt et al., USENIX ATC 2008, "
        "https://www.usenix.org/legacy/event/usenix08/tech/full_papers/wendlandt/wendlandt.pdf)."
    )
    result = check_citations(str(paper))
    assert result["clean"] is True
    assert result["unverified_urls"] == []


def test_unwhitelisted_url_is_flagged(tmp_path):
    paper = tmp_path / "p.md"
    paper.write_text("See https://example.com/not-a-real-citation for details.")
    result = check_citations(str(paper))
    assert result["clean"] is False
    assert "https://example.com/not-a-real-citation" in result["unverified_urls"]


def test_clean_paper_with_no_citations_at_all(tmp_path):
    paper = tmp_path / "p.md"
    paper.write_text("No citations here at all.")
    result = check_citations(str(paper))
    assert result["clean"] is True
    assert result["found_arxiv_ids"] == []
    assert result["found_dois"] == []
    assert result["cite_needed_placeholder_count"] == 0


# ---------------------------------------------------------------------------
# paper_tables_v3.py: CI formatting and slot generation
# ---------------------------------------------------------------------------


def test_fmt_ci_formats_mean_and_bounds():
    from paper_tables_v3 import _fmt_ci

    stat = {"mean": 1.23456, "ci95_low": 1.0, "ci95_high": 1.5, "n": 30}
    formatted = _fmt_ci(stat, decimals=2)
    assert "1.23" in formatted
    assert "1.00" in formatted
    assert "1.50" in formatted
    assert "n=30" in formatted


def test_generate_v3_slots_end_to_end():
    metrics_path = _require("out/metrics.json")
    sweep_path = _require("out/results/sweep_summary.json")
    lattice_path = _require("out/checkers/lattice_check.json")
    compensation_path = _require("out/checkers/compensation_check.json")
    remediator_path = _require("out/checkers/remediator_check.json")

    from manifest import build_manifest
    from paper_tables_v3 import generate_v3_slots

    metrics = json.loads(Path(metrics_path).read_text())
    sweep = json.loads(Path(sweep_path).read_text())
    lattice_result = json.loads(Path(lattice_path).read_text())
    compensation_result = json.loads(Path(compensation_path).read_text())
    remediator_result = json.loads(Path(remediator_path).read_text())
    manifest = build_manifest(data_sha256="deadbeef", seed=26313)

    slots = generate_v3_slots(metrics, manifest, sweep, lattice_result, compensation_result, remediator_result)

    assert "abstract_results_sentence_v3" in slots
    assert "CH1" in slots["abstract_results_sentence_v3"]
    assert "CH8" in slots["abstract_results_sentence_v3"]
    assert slots["checkers.lattice_all_hold"] == "True"
    assert slots["checkers.compensation_holds"] == "True"
    assert slots["checkers.remediator_outcome"] in ("confluent", "non_confluent")
    assert "table6_ch6" in slots and "W1" in slots["table6_ch6"] and "W2" in slots["table6_ch6"]


# ---------------------------------------------------------------------------
# End-to-end: v0.3 template populates with zero unfilled slots.
# ---------------------------------------------------------------------------


def test_v3_draft_populates_with_zero_unfilled_slots(tmp_path):
    for p in (
        "out/metrics.json", "out/results/sweep_summary.json",
        "out/checkers/lattice_check.json", "out/checkers/compensation_check.json",
        "out/checkers/remediator_check.json", "appendix-a-proofs.md",
    ):
        _require(p)

    import hashlib

    from manifest import build_manifest
    from paper_tables_v3 import generate_v3_slots
    from populate_draft import populate_draft
    from paper_v3 import PAPER_DRAFT_TEXT, _read_appendix_a

    metrics = json.loads(Path("out/metrics.json").read_text())
    sweep = json.loads(Path("out/results/sweep_summary.json").read_text())
    lattice_result = json.loads(Path("out/checkers/lattice_check.json").read_text())
    compensation_result = json.loads(Path("out/checkers/compensation_check.json").read_text())
    remediator_result = json.loads(Path("out/checkers/remediator_check.json").read_text())
    sha = hashlib.sha256(open("data/open_retail_daily.csv", "rb").read()).hexdigest()
    manifest = build_manifest(sha, 26313)

    slots = generate_v3_slots(metrics, manifest, sweep, lattice_result, compensation_result, remediator_result)
    slots["appendixA_proofs"] = _read_appendix_a()

    draft = tmp_path / "v0.3.md"
    draft.write_text(PAPER_DRAFT_TEXT)
    populated = tmp_path / "v0.3-populated.md"
    unfilled = populate_draft(str(draft), slots, str(populated))
    assert unfilled == []

    populated_text = populated.read_text()
    assert "[GENERATED:" not in populated_text

    citation_result = check_citations(str(populated))
    assert citation_result["clean"] is True


def test_v3_draft_mentions_ch5_through_ch8():
    from paper_v3 import PAPER_DRAFT_TEXT

    for ch in ("CH5", "CH6", "CH7", "CH8"):
        assert ch in PAPER_DRAFT_TEXT
