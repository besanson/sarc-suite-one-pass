#!/usr/bin/env python3
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
arXiv LaTeX conversion task: parity/quality gates G1-G9. G1 drives its
own build (see gate_g1_build) -- it does not require a prior
latexmk/tectonic invocation -- so this script is the single entry point
`make arxiv` / `make release-check` need. Writes paper-tex/parity-report.json
and prints a summary; exits non-zero if any gate fails, so `make arxiv`
stops before packaging on a failed gate.

Every gate compares paper-tex/main.tex / main.pdf against the source
paper4-composition-draft-v0.5-populated.md -- the "zero content changes"
non-negotiable is not just asserted, it is checked.

Round-three response (finding R3-F2): G1 was latexmk-log-dependent (it
read main.log's specific line formats), which made `make arxiv` fail
under the now-canonical Tectonic toolchain (Tectonic never writes
main.log at all). G1 is now compiler-aware and artifact-based: it runs
the detected compiler itself, twice, and checks compiler-agnostic
artifacts (exit code, PDF produced, page count, and file list, the last
two compared build-to-build) plus each compiler's own diagnostic output
in that compiler's own format (undefined refs/citations, which Tectonic
under --print emits in the same pdflatex-compatible text Tectonic and
latexmk/pdflatex share; Overfull \\hbox warnings, whose line-prefix format
differs between the two and is looked up per compiler below).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

GATES_DIR = Path(__file__).resolve().parent
PAPER_TEX_DIR = GATES_DIR.parent
REPO_ROOT = PAPER_TEX_DIR.parent

SOURCE_MD = REPO_ROOT / "paper4-composition-draft-v0.5-populated.md"
MAIN_TEX = PAPER_TEX_DIR / "main.tex"
MAIN_PDF = PAPER_TEX_DIR / "main.pdf"
REPORT_PATH = PAPER_TEX_DIR / "parity-report.json"
ARXIV_ABSTRACT = PAPER_TEX_DIR / "arxiv-abstract.txt"
ARXIV_METADATA = PAPER_TEX_DIR / "arxiv-metadata.txt"
REFS_BIB = PAPER_TEX_DIR / "refs.bib"
CITATIONS_JSON = REPO_ROOT / "verified-citations.json"
BIB_AUDIT_JSON = REPO_ROOT / "review-secondary" / "bib-audit.json"

# The 15 real sections (12 numbered body sections + Appendix A/B/C) --
# Abstract is excluded (it is \begin{abstract}, not a \section, on both
# sides) and Appendix A's individual Proposition/Lemma/Theorem/Corollary
# sub-headers are folded into the single "Proofs" bucket, matching how
# they became theorem environments inside \section{Proofs} rather than
# their own \section commands (see G5's theorem-environment count for
# where those are actually counted).
SECTION_TITLES = [
    "1. Introduction",
    "2. Model and terminology",
    "3. Hard constraints versus compensatory aggregation",
    "4. Single-remediator composition",
    "5. Multi-remediator composition",
    "6. Stateful governance and evidence-buffer contamination",
    "7. The unified Evidence Set",
    "8. Empirical validation",
    "9. Related work",
    "10. Limitations and open theory",
    "11. Conclusion",
    "Appendix A. Proofs",
    "Appendix B. Artifact manifest",
    "Appendix C. Statistical methodology (V3 gate)",
    "Validation note",
]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kwargs)


# ---------------------------------------------------------------------------
# G1: Build (compiler-aware, artifact-based -- see module docstring)
# ---------------------------------------------------------------------------

# Tectonic is the canonical, pinned (0.17.0, see bootstrap.sh) release
# toolchain -- bootstrap-installable everywhere via a static binary
# download, unlike latexmk which needs a full TeX Live install. latexmk
# remains a supported alternative for contributors who already have one.
# Set SARC_LATEX_COMPILER=tectonic|latexmk to force a choice; otherwise
# Tectonic is preferred when both are on PATH.
COMPILER_ENV_VAR = "SARC_LATEX_COMPILER"

# Undefined-reference/citation warnings: verified identical wording under
# `tectonic --print` and under latexmk/pdflatex, both being the same
# underlying TeX engine warning text -- one pattern serves both compilers.
UNDEFINED_REF_RE = re.compile(r"LaTeX Warning: Reference `([^']*)' on page \d+ undefined")
UNDEFINED_CITE_RE = re.compile(r"LaTeX Warning: Citation `([^']*)' .*undefined")

# Overfull \hbox warnings: the underlying pt/line data is the same, but
# the line-prefix format differs per compiler (verified directly against
# both toolchains) -- latexmk/pdflatex print a bare "Overfull \hbox ..."
# log line, while Tectonic prefixes each diagnostic with "warning: FILE:LINE:".
OVERFULL_PATTERNS = {
    "latexmk": re.compile(
        r"Overfull \\hbox \(([\d.]+)pt too wide\) in paragraph at lines (\d+)--(\d+)"
    ),
    "tectonic": re.compile(
        r"warning: [^:\s]+:(\d+): Overfull \\hbox \(([\d.]+)pt too wide\)"
    ),
}

# main.tex's own source files plus every byproduct any supported compiler
# leaves in paper-tex/ -- removed before each of G1's two builds so the
# "identical file list" check reflects what THIS build produced, not
# leftovers from a previous, possibly different, compiler run.
GENERATED_FILE_GLOBS = ["main.pdf", "main.log", "main.aux", "main.bbl", "main.blg",
                         "main.out", "main.fls", "main.fdb_latexmk", "main.synctex.gz",
                         "main.toc", "texput.log"]


# Errata closure protocol, item E3 ("content-stable PDF reproducibility"):
# a fixed constant, not derived from the current HEAD commit. The prior
# HEAD-derived scheme (round-three response, byte-reproducible build
# gate upgrade) embedded the CURRENT commit's own timestamp into the
# PDF, so the byte-identical same manuscript built at two different
# commits (e.g. across a documentation-only commit after the last
# content change) produced two DIFFERENT PDF byte streams -- defeating
# "identical sources yield identical bytes" as a cross-commit property,
# leaving it true only within a single commit's own two-build G1 check.
#
# The value below is the git commit timestamp of the prereg-v1 commit
# (31552b2ee6548787e766b0253498014eb0a5093c, "V1 prereg: untrack result
# artifacts so prereg-v1's tree is results-free", 2026-08-13T08:32:43Z
# -- reproducible via `git show -s --format=%ct
# 31552b2ee6548787e766b0253498014eb0a5093c`). This is not an arbitrary
# choice: prereg-v1 is already this artifact's own established fixed
# point of reference for "before any result existed" (prereg/hypotheses.md,
# README.md's Preregistration tag section, and every populated paper's
# own appendixB_manifest.prereg_v1_sha all cite the same sha) -- reused
# here rather than inventing a second reference commit. A literal
# constant, not a live `git show` of that sha, so the build stays
# reproducible even from a source tarball with no git history at all.
SOURCE_DATE_EPOCH = "1786609963"


def _source_date_epoch() -> str:
    return SOURCE_DATE_EPOCH


def _reproducible_build_env() -> dict:
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = _source_date_epoch()
    env["TZ"] = "UTC"
    return env


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detect_compiler() -> str:
    forced = os.environ.get(COMPILER_ENV_VAR, "").strip().lower()
    if forced:
        return forced
    if shutil.which("tectonic"):
        return "tectonic"
    if shutil.which("latexmk"):
        return "latexmk"
    return ""


def _clean_generated() -> None:
    for name in GENERATED_FILE_GLOBS:
        f = PAPER_TEX_DIR / name
        if f.exists():
            f.unlink()


def _pdf_page_count(pdf_path: Path) -> int | None:
    if not pdf_path.exists():
        return None
    r = run(["pdfinfo", str(pdf_path)])
    m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.MULTILINE)
    return int(m.group(1)) if m else None


def _run_compiler_once(compiler: str) -> tuple[int, str]:
    env = _reproducible_build_env()
    if compiler == "tectonic":
        # --print surfaces undefined-ref/citation/overfull-hbox warnings
        # that Tectonic otherwise suppresses entirely (verified directly:
        # a plain `tectonic main.tex` build with a deliberately broken
        # \ref/\cite produced no warning output at all).
        r = run(["tectonic", "--print", "main.tex"], cwd=str(PAPER_TEX_DIR), env=env)
    elif compiler == "latexmk":
        r = run(["latexmk", "-pdf", "-interaction=nonstopmode", "main.tex"], cwd=str(PAPER_TEX_DIR), env=env)
    else:
        raise RuntimeError(f"unsupported compiler {compiler!r}")
    return r.returncode, f"{r.stdout or ''}\n{r.stderr or ''}"


def _parse_build_diagnostics(compiler: str, output: str) -> dict:
    errors = [l for l in output.splitlines() if l.startswith("! ")]
    undefined_refs = UNDEFINED_REF_RE.findall(output)
    undefined_cites = UNDEFINED_CITE_RE.findall(output)

    overfull = []
    pattern = OVERFULL_PATTERNS[compiler]
    if compiler == "tectonic":
        for m in pattern.finditer(output):
            pts = float(m.group(2))
            if pts > 10.0:
                overfull.append({"pt": pts, "line": m.group(1)})
    else:
        for m in pattern.finditer(output):
            pts = float(m.group(1))
            if pts > 10.0:
                overfull.append({"pt": pts, "lines": f"{m.group(2)}--{m.group(3)}"})

    return {
        "errors": errors,
        "undefined_references": undefined_refs,
        "undefined_citations": undefined_cites,
        "overfull_hbox_above_10pt": overfull,
    }


def _do_one_build(compiler: str) -> dict:
    _clean_generated()
    rc, output = _run_compiler_once(compiler)
    diagnostics = _parse_build_diagnostics(compiler, output)
    return {
        "exit_code": rc,
        "pdf_produced": MAIN_PDF.exists(),
        "page_count": _pdf_page_count(MAIN_PDF),
        "file_list": sorted(p.name for p in PAPER_TEX_DIR.glob("main.*")),
        "pdf_sha256": _sha256_file(MAIN_PDF),
        **diagnostics,
    }


