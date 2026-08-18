# Final Recommendations for SARC v0.5

These are the only two repository changes I recommend before submission.

Do **not** add new experiments, new workflows, new remediation operators, concurrency, delegation, production datasets, or broader theory to this paper.

The science is now sufficiently mature. The remaining work is publication and reproducibility cleanup.

---

# P0. Fix the scholarly bibliography metadata

## Problem

The citation-verification pipeline currently stores mainly:

- `first_author`
- `title`
- `year`
- `doi` / `url`

and `paper-tex/refs.bib` is generated from that reduced metadata.

As a result, multi-author papers are rendered with only the first author and many references are emitted as `@misc`, even when the underlying publication is a journal article, conference paper, proceedings chapter, or standard.

For example, the current generated BibTeX for *Compositional Runtime Enforcement* contains only:

```bibtex
author = {Srinivas Pinisetty}
```

even though the work has multiple authors.

The same issue affects other multi-author references.

This is **not a scientific-validity problem**, because the DOI/title identity is correct, but it is a publication-quality problem and should be fixed before submission.

---

## Recommendation

Extend `verified-citations.json` so it preserves full bibliographic metadata rather than only citation identity.

Suggested structure:

```json
{
  "id": "pinisetty-tripakis-compositional-enforcement",
  "entry_type": "inproceedings",
  "authors": [
    "Srinivas Pinisetty",
    "Stavros Tripakis"
  ],
  "title": "Compositional Runtime Enforcement",
  "year": 2016,
  "booktitle": "NASA Formal Methods",
  "pages": "82-99",
  "doi": "10.1007/978-3-319-40648-0_7",
  "url": "https://doi.org/10.1007/978-3-319-40648-0_7",
  "verified_via": "..."
}
```

For journal articles, use fields such as:

```json
{
  "entry_type": "article",
  "authors": [
    "...",
    "...",
    "..."
  ],
  "journal": "...",
  "volume": "...",
  "number": "...",
  "pages": "...",
  "year": 2022,
  "doi": "..."
}
```

For standards or webpages, keep `@misc` where appropriate.

---

## Required generator changes

Update `paper-tex/generate_refs_bib.py` so it maps:

- `entry_type = article` -> `@article`
- `entry_type = inproceedings` -> `@inproceedings`
- `entry_type = incollection` -> `@incollection`
- `entry_type = misc` -> `@misc`

and writes the full author list in BibTeX form:

```bibtex
author = {Author One and Author Two and Author Three}
```

The verification pipeline should remain strict.

Do **not** weaken citation verification. Improve the metadata captured during verification.

---

## Add a bibliography-quality gate

Add a release gate that fails if a scholarly reference:

- has only `first_author` when the verified source has multiple authors;
- lacks an `authors` array;
- lacks the required publication fields for its declared `entry_type`;
- is emitted as `@misc` when its verified metadata identifies it as a journal or conference publication.

Suggested checks:

```text
all scholarly citations have full author lists
all entry_type values are valid
article -> journal + year required
inproceedings -> booktitle + year required
all DOI-bearing references preserve DOI exactly
generated refs.bib matches verified-citations.json
```

This should become part of `make release-check`.

---

# P1. Make G4 deterministic from manuscript content, not Git HEAD

## Problem

The G4 prose-parity gate currently derives its deterministic sentence sample from:

```python
git rev-parse HEAD
```

The helper then hashes that HEAD value to choose sample sentences.

This means the same manuscript content committed under a different Git SHA can select a different set of parity sentences.

The current committed parity report was generated while the repository HEAD was the immediately preceding review commit, before the final v0.5 commit was created.

This is not a correctness failure, but it weakens the meaning of:

> deterministic / byte-reproducible manuscript validation

because the parity sample is partly a property of repository history rather than manuscript content.

The repository has already solved the same class of issue elsewhere by removing HEAD-derived randomness from the CH7 off-grid probe.

G4 should follow the same principle.

---

## Recommendation

Derive the G4 sampling seed from the manuscript source itself.

Instead of:

```python
head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
idxs = deterministic_sentence_indices(sentences, head, k=10)
```

use something like:

```python
source_hash = hashlib.sha256(SOURCE_MD.read_bytes()).hexdigest()
idxs = deterministic_sentence_indices(sentences, source_hash, k=10)
```

This gives the desired invariant:

```text
same manuscript bytes
    ->
same G4 sentence sample
```

regardless of:

- commit SHA;
- branch;
- repository packaging commit;
- README-only edits;
- review-report commits.

---

## Better provenance field

Change the report field from:

```json
"repo_head": "..."
```

to something like:

```json
"source_sha256": "..."
```

Optionally keep:

```json
"generated_at_head_sha": "..."
```

as informational provenance only.

The release gate should depend on `source_sha256`, not Git HEAD.

---

## Why this is better

A reproducibility gate should be a deterministic function of the artifact it validates.

Formally:

\[
G4 = f(M)
\]

where \(M\) is the manuscript content.

It should not be:

\[
G4 = f(M, GitHistory)
\]

unless repository history is part of the scientific claim being tested.

For prose parity, it is not.

---

# Do not change the scientific content further

Do not add:

- more seeds;
- another workflow;
- another remediation operator;
- multi-agent concurrency;
- delegation;
- a production dataset;
- LLM-based experiments;
- additional defect classes;
- generalized fixed-point semantics;
- arbitrary remediator convergence;
- distributed execution.

Those belong in the next SARC paper.

The current paper should remain focused on:

\[
	ext{Remediation changes the governed object}
\Rightarrow
	ext{prior judgments can become stale}
\Rightarrow
	ext{dependent controls must be reevaluated}
\]

and:

\[
ho_i \circ ho_j

eq
ho_j \circ ho_i
\Rightarrow
	ext{remediation order is governance semantics}
\]

---

# Final acceptance condition

After the two repository fixes above:

## Publication metadata

- full author lists;
- correct BibTeX publication types;
- correct venue/volume/pages where available;
- citation metadata generated from verified sources;
- bibliography-quality release gate passes.

## Reproducibility

- G4 sample derived from manuscript SHA-256;
- same manuscript bytes always produce the same sentence sample;
- Git HEAD retained only as informational provenance;
- all existing G1-G8 gates remain green.

---

# Final recommendation

Make these two changes and stop modifying the science.

Priority:

1. **P0: Full scholarly bibliography metadata**
2. **P1: Source-hash-derived G4 deterministic sampling**

After that, the repository is effectively in **10/10 artifact-quality territory**.

Any remaining gap to a literal 10/10 paper is not an engineering problem. It is independent human scholarly review of the formal claims and novelty boundary.
