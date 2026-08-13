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
PROOF-STATUS linter tests (Phase 4 / V2 gate). "Clearing any
PROOF-STATUS tag to proven" is human-only -- this repo's own pipeline
must never write that value into a proof file, and this test is the
standing tripwire against a future edit crossing that line.

SEED = 26313
"""
from __future__ import annotations

from checkers import proof_status_lint


def test_appendix_a_proofs_file_exists_and_has_tags():
    result = proof_status_lint.lint()
    assert result["total_tags"] > 0
    assert result["all_clean"] is True


def test_every_tag_is_one_of_the_two_allowed_values():
    result = proof_status_lint.lint_file("appendix-a-proofs.md")
    for tag in result["tags"]:
        assert tag in proof_status_lint.ALLOWED


def test_proven_is_not_an_allowed_value():
    """The human-only status is intentionally not in ALLOWED -- this
    pipeline is never entitled to write it."""
    assert "proven" not in proof_status_lint.ALLOWED


def test_linter_catches_a_forbidden_status(tmp_path):
    bad_file = tmp_path / "bad-proofs.md"
    bad_file.write_text("Proposition X. Some claim.\n\nPROOF-STATUS: proven\n")
    result = proof_status_lint.lint_file(str(bad_file))
    assert result["clean"] is False
    assert "proven" in result["forbidden_values_found"]


def test_linter_catches_a_typo_status(tmp_path):
    bad_file = tmp_path / "typo-proofs.md"
    bad_file.write_text("PROOF-STATUS: machine checked\n")  # missing hyphen
    result = proof_status_lint.lint_file(str(bad_file))
    assert result["clean"] is False


def test_linter_accepts_a_clean_file(tmp_path):
    good_file = tmp_path / "good-proofs.md"
    good_file.write_text(
        "Proposition X.\n\nPROOF-STATUS: machine-checked\n\n"
        "Proposition Y.\n\nPROOF-STATUS: pending-human-review\n"
    )
    result = proof_status_lint.lint_file(str(good_file))
    assert result["clean"] is True
    assert result["tag_count"] == 2


def test_every_proposition_lemma_theorem_heading_has_a_following_tag():
    """Structural completeness: every numbered claim in Appendix A must
    carry its own PROOF-STATUS -- a tag count lower than the claim count
    would mean some claim shipped unlabelled."""
    import re
    from pathlib import Path

    text = Path("appendix-a-proofs.md").read_text()
    claim_headings = re.findall(
        r"^## (Proposition \d+|Lemma \d+|Theorem \d+|CH\d+)", text, re.MULTILINE
    )
    tags = proof_status_lint.find_tags(text)
    assert len(claim_headings) == len(tags), (claim_headings, tags)