def gate_g1_build() -> dict:
    compiler = _detect_compiler()
    if not compiler:
        return {
            "pass": False,
            "detail": (
                f"no supported LaTeX compiler on PATH -- install pinned Tectonic "
                f"(canonical, see bootstrap.sh) or latexmk, or set {COMPILER_ENV_VAR}"
            ),
        }

    # Two consecutive builds, from a clean generated-file state each time:
    # the artifact-based replacement for "diff main.log against itself",
    # since Tectonic has no log file to diff at all.
    builds = [_do_one_build(compiler), _do_one_build(compiler)]
    latest = builds[-1]

    exit_code_zero = all(b["exit_code"] == 0 for b in builds)
    pdf_produced = all(b["pdf_produced"] for b in builds)
    two_build_identical = (
        builds[0]["page_count"] is not None
        and builds[0]["page_count"] == builds[1]["page_count"]
        and builds[0]["file_list"] == builds[1]["file_list"]
        # Round-three response: byte-reproducible build gate upgrade --
        # SOURCE_DATE_EPOCH pinning (see _reproducible_build_env) makes a
        # byte-identical PDF the achievable bar, so two_build_identical
        # now requires it rather than stopping at page count/file list.
        and builds[0]["pdf_sha256"] is not None
        and builds[0]["pdf_sha256"] == builds[1]["pdf_sha256"]
    )
    no_diagnostics = (
        not latest["errors"]
        and not latest["undefined_references"]
        and not latest["undefined_citations"]
        and not latest["overfull_hbox_above_10pt"]
    )

    ok = exit_code_zero and pdf_produced and two_build_identical and no_diagnostics
    return {
        "pass": ok,
        "compiler": compiler,
        "source_date_epoch": _source_date_epoch(),
        "exit_code_zero": exit_code_zero,
        "pdf_produced": pdf_produced,
        "two_build_identical": two_build_identical,
        "pdf_sha256": latest["pdf_sha256"],
        "page_count": latest["page_count"],
        "file_list": latest["file_list"],
        "builds": builds,
        "errors": latest["errors"],
        "undefined_references": latest["undefined_references"],
        "undefined_citations": latest["undefined_citations"],
        "overfull_hbox_above_10pt": latest["overfull_hbox_above_10pt"],
    }


# ---------------------------------------------------------------------------
# G2: Token purity
# ---------------------------------------------------------------------------

def gate_g2_token_purity() -> dict:
    tex = MAIN_TEX.read_text()
    # "[GENERATED" and raw markdown syntax are always leftover-template
    # bugs -- they must never survive into the final typeset LaTeX.
    # "[CITE" is different: citation_check.py's own CITE_PLACEHOLDER_PATTERN
    # (r"\[CITE[-:][^\]]*\]") treats "[CITE:" / "[CITE-NEEDED:" as this
    # artifact's own established, HONEST placeholder convention for a
    # citation gap the V4 fetch-and-verify pipeline could not resolve --
    # not a template leftover, a disclosed and separately-counted state.
    # Round-two positioning response (commissioned second review): the
    # expanded Related Work section intentionally carries new
    # [CITE-NEEDED: ...] gaps rather than inventing unverified citations,
    # per this artifact's own citation-gate discipline; forbidding the
    # literal token here would make honest disclosure a gate failure.
    forbidden = {
        "**": tex.count("**"),
        "```": tex.count("```"),
        "[GENERATED": tex.count("[GENERATED"),
    }
    hits = {k: v for k, v in forbidden.items() if v}
    return {
        "pass": not hits,
        "forbidden_token_counts": forbidden,
        "cite_needed_placeholder_count": tex.count("[CITE"),
    }


# ---------------------------------------------------------------------------
# Shared text extraction helpers
# ---------------------------------------------------------------------------

def _trim_bibliography(text: str) -> str:
    """The auto-generated \\bibliography{refs} apparatus (dates, DOIs,
    arXiv ids, access timestamps, page footers) is LaTeX/bibtex output,
    not content from the source markdown -- which has no References
    section at all. G3's number multiset compares the PAPER's own
    numbers, so the bibliography is excluded from both sides the same
    way it is simply absent from the source."""
    # The heading is preceded by "\n" in reflow mode but by a form-feed
    # page-break marker ("\x0c") in -layout mode, not "\n" -- matched
    # with a regex on either preceding control character rather than a
    # literal substring so both extraction modes trim correctly.
    m = re.search(r"[\n\x0c]References[\n\x0c]", text)
    return text[:m.start()] if m else text


def _strip_page_footers(text: str) -> str:
    """-layout mode preserves each page's centered page-number footer as
    its own line -- pagination, not paper content, and not present in
    the source markdown at all. Dropped before G3's number comparison."""
    return "\n".join(l for l in text.splitlines() if not re.fullmatch(r"\s*\d+\s*", l))


