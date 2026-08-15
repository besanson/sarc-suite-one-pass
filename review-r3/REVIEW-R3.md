# SARC Suite Independent Automated Review, Round 3

## Review identity and disposition

| Field | Value |
|---|---|
| Artifact | `sarc-suite-one-pass` |
| Review | Independent automated review, round 3 |
| Reviewer model | Perplexity Computer |
| Date | 2026-08-15 |
| Reviewed HEAD | `5e5e00812acb1990535d1ede85195d9e5c03790b` |
| Protocol | `sarc-suite-agent-review-r3.md` |
| Overall disposition | **NOT RELEASE-READY: two severity-2 fix obligations remain** |

**Closure rule.** This is the closure round. Severity-1 and severity-2 findings are fix obligations. Severity-3 and below are recorded as known issues for the repository issue list; they explicitly do **not** block release and do **not** trigger a further review round.

The scientific core is substantially stronger than in rounds one and two. The corrected Proposition 1, persisted-evidence CH1 audit, durable substitution provenance, fixed CH7 probe, deterministic statistics, and seed artifacts all survived independent replication. Release closure is withheld for two reproducibility defects: committed formal outputs identify an earlier HEAD, and the documented Tectonic arXiv fallback builds a PDF but cannot pass its own release gates.

## Provenance and review-chain integrity

- **Fresh review environment:** The repository was cloned into a fresh directory. Review outputs were written only to the sibling `review-out-r3/` directory. The reviewer did not edit source files.
- **HEAD and history:** The reviewed HEAD was `5e5e00812acb1990535d1ede85195d9e5c03790b`. The relevant final sequence was round-two report commit `cee2d7f`, response commit `77bf676`, regeneration/stable-sum commit `f0d2bdf`, and LaTeX-package commit `5e5e008`.
- **Preregistration:** `prereg-v1` resolves to `31552b2ee6548787e766b0253498014eb0a5093c`; its tree contains no result artifacts.
- **Round-two integrity:** `sha256(review-r2/REVIEW-R2.md)` was exactly `411c05f0efe7676fee2acb3dfdb099163d383b54b7dd547bb93765b0226b6a94`. The JSON hash was exactly `2b062e9d86b86eb58d4f7aa8a0762f47b95ec69ab329ac59546e00db78167c56`, matching the review-r2 commit message.
- **Pinned engines:** Bootstrap completed in 9.624 seconds at `dqSarc db6c396128a4df7fe12d13be163b1e7d32087177`, `governance 74df5de29a305a76bf3cc97a185ece2f11b1b833`, and `Green 8482226b461ccbf91971f90ea6de42cd7a931e5c`.
- **Source data:** The source-data SHA-256 remained `4f637bc36ba5cffb56c31cd2b8273a135f89cc65448b28929ee71e73ded8f1d9`.

The review builds regenerated tracked outputs in the disposable clone, as expected. The resulting diffs were limited to the three checker artifacts plus the Tectonic-built PDF and parity report; no source fix was made.

## Round-two response audit

| Finding or follow-up | Status | Independent evidence |
|---|---|---|
| R2-F1: build graph did not force checker freshness | **RESOLVED** | After touching a checker input without changing its content, `make paper` regenerated all checker outputs and repopulated the paper with current scientific values. |
| R2-F2: CH7 post-hoc probe lacked a stable registered seed | **RESOLVED** | The probe is fixed at seed 26313 with \(n=200\), documented as post-hoc, and commit-stable. Direct composition replay gave 150/200 non-confluent points and 200/200 downroute-feasible points. |
| R2-F3: unstable floating-point reduction | **RESOLVED** | The affected aggregate uses `math.fsum`. Independent recomputation matched every mean and interval at \(10^{-6}\), and two formal runs were byte-identical. |
| R2-F4: incomplete schema/empty-predicate documentation | **RESOLVED** | Evidence schema v2 and empty-predicate behavior are documented. A HEAD-derived sample of 200 lines had zero validation errors. |
| R2-F5: required disclosure absent | **RESOLVED** | The two-round disclosure is present verbatim in Markdown and in independently extracted, dehyphenated PDF text. |
| R2-F6: substitutions lacked durable event resolution | **RESOLVED** | The durable buffer log resolves all 3,478 substitutions, representing 1,684 unique event IDs, to exactly one event. No ID was unresolved or multiply resolved. |
| Follow-up regeneration commit | **REGRESSED** | All three selected per-seed artifacts now replay byte-for-byte, but every committed checker JSON still stamps `77bf676` rather than current HEAD `5e5e008`. |
| CH1 persisted-evidence follow-up | **RESOLVED** | The audit loads persisted Evidence Set lines rather than synthesizing clean DQ evidence in memory. |

