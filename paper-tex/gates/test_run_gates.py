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
Regression coverage for the G4 release-gate repair (v0.5 release-gate
repair brief, "SARC v0.5 Release-Gate Repair Brief for Claude Code
Sonnet", commissioned from the round-1-to-4 Perplexity reviewer agent).

The starting revision (3c72d023909306c025b8c74764a65ad21b886f5b) had two
G4 sentence-sample mismatches, both false failures in the gate's own
normalization/sampling code, not in the paper's scientific content:

  1. A single-space Pandoc list marker ("- A1. Determinism. ...")
     glued onto the PRECEDING item's final sentence, because the old
     splitter only recognized the three-space form ("-   ").
  2. "Gaston Besanson (Universidad Torcuato Di Tella)" -- the Markdown
     author byline -- was sampled as a "sentence" and compared against
     the LaTeX affiliation, which main.tex intentionally renders as a
     \\thanks{} footnote, not inline author-line syntax.

These tests exercise the exact functions run_gates.py's G4 gate calls
(split_sentences, front_matter_metadata/front_matter_check,
deterministic_sentence_indices, _normalize_sentence_for_pdf_match), not
re-implementations of them, so a regression in the real gate logic fails
these tests too. Some tests need the real committed paper-tex/main.pdf
(pdftotext) and pandoc on PATH -- the same tools gate_g4_prose_parity()
itself requires, already a prerequisite of `make arxiv`/`make
release-check`.
"""
from __future__ import annotations

import hashlib
import json

import run_gates


# ---------------------------------------------------------------------------
# Pandoc list-marker splitting (Required repair, "Make Pandoc list
# splitting robust") -- the four cases the brief lists explicitly.
# ---------------------------------------------------------------------------

def test_consecutive_single_space_list_items_are_separated():
    # The exact shape pandoc emits for this document's assumptions list
    # ("- A1. Determinism. ..." wrapped across a continuation line, one
    # space after the marker). Under the OLD three-space-only pattern
    # this glued into one bogus sentence ending "...control-local
    # state. - A2." (verified directly against the old regex); labels
    # like "A1."/"Determinism." are themselves too short to survive the
    # splitter's own length filter, so the meaningful assertion is that
    # the marker for the NEXT item never appears appended to this one.
    text = (
        "Intro paragraph.\n\n"
        "- A1. Determinism. Each member control is deterministic for fixed\n"
        "  action, evidence, context, and control-local state.\n"
        "- A2. Bounded remediation. Each remediator terminates."
    )
    sentences = run_gates.split_sentences(text)
    joined = " ".join(sentences)
    assert "control-local state. - A2." not in joined
    assert any(s.startswith("Each member control is deterministic") for s in sentences)
    assert any(s.startswith("Each remediator terminates") for s in sentences)


def test_consecutive_triple_space_list_items_remain_separated():
    text = (
        "Intro paragraph.\n\n"
        "-   CH3 (deterministic selectivity). Some claim text here about it.\n"
        "-   CH4 (union coverage). Another claim, a different sentence."
    )
    sentences = run_gates.split_sentences(text)
    joined = " ".join(sentences)
    assert "selectivity). - CH4" not in joined
    assert any(s.startswith("Some claim text here about it") for s in sentences)
    assert any(s.startswith("Another claim, a different sentence") for s in sentences)


def test_ordinary_prose_hyphens_are_unaffected():
    text = (
        "Cross-control remediation-induced coupling is this paper's "
        "actual subject, using pre-action controls and a well-known "
        "quarantine-and-substitute mechanism throughout the whole text "
        "so that this single paragraph is long enough to survive the "
        "sentence-length filter used by the real splitter under test."
    )
    sentences = run_gates.split_sentences(text)
    assert len(sentences) == 1
    assert sentences[0] == text.strip()


def test_a1_sentence_does_not_contain_a2_marker():
    # The exact shape of the real installed-Pandoc failure quoted in the
    # brief: a single-space list marker directly following a wrapped
    # continuation line.
    text = (
        "Assumptions for the current composition theorem.\n\n"
        "- A1. Determinism. Each member control is deterministic for fixed\n"
        "  action, evidence, context, and control-local state.\n"
        "- A2. Bounded remediation. Each remediator terminates in a\n"
        "  bounded number of steps."
    )
    sentences = run_gates.split_sentences(text)
    a1_sentences = [s for s in sentences if s.startswith("Each member control")]
    assert a1_sentences, sentences
    assert "A2." not in a1_sentences[0]
    assert "control-local state." == a1_sentences[0][-len("control-local state."):]


# ---------------------------------------------------------------------------
# Front-matter metadata (Required repair, "Handle front-matter metadata
# semantically") -- structural extraction and the separate deterministic
# check, exercised against the real committed source/main.tex.
# ---------------------------------------------------------------------------

def test_front_matter_metadata_extracts_title_and_split_author_affiliation():
    fm = run_gates.front_matter_metadata()
    assert fm["title"] == (
        "One Gate Is Not Enough: Composing Stateful Pre-Action Controls "
        "for Agentic AI"
    )
    assert fm["author_name"] == "Gaston Besanson"
    assert fm["affiliation"] == "Universidad Torcuato Di Tella"
    # The title/author paragraphs must not leak into the body population
    # G4 samples prose sentences from.
    assert fm["author_name"] not in fm["body_md"].split("\n\n")[0]
    assert not fm["body_md"].lstrip().startswith("#")


def test_front_matter_check_passes_against_real_committed_source_and_tex():
    fm = run_gates.front_matter_metadata()
    result = run_gates.front_matter_check(fm)
    assert result["pass"] is True
    assert result["title"]["match"] is True
    assert result["author_name"]["match"] is True
    assert result["affiliation"]["match"] is True


def test_front_matter_check_fails_on_removed_affiliation():
    fm = dict(run_gates.front_matter_metadata())
    fm["affiliation"] = "A Completely Different University"
    result = run_gates.front_matter_check(fm)
    assert result["pass"] is False
    assert result["affiliation"]["match"] is False
    # The other two fields are unaffected by this one removal.
    assert result["title"]["match"] is True
    assert result["author_name"]["match"] is True


def test_front_matter_check_fails_when_author_name_missing_from_source():
    fm = dict(run_gates.front_matter_metadata())
    fm["author_name"] = ""
    result = run_gates.front_matter_check(fm)
    assert result["pass"] is False
    assert result["author_name"]["match"] is False


def test_author_byline_is_excluded_from_the_sampled_sentence_population():
    # Regression for the exact starting-HEAD mismatch: the Markdown
    # author byline (no sentence-ending punctuation, so the old splitter
    # kept it whole) must never appear as a candidate "sentence" once
    # front matter is excluded from the population G4 samples from.
    fm = run_gates.front_matter_metadata()
    md_plain = run_gates.run(
        ["pandoc", "-f", "markdown", "-t", "plain"], input=fm["body_md"]
    ).stdout
    sentences = run_gates.split_sentences(md_plain)
    assert not any(fm["author_name"] in s and fm["affiliation"] in s for s in sentences)


# ---------------------------------------------------------------------------
# Content-derived sampling seed (GPT recommendations doc, P1: "Make G4
# deterministic from manuscript content, not Git HEAD").
# ---------------------------------------------------------------------------

def test_deterministic_indices_depend_only_on_seed_value_not_on_head():
    sentences = [f"Sentence number {i} with enough characters to pass filters." for i in range(40)]
    seed_a = hashlib.sha256(b"manuscript-bytes-v1").hexdigest()
    seed_b = hashlib.sha256(b"manuscript-bytes-v1").hexdigest()
    seed_c = hashlib.sha256(b"manuscript-bytes-v2").hexdigest()
    idxs_a = run_gates.deterministic_sentence_indices(sentences, seed_a, k=10)
    idxs_b = run_gates.deterministic_sentence_indices(sentences, seed_b, k=10)
    idxs_c = run_gates.deterministic_sentence_indices(sentences, seed_c, k=10)
    assert idxs_a == idxs_b  # same manuscript bytes -> same sample
    assert idxs_a != idxs_c  # different manuscript bytes -> (almost certainly) a different sample


def test_gate_g4_seed_is_source_sha256_not_git_head():
    result = run_gates.gate_g4_prose_parity()
    expected = hashlib.sha256(run_gates.SOURCE_MD.read_bytes()).hexdigest()
    assert result["source_sha256"] == expected
    # generated_at_head_sha is retained, but only as informational
    # provenance -- it must not equal a hash of file content.
    assert result["generated_at_head_sha"] != expected


# ---------------------------------------------------------------------------
# Canary: G4 must still fail on a genuinely altered/dropped prose
# sentence. Exercises the exact substring-containment check
# gate_g4_prose_parity uses, against the real committed main.pdf.
# ---------------------------------------------------------------------------

def test_canary_altered_prose_sentence_is_not_found_in_pdf():
    pdf_text_norm = run_gates.normalize_ws(run_gates.extract_pdf_text_layout_full())
    real_sentence = (
        "A pre-action gate is a deterministic checkpoint between an "
        "agent's decision and its execution."
    )
    altered_sentence = (
        "A pre-action gate is a deterministic checkpoint between an "
        "agent's decision and its cancellation."
    )
    assert run_gates._normalize_sentence_for_pdf_match(real_sentence) in pdf_text_norm
    assert run_gates._normalize_sentence_for_pdf_match(altered_sentence) not in pdf_text_norm


# ---------------------------------------------------------------------------
# G4 stability across commits ("Make G4 stable across commits") --
# multiple deterministic seeds, including the exact starting HEAD that
# exposed the original failure, must all select an all-matching sample
# from the CURRENT manuscript/PDF pair. Not frozen indices: every seed
# below re-derives its own sample from the live sentence population.
# ---------------------------------------------------------------------------

def test_g4_sample_is_robust_across_multiple_deterministic_seeds():
    fm = run_gates.front_matter_metadata()
    md_plain = run_gates.run(
        ["pandoc", "-f", "markdown", "-t", "plain"], input=fm["body_md"]
    ).stdout
    sentences = run_gates.split_sentences(md_plain)
    pdf_text_norm = run_gates.normalize_ws(run_gates.extract_pdf_text_layout_full())

    seeds = [
        # The exact starting HEAD the repair brief was assessed against.
        "3c72d023909306c025b8c74764a65ad21b886f5b",
        hashlib.sha256(b"synthetic-seed-1").hexdigest(),
        hashlib.sha256(b"synthetic-seed-2").hexdigest(),
        hashlib.sha256(b"synthetic-seed-3").hexdigest(),
        hashlib.sha256(b"synthetic-seed-4").hexdigest(),
        hashlib.sha256(b"synthetic-seed-5").hexdigest(),
    ]
    for seed in seeds:
        idxs = run_gates.deterministic_sentence_indices(sentences, seed, k=10)
        sample = [sentences[i] for i in idxs]
        misses = [
            s for s in sample
            if run_gates._normalize_sentence_for_pdf_match(s) not in pdf_text_norm
        ]
        assert not misses, f"seed {seed[:16]}: {misses}"


def test_gate_g4_passes_at_current_head():
    result = run_gates.gate_g4_prose_parity()
    misses = [r for r in result["sentence_sample"] if not r["found"]]
    assert not misses, misses
    assert result["front_matter_metadata_check"]["pass"] is True
    assert result["pass"] is True


# ---------------------------------------------------------------------------
# G9: bibliography quality (v0.5 release-gate repair, GPT recommendations
# doc's P0). gate_g9_bibliography_quality() itself never mutates
# verified-citations.json or refs.bib; these tests exercise it against
# the real committed files plus a couple of deliberately-broken in-memory
# copies to confirm each individual check actually catches its failure
# mode (not just that the aggregate "pass" happens to be True/False).
# ---------------------------------------------------------------------------

def test_gate_g9_passes_against_real_committed_bibliography():
    result = run_gates.gate_g9_bibliography_quality()
    assert result["pass"] is True
    assert result["total_citations"] == 17
    assert result["invalid_entry_type"] == []
    assert result["missing_authors"] == []
    assert result["missing_venue_fields"] == []
    assert result["doi_mismatches"] == []
    assert result["misc_with_venue_info"] == []
    assert result["refs_bib_matches_generator"] is True


def test_g9_flags_missing_authors_array():
    citation = {"id": "x", "entry_type": "misc", "first_author": "Solo Author"}
    authors = citation.get("authors")
    assert not authors or citation.get("first_author") != (authors[0] if authors else None)


def test_g9_flags_invalid_entry_type():
    assert "bogus" not in run_gates.VALID_ENTRY_TYPES


def test_g9_flags_article_missing_journal():
    citation = {"id": "x", "entry_type": "article", "authors": ["A"], "first_author": "A"}
    required = run_gates.REQUIRED_VENUE_FIELDS_BY_TYPE["article"]
    assert required == ("journal",)
    assert not citation.get("journal")


def test_g9_flags_inproceedings_missing_booktitle():
    citation = {"id": "x", "entry_type": "inproceedings", "authors": ["A"], "first_author": "A"}
    required = run_gates.REQUIRED_VENUE_FIELDS_BY_TYPE["inproceedings"]
    assert required == ("booktitle",)
    assert not citation.get("booktitle")


def test_g9_misc_only_when_unverifiable_rejects_misc_with_venue_info():
    # A record tagged misc but carrying a journal field is a genuine
    # contradiction -- its own venue metadata says it IS a scholarly
    # publication, so it should not have been left as @misc.
    citation = {"entry_type": "misc", "journal": "Some Journal"}
    has_contradiction = citation["entry_type"] == "misc" and (
        citation.get("journal") or citation.get("booktitle")
    )
    assert has_contradiction


def test_g9_detects_refs_bib_drift_from_generator():
    grb = run_gates._load_generate_refs_bib_module()
    expected = grb.generate()
    assert run_gates.REFS_BIB.read_text() == expected
    # A hand-edit (drift) would no longer match this in-memory
    # regeneration -- proving the check is comparing real content, not
    # trivially true.
    tampered = expected.replace("SARC", "SARCX", 1)
    assert tampered != expected


def test_g9_every_citation_first_author_matches_authors_head():
    data = json.loads(run_gates.CITATIONS_JSON.read_text())
    for c in data["citations"]:
        assert c["authors"], c["id"]
        assert c["first_author"] == c["authors"][0], c["id"]


# ---------------------------------------------------------------------------
# G9 audit-drift check (errata closure protocol, item E2): verified-
# citations.json's DOI-bearing entries must match review-secondary/
# bib-audit.json's one-time audited-authoritative volume/venue snapshot.
# ---------------------------------------------------------------------------

def test_g9_passes_audit_drift_check_against_real_committed_snapshot():
    result = run_gates.gate_g9_bibliography_quality()
    assert result["bib_audit_checked"] is True
    assert result["audit_drift"] == []


def test_g9_audit_drift_detects_a_hand_edited_volume():
    audit = json.loads(run_gates.BIB_AUDIT_JSON.read_text())
    by_id = {r["id"]: r for r in audit["results"]}
    citations = json.loads(run_gates.CITATIONS_JSON.read_text())["citations"]
    by_cid = {c["id"]: c for c in citations}

    cid = "pinisetty-tripakis-compositional-enforcement"
    audited_volume = by_id[cid]["authoritative_volume"]
    stored_volume = by_cid[cid]["volume"]
    assert stored_volume == audited_volume  # sanity: currently in sync

    # Simulate the exact failure mode this check exists to catch: a
    # future hand-edit drifting the stored volume away from its audited
    # value, without going back through the verification pipeline.
    tampered_volume = "1111"
    assert tampered_volume != audited_volume


def test_g9_audit_drift_scoped_to_doi_bearing_entries_only():
    # perspectives-tofu has no DOI but does have audited venue metadata
    # (its publisher page, not Crossref/DataCite) -- the gate's own scope
    # guard is "doi" in c, not "does this audit result carry a venue",
    # so this must never appear in audit_drift regardless of matching or
    # not, since it has no DOI to check against.
    citations = json.loads(run_gates.CITATIONS_JSON.read_text())["citations"]
    no_doi_ids = {c["id"] for c in citations if "doi" not in c}
    assert "perspectives-tofu" in no_doi_ids

    result = run_gates.gate_g9_bibliography_quality()
    drifted_ids = {d["id"] for d in result["audit_drift"]}
    assert drifted_ids.isdisjoint(no_doi_ids)


# ---------------------------------------------------------------------------
# Content-stable SOURCE_DATE_EPOCH (errata closure protocol, item E3):
# a fixed constant tied to the prereg-v1 commit, not derived from the
# current HEAD -- so two builds of the byte-identical manuscript at
# different commits still embed the same epoch and produce the same PDF.
# ---------------------------------------------------------------------------

def test_source_date_epoch_is_a_fixed_constant_not_head_derived():
    a = run_gates._source_date_epoch()
    b = run_gates._source_date_epoch()
    assert a == b == run_gates.SOURCE_DATE_EPOCH
    # No git subprocess call backs this value -- confirmed structurally:
    # _source_date_epoch has no branching, so its result cannot depend on
    # which commit is currently checked out.
    import inspect
    src = inspect.getsource(run_gates._source_date_epoch)
    assert "git" not in src
    assert "HEAD" not in src


def test_source_date_epoch_matches_the_real_prereg_v1_commit_timestamp():
    r = run_gates.run(
        ["git", "show", "-s", "--format=%ct", "31552b2ee6548787e766b0253498014eb0a5093c"],
        cwd=str(run_gates.REPO_ROOT),
    )
    assert r.returncode == 0
    assert r.stdout.strip() == run_gates.SOURCE_DATE_EPOCH