def _strip_repeated_page_furniture(text: str) -> str:
    """Round-three normalization item 3: remove a repeated short-title
    running header, if the document has one. main.tex sets no
    \\pagestyle{fancy}/\\lhead/\\rhead (plain LaTeX article default: page
    numbers only, already handled by _strip_page_footers), so this is
    currently a no-op for this specific paper -- kept as its own,
    independently testable step (rather than folded into
    _strip_page_footers) so the canonical five-item normalization list
    stays literally enumerable in code, and so it activates unchanged if
    a running header is ever added.

    MUST run on -layout output before _strip_page_footers, which
    collapses pdftotext's raw "\\x0c" page-break markers into plain "\\n"
    (str.splitlines() treats form-feed as a line boundary) -- once that
    happens there is no per-page structure left to detect a POSITIONAL
    repeat against. Detection is deliberately positional, not a whole-
    document frequency count: only a page's own first non-blank line is
    a candidate, and only if that exact line recurs as the first line of
    at least half the document's pages (a genuine running header's
    signature). A frequency count over every line in the document would
    misfire on ordinary repeated short content -- e.g. this paper's
    Appendix B artifact-manifest JSON listing repeats "}," and a
    License field verbatim across three separate manifest entries, which
    are real content appearing at unrelated positions on their pages,
    not a header repeating at the same position on every page."""
    pages = text.split("\x0c")
    if len(pages) < 3:
        return text
    first_lines = []
    for p in pages:
        candidates = [l for l in p.splitlines() if l.strip()]
        first_lines.append(candidates[0].strip() if candidates else None)
    threshold = max(3, len(pages) // 2)
    furniture = {l for l, n in Counter(l for l in first_lines if l is not None).items() if n >= threshold}
    if not furniture:
        return text
    out_pages = []
    for p in pages:
        lines = p.splitlines()
        idx = next((i for i, l in enumerate(lines) if l.strip()), None)
        if idx is not None and lines[idx].strip() in furniture:
            lines = lines[:idx] + lines[idx + 1:]
        out_pages.append("\n".join(lines))
    return "\x0c".join(out_pages)


def extract_pdf_text() -> str:
    """Layout-preserving extraction: repeated-header, bibliography, and
    page-number-footer normalization, in that order (furniture detection
    needs the raw \\x0c page markers _strip_page_footers destroys) --
    used by G3's number-multiset comparison."""
    r = run(["pdftotext", "-layout", str(MAIN_PDF), "-"])
    text = _strip_repeated_page_furniture(r.stdout)
    text = _trim_bibliography(text)
    return _strip_page_footers(text)


def extract_pdf_text_reflow() -> str:
    """Reflowed (non-layout) extraction of the FULL document including
    the bibliography, with the repeated-header normalization (round-three
    canonical item 3) applied -- used by G6's disclosure/banner check.
    Also strips bare-digit page-number footer lines the same way the
    -layout pipeline does (_strip_page_footers): reflow mode still emits
    each page's centered page number as its own line between the
    "\\x0c" page-break markers, and this revision's longer pagination
    newly puts a page break (and so a bare page-number line) inside a
    sentence that G6 matches verbatim -- not a content difference, a
    pagination artifact of the same kind G3 already normalizes away."""
    r = run(["pdftotext", str(MAIN_PDF), "-"])
    return _strip_page_footers(_strip_repeated_page_furniture(r.stdout))


def extract_pdf_text_layout_full() -> str:
    """Layout-preserving extraction of the FULL document (bibliography
    included, page footers stripped) -- used by G4's section slicing and
    sentence-sample check. Layout mode keeps each \\section's auto-number
    on the same physical line as its title (reflow mode sometimes splits
    them across a page boundary, e.g. Table 9's longtable ending right
    where \\section{Related work} begins drops the "10" from reflow's
    output entirely) and lets dehyphenate() correctly rejoin a compound
    word broken at its own hyphen across a line wrap; the bibliography is
    kept (not trimmed) since section slicing needs the "References"
    heading intact as the end-of-document anchor, but page-number footers
    are stripped -- otherwise a footer digit can land mid-sentence after
    whitespace normalization (e.g. "...has an 11 admissible profile.",
    the page-11 footer bleeding into running prose). Repeated-header
    normalization (round-three canonical item 3) is applied first, for
    the same \\x0c-ordering reason documented on extract_pdf_text."""
    r = run(["pdftotext", "-layout", str(MAIN_PDF), "-"])
    return _strip_page_footers(_strip_repeated_page_furniture(r.stdout))


def extract_md_pandoc() -> str:
    r = run(["pandoc", "-f", "markdown", "-t", "plain", str(SOURCE_MD)])
    return r.stdout


NUMBER_RE = re.compile(
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b"       # 17,151 / 1,064
    r"|\b\d+\.\d+(?:[eE][-+]?\d+)?\b"          # 2.045230 / 3.77e-6 / 0.975
    r"|\b\d+[eE][-+]?\d+\b"                    # bare scientific notation
    r"|\b\d+\b"                                # plain integers
)


def dehyphenate(text: str) -> str:
    """Rejoin words split across a line-wrap hyphen (a PDF-text-extraction
    artifact, not a content difference -- e.g. 'pending-human-\\nreview'
    from a natural line break coinciding with the compound word's own
    hyphen). Only joins lowercase-continuation breaks, so it never
    merges an intentional end-of-line hyphenated compound with an
    unrelated following word. Tolerates optional whitespace between the
    newline and the continuation letter (verified: "weekly-commitment"
    wraps as "weekly-\\n commitment" -- -layout mode's column
    reconstruction leaves the next line's own leading indentation space
    intact -- so a bare "-\\n(?=[a-z])" lookahead misses it and a stray
    "weekly- commitment" survives into the normalized text). Also rejoins
    a scientific-notation exponent marker split across the same kind of
    line-wrap (e.g. "3.77e-\\n6" -- pdftotext wrapping mid-token at the
    exponent sign, exposed by this revision's longer pagination): a
    trailing "e-"/"e+"/"E-"/"E+" immediately before the line break,
    followed by a continuation digit, is rejoined the same way."""
    text = re.sub(r"-\n\s*(?=[a-z])", "-", text)
    return re.sub(r"([eE][-+])\n\s*(?=\d)", r"\1", text)


def extract_numbers(text: str) -> Counter:
    text = dehyphenate(text)
    return Counter(NUMBER_RE.findall(text))


# ---------------------------------------------------------------------------
# G3: Number parity
# ---------------------------------------------------------------------------

# The paper's own headline numeric claims (task spec: "the values
# 150/200, 86/243 ... must each be individually asserted present").
REQUIRED_VALUES = ["150", "200", "86", "243"]

# PROOF-STATUS tag classes: substring occurrence counts, not numeric
# tokens (task spec: "the tag counts 21, 26, 7"). Checked against the
# SOURCE's own counts (computed, not hardcoded) so the gate stays valid
# if the source ever changes, with the task's stated values asserted as
# a sanity check on top.
#
# "machine-checked": 21 -> 20 (front-matter cleanup task): the removed
# front-matter version-history paragraph ("...full machine-checked or
# human-reviewed proofs for every numbered claim.") contained one
# incidental PROSE use of the word "machine-checked", not a
# PROOF-STATUS tag -- appendix-a-proofs.md's own tag population (the
# authoritative source every real tag is drawn from) is completely
# unchanged by this edit (still 13 machine-checked/10 checked-scope-
# only/4 pending-human-review there), and checked-scope-only/pending-
# human-review's whole-document counts (26/7) are likewise untouched,
# since that paragraph never mentioned either phrase. Verified directly:
# `grep -c 'PROOF-STATUS: machine-checked'
# paper4-composition-draft-v0.5-populated.md` is unchanged at 5 (every
# formal tag line still present) before and after this removal.
TAG_PHRASES = ["machine-checked", "checked-scope-only", "pending-human-review"]
TASK_STATED_TAG_COUNTS = {"machine-checked": 20, "checked-scope-only": 26, "pending-human-review": 7}

# Round-three response (R3-F2/closes R3-F3): the round-three review's own
# reproduction of this gate found the SAME single explainable delta this
# gate already allowlisted, but the committed report only ever printed
# the post-exception (empty) diff, leaving the raw 689-vs-688 totals
# unexplained on their own. This is now printed as three explicit tiers
# (see gate_g3_number_parity's return value: raw_diff, exceptions_applied,
# post_exception_diff) instead of only the last one -- a single,
# understood PDF-text-extraction artifact: math-mode $2^{31}$ (Appendix
# C's [1, 2^31-1] range, non-negotiable #4's required math mode for
# interval notation) has its superscript "31" concatenated onto the base
# "2" with no separator by pdftotext, since PDF has no baseline-shift
# marker in its text layer -- extracting as "231" instead of "2" and
# "31". This is a property of PDF text extraction, not a content change
# (the visible glyphs are correct: 2 with 31 raised); allowlisted
# explicitly rather than silently ignored.
KNOWN_EXTRACTION_ARTIFACTS = {"missing_from_pdf": {"31": 1, "2": 1}, "added_in_pdf": {"231": 1}}


def gate_g3_number_parity() -> dict:
    md_text = SOURCE_MD.read_text()
    pdf_text = extract_pdf_text()

    md_numbers = extract_numbers(md_text)
    pdf_numbers = extract_numbers(pdf_text)

    # Tier 1: raw totals and raw diff, before any allowlisted exception.
    raw_missing_from_pdf = md_numbers - pdf_numbers
    raw_added_in_pdf = pdf_numbers - md_numbers

    # Tier 2: the enumerated allowlist itself, and which of its entries
    # actually matched the raw diff computed just above (so a change
    # that makes an allowlisted entry stop matching shows up here as
    # "matched": false rather than silently vanishing).
    exceptions_applied = []
    post_missing_from_pdf = Counter(raw_missing_from_pdf)
    post_added_in_pdf = Counter(raw_added_in_pdf)
    for tok, n in KNOWN_EXTRACTION_ARTIFACTS["missing_from_pdf"].items():
        matched = post_missing_from_pdf.get(tok) == n
        exceptions_applied.append({"side": "missing_from_pdf", "token": tok, "count": n, "matched": matched})
        if matched:
            del post_missing_from_pdf[tok]
    for tok, n in KNOWN_EXTRACTION_ARTIFACTS["added_in_pdf"].items():
        matched = post_added_in_pdf.get(tok) == n
        exceptions_applied.append({"side": "added_in_pdf", "token": tok, "count": n, "matched": matched})
        if matched:
            del post_added_in_pdf[tok]

    # Tier 3: post-exception totals -- what G3 actually gates on.
    post_exception_diff_empty = not post_missing_from_pdf and not post_added_in_pdf

    required_present = {n: (pdf_numbers.get(n, 0) > 0) for n in REQUIRED_VALUES}

    md_dehyph = dehyphenate(md_text)
    pdf_dehyph = dehyphenate(pdf_text)
    tag_counts = {}
    for phrase in TAG_PHRASES:
        src_count = md_dehyph.count(phrase)
        pdf_count = pdf_dehyph.count(phrase)
        tag_counts[phrase] = {
            "source_count": src_count,
            "pdf_count": pdf_count,
            "task_stated_count": TASK_STATED_TAG_COUNTS[phrase],
            "equal": src_count == pdf_count == TASK_STATED_TAG_COUNTS[phrase],
        }

    ok = (
        post_exception_diff_empty
        and all(required_present.values())
        and all(t["equal"] for t in tag_counts.values())
    )
    return {
        "pass": ok,
        "raw_totals": {
            "md_number_token_count": sum(md_numbers.values()),
            "pdf_number_token_count": sum(pdf_numbers.values()),
        },
        "raw_diff": {
            "missing_from_pdf": dict(raw_missing_from_pdf),
            "added_in_pdf": dict(raw_added_in_pdf),
        },
        "exceptions_applied": exceptions_applied,
        "post_exception_totals": {
            "md_number_token_count": sum(md_numbers.values()),
            "pdf_number_token_count": sum(pdf_numbers.values()) - sum(
                e["count"] for e in exceptions_applied if e["side"] == "added_in_pdf" and e["matched"]
            ) + sum(
                e["count"] for e in exceptions_applied if e["side"] == "missing_from_pdf" and e["matched"]
            ),
        },
        "post_exception_diff": {
            "missing_from_pdf": dict(post_missing_from_pdf),
            "added_in_pdf": dict(post_added_in_pdf),
        },
        "required_values_present": required_present,
        "tag_counts": tag_counts,
    }


# ---------------------------------------------------------------------------
# G4: Prose parity
# ---------------------------------------------------------------------------

# Standard LaTeX typography renders the plain ASCII apostrophe/quote
# characters the source markdown uses as typographic (curly) glyphs --
# a font-rendering upgrade, not a content change, but pdftotext extracts
# the resulting glyphs as their own Unicode code points rather than the
# ASCII originals. Normalized away before any text comparison.
_QUOTE_NORMALIZE = {
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    # LaTeX math mode renders "*" as the math asterisk-operator glyph
    # (U+2217), not the ASCII asterisk -- unavoidable font behavior for
    # any math-mode "*" (r^*, L^*, s^*, ...), not a content choice.
    "\u2217": "*",
    # $a'$ (math mode) renders the apostrophe as a prime symbol (U+2032),
    # not an apostrophe glyph -- the source's a' throughout Section 5's
    # remediated-context notation.
    "\u2032": "'",
    # pandoc's own "smart typography" upgrades the source markdown's "--"
    # into a real en dash when rendering to plain text -- exactly the
    # em/en-dash introduction non-negotiable #5 forbids, but it is
    # pandoc's transformation for this gate script's OWN extraction
    # convenience, not something introduced into the PDF (which keeps
    # the source's literal "--", dash-ligature-protected as "-{}-" in
    # main.tex). Reversed here so the two sides compare like for like.
    "\u2013": "--",
    # Round-three response (finding R3-F2): Tectonic's font handling
    # renders the standard "ff"/"fi"/"fl"/"ffi"/"ffl" typographic
    # ligatures as their own single Unicode ligature codepoints
    # (U+FB00-FB04) with no reverse ToUnicode mapping back to the
    # letter sequence -- pdftotext then extracts the ligature glyph
    # itself, e.g. "Buffer" as "Bu\ufb00er". latexmk/pdflatex's default
    # Latin Modern fonts decompose the same ligatures back to plain
    # ASCII on extraction, so this is a compiler-specific rendering
    # difference (verified directly: "Bu\ufb00er poisoning" is what
    # Tectonic's own build of this exact main.tex extracts), not a
    # content difference -- the visible glyphs are the same ligature
    # either way.
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl",
}


def normalize_ws(text: str) -> str:
    text = dehyphenate(text)
    text = text.replace("\u00ad", "")
    for uni, ascii_ in _QUOTE_NORMALIZE.items():
        text = text.replace(uni, ascii_)
    # Math mode's prime glyph (the U+2032 normalized to "'" just above,
    # e.g. $a'$, $c(a')$ throughout Section 5's remediated-context
    # notation) carries its own kerning box, which pdftotext extracts as
    # a trailing space before whatever punctuation immediately follows
    # it -- "(a' , c(a' ), E(a' ))" instead of "(a', c(a'), E(a'))". Not
    # present when "'" is a plain ASCII apostrophe already (contractions
    # like "gate's" never get a following comma/paren directly, so this
    # cannot misfire on those).
    text = re.sub(r"'\s+([,)])", r"'\1", text)
    text = re.sub(r"\s+", " ", text)
    # \path{}'s line-breaking (used for long code identifiers that would
    # otherwise overfull a narrow line) leaves no hyphen at the break --
    # unlike a hyphenated word, so dehyphenate() above has nothing to
    # rejoin -- and layout-mode extraction of the two now-separate lines
    # leaves a literal space where the identifier broke, e.g.
    # "test_repeated_identical_writes_stay_ individually_resolvable".
    # A space directly against an underscore is never genuine content in
    # either source or PDF, so it is collapsed here as an extraction
    # artifact, not a text difference.
    text = re.sub(r"\s*_\s*", "_", text)
    # "sum_i"/"sum_j" (source ASCII for \sum_i, \sum_j) reduce to just
    # the bare subscript letter once \sum's own glyph is stripped below
    # ("P i", not "P" "i" merged as "Pi") -- removed here, before the
    # "P" strip, rather than merged like the other subscripts further
    # down, since \sum's base symbol vanishes entirely on extraction
    # instead of concatenating onto its subscript.
    text = re.sub(r"\bsum_([a-zA-Z])\b", r"\1", text)
    # \sum has no usable ToUnicode mapping in this font/toolchain combo
    # and pdftotext extracts it as a stray "P" (verified directly: even
    # a small-size inline $\sum_i w_i$ -- not just the big display-style
    # operator -- extracts as "P i wi", never the correct summation
    # glyph or nothing at all). This is a known pdftotext/Latin-Modern-
    # math limitation, not a font choice available to fix here, and
    # \sum is non-negotiable #4's own required rendering for the leave-
    # one-out weight sums it appears in. "P" never otherwise occurs as
    # a standalone word in this paper (verified against the source), so
    # dropping it here is unambiguous.
    text = re.sub(r"(?<![A-Za-z0-9])P(?![A-Za-z0-9])\s*", "", text)
    # The source's "--" prose dash (dash-ligature-protected in main.tex
    # as "-{}-" so it never becomes a real em/en dash -- non-negotiable
    # #5) is always written " -- " with a surrounding space on each
    # side, but pdftotext's layout extraction occasionally drops the
    # space on one side depending on exactly where the "-{}-" glyph pair
    # falls relative to the rest of the line's spacing; canonicalized
    # here to " -- " on both sides so a dropped space is not mistaken
    # for missing/altered content.
    text = re.sub(r"\s*(?<!-)--(?!-)\s*", " -- ", text)
    text = re.sub(r"\s+", " ", text)
    # Same \path{}-break-leaves-a-space artifact as the underscore case
    # above, but at the identifier's "." this time: \path{composition.
    # Response^3} (Corollary 2's Statement) extracts as "composition.
    # Response^3" with a space nowhere in the source's single-token
    # identifier. Narrowly targeted to this one known identifier rather
    # than collapsing every "word. Capitalized" -- that pattern is
    # ordinary sentence-boundary punctuation everywhere else.
    text = text.replace("composition. Response^3", "composition.Response^3")
    # Same class of artifact again: plain prose "reachability/
    # executability" (no \path/\texttt -- an ordinary compound, not a
    # code identifier) happens to line-wrap at its own "/" in -layout
    # mode, and pdftotext leaves a space there too. Not generalized to
    # every "/" in the document: "(stdev / sqrt(30))" genuinely has
    # spaces around its slash in the source itself.
    text = text.replace("reachability/ executability", "reachability/executability")
    # Same class of artifact again: the OASIS XACML citation URL
    # (Section 9/10 related work) happens to line-wrap in -layout mode
    # at its own "." between "docs" and "oasis-open.org", with no
    # hyphen to rejoin (a straight break, not a hyphenated compound) --
    # "https://docs.\noasis-open.org/..." collapses to "docs.
    # oasis-open.org" once \s+ above merges the newline to a space.
    # Not generalized to every URL in the document: this is the only
    # URL long enough to wrap mid-domain at all.
    text = text.replace("https://docs. oasis-open.org", "https://docs.oasis-open.org")
    # Math mode's default comma spacing: $[0,1]$ (non-negotiable #4's
    # required math-mode interval notation) typesets with a small space
    # after the comma by convention, which pdftotext extracts as a real
    # space character -- "[0, 1]" -- though the source's literal
    # characters are "[0,1]" with none. A property of math-mode commas
    # generally, not just this interval, but scoped to this exact
    # bracketed pattern to stay conservative.
    text = re.sub(r"\[0, 1\]", "[0,1]", text)
    # Math mode's italic-correction kerning before an open paren
    # following the single-letter function name "f" (this paper's only
    # aggregator, used as $f(s)$ throughout) is wide enough that
    # pdftotext extracts it as a literal space -- "f (s)" -- though
    # \texttt{f(s)} (used where the source backticks it as code)
    # extracts with no space at all, confirming this is a math-mode
    # rendering property, not a source difference.
    text = re.sub(r"\bf \(", "f(", text)
    # Same italic-correction kerning artifact as "f (" above, but for
    # \rhosub/\rhoroute (Section 5's remediation-operator notation,
    # applied throughout: $\rhosub(a)$, $\rhoroute(a')$, ...) --
    # "ρsub (a)" instead of "ρsub(a)".
    text = re.sub(r"ρsub \(", "ρsub(", text)
    text = re.sub(r"ρroute \(", "ρroute(", text)
    # [0,1]^n (a math-mode superscript, same class of loss as 2^{31} and
    # composition.Response^3 above) loses the caret entirely against a
    # letter exponent -- "[0,1]n" -- with no leftover marker to recover
    # the boundary from, unlike a digit exponent concatenating onto a
    # digit base.
    text = text.replace("[0,1]n with", "[0,1]^n with")
    # Every math-mode subscript on this paper's small set of single-
    # letter base symbols (s, w, L, r, G, a, W -- score, weight,
    # leave-one-out sum, response, gate, action, total weight) loses its
    # underscore separator on extraction the same way \sum's glyph is
    # lost above -- verified directly for e.g. "a_exec" -> "aexec",
    # "G_i" -> "Gi", "r_1..r_n" -> "r1..rn", "min_i w_i" -> "mini wi".
    # Scoped to exactly these seven bases (not a blanket "any
    # identifier_suffix" pattern) so it cannot misfire on this
    # document's actual multi-word \texttt/\path code identifiers
    # (score_encoding, ch5_aggregator.py, buffer_write_eid,
    # remediate_regate, GateDecision.evidence_ids, ...), none of which
    # begin with a bare "s"/"w"/"L"/"r"/"G"/"a"/"W" immediately followed
    # by "_".
    text = re.sub(r"\b(s|w|L|r|G|a|W)_([A-Za-z0-9]+)\b", r"\1\2", text)
    # The same subscript's own math-mode kerning also leaves a stray
    # space before a closing paren directly following it -- e.g. "gate
    # $G_i$ maps $(a, c, E, s_i)$" extracts as "...E, si )" instead of
    # "...E, si)" -- verified directly against Section 2's gate
    # definition, the one place in this document a subscripted symbol
    # sits immediately before a closing paren. English prose never puts
    # a space directly before a closing paren, so collapsing it
    # generally is unambiguous rather than one more scoped phrase (same
    # policy already applied to "s1+s2+s3"/"f(1,1,1)"/"n=3" above).
    text = re.sub(r"\s+\)", ")", text)
    # "tau becomes \tau" (non-negotiable #4, this paper's admission
    # threshold symbol) is the same class of unconditional rewrite as
    # "rho becomes \rho" below -- verified the same way: every bare
    # "tau" in the source (28 occurrences) is this one threshold symbol,
    # never a different sense, so safe to rewrite everywhere rather than
    # scoping to specific phrases (the previous scoped-phrase approach
    # in _SANCTIONED_NOTATION missed sentences outside those two exact
    # phrases, e.g. Section 3's own counterexample narrative and the
    # Necessity proof's "f(s) < tau" step -- both real prose, not table
    # garbage, that a HEAD-seeded sentence sample can land on).
    text = re.sub(r"\btau\b", "τ", text)
    # Compact algebraic "+"/"=" between single-letter-subscript terms
    # (s1+s2+s3, f(1,1,1), n=3) render with math-mode's default spacing
    # around binary operators -- "s1 + s2 + s3", "f(1, 1, 1)", "n = 3"
    # -- the same class of loss as "," and "f(" above. Previously
    # applied only to whichever section's word-count text a caller
    # explicitly patched (gate_g4_prose_parity's per-section loop);
    # moved here so the sentence-sample check (which calls normalize_ws
    # directly, not through that per-section loop) gets the same
    # normalization instead of missing it.
    text = text.replace("s1+s2+s3", "s1 + s2 + s3")
    text = text.replace("f(1,1,1)", "f(1, 1, 1)")
    text = re.sub(r"\bn=3\b", "n = 3", text)
    text = text.replace("f's", "f 's")
    # A math-mode close followed directly by punctuation (e.g. "$\tau$:"
    # in the Necessity proof's "So $f(s) < \tau$: $s$ is not admitted")
    # keeps the inline-math box's own trailing kerning space when
    # pdftotext extracts it -- "τ : s is not admitted" -- though the
    # source has no space before the colon. English prose never puts a
    # space before a colon in this document, so collapsing it generally
    # is unambiguous rather than one more scoped phrase.
    text = re.sub(r"\s+:", ":", text)
    return text.strip()


MD_SECTION_ANCHORS = {
    "1. Introduction": "1. Introduction",
    "2. Model and terminology": "2. Model and terminology",
    "3. Hard constraints versus compensatory aggregation": "3. Hard constraints versus compensatory aggregation",
    "4. Single-remediator composition": "4. Single-remediator composition",
    "5. Multi-remediator composition": "5. Multi-remediator composition",
    "6. Stateful governance and evidence-buffer contamination": "6. Stateful governance and evidence-buffer contamination",
    "7. The unified Evidence Set": "7. The unified Evidence Set",
    "8. Empirical validation": "8. Empirical validation",
    "9. Related work": "9. Related work",
    "10. Limitations and open theory": "10. Limitations and open theory",
    "11. Conclusion": "11. Conclusion",
    "Appendix A. Proofs": "Appendix A. Proofs",
    "Appendix B. Artifact manifest": "Appendix B. Artifact manifest",
    "Appendix C. Statistical methodology (V3 gate)": "Appendix C. Statistical methodology (V3 gate)",
    "Validation note": "Validation note",
}


def md_section_slices() -> dict:
    """pandoc's plain-text rendering of the source (per the task spec:
    "extract plain text from both -- pandoc for the md, pdftotext for
    the PDF") -- markdown table pipes/dashes/heading hashes are not
    prose and have no equivalent in the typeset PDF, so raw-markdown
    line slicing (this function's earlier implementation) inflated the
    source's word counts with syntax that was never content.

    Searches sequentially (search_from advances past each match), the
    same way pdf_section_slices() already does -- otherwise an anchor
    that also appears as an earlier cross-reference in running prose
    (e.g. "Validation note" mentioned in the front-matter version note,
    well before its own heading further down) matches that earlier
    occurrence instead of the section's real heading, corrupting every
    boundary that depends on it (v0.5 third-review response, item S8:
    exposed by moving Validation note to back matter, after Appendix C,
    while a front-matter sentence still references it by name)."""
    r = run(["pandoc", "-f", "markdown", "-t", "plain", str(SOURCE_MD)])
    text = normalize_ws(r.stdout)

    positions = {}
    search_from = 0
    for title in SECTION_TITLES:
        anchor = MD_SECTION_ANCHORS[title]
        idx = text.find(anchor, search_from)
        if idx == -1:
            idx = text.find(anchor)
        positions[title] = idx
        if idx != -1:
            search_from = idx + len(anchor)

    order = SECTION_TITLES
    slices = {}
    for pos, title in enumerate(order):
        start = positions[title]
        end = None
        for later in order[pos + 1:]:
            if positions[later] != -1:
                end = positions[later]
                break
        slices[title] = text[start:end] if start != -1 else ""
    return slices


PDF_SECTION_ANCHORS = {
    "1. Introduction": "1 Introduction",
    "2. Model and terminology": "2 Model and terminology",
    "3. Hard constraints versus compensatory aggregation": "3 Hard constraints versus compensatory aggregation",
    "4. Single-remediator composition": "4 Single-remediator composition",
    "5. Multi-remediator composition": "5 Multi-remediator composition",
    "6. Stateful governance and evidence-buffer contamination": "6 Stateful governance",
    "7. The unified Evidence Set": "7 The unified Evidence Set",
    "8. Empirical validation": "8 Empirical validation",
    "9. Related work": "9 Related work",
    "10. Limitations and open theory": "10 Limitations and open theory",
    "11. Conclusion": "11 Conclusion",
    "Appendix A. Proofs": "A Proofs",
    "Appendix B. Artifact manifest": "B Artifact manifest",
    "Appendix C. Statistical methodology (V3 gate)": "C Statistical methodology (V3 gate)",
    "Validation note": "Validation note",
    "__END__": "References",
}


def pdf_section_slices() -> dict:
    # Anchors are matched against whitespace-normalized text so the
    # (possibly multi-space, layout-padded) gap between a \section's
    # auto-number and its title collapses to the single space the
    # anchor strings use.
    text = normalize_ws(extract_pdf_text_layout_full())
    order = SECTION_TITLES + ["__END__"]
    positions = []
    search_from = 0
    for title in order:
        anchor = PDF_SECTION_ANCHORS[title]
        idx = text.find(anchor, search_from)
        if idx == -1:
            idx = text.find(anchor)
        positions.append(idx)
        if idx != -1:
            search_from = idx + len(anchor)

    slices = {}
    for pos, title in enumerate(SECTION_TITLES):
        start = positions[pos]
        end = None
        for later in positions[pos + 1:]:
            if later != -1:
                end = later
                break
        if start == -1:
            slices[title] = ""
            continue
        slices[title] = text[start:end] if end else text[start:]
    return slices


def word_count(text: str) -> int:
    return len(normalize_ws(text).split())


def deterministic_sentence_indices(sentences: list[str], head: str, k: int = 10) -> list[int]:
    n = len(sentences)
    if n == 0:
        return []
    idxs = []
    seed = head
    i = 0
    while len(idxs) < min(k, n):
        h = hashlib.sha256(f"{seed}:{i}".encode()).hexdigest()
        cand = int(h, 16) % n
        if cand not in idxs:
            idxs.append(cand)
        i += 1
    return sorted(idxs)


def split_sentences(text: str) -> list[str]:
    # Split on blank-line paragraph breaks FIRST, while they still exist
    # in the input -- otherwise a heading like the next section's "9.
    # Claims to evidence" glues onto the end of the prior paragraph's
    # last sentence once normalize_ws collapses all whitespace to single
    # spaces, since nothing then marks where one paragraph ended and the
    # next (a bare number followed by a title) began.
    # Also split before a pandoc bullet-list marker: pandoc does not put
    # a blank line between consecutive list items (only between the list
    # and surrounding prose), so without this a list item's text glues
    # onto the end of the PRECEDING item once normalize_ws below
    # collapses all whitespace to single spaces -- e.g. "...label-only.
    # - CH3 (deterministic selectivity)." reading as one bogus "sentence"
    # instead of two real ones.
    #
    # G4 repair (Perplexity brief, "Make Pandoc list splitting robust"):
    # the installed Pandoc version emits some lists with a single space
    # after the marker ("- A1. Determinism. ...") and others with three
    # ("-   CH3 (...)"), and mixes both within one document -- the old
    # three-space-only pattern let a single-space marker glue onto the
    # PRECEDING item's last sentence (verified: "...control-local state.
    # - A2." read as one bogus sentence). Anchored to the line start
    # (re.MULTILINE "^" only matches right after a newline, never
    # mid-line) and requiring one-or-more spaces after a single "-"
    # subsumes both marker widths in one general rule without ever
    # matching a mid-line prose hyphen or compound word (e.g.
    # "cross-control", "pre-action") or a dashed table/rule line (those
    # have a second "-" or non-space character immediately after the
    # first, never whitespace). Leading [ \t]* tolerates an indented
    # (nested) list marker the same way. Not special-cased to the A1/A2
    # text itself -- see test_run_gates.py for the regression coverage.
    text = re.sub(r"(?m)^[ \t]*-[ \t]+", "\n\n", text)
    paragraphs = re.split(r"\n\s*\n", text)
    out = []
    for para in paragraphs:
        # Math-density is checked on the RAW paragraph, before
        # normalize_ws below merges subscript underscores away (e.g.
        # "s_j" -> "sj") -- checking post-normalize text would miss
        # exactly the paragraphs this filter exists to catch, since
        # their math notation is already gone by the time a per-
        # sentence check would see it. Whole-PARAGRAPH exclusion (not
        # just the individual math-heavy sentence) also naturally
        # excludes a short plain-prose sentence that shares a paragraph
        # with math-dense neighbors -- e.g. "Let s be any vetoed
        # profile, s_j = 0 for some j." immediately follows the
        # "*Necessity (...)*" proof-step header inside the SAME
        # paragraph, and inherits that header's -layout column-
        # interleaving artifact (see the header-exclusion note below)
        # even though this one sentence has no math notation of its own
        # once merged.
        if re.search(r"[_^]|>=|<=|\bmax\b|\bmin\b|\bsum\b", para):
            continue
        # A pandoc-rendered pipe-table row with no leading numeric/letter
        # ID column (e.g. the Claims-versus-non-claims table's two bare
        # prose columns) is invisible to the "^CH?\d+\s" ID-prefix filter
        # below, but has the same "no single linear reading order" defect
        # as the tables that filter does catch: pandoc's plain-text
        # renderer lays each row out as side-by-side fixed-width columns
        # padded with a multi-space gutter (verified: "Evidence Sets
        # preserve identity     Hashes alone reconstruct source\n
        # commitments                         bytes" -- reading this
        # RAW, PRE-normalize_ws paragraph top-to-bottom/left-to-right
        # yields "...identity Hashes alone reconstruct source
        # commitments bytes", column 1's wrapped second line landing
        # after the whole of column 2's first line). Ordinary prose
        # paragraphs from pandoc's plain renderer never contain a run of
        # 3+ spaces (word-wrapped prose uses single spaces throughout),
        # so a raw paragraph with two or more such gutters is a reliable,
        # general signature of "this is a rendered table row, not
        # prose" -- catching any future bare-column table the same way,
        # not just this one's specific row text.
        if len(re.findall(r"  {2,}", para)) >= 2:
            continue
        para = normalize_ws(para)
        if not para:
            continue
        # Appendix A's five "Why this changed." rationale notes narrate,
        # in ordinary prose, the SAME symbols (tau, f, s1/s2/s3, ...)
        # this paper's main body states in math mode -- but main.tex
        # hand-typesets these five notes' backtick-code spans as
        # \texttt (verified: Proposition 1's note renders `tau > 0` as
        # \texttt{tau > 0}, literal ASCII), while the main-body sentence
        # making the identical point (Section 3's own "aggregator f
        # admit a iff f(s) >= tau with tau > 0") renders the same content
        # in math mode ($\tau$). One normalize_ws pass cannot give the
        # bare word "tau" two different target spellings depending on
        # which of these two paragraphs it came from, so byte-exact
        # sentence matching against these five notes is not a meaningful
        # check -- same rationale as the Table 9/Table 8 row exclusion
        # above. The word-count check (2% tolerance, not byte-exact)
        # still covers this content, since Appendix A's word count
        # includes these notes either way.
        if para.startswith("Why this changed."):
            continue
        # Simple sentence splitter: break after . ! ? followed by a space
        # and a capital letter/quote, skipping the many mid-sentence
        # abbreviation dots this paper uses (e.g. "e.g.", "et al.",
        # "v0.3", code identifiers).
        raw = re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", para)
        for s in raw:
            s = s.strip()
            # A markdown "---" horizontal-rule line (source's table/
            # section dividers) can glue onto the table caption right
            # after it once blank lines collapse (e.g. "---...---
            # Table 6."); filtered out by requiring most characters be
            # letters, which no rule-dominated fragment satisfies.
            if len(s) <= 20 or sum(c.isalpha() for c in s) / len(s) <= 0.5:
                continue
            # pandoc's plain-text rendering of a wide multi-column table
            # (e.g. Table 9, Claims to evidence) sometimes still has
            # enough alphabetic content over its whole run-on fragment to
            # survive the ratio filter above -- the actual signature of
            # "this is a rendered table, not prose" is its own dashed
            # column-rule ("---...---"), which real prose in this paper
            # never contains a run of 4+ literal hyphens of (verified:
            # zero occurrences in the source markdown).
            if re.search(r"-{4,}", s):
                continue
            # A Table 8 (Hypotheses) or Table 9 (Claims to evidence) row,
            # e.g. "CH2 (single-pass unsoundness, new semantics)" | True"
            # or "C9 Full reproducibility seed list, ...": a multi-
            # column table cell wrapped across several lines has no
            # single well-defined linear reading order once extracted
            # (columns can and do interleave -- e.g. this exact CH2 row
            # extracts as "...new True semantics)", the next column's
            # "True" landing mid-cell), so exact-sentence matching
            # against it is not a meaningful check -- G3's number
            # multiset and G5's table count already verify these
            # tables' actual content.
            if re.match(r"^CH?\d+\s", s):
                continue
            # Appendix A's short italic proof-step headers ("Necessity
            # (...)", "Sufficiency (...)", "Min. (...)") and its
            # Proposition/Lemma/Theorem/Corollary N (...) statement
            # headers are typeset as their own short line immediately
            # preceding a much longer paragraph. -layout mode's column
            # reconstruction sometimes interleaves the tail of one such
            # short header with the START of the following paragraph
            # (verified: "Necessity (tau > L* implies no vetoed profile
            # is admitted)." extracts with an unrelated sentence spliced
            # in the middle of its own closing parenthetical) -- a
            # genuine pdftotext positional artifact for this specific
            # short-line-before-long-paragraph shape, not a content
            # difference. Separately, a Corollary/Proposition/etc.
            # heading's parenthetical is sometimes punctuated differently
            # in main.tex's theorem-environment title argument than in
            # the source markdown's own heading line (e.g. "Corollary 1
            # (X, Y -- Z)" in source vs "Corollary 1 (X, Y) -- Z" in the
            # \begin{corollary}[...] optional argument) -- semantically
            # identical, a hand-typesetting punctuation choice, not a
            # dropped or altered claim. Both classes are headings, not
            # prose: G5's theorem-environment count and the per-section
            # word-count check above already verify them; excluded here
            # the same way Table 8/9 rows are.
            if re.match(r"^(Necessity|Sufficiency|Min\.|Proposition \d|Lemma \d|Theorem \d|Corollary \d)\s*\(", s):
                continue
            out.append(s)
    return out


def _md_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def front_matter_metadata() -> dict:
    """G4 repair (Perplexity brief, "Handle front-matter metadata
    semantically", preferred option 1): structural front matter, not
    prose. By this artifact's own fixed convention (see PAPER_DRAFT_TEXT's
    opening in paper_v3.py), the source markdown's first blank-line-
    separated paragraph is the H1 title and its second is the
    "Name (Affiliation)" author byline -- title and author identity, not
    a sentence a random prose sample should ever land on (verified
    failure mode: "Gaston Besanson (Universidad Torcuato Di Tella)" has
    no sentence-ending punctuation, so the naive splitter kept it whole
    and a hash-selected sample landed on it, where LaTeX intentionally
    renders the affiliation as a \\thanks{} footnote rather than inline
    markdown-author-line syntax). Position-based (paragraph 1, paragraph
    2), not a literal match on any one author's name, so this keeps
    working under a future title/author change without editing this
    function -- the general, structured solution the brief asks for
    instead of a one-off substitution."""
    paragraphs = _md_paragraphs(SOURCE_MD.read_text())
    title = paragraphs[0].lstrip("#").strip() if paragraphs else ""
    author_line = paragraphs[1].strip() if len(paragraphs) > 1 else ""
    # The established "Name (Affiliation)" convention (paper_v3.py's own
    # front matter, unchanged by this repair) -- splitting on the last
    # top-level parenthetical is a structural parse of that convention,
    # not a hardcoded name.
    m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", author_line)
    author_name = m.group(1).strip() if m else author_line
    affiliation = m.group(2).strip() if m else ""
    body_md = "\n\n".join(paragraphs[2:])
    return {
        "title": title,
        "author_name": author_name,
        "affiliation": affiliation,
        "body_md": body_md,
    }


def front_matter_check(fm: dict) -> dict:
    """The deterministic check the brief requires in place of sampling
    front matter as prose: title, author name, and affiliation must each
    be present in both the populated Markdown source and main.tex, and
    this fails if any of them is removed or materially changed --
    exactly the "structured metadata, verified separately" half of the
    chosen repair."""
    tex = MAIN_TEX.read_text()

    title_m = re.search(r"\\title\{([^\n]*)\}", tex)
    author_m = re.search(r"\\author\{([^\n]*)\}", tex)
    tex_title = title_m.group(1).strip() if title_m else ""
    tex_author_raw = author_m.group(1).strip() if author_m else ""

    # \thanks{...} is this document's chosen footnote-affiliation macro
    # (non-inline, per v0.5 item S11) -- its argument is the affiliation,
    # and everything in \author{...} before it is the author's name.
    thanks_m = re.search(r"\\thanks\{([^\n}]*)\}", tex_author_raw)
    tex_affiliation = thanks_m.group(1).strip() if thanks_m else ""
    tex_author_name = (tex_author_raw[:thanks_m.start()] if thanks_m else tex_author_raw).strip()
    # \\ (a manual LaTeX line break, used by some author-block styles)
    # is not part of the name itself.
    tex_author_name = re.sub(r"\\\\\s*$", "", tex_author_name).strip()

    title_ok = bool(fm["title"]) and fm["title"] == tex_title
    author_ok = bool(fm["author_name"]) and fm["author_name"] == tex_author_name
    affiliation_ok = bool(fm["affiliation"]) and fm["affiliation"] == tex_affiliation

    return {
        "pass": title_ok and author_ok and affiliation_ok,
        "title": {"md": fm["title"], "tex": tex_title, "match": title_ok},
        "author_name": {"md": fm["author_name"], "tex": tex_author_name, "match": author_ok},
        "affiliation": {"md": fm["affiliation"], "tex": tex_affiliation, "match": affiliation_ok},
    }


# The literal substitutions non-negotiable #4 mandates for a hash-
# selected sentence to ever be able to match byte-for-byte against the
# typeset PDF (math-mode symbols, the \proofstatus bracket convention,
# subscript-underscore loss, ...) -- hoisted to module level (out of
# gate_g4_prose_parity's body) so both the gate and its own regression/
# robustness tests in test_run_gates.py apply the exact same transform,
# not a re-implementation that could silently diverge from it.
_SANCTIONED_NOTATION = {
    "admit < substitute < degrade < escalate < block": "admit ⊑ substitute ⊑ degrade ⊑ escalate ⊑ block",
    "(R, max) is a join semilattice.": "(R, ⊔) is a join semilattice.",
    "r* = max_i r_i": "r* = ⊔i ri",
    "sum_i w_i s_i": "i wi si",
    "iff f(s) >= tau for tau > 0.": "iff f(s) ≥τ for τ > 0.",
    "weights w_i >= 0,": "weights wi ≥ 0,",
    "authority cap kappa strictly between the order values": "authority cap κ strictly between the order values",
    # The A1-A7 assumptions block's closing line (Section 4, v0.5 item
    # S5) is plain English prose in the source ("A1 and A2 and ... imply
    # per-action soundness") but non-negotiable #4's math-mode mandate
    # renders it as a logical formula in main.tex ($A_1 \land A_2 \land
    # ... \Rightarrow \mathit{PerActionSoundness}$) -- verified directly
    # against the typeset PDF: "A1 ∧ A2 ∧ A3 ∧ A4 ∧ A5 ∧ A6 ∧ A7 ⇒
    # PerActionSoundness (Definition 3)." A hash-selected sentence
    # landing on this one line can never match byte-for-byte without
    # this translation, the same rationale as every other entry above.
    "Read together: A1 and A2 and A3 and A4 and A5 and A6 and A7 imply per-action soundness (Definition 3).":
        "Read together: A1 ∧ A2 ∧ A3 ∧ A4 ∧ A5 ∧ A6 ∧ A7 ⇒ PerActionSoundness (Definition 3).",
}


def _normalize_sentence_for_pdf_match(sentence: str) -> str:
    """The exact transform a sampled source sentence undergoes before
    G4's substring-containment check against the typeset PDF -- see each
    _SANCTIONED_NOTATION entry and the inline rho/PROOF-STATUS/subscript
    rewrites below for what each one is for and why it is safe."""
    plain = sentence
    for src, tgt in _SANCTIONED_NOTATION.items():
        plain = plain.replace(src, tgt)
    plain = re.sub(r"\brho_sub\b", "ρsub", plain)
    plain = re.sub(r"\brho_route\b", "ρroute", plain)
    plain = re.sub(r"\brho\b", "ρ", plain)
    plain = re.sub(
        r"PROOF-STATUS: (pending-human-review|machine-checked|checked-scope-only \(REVIEW\.md\))",
        r"[PROOF-STATUS: \1]",
        plain,
    )
    plain = re.sub(r"\b([A-Za-z]+)_([a-z])\b", r"\1\2", plain)
    return normalize_ws(plain)


def gate_g4_prose_parity() -> dict:
    # Informational only -- NOT the sampling seed (see source_sha256
    # below). checkers/_provenance.py already establishes
    # generated_at_head_sha as an informational-only field elsewhere in
    # this repo (round-two response, finding R2-F1(b)); G4 now follows
    # the same convention instead of inventing a second one, per the
    # Perplexity brief's Provenance rule.
    generated_at_head_sha = run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT)).stdout.strip()

    md_slices = md_section_slices()
    pdf_slices = pdf_section_slices()

    section_report = {}
    all_within = True
    for title in SECTION_TITLES:
        md_section_text = md_slices.get(title, "")
        # \appendix mode's auto-numbering prints just "A"/"B"/"C" before
        # a \section title, not the word "Appendix" the source markdown
        # heading spells out ("Appendix A. Proofs") -- standard LaTeX
        # appendix convention, not a dropped word. Negligible against
        # Appendix A/C's ~5000/~175-word bodies but a full percentage
        # point on Appendix B's 44-word one, so normalized here to keep
        # the word-count comparison about the section's actual prose.
        # Only the slice's OWN leading heading, not every later
        # cross-reference to "Appendix A"/"Appendix B" inside other
        # sections' body prose (which correctly keeps the word
        # "Appendix" on both sides and must not be touched).
        for letter in ("A", "B", "C"):
            prefix = f"Appendix {letter}."
            if md_section_text.startswith(prefix):
                md_section_text = letter + md_section_text[len(prefix):]
                break
        # Math mode's standard operator spacing (already documented above
        # for "," and "="; the same applies to "+") turns a source's
        # compact "s1+s2+s3"/"f(1,1,1)"/"n=3" into visibly spaced
        # "s1 + s2 + s3"/"f(1, 1, 1)"/"n = 3" -- each splitting one
        # source word-count token into two or three PDF ones. Handled
        # inside normalize_ws itself (word_count() calls it below), so
        # both this section-level check and the sentence-sample check
        # further down get the same normalization from one place.
        md_wc = word_count(md_section_text)
        pdf_wc = word_count(pdf_slices.get(title, ""))
        if md_wc == 0:
            pct = None
            within = pdf_wc == 0
        else:
            pct = abs(pdf_wc - md_wc) / md_wc * 100
            within = pct <= 2.0
        all_within = all_within and within
        section_report[title] = {
            "md_words": md_wc,
            "pdf_words": pdf_wc,
            "pct_diff": round(pct, 3) if pct is not None else None,
            "within_2pct": within,
        }

    # G4 repair (Perplexity brief, "Handle front-matter metadata
    # semantically", preferred option 1): title/author are structured
    # identity, checked separately by front_matter_check() below, and
    # excluded here from the population the random prose sample is drawn
    # from -- body_md is the source markdown with its first two
    # paragraphs (title, author byline) stripped, everything else
    # (companion-artifact line, version history, Abstract, all numbered
    # sections) unchanged and still sampled.
    fm = front_matter_metadata()
    metadata_check = front_matter_check(fm)

    # pandoc's plain rendering, not raw markdown: raw markdown's table
    # pipes/bullet hyphens/**bold**/*italic*/`code` markup have no
    # equivalent in the typeset PDF and would either leak into the
    # sampled sentence text or (for bullet markers) let the naive
    # sentence splitter glue two adjacent list items into one bogus
    # "sentence" that can never match anything. Piped via stdin (not a
    # temp file) since the population being sampled is body_md, not the
    # whole of SOURCE_MD.
    md_plain = run(["pandoc", "-f", "markdown", "-t", "plain"], input=fm["body_md"]).stdout
    md_sentences = split_sentences(md_plain)

    # G4 repair (GPT doc's P1, "Make G4 deterministic from manuscript
    # content, not Git HEAD"): same principle already applied to CH7's
    # off-grid probe (prereg/probe-seeds.json, round-two response
    # R2-F1(b)) for the identical class of issue -- the sampling seed is
    # now a hash of the manuscript's own bytes, so the same manuscript
    # content always selects the same ten sentences regardless of commit
    # SHA, branch, or packaging/README-only commits. generated_at_head_sha
    # above remains informational provenance only, per
    # checkers/_provenance.py's documented design.
    source_sha256 = hashlib.sha256(SOURCE_MD.read_bytes()).hexdigest()
    idxs = deterministic_sentence_indices(md_sentences, source_sha256, k=10)
    sample_sentences = [md_sentences[i] for i in idxs]

    # -layout mode, not reflow: reflow's own internal line-joining drops
    # the hyphen from a compound word broken exactly at that hyphen at a
    # line wrap (e.g. "quarantine-and-substitute" -> "quarantine-and
    # substitute", the hyphen silently vanishing) -- a real PDF-text-
    # extraction data loss, not present when -layout's explicit line
    # breaks are rejoined by this module's own dehyphenate().
    pdf_text_norm = normalize_ws(extract_pdf_text_layout_full())

    sentence_report = []
    for i, s in zip(idxs, sample_sentences):
        plain = _normalize_sentence_for_pdf_match(s)
        found = plain in pdf_text_norm
        sentence_report.append({"index": i, "sentence": s[:120], "found": found})

    all_sentences_found = all(r["found"] for r in sentence_report)

    ok = all_within and all_sentences_found and metadata_check["pass"]
    return {
        "pass": ok,
        "source_sha256": source_sha256,
        "generated_at_head_sha": generated_at_head_sha,
        "sections": section_report,
        "front_matter_metadata_check": metadata_check,
        "sentence_sample": sentence_report,
    }


