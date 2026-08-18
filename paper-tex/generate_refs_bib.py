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
arXiv LaTeX conversion, non-negotiable #2: "Every citation in refs.bib is
generated from verified-citations.json, nothing else. No new references.
If a reference lacks a BibTeX-required field, derive it only from the
verified record's stored fields."

This script is that generator: it reads exactly verified-citations.json
(../verified-citations.json relative to this file) and writes one BibTeX
entry per citation record. Every BibTeX field below maps 1:1 to a
verified-citations.json key:

  id           -> citation key (BibTeX entry key)
  entry_type   -> @article / @inproceedings / @incollection / @misc
  authors      -> author (full " and "-joined list; falls back to
                  first_author only for a record with no authors array)
  title        -> title
  year         -> year
  journal      -> journal      (article only, if present)
  booktitle    -> booktitle    (inproceedings/incollection only, if present)
  volume       -> volume       (only if present)
  number       -> number       (only if present)
  pages        -> pages        (only if present)
  publisher    -> publisher    (only if present)
  doi          -> doi          (only if present in the record)
  arxiv_id     -> eprint + archivePrefix={arXiv}  (only if present)
  url          -> url
  verified_via -> note (audit trail: how/when this repo verified it)

Release-gate repair (v0.5 P0, bibliography quality): entry_type used to
be hardcoded to @misc uniformly because verified-citations.json never
stored a journal/booktitle field, so every reference -- including
multi-author journal articles and conference papers -- rendered with
only its first author and no venue. entry_type/authors/venue fields are
now fetched and stored per record (see verified-citations.json's own
_schema_note); this generator only maps what is already there, deriving
nothing new and never guessing a field the stored record lacks. A
record with no entry_type (should not occur post-repair, but handled
defensively) still renders as @misc as before, so this stays backward-
compatible with rendering an unaudited record.

Deterministic and idempotent: re-running with an unchanged
verified-citations.json produces a byte-identical refs.bib. Run this
script directly, or via `make -C paper-tex/.. arxiv` which regenerates
refs.bib on every build so it can never drift from verified-citations.json.
"""
from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CITATIONS_PATH = SCRIPT_DIR.parent / "verified-citations.json"
OUT_PATH = SCRIPT_DIR / "refs.bib"

_BIB_ESCAPES = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
}

_ENTRY_TYPE_TO_BIBTEX = {
    "article": "article",
    "inproceedings": "inproceedings",
    "incollection": "incollection",
    "misc": "misc",
}

# entry_type -> which stored field is this type's venue field, if any.
_VENUE_FIELD_BY_TYPE = {
    "article": "journal",
    "inproceedings": "booktitle",
    "incollection": "booktitle",
}


def _escape(value: str) -> str:
    return "".join(_BIB_ESCAPES.get(ch, ch) for ch in value)


def _author_field(citation: dict) -> str:
    authors = citation.get("authors")
    if authors:
        return " and ".join(_escape(a) for a in authors)
    return _escape(citation["first_author"])


def _entry(citation: dict) -> str:
    key = citation["id"]
    bib_type = _ENTRY_TYPE_TO_BIBTEX.get(citation.get("entry_type"), "misc")
    lines = [f"@{bib_type}{{{key},"]
    lines.append(f"  author = {{{_author_field(citation)}}},")
    lines.append(f"  title = {{{{{_escape(citation['title'])}}}}},")
    lines.append(f"  year = {{{citation['year']}}},")
    venue_field = _VENUE_FIELD_BY_TYPE.get(citation.get("entry_type"))
    if venue_field and venue_field in citation:
        lines.append(f"  {venue_field} = {{{_escape(citation[venue_field])}}},")
    for field in ("volume", "number", "pages", "publisher"):
        if field in citation:
            lines.append(f"  {field} = {{{_escape(str(citation[field]))}}},")
    if "doi" in citation:
        lines.append(f"  doi = {{{citation['doi']}}},")
    if "arxiv_id" in citation:
        lines.append(f"  eprint = {{{citation['arxiv_id']}}},")
        lines.append("  archivePrefix = {arXiv},")
    lines.append(f"  url = {{{citation['url']}}},")
    lines.append(f"  note = {{{_escape(citation['verified_via'])}}},")
    lines[-1] = lines[-1].rstrip(",")  # no trailing comma on the last field
    lines.append("}")
    return "\n".join(lines)


def generate() -> str:
    data = json.loads(CITATIONS_PATH.read_text())
    citations = data["citations"]
    header = (
        "% Generated by paper-tex/generate_refs_bib.py from verified-citations.json.\n"
        "% Do not hand-edit -- every field is derived from that file's stored\n"
        "% records alone (arXiv LaTeX conversion task, non-negotiable #2).\n"
        f"% {len(citations)} entries.\n\n"
    )
    return header + "\n\n".join(_entry(c) for c in citations) + "\n"


if __name__ == "__main__":
    data = json.loads(CITATIONS_PATH.read_text())
    text = generate()
    OUT_PATH.write_text(text)
    print(f"wrote {OUT_PATH} ({len(data['citations'])} entries)")