## Fresh claim verdicts

Allowed verdicts in this review are `CONFIRMED`, `CONFIRMED-WITH-CAVEAT`, `REFUTED`, and `UNVERIFIED`.

| Claim | Evidence checked | Verdict | Note |
|---|---|---|---|
| C1 | Corrected positive-weight linear lemma, proof tags, 17,151-point lattice checker, and 1,500 independent rational-weight cases | **CONFIRMED** | The former universal statement and unsupported necessity corollary remain retracted. The corrected iff lemma survived the declared finite checker and the independent adversarial family. |
| C2 | Composition implementation, tests, and formal outputs | **CONFIRMED** | Single-pass remediation can invalidate an earlier gate decision. |
| C3 | Remediate-and-regate construction and executable tests | **CONFIRMED-WITH-CAVEAT** | Confirmed for the implemented construction and stated domain, not for arbitrary remediation systems. |
| C4 | Termination lemma, proof taxonomy, and persisted-line reload audit | **CONFIRMED-WITH-CAVEAT** | Termination holds under the stated one-remediation assumptions. |
| C5 | All 81,312 Evidence Set lines and the durable substitution log | **CONFIRMED-WITH-CAVEAT** | Full lineage is present and every substitution resolves to a unique event; reconstruction of external original record bytes remains conditional on the referenced record store. |
| C6 | Coverage definitions and paper wording | **CONFIRMED-WITH-CAVEAT** | The no-new-coverage result is definitional under the paper's union model. |
| C7 | Synthetic poisoning experiment, evidence scans, and mitigations | **CONFIRMED-WITH-CAVEAT** | Supported as a mechanism demonstration, not as a prevalence estimate. |
| C8 | Evidence generation, schema, leakage scan, and statistics | **CONFIRMED** | One unified Evidence Set per action is emitted with documented schema and lineage. |
| C9 | Fresh clone, pinned bootstrap, `make all`, formal reruns, seed replays, and arXiv fallback rebuild | **REFUTED** | Scientific computations replay, but the current-HEAD formal artifacts carry stale provenance and the documented Tectonic fallback cannot complete `make arxiv`. |
| CH1 | Persisted-line reload path and 30-seed outputs | **CONFIRMED** | The round-two synthetic-audit defect is resolved. |
| CH2 | Independent recomputation from per-seed artifacts | **CONFIRMED** | Reported means and intervals recompute exactly. |
| CH3 | Per-seed artifacts and scope statements | **CONFIRMED-WITH-CAVEAT** | Supported for the preregistered workflows and implemented engines. |
| CH4 | Per-seed artifacts and mechanism scope | **CONFIRMED-WITH-CAVEAT** | Supported as a mechanism demonstration, not a broad prevalence claim. |
| CH5 | Exhaustive \(125 \times 264\) finite grid | **CONFIRMED** | The maximum observed violation count was 48; the result is exhaustive over the declared discrete domain. |
| CH6 | Both preregistered workflows and robustness outputs | **CONFIRMED-WITH-CAVEAT** | Supported for the daily workflow and not supported for the weekly workflow, as disclosed. |
| CH7 | 243-point grid, published counterexample, fixed 200-point probe, and independent 200-point probe | **CONFIRMED** | Non-confluence reproduced at 86/243 grid points, 150/200 fixed-seed points, and 140/200 independent points. Downroute feasibility was 200/200 in both off-grid probes. |
| CH8 | Thirty-seed robustness outputs | **CONFIRMED** | Robustness holds for CH1-CH5 and not CH6, matching the qualified claim. |

## Delta from round two

| Claim | Round 2 | Round 3 | Reason |
|---|---|---|---|
| C1 | CONFIRMED-WITH-CAVEAT | **CONFIRMED** | Corrected theorem scope, tag taxonomy, and the 1,500-case adversarial family all pass. |
| C2 | CONFIRMED | **CONFIRMED** | No material change. |
| C3 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | Construction remains sound within its stated scope. |
| C4 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | Reload and proof-label defects are fixed; lemma assumptions remain a necessary caveat. |
| C5 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | Durable event resolution is fixed; external byte reconstruction remains conditional. |
| C6 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | No material change. |
| C7 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | No material change. |
| C8 | CONFIRMED | **CONFIRMED** | No material change. |
| C9 | REFUTED | **REFUTED** | Seed staleness is fixed, but current-HEAD checker provenance regressed and the arXiv fallback fails. |
| CH1 | CONFIRMED-WITH-CAVEAT | **CONFIRMED** | The audit now reloads exact persisted evidence lines. |
| CH2 | CONFIRMED | **CONFIRMED** | No material change. |
| CH3 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | No material change. |
| CH4 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | No material change. |
| CH5 | CONFIRMED | **CONFIRMED** | No material change. |
| CH6 | CONFIRMED-WITH-CAVEAT | **CONFIRMED-WITH-CAVEAT** | No material change. |
| CH7 | CONFIRMED-WITH-CAVEAT | **CONFIRMED** | Fixed and independent probes reproduce non-confluence while preserving downroute feasibility. |
| CH8 | CONFIRMED | **CONFIRMED** | No material change. |