# ---------------------------------------------------------------------------
# G5: Structure parity
# ---------------------------------------------------------------------------

def gate_g5_structure_parity() -> dict:
    md_text = SOURCE_MD.read_text()
    tex_text = MAIN_TEX.read_text()

    md_section_count = len(SECTION_TITLES)  # by construction (see SECTION_TITLES)
    # Also counts the one starred \section*{Validation note} (v0.5 third-
    # review response, item S8): moved to back matter as an unnumbered
    # section -- like the appendices' lettering, it should not carry a
    # body section NUMBER, but it is still one of the document's real
    # SECTION_TITLES entries and must count as a section here the same
    # way the lettered \section{Proofs} etc. already do.
    tex_section_count = len(re.findall(r"^\\section\*?\{", tex_text, re.MULTILINE))

    md_table_count = len(re.findall(r"^\|[\s:|-]+\|\s*$", md_text, re.MULTILINE))
    tex_table_count = len(re.findall(r"^\\begin\{table\}", tex_text, re.MULTILINE)) + \
        len(re.findall(r"^\\begin\{longtable\}", tex_text, re.MULTILINE))

    md_theorem_headers = len(re.findall(
        r"^## (?:Proposition|Lemma|Theorem|Corollary) \d", md_text, re.MULTILINE
    ))
    md_definition_count = len(re.findall(r"^Definition \d+ \(", md_text, re.MULTILINE))
    md_theorem_env_count = md_theorem_headers + md_definition_count

    tex_theorem_env_count = sum(
        len(re.findall(rf"^\\begin\{{{env}\}}", tex_text, re.MULTILINE))
        for env in ("proposition", "lemma", "theorem", "corollary", "definition")
    )

    md_footnote_count = len(re.findall(r"\[\^\w+\]", md_text))
    tex_footnote_count = len(re.findall(r"\\footnote\{", tex_text))

    checks = {
        "sections": (md_section_count, tex_section_count),
        "tables": (md_table_count, tex_table_count),
        "theorem_environments": (md_theorem_env_count, tex_theorem_env_count),
        "footnotes": (md_footnote_count, tex_footnote_count),
    }
    ok = all(a == b for a, b in checks.values())
    return {
        "pass": ok,
        "counts": {k: {"source": a, "tex": b, "equal": a == b} for k, (a, b) in checks.items()},
    }


