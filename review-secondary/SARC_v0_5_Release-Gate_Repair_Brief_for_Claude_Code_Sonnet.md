# SARC v0.5 Release-Gate Repair Brief for Claude Code Sonnet

## Mission

Work directly in the `besanson/sarc-suite-one-pass` repository and repair the current v0.5 release-gate failure with the smallest defensible change.

The starting revision assessed was:

```text
3c72d023909306c025b8c74764a65ad21b886f5b
paper v0.5: final pass per third-round proposals; reviewer patch reimplemented via pipeline, not applied; byte-reproducible builds
```

Do not merely propose a solution. Inspect the current repository state, implement the repair, add regression coverage, regenerate the required artifacts through the repository's normal pipeline, and verify the complete release contract.

If `main` has moved since the starting revision, first inspect the intervening commits. Preserve any valid newer work and apply this brief to the current tree rather than resetting or force-replacing it.

## Current independent findings

From a fresh checkout of the starting revision:

- `python3 -m pytest -v` completed with **180 passed**.
- The formal checkers reproduced their expected results and were deterministic across repeated runs.
- G1, G2, G3, G5, G6, G7, and G8 passed.
- G4 prose parity failed.
- The committed PDF is visually sound and 28 pages.
- The failure is in the parity tool's normalization and sampling behavior, not in the paper's scientific content.

The two G4 sample mismatches were:

```text
Gaston Besanson (Universidad Torcuato Di Tella)
```

and:

```text
Each member control is deterministic for fixed action, evidence, context, and control-local state. - A2.
```

The first is front-matter metadata represented differently in Markdown and LaTeX:

```markdown
Gaston Besanson (Universidad Torcuato Di Tella)
```

versus:

```tex
\author{Gaston Besanson\thanks{Universidad Torcuato Di Tella}}
```

The second is a false sentence produced because the current `split_sentences()` preprocessor only splits Pandoc bullet markers matching:

```python
r"\n-   "
```

The installed Pandoc emits this assumptions list as:

```text
- A1. Determinism. Each member control is deterministic for fixed
  action, evidence, context, and control-local state.
- A2. Bounded remediation. ...
```

Consequently, the A2 marker is glued to the preceding A1 sentence after whitespace normalization.

## Required repair

### Make Pandoc list splitting robust

Update the G4 sentence extraction in `paper-tex/gates/run_gates.py` so that Pandoc list markers are split before whitespace normalization regardless of the number of spaces Pandoc places after the hyphen.

The implementation should:

- recognize the actual `- ` form shown above;
- continue recognizing the previously handled `-   ` form;
- tolerate indentation where appropriate;
- operate only at line starts, so prose hyphens and compounds cannot be mistaken for list markers;
- preserve the content of every list item;
- prevent one list item's marker from being appended to the preceding item's final sentence.

Use a general line-oriented expression or equivalent parser logic. Do not special-case the literal A1/A2 text.

Add focused regression tests demonstrating at least:

1. consecutive `- ` list items are separated;
2. consecutive `-   ` list items remain separated;
3. ordinary prose containing hyphens is unchanged;
4. the A1 sentence does not contain the A2 marker after `split_sentences()`.

### Handle front-matter metadata semantically

The G4 random sentence sample should compare prose, not require Markdown author-affiliation syntax to appear contiguously in PDF text when LaTeX intentionally renders the affiliation as a `\thanks{}` footnote.

Implement a principled treatment of front-matter metadata. Preferred approaches, in order:

1. exclude title and author metadata from the random prose-sentence population and verify them through a separate deterministic metadata check; or
2. normalize the author and affiliation representation on both sides before comparison.

The preferred solution is the first because title and author identity are structured metadata, not prose. If used, the deterministic check must verify:

- the title is present in both the populated Markdown source and `main.tex`;
- the author name is present in both;
- the affiliation is present in both;
- the check fails if any of those values is removed or materially changed.

Do not add an exact one-off substitution for Gaston's full author line unless no general structured solution is viable.

Add regression tests covering the chosen behavior.

### Make G4 stable across commits

G4 currently selects ten sentences using the repository HEAD as its deterministic seed. This is acceptable only if every eligible sentence can be compared correctly.

After the normalization repair:

- test the exact starting HEAD sample that exposed the problem;
- test at least several alternative deterministic seeds or synthetic HEAD values;
- ensure list markers, front-matter metadata, tables, proof headings, and known PDF-extraction artifacts cannot create false failures merely because the commit hash changes;
- do not simply freeze the old sample or hard-code indices that happen to pass.

The gate must remain capable of detecting a genuine dropped or altered prose sentence.

## Provenance and generated-artifact rule

Do **not** redefine checker freshness around `generated_at_head_sha`.

The repository explicitly documents in `checkers/_provenance.py` and `test_freshness.py` that:

- `generated_at_head_sha` is informational;
- it may legitimately name an earlier commit after a publication-only commit;
- authoritative freshness is defined by `inputs_hash`;
- a fresh checker invocation must still stamp its actual current HEAD;
- committed artifacts are fresh when their committed `inputs_hash` equals the hash recomputed from their declared current-tree inputs.

Therefore:

- do not fabricate or predict the SHA of the commit being created;
- do not weaken or delete the `inputs_hash` checks;
- do not change scientific outputs merely to make the informational SHA equal the final commit;
- do not claim that a parent-commit informational stamp is stale when the authoritative `inputs_hash` matches;
- preserve the existing tests that fresh invocations stamp the actual current HEAD.

A fresh `make formal` can update the informational SHA fields in the working tree. That is expected under the documented design and is not, by itself, a scientific or freshness failure.

If you choose to make `make release-check` non-mutating, do so only through isolation or cleanup of generated verification outputs. Do not accomplish it by making fresh checker runs lie about the HEAD or by removing provenance fields. This is optional; the mandatory requirement is that the complete release check passes.

## Reproducible PDF rule

Preserve exact within-invocation PDF byte reproducibility:

- G1 must build twice;
- both PDF SHA-256 values must be identical;
- `two_build_identical` must be `true`;
- no undefined citations, undefined references, missing-character warnings, or overfull boxes above the configured threshold may appear.

Do not weaken G1, suppress diagnostics, loosen a threshold, or compare only page counts/file lists.

If you alter `SOURCE_DATE_EPOCH` handling, explain why and add a test proving the replacement is deterministic. Do not make this change unless it is necessary for the G4 repair or a demonstrated release failure.

## Scientific-content freeze

This task is a release-tooling repair, not another scientific review.

Do not change:

- any theorem, proposition, lemma, corollary, or proof classification;
- any CH1-CH8 result or decision rule;
- any experimental number, confidence interval, seed, weight, threshold, or workflow definition;
- the response lattice or aggregation semantics;
- the 17,151 lattice-check count;
- the 125-state by 264-cell compensation evaluation;
- the 86/243 order-divergent grid result;
- the fixed off-grid probe result;
- the 30-seed results;
- the four-round review disclosure;
- the v0.5 scholarly positioning;
- the abstract's scoped soundness, bounded/idempotent qualification, or W1/W2 qualification;
- citations or bibliography content unless a real citation-gate defect is independently demonstrated.

Do not apply the historical reviewer patch stored under `review-secondary/perplexity-followup/`. The v0.5 commit states that accepted changes were reimplemented through the pipeline rather than applying that patch directly. Preserve that separation.

## Documentation consistency

While touching release tooling, correct only directly related stale documentation.

Check that:

- README descriptions of G1-G8 match the actual implemented gates;
- the proof-status documentation recognizes `machine-checked`, `pending-human-review`, and `checked-scope-only` where the implementation does;
- `make arxiv` and `make release-check` descriptions match their real behavior;
- comments referring to “six gates” are updated if the code actually runs eight gates.

Do not perform broad editorial rewrites.

## Required verification sequence

Run from the repository root:

```bash
git status --short
git diff --check
python3 -m pytest -v
make formal
make formal
make arxiv
make release-check
```

The two `make formal` runs must be byte-identical after excluding no fields. Use the repository's existing formal double-run check or an equivalent explicit directory comparison.

Then run:

```bash
git diff --check
git status --short
```

Inspect every changed file. Generated changes must be explainable by the normal pipeline. No unrelated file may be modified.

Also verify:

```bash
grep -RInE 'CITE-NEEDED|\[CITE:|TODO|TBD|FIXME|PLACEHOLDER' \
  paper-tex paper4-composition-draft-v0.5-populated.md README.md \
  --exclude='*.pdf' --exclude='*.tar.gz'
```

Comments explaining how placeholder detection works are allowed. Actual unresolved manuscript or metadata placeholders are not.

## Acceptance criteria

The task is complete only when all of the following are true:

- all tests pass;
- new regression tests cover both observed G4 failures;
- G4 passes at the current HEAD;
- G4 is robust to multiple deterministic sample seeds;
- all G1-G8 gates pass;
- `make release-check` exits zero and prints:

```text
release-check: ALL CHECKS PASS
```

- G1 reports two byte-identical PDF builds;
- formal checker double-run identity passes;
- authoritative checker `inputs_hash` values match current declared inputs;
- no scientific number, verdict, proof status, or claim scope changes;
- `git diff --check` passes;
- the final diff contains only the minimal tooling, tests, directly related documentation, and pipeline-regenerated artifacts needed for this repair.

## Final handoff format

Return a concise implementation report containing:

1. current HEAD before the work;
2. root cause of each observed G4 mismatch;
3. files changed and why;
4. exact tests added;
5. exact verification commands run;
6. test count and result;
7. G1-G8 result summary;
8. final PDF SHA-256;
9. formal checker input hashes and key mechanical results;
10. confirmation that scientific content and numerical results were unchanged;
11. final `git status --short`;
12. any remaining limitation.

Do not label the work complete if `make release-check` is not green.