## Findings by severity

### R3-F1: Committed formal artifacts carry stale current-HEAD provenance

**Severity 2. Fix obligation.**

All three committed checker JSON files identify `generated_at_head_sha` as response commit `77bf676`, while the reviewed repository HEAD is `5e5e008`. Fresh `make formal` runs are deterministic and agree with the paper's scientific values, but they modify the tracked artifacts to carry current-HEAD stamps.

The impact is provenance rather than a changed checker result: a consumer cannot establish that the committed formal outputs were generated at the revision containing them. Regenerate and commit all formal outputs at release HEAD, or redesign the stamp so publication-only commits do not immediately stale the committed artifacts.

### R3-F2: The documented Tectonic arXiv fallback cannot pass its own gates

**Severity 2. Fix obligation.**

With `latexmk` unavailable, the Makefile's documented fallback selected pinned Tectonic 0.17.0. Two builds produced the same file list and the same 19-page count, but `make arxiv` exited 2 both times. G1 expects a `main.log` file that Tectonic does not create, while G4 and G6 depend on compiler- and extraction-sensitive prose matching. The rebuilt PDF and parity report also differ from the committed artifacts.

The fallback therefore is not a successful reproducible release path. Make the gates compiler-aware, demonstrate a clean `make arxiv` under every documented compiler, and commit the PDF and parity report from the declared release toolchain.

### R3-F3: The parity report obscures an allowed raw numeric delta

**Severity 3. Known issue; non-blocking; no further round.**

Committed G3 reports raw number totals of 689 for Markdown and 688 for PDF while showing empty normalized differences. Independent extraction explains the discrepancy exactly: the Markdown tokens `2` and `31` in \(2^{31}\) flatten into the PDF token `231`. After this enumerated allowance, no unexplained number remains.

This is reporting sloppiness, not artifact damage. The report should distinguish raw from post-allowlist totals and list every exception, but under the closure rule this issue does not block release and does not trigger another review.

No severity-1 finding was identified.

## Mechanical replication, statistics, and replays

| Check | Result | Wall-clock time |
|---|---|---:|
| Pinned bootstrap | Passed | 9.624 s |
| Full test suite | 176 passed, 0 failed, 0 skipped | 117.48 s pytest; 119.210 s `make test` |
| `make all` | Exit 0 | 133.897 s |
| Formal rerun 1 | Passed | Recorded in `evidence/formal-pass1.time` |
| Formal rerun 2 | Passed; outputs byte-identical to rerun 1 | Recorded in `evidence/formal-pass2.time` |
| Seed 26313 replay | Byte-exact to committed artifact | 10.055 s |
| Seed 1028331701 replay | Byte-exact to committed artifact | 9.758 s |
| HEAD-derived registered seed 1179730076 replay | Byte-exact to committed artifact | 10.490 s |
| Mutation sample | 130 killed, 20 survived of 150 | 47.881 s |

The three replay hashes were respectively `7c922b783c270fdbd0cbbfecb852cd4f6c706971063479709e5927dc2bdb5820`, `5616122194edcd5e39b40977a6129684c5b1af466c19ec1049286b9f45a417c0`, and `4f3b0e9cdd23925afb75b00d980067825af62b0bbc930bee56f60fdf132e611b`.

Independent recomputation of every mean and interval in `sweep_summary.json` from the per-seed artifacts matched exactly; no delta exceeded \(10^{-6}\). The Evidence Set contained 81,312 schema-v2 lines. A HEAD-derived 200-line schema sample had zero errors, and a scan of all lines found zero forbidden ground-truth or label fields.

The lattice checker executed 17,151 checks. CH5 covered 125 thresholds by 264 composition cells with a maximum of 48 violations. The CH7 finite grid found 86 non-confluent points among 243. The fixed off-grid probe found 150/200 non-confluent points; the independent HEAD-derived probe, seed 6401200729396269334, found 140/200. Both probes had 200/200 downroute-feasible points.