# ---------------------------------------------------------------------------
# G6: Disclosure and banners
# ---------------------------------------------------------------------------

DISCLOSURE_FIRST_SENTENCE = (
    "This artifact was independently replicated and adversarially reviewed "
    "in four rounds by automated agents following the published protocols "
    "in sarc-suite-agent-review.md, sarc-suite-agent-review-r2.md, "
    "sarc-suite-agent-review-r3.md, and sarc-suite-agent-review-r4.md; the "
    "round-one report and evidence are at review/REVIEW.md and "
    "review/review.json, the round-two report and evidence are at "
    "review-out-r2/REVIEW-R2.md, review-out-r2/review.json, and "
    "review-out-r2/evidence/, the round-three report and evidence are at "
    "review-out-r3/REVIEW-R3.md, review-out-r3/review.json, and "
    "review-out-r3/evidence/, and the round-four report and evidence are "
    "at review-out-r4/REVIEW-R4.md, review-out-r4/review.json, and "
    "review-out-r4/evidence/."
)
# Round-four response: the paper now presents this sentence as a
# QUOTATION from the round-four report (see main.tex's Validation note),
# not as the paper's own unqualified first-person claim -- the
# quotation-mark glyphs around it are typographic wrapping, not part of
# the sentence itself, so the substring check above (unchanged) still
# finds it exactly.
PROCESS_PROVENANCE_SENTENCE = (
    "Process provenance: the review protocols were authored by the "
    "author's AI assistant before each round and are committed in this "
    "repository; the reviews were commissioned by the author and "
    "executed by a separate vendor's automated agent in fresh sessions "
    "with access only to this public repository; adjudication between "
    "rounds was performed by the same assistant that authored the "
    "protocols and is not independent; every mechanical claim in the "
    "review reports is re-runnable from this repository."
)
ACKNOWLEDGEMENTS_SENTENCE = (
    "Drafting, engineering, review automation, and a positioning review "
    "were AI-assisted (Claude, Perplexity, and OpenAI GPT systems); the "
    "author is solely responsible for all claims."
)
DISCLOSURE_LAST_SENTENCE = (
    "This draft is the artifact's response to that review: findings F1-F6 "
    "(review/REVIEW.md Section 4) are fixed or weakened per the review's "
    "own binding-unless-fixed policy, never argued with in this text; the "
    "proof-tag reclassifications in Appendix A (checked-scope-only for "
    "Proposition 3 and Lemma 1, sufficiency-only for Corollary 1) follow "
    "the review's Section 3 proof-tag policy exactly, and no tag here "
    "claims more than that review certified."
)
HONESTY_BANNERS = [
    "Scope honesty. This paper claims composition semantics and a "
    "mechanism demonstration. It does not claim production prevalence, "
    "uses no model calls, and its artifact is not a GIGO-Bench release.",
    "Negative-results commitment. Any CH not supported as written is "
    "reported as NOT SUPPORTED as written, following the practice of the "
    "prior papers -- CH6 under W2 is the concrete instance of this "
    "commitment in this version.",
]


def gate_g6_disclosure_and_banners() -> dict:
    pdf_text = normalize_ws(extract_pdf_text_reflow())
    # The source's own "--" prose dash is typeset dash-ligature-protected
    # (`-{}-`) but detexes/extracts back to a plain double hyphen; strip
    # any stray "{}" artifacts defensively before matching.
    pdf_text_for_match = pdf_text

    def present(snippet: str) -> bool:
        return normalize_ws(snippet) in pdf_text_for_match

    disclosure_first = present(DISCLOSURE_FIRST_SENTENCE)
    disclosure_last = present(DISCLOSURE_LAST_SENTENCE)
    process_provenance = present(PROCESS_PROVENANCE_SENTENCE)
    acknowledgements = present(ACKNOWLEDGEMENTS_SENTENCE)
    banners = {b[:50]: present(b) for b in HONESTY_BANNERS}

    ok = (
        disclosure_first
        and disclosure_last
        and process_provenance
        and acknowledgements
        and all(banners.values())
    )
    return {
        "pass": ok,
        "disclosure_first_sentence_present": disclosure_first,
        "disclosure_last_sentence_present": disclosure_last,
        "process_provenance_sentence_present": process_provenance,
        "acknowledgements_sentence_present": acknowledgements,
        "honesty_banners_present": banners,
    }