For Proposition 1, the independent adversarial seed was 18041528044683440488. Positive rational weights in dimensions 2 through 9 were combined with five thresholds per case for 1,500 exact checks; there were zero failures.

Mutation sampling was derived by selecting the 150 lowest values of `sha256(HEAD + ':r3-mutation:' + mutant_name)` from 1,264 generated mutants. The kill rate was 130/150, or 0.8667, with Wilson 95% interval \([0.8030, 0.9120]\). The committed score of 0.8804 lies inside that interval.

All ten citation URLs were re-fetched. DOI metadata for the two direct-fetch failures was recovered through Crossref, and the verified titles, authors, years, and identifiers matched the registry. The UCI registry page dates the dataset release to 2015; this is distinct from the 2012 introductory paper and is not a citation defect.

## Formal-claim scope and proof taxonomy

The paper contains five `machine-checked`, five `checked-scope-only`, and one `pending-human-review` proof-classification entries at the claim level. All eleven labels matched their stated scope. Every machine-checked statement names an executable checker and finite domain; broader mathematical statements retain the narrower taxonomy.

The unsupported universal C1 statement remains absent. Necessity appears only in the corrected positive-weight linear Proposition 1 iff statement, while Corollary 1 is sufficiency-only and the old iff is explicitly retracted. The paper-level rendered tag totals also matched the required 21 `machine-checked`, 26 `checked-scope-only`, and 7 `pending-human-review` occurrences after dehyphenation.

## LaTeX and arXiv package audit

### Build behavior

The environment did not provide `latexmk`; pinned Tectonic 0.17.0 was installed as the permitted fallback. Two source builds produced the same file list and the same 19-page count. The arXiv tarball contained only `main.tex` and `main.bbl`, which is appropriate. Both `make arxiv` invocations nevertheless exited 2 for the gate incompatibilities described in R3-F2.

### Independent content extraction

The independent extraction applied these normalizations:

1. Rejoin lowercase continuation hyphen line breaks.
2. Remove standalone page-number lines.
3. Remove repeated short-title page furniture.
4. Remove the formatted PDF reference list, absent from Markdown by design.
5. Allow exactly one superscript-flattening transformation: source tokens `2` and `31` become PDF token `231`.

Markdown contained 689 numeric tokens and the normalized PDF contained 688. The raw differences were exactly one missing `2`, one missing `31`, and one added `231`; after the enumerated typesetting allowance, there were no unexplained additions or omissions. Number-multiset parity therefore passes. The committed G3 discrepancy is reporting sloppiness rather than content damage.

The required tag counts were exact in both Markdown and PDF: 21 `machine-checked`, 26 `checked-scope-only`, and 7 `pending-human-review`. The two-round disclosure was verbatim after whitespace normalization and dehyphenation. The scope-honesty and negative-results banners were present in both forms.

`refs.bib` has exactly ten entries and its keys match exactly the ten verified registry records. The arXiv abstract is 1,900 characters, within the 1,920-character limit, and is a faithful condensation that adds no scientific claim absent from the paper.

## Scores

### Research artifact: 8.5/10

The central scientific claims, corrected theorem, finite checks, 30-seed statistics, persisted-evidence audit, direct CH7 probes, and qualified negative results are unusually well evidenced. The severity-1 scientific overclaims found in round one have been repaired, and the key round-two methodological weaknesses are resolved. The remaining deductions concern release provenance and package reproducibility, not a newly discovered false scientific result.

### Software engineering: 8.0/10

The pinned bootstrap, 176-test suite, byte-exact seed replays, stable-sum regeneration, schema validation, durable substitution log, real build dependencies, and mutation result are strong. The stale checker provenance at final HEAD and a documented compiler fallback that cannot pass its own gates are material release-engineering failures and prevent a higher score.

## Author-reuse disclosure

This artifact was independently replicated and adversarially reviewed in three rounds by automated agents following the published protocols in sarc-suite-agent-review.md, sarc-suite-agent-review-r2.md, and sarc-suite-agent-review-r3.md; the round-one report and evidence are at review/REVIEW.md and review/review.json, the round-two report and evidence are at review-out-r2/REVIEW-R2.md, review-out-r2/review.json, and review-out-r2/evidence/, and the round-three report and evidence are at review-out-r3/REVIEW-R3.md, review-out-r3/review.json, and review-out-r3/evidence/. Automated review complements and does not replace human peer review.

All supporting artifacts for this review are under `review-out-r3/evidence/`. The machine-readable mirror is `review-out-r3/review.json`.