# ---------------------------------------------------------------------------
# G7: arXiv sidecar sync (v0.4 final-feedback item F7)
# ---------------------------------------------------------------------------
# The reviewer's second finding: paper-tex/arxiv-abstract.txt and
# paper-tex/arxiv-metadata.txt are hand-maintained sidecars, not
# generated from the manuscript, and had drifted -- the abstract sidecar
# still carried v0.3's "This paper studies what none answer" framing
# after the manuscript itself was rewritten around remediation-induced
# control coupling, and the metadata sidecar still said "completeness"
# with no completeness theorem anywhere in the paper. This gate makes
# that drift a release-check failure instead of something only caught by
# a second commissioned review.

ARXIV_ABSTRACT_MAX_CHARS = 1900
ARXIV_ABSTRACT_REQUIRED_PHRASE = "remediation-induced control coupling"
ARXIV_ABSTRACT_LEGACY_PHRASE = "none answer"
ARXIV_METADATA_FORBIDDEN_PHRASE = "completeness"


def gate_g7_sidecar_sync() -> dict:
    abstract_text = ARXIV_ABSTRACT.read_text()
    metadata_text = ARXIV_METADATA.read_text()

    abstract_len = len(abstract_text.rstrip("\n"))
    has_required_phrase = ARXIV_ABSTRACT_REQUIRED_PHRASE in abstract_text
    has_legacy_phrase = ARXIV_ABSTRACT_LEGACY_PHRASE in abstract_text
    within_length = abstract_len <= ARXIV_ABSTRACT_MAX_CHARS
    metadata_has_completeness = ARXIV_METADATA_FORBIDDEN_PHRASE in metadata_text.lower()

    ok = has_required_phrase and not has_legacy_phrase and within_length and not metadata_has_completeness
    return {
        "pass": ok,
        "abstract_char_count": abstract_len,
        "abstract_within_max_chars": within_length,
        "abstract_has_required_phrase": has_required_phrase,
        "abstract_has_legacy_phrase": has_legacy_phrase,
        "metadata_has_completeness": metadata_has_completeness,
    }


# ---------------------------------------------------------------------------
# G8: citation completeness (v0.4 final-feedback item F7)
# ---------------------------------------------------------------------------
# The reviewer's recommendation: "Make unresolved [CITE-NEEDED]
# placeholders a release-check failure for release candidates." Mirrors
# citation_check.py's own CITE_PLACEHOLDER_PATTERN rather than importing
# it, matching this script's existing self-contained-gate-script
# convention (no cross-directory imports from repo root elsewhere in
# this file). Both token forms count: [CITE-NEEDED: ...] (an unresolved
# gap) and [CITE: ...] (this artifact's older placeholder spelling, from
# v0.1/v0.2 -- neither should survive into a populated release candidate).

CITE_PLACEHOLDER_PATTERN = re.compile(r"\[CITE[-:][^\]]*\]")


def gate_g8_citation_completeness() -> dict:
    text = SOURCE_MD.read_text()
    matches = CITE_PLACEHOLDER_PATTERN.findall(text)
    count = len(matches)
    return {
        "pass": count == 0,
        "cite_placeholder_count": count,
        "cite_placeholders": matches,
    }


# ---------------------------------------------------------------------------
# G9: Bibliography quality (v0.5 release-gate repair, GPT recommendations
# doc's P0: "Add a bibliography-quality gate")
# ---------------------------------------------------------------------------
# Before this repair, verified-citations.json stored only citation
# identity (url, title, first_author, year, doi/arxiv_id); a multi-author
# paper rendered in refs.bib with only its first author, and every
# reference emitted as @misc regardless of whether it was actually a
# journal article or conference paper. This gate makes that a release-
# check failure instead of a hand-noticed publication-quality gap,
# enforcing exactly the checks the recommendations doc lists.

VALID_ENTRY_TYPES = {"article", "inproceedings", "incollection", "misc"}
# entry_type -> the venue field(s) required for that type, per the GPT
# doc's explicit rules ("article -> journal + year required",
# "inproceedings -> booktitle + year required"); incollection is the
# same "chapter within a larger work" shape as inproceedings (a book
# instead of a proceedings volume) and is held to the same booktitle
# requirement for consistency, since the doc's own suggested schema
# gives incollection entries a booktitle field too.
REQUIRED_VENUE_FIELDS_BY_TYPE = {
    "article": ("journal",),
    "inproceedings": ("booktitle",),
    "incollection": ("booktitle",),
}


def _load_generate_refs_bib_module():
    # Cross-directory import (paper-tex/generate_refs_bib.py from
    # paper-tex/gates/run_gates.py) via importlib rather than a sys.path
    # hack -- loaded purely to call its generate() function in memory
    # (no file write), so this check never mutates refs.bib itself.
    spec = importlib.util.spec_from_file_location(
        "generate_refs_bib", str(PAPER_TEX_DIR / "generate_refs_bib.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gate_g9_bibliography_quality() -> dict:
    data = json.loads(CITATIONS_JSON.read_text())
    citations = data["citations"]

    invalid_entry_type = []
    missing_authors = []
    missing_venue_fields = []
    doi_mismatches = []
    misc_with_venue_info = []
    audit_drift = []

    refs_bib_text = REFS_BIB.read_text() if REFS_BIB.exists() else ""

    # Errata closure protocol, item E2: "Extend G9 to check volume and
    # venue consistency against stored authoritative metadata where a
    # DOI exists." This gate never calls Crossref/DataCite itself --
    # gates in this repo stay deterministic and offline-capable by
    # convention (compare G1's own artifact-based, non-log-dependent
    # design) -- so instead it re-checks the CURRENT verified-
    # citations.json values against review-secondary/bib-audit.json's
    # one-time audited-authoritative snapshot (every DOI-bearing entry's
    # own venue/volume, recorded whether or not the audit found a
    # mismatch). A future hand-edit that silently drifts a DOI-bearing
    # entry's volume or venue away from its audited value becomes a
    # failure here. Skipped (not failed) if the audit file is absent,
    # since it is a one-time supplementary artifact, not a required
    # input the pipeline itself generates on every run.
    audit_by_id = {}
    if BIB_AUDIT_JSON.exists():
        audit_by_id = {r["id"]: r for r in json.loads(BIB_AUDIT_JSON.read_text()).get("results", [])}

    for c in citations:
        cid = c.get("id", "<no id>")
        entry_type = c.get("entry_type")

        if entry_type not in VALID_ENTRY_TYPES:
            invalid_entry_type.append({"id": cid, "entry_type": entry_type})
            continue

        # "all scholarly citations have full author lists": every entry
        # must carry a non-empty authors array, and first_author (kept
        # for citation_check.py's schema check) must agree with its
        # first element -- catches the pre-repair failure mode directly
        # (a stored first_author with no authors array at all, silently
        # dropping every co-author).
        authors = c.get("authors")
        if not authors or c.get("first_author") != authors[0]:
            missing_authors.append({"id": cid, "authors": authors, "first_author": c.get("first_author")})

        # "article -> journal + year required" / "inproceedings ->
        # booktitle + year required": year is already a REQUIRED_FIELD
        # citation_check.py's own schema check enforces on every entry,
        # so only the type-specific venue field is checked here.
        for field in REQUIRED_VENUE_FIELDS_BY_TYPE.get(entry_type, ()):
            if not c.get(field):
                missing_venue_fields.append({"id": cid, "entry_type": entry_type, "missing_field": field})

        # "all DOI-bearing references preserve DOI exactly": the DOI
        # string generate_refs_bib.py writes into refs.bib must be
        # byte-identical to the DOI stored here, not merely present.
        if "doi" in c:
            expected_doi_line = f"doi = {{{c['doi']}}},"
            if expected_doi_line not in refs_bib_text and not refs_bib_text.rstrip().endswith(expected_doi_line.rstrip(",") + "}"):
                # doi is virtually never the last field written (url/note
                # always follow it in _entry()), so the comma-terminated
                # form is the expected one; the endswith fallback only
                # guards against a future field-order change.
                doi_mismatches.append({"id": cid, "doi": c["doi"]})

        # GPT doc's "@misc only when unverifiable" rule, in its concrete
        # automatable form: an entry cannot simultaneously be tagged
        # misc (no formal venue) and carry a journal/booktitle field --
        # that combination is itself a contradiction this gate can catch
        # without a human judgment call about what "unverifiable" means.
        if entry_type == "misc" and (c.get("journal") or c.get("booktitle")):
            misc_with_venue_info.append({"id": cid, "journal": c.get("journal"), "booktitle": c.get("booktitle")})

        # Volume/venue consistency against the audited snapshot (see
        # above): DOI-bearing entries only, matching the audit's own
        # scope (a citation with no DOI has no Crossref/DataCite record
        # to audit venue/volume against in the first place).
        if "doi" in c:
            audit_entry = audit_by_id.get(cid)
            if audit_entry is not None:
                venue_field = audit_entry.get("authoritative_venue_field")
                authoritative_venue = audit_entry.get("authoritative_venue")
                if venue_field and authoritative_venue is not None and c.get(venue_field) != authoritative_venue:
                    audit_drift.append({
                        "id": cid, "field": venue_field,
                        "current": c.get(venue_field), "audited": authoritative_venue,
                    })
                authoritative_volume = audit_entry.get("authoritative_volume")
                if authoritative_volume is not None and c.get("volume") != authoritative_volume:
                    audit_drift.append({
                        "id": cid, "field": "volume",
                        "current": c.get("volume"), "audited": authoritative_volume,
                    })

    # "generated refs.bib matches verified-citations.json": regenerate
    # in memory (never writes to disk) and compare byte-for-byte against
    # the committed file -- the same drift check G7 already applies to
    # the arXiv sidecar files, applied here to the bibliography.
    grb = _load_generate_refs_bib_module()
    expected_refs_bib = grb.generate()
    refs_bib_matches = refs_bib_text == expected_refs_bib

    ok = (
        not invalid_entry_type
        and not missing_authors
        and not missing_venue_fields
        and not doi_mismatches
        and not misc_with_venue_info
        and not audit_drift
        and refs_bib_matches
    )
    return {
        "pass": ok,
        "total_citations": len(citations),
        "invalid_entry_type": invalid_entry_type,
        "missing_authors": missing_authors,
        "missing_venue_fields": missing_venue_fields,
        "doi_mismatches": doi_mismatches,
        "misc_with_venue_info": misc_with_venue_info,
        "audit_drift": audit_drift,
        "bib_audit_checked": bool(audit_by_id),
        "refs_bib_matches_generator": refs_bib_matches,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    results = {
        "G1_build": gate_g1_build(),
        "G2_token_purity": gate_g2_token_purity(),
        "G3_number_parity": gate_g3_number_parity(),
        "G4_prose_parity": gate_g4_prose_parity(),
        "G5_structure_parity": gate_g5_structure_parity(),
        "G6_disclosure_and_banners": gate_g6_disclosure_and_banners(),
        "G7_sidecar_sync": gate_g7_sidecar_sync(),
        "G8_citation_completeness": gate_g8_citation_completeness(),
        "G9_bibliography_quality": gate_g9_bibliography_quality(),
    }
    all_pass = all(g["pass"] for g in results.values())
    report = {"all_pass": all_pass, "gates": results}

    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True))

    print(json.dumps(report, indent=2, sort_keys=True))
    print()
    for name, g in results.items():
        print(f"{name}: {'PASS' if g['pass'] else 'FAIL'}")
    print()
    print("ALL GATES PASS" if all_pass else "GATE FAILURE -- see detail above")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
