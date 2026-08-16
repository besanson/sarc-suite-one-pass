# SARC Suite Independent Automated Review, Round 4, Terminal

## Review identity and terminal disposition

| Field | Value |
|---|---|
| Artifact | `sarc-suite-one-pass` |
| Review | Independent automated review, round 4, terminal |
| Reviewer model | Perplexity Computer |
| Date | 2026-08-16 |
| Release-candidate HEAD | `75e050ca9a2246849b5b82b06e0ba9201afeae80` |
| Protocol | `sarc-suite-agent-review-r4.md` |
| Official research-artifact score | **9.5/10** |
| Official software-engineering score | **9.5/10** |
| Disposition | **RELEASE** |

**Terminal rule.** This is the terminal reviewer round. The scores issued here stand as the released official scores, except through this review's own conditional disposition, whose required changes would be verified by the external adjudicator, never by a further reviewer round. Only a severity-1 finding blocks release. Severity-2 and below become recorded known issues and block nothing. There is no round five under any outcome, and this review does not recommend one.

The release candidate closes both severity-2 defects from Round 3 by design and in execution. Authoritative checker input hashes match the current tree, the mandatory `make release-check` passes end to end, canonical Tectonic builds pass every publication gate, three seed artifacts replay byte-for-byte, all reported statistics recompute, and the independent adversarial checks found no scientific regression. No severity-1 finding and no new lower-severity finding were identified.

**DISPOSITION: RELEASE.**

## Provenance and review-chain integrity

- **Fresh environment:** The repository was cloned from `https://github.com/besanson/sarc-suite-one-pass` into a fresh empty Round 4 directory. Review outputs were written to the sibling `review-out-r4/` directory. The reviewer did not alter source code.
- **HEAD and commit order:** The release candidate is `75e050ca9a2246849b5b82b06e0ba9201afeae80`, following the preserved Round 3 review commit `4c887ad`, LaTeX package commit `5e5e008`, regeneration commit `f0d2bdf`, and earlier review-response commits.
- **Preregistration:** `prereg-v1` resolves to `31552b2ee6548787e766b0253498014eb0a5093c`. Its tree contains no result artifacts.
- **Round 3 integrity:** `sha256(review-r3/REVIEW-R3.md)` is exactly `8a3da7bf580b6d3560065dd60089b7974b3dbad3c6a4a66cf8a0281e2acda927`. `sha256(review-r3/review.json)` is exactly `4d6dd5672cd5fdc653efe3837877c45c0b0fcc4f1e53e5dab12ab17be6857ddd`.
- **Pinned engines:** Bootstrap pinned `dqSarc` at `db6c396128a4df7fe12d13be163b1e7d32087177`, `sarc-governance` at `74df5de29a305a76bf3cc97a185ece2f11b1b833`, and `Greensarc` at `8482226b461ccbf91971f90ea6de42cd7a931e5c`. All three remained clean.
- **Canonical compiler:** The repository's own `bootstrap.sh` installed Tectonic 0.17.0. `latexmk` was absent, so the protocol-required canonical path was tested and the optional supported-alternative path was correctly skipped with notice.
- **Source data:** `data/open_retail_daily.csv` remained at SHA-256 `4f637bc36ba5cffb56c31cd2b8273a135f89cc65448b28929ee71e73ded8f1d9`.

Generated-output targets modified only the expected disposable-clone artifacts: the three checker JSON files, `paper-tex/main.pdf`, and `paper-tex/parity-report.json`. No source diff was produced.

## Closure-fix audit

| Round 3 item | Status | Independent evidence |
|---|---|---|
| R3-F1: committed formal artifacts carried stale current-HEAD provenance | **RESOLVED** | The authoritative `inputs_hash` was independently recomputed from literal current-tree bytes for every declared input of all three checkers. Each recomputation exactly matched the committed artifact. Touching `composition.py` and running `make paper` regenerated all checker outputs and paper slots in 15 seconds. |
| R3-F2: documented Tectonic fallback could not pass its gates | **RESOLVED** | Tectonic 0.17.0 is now canonical rather than a best-effort fallback. `make release-check` exited 0 and printed `release-check: ALL CHECKS PASS`. Two additional `make arxiv` runs each exited 0, passed G1-G6, produced the same file list, and produced 19-page PDFs. |
| R3-F3: parity report hid the allowed raw numeric delta | **RESOLVED** | G3 now reports raw totals 689/688, all three matched exception entries (`2`, `31`, and `231`), post-exception totals 689/689, and empty post-exception differences. The compiler is named as `tectonic`. |
| `KNOWN-ISSUES.md` | **RESOLVED** | The file is present and accurately records R3-F3's original severity, non-blocking status, cause, and implemented reporting correction. |
| Informational amended-away HEAD stamp | **RESOLVED** | The committed `generated_at_head_sha` is `847d97f8e60961b0145bcdbf2ffcc9bc6fc542a7`, an amended-away object not present in current history. This does not indicate stale scientific content: `inputs_hash` is explicitly authoritative, all three committed input hashes match the current tree, and fresh checker runs stamp current HEAD without changing results. |

### Inputs-hash recomputation

| Checker | Committed and independently recomputed `inputs_hash` | Equal |
|---|---|---|
| Lattice | `ef17526509da3d0ff26ae9c34b50d213227cc480f69a90c976b83df7ef662f54` | Yes |
| Compensation | `ae395aba5633365aee56a5b7003ad22631ec0eb013386c4c5dcf86840dc9a6ae` | Yes |
| Remediator | `1496570e6dbedb2446f9735cd8131dd15224ea0cdda2b414c954293eef4b0f5e` | Yes |

The content-addressed design is the correct freshness authority. A whole-repository HEAD stamp cannot distinguish changed generating inputs from publication-only commits; the declared, path-delimited input hash can. The retained HEAD field is useful generation metadata but is not a freshness predicate.

## Release-check and core replication

`make release-check` completed in 127 seconds and passed every stage:

1. The full suite collected 180 tests and reported **180 passed, 0 failed, 0 skipped** in 120.20 seconds. Slow tests were included.
2. The formal checkers ran twice as subprocesses and their output directories were byte-identical.
3. `make arxiv` ran under canonical Tectonic 0.17.0, passed G1-G6, and packaged `main.tex` plus `refs.bib`.

### Deterministic seed replays

The third seed was selected as:

`int(sha256(HEAD + ':r4-replay-seed'), 16) mod len(registered seeds excluding 26313 and 1028331701)`.

| Seed | Selection | Wall time | Byte comparison to committed artifact | SHA-256 |
|---:|---|---:|---|---|
| 26313 | First registered | 9.804 s | Exact | `7c922b783c270fdbd0cbbfecb852cd4f6c706971063479709e5927dc2bdb5820` |
| 1028331701 | Explicit protocol seed | 9.675 s | Exact | `5616122194edcd5e39b40977a6129684c5b1af466c19ec1049286b9f45a417c0` |
| 778087005 | HEAD-derived registered seed | 9.634 s | Exact | `ea27f19974836c8cde004802dc8840818f9c5e8ceff33e954590656e2f272c0e` |

### Statistics and formal checks

Every mean and confidence interval in `sweep_summary.json` was recomputed from the committed per-seed artifacts. The recomputed object was exactly equal to the committed summary, with no difference above \(10^{-6}\).

The lattice checker executed 17,151 checks and all laws held. The compensation checker covered 125 response profiles and 264 grid cells, with a maximum of 48 violations, and the corrected Proposition 1 condition agreed on all 1,064 built-in verification cases. The remediator checker found 86 non-confluent points among 243 grid points. Its fixed seed 26313 off-grid probe reproduced 150 non-confluent points among 200.

The CH7 published counterexample was replayed directly through the two composition orders. Substitute-then-downroute produced quantity 5 and order value 50; downroute-then-substitute produced quantity 10 and order value 100.

The independent Proposition 1 family used seed 17855364338959654384, derived from `sha256(HEAD + ':r4-proposition1-family')`. It generated 300 positive rational-weight families across dimensions 2 through 9 and tested five boundary-sensitive thresholds per family. All **1,500 exact checks passed**.

### Leakage and mutation

The leakage scan covered all **81,312 scenario Evidence Set lines** in eight files. It found zero occurrences of forbidden ground-truth, defect-label, injected-defect, true-cost, or label fields.

Mutation selection ranked the 1,264 generated `composition.py` and `metrics.py` mutants by `sha256(HEAD + ':r4-mutation:' + mutant_name)` and selected the lowest 150. Results were 131 killed and 19 survived, a kill rate of 0.8733. The Wilson 95% interval was \([0.8106, 0.9174]\); the committed score 0.8804 lies inside it. Runtime was 51.921 seconds.

### Citation re-fetch

All ten registry URLs were re-fetched. Seven returned directly with the registered metadata. The Nowak, Schneider, and Clark-Wilson DOI endpoints were blocked or JavaScript-dependent through the direct fetch path; all three were independently recovered from Crossref and matched the registered title, author, year, and DOI. The USENIX PDF rendered its title as “Multi-Path Probing” rather than the registry's “Multi-path Network Probing”, while author, year, source document, and subject matched; this is a harmless title-style abbreviation in the fetched extraction, not evidence of a different work.

## Independent PDF and arXiv audit

Two additional canonical `make arxiv` runs each took 4 seconds, exited 0, produced identical file lists, and produced 19-page PDFs. The PDF byte hashes differed between builds, but the protocol requires equal file lists and page counts rather than byte-identical PDFs; independent content parity passed, and the deterministic arXiv tarball hash was stable. The tarball contains exactly `main.tex` and `refs.bib`.

The independent extraction applied these normalisations:

1. Rejoin lowercase continuation hyphen line breaks.
2. Remove standalone page-number lines.
3. Remove repeated short-title page furniture.
4. Remove the formatted PDF reference list, which is absent from the Markdown source by design.
5. Allow exactly one enumerated superscript-flattening transformation: Markdown tokens `2` and `31` become PDF token `231`.

The Markdown contained 689 numeric tokens and the PDF contained 688 before exceptions. The raw difference was exactly one missing `2`, one missing `31`, and one added `231`. After the enumerated exception, both sides total 689 and no unexplained token remains.

Wrap-tolerant tag counts matched exactly in Markdown and PDF: 21 `machine-checked`, 26 `checked-scope-only`, and 7 `pending-human-review`. The three-round disclosure was present verbatim in Markdown and after whitespace/dehyphenation normalisation in the PDF.

## Refreshed claim verdicts

| Claim | Evidence checked | Round 4 verdict | Delta from Round 3 |
|---|---|---|---|
| C1 | Corrected lemma, finite checker, and 1,500 independent rational-weight checks | **CONFIRMED** | Unchanged; all new checks pass. |
| C2 | Composition counterexample, formal output, and tests | **CONFIRMED** | Unchanged. |
| C3 | Remediate-and-regate construction and executable tests | **CONFIRMED-WITH-CAVEAT** | Unchanged; implemented-domain scope remains binding. |
| C4 | Termination lemma, proof taxonomy, and persisted-line behavior | **CONFIRMED-WITH-CAVEAT** | Unchanged; stated one-remediation assumptions remain necessary. |
| C5 | Evidence lines and durable lineage | **CONFIRMED-WITH-CAVEAT** | Unchanged; external original-byte reconstruction remains record-store conditional. |
| C6 | Coverage definitions and wording | **CONFIRMED-WITH-CAVEAT** | Unchanged; definitional under the declared union model. |
| C7 | Synthetic poisoning mechanism and mitigations | **CONFIRMED-WITH-CAVEAT** | Unchanged; mechanism, not prevalence. |
| C8 | Unified Evidence Sets and leakage scan | **CONFIRMED** | Unchanged. |
| C9 | Input hashes, release-check, formal identity, seed replays, and canonical arXiv builds | **CONFIRMED** | **Upgraded from REFUTED**; both Round 3 reproducibility defects are resolved. |
| CH1 | Persisted-evidence audit | **CONFIRMED** | Unchanged. |
| CH2 | Independent statistical recomputation | **CONFIRMED** | Unchanged. |
| CH3 | Per-seed outputs and scope | **CONFIRMED-WITH-CAVEAT** | Unchanged; preregistered-workflow scope. |
| CH4 | Per-seed outputs and mechanism scope | **CONFIRMED-WITH-CAVEAT** | Unchanged; mechanism, not prevalence. |
| CH5 | Exhaustive declared finite grid | **CONFIRMED** | Unchanged. |
| CH6 | W1 and W2 outputs | **CONFIRMED-WITH-CAVEAT** | Unchanged; supported under W1 and not robust under W2, as disclosed. |
| CH7 | Grid counterexample and fixed off-grid replay through composition code | **CONFIRMED** | Unchanged. |
| CH8 | Thirty-seed robustness output | **CONFIRMED** | Unchanged. |

## Findings by severity

No new severity-1, severity-2, severity-3, or lower-severity finding was identified.

R3-F1, R3-F2, and R3-F3 are independently verified as resolved. The amended-away `generated_at_head_sha` is not promoted to a finding because it is explicitly non-authoritative, the authoritative current-tree input hashes all match, and fresh generation reproduces the scientific values. `KNOWN-ISSUES.md` accurately preserves the historical R3-F3 record and its resolution.

## Official scores

### Research artifact: 9.5/10

The paper now combines unusually strong claim discipline with executable finite checks, deterministic multi-seed evidence, byte-exact replay against committed artifacts, explicit negative results, durable lineage, adversarial replication, and a clean publication package. The false universal theorem and reconstruction overclaim identified in Round 1 remain corrected, the Round 2 methodological gaps remain closed, and the Round 3 release defects are fixed. The remaining half-point is not an unfixed defect: it reflects the paper's honest permanent scope as a mechanism demonstration on open payload data with synthetic metadata rather than a live prevalence study or external-domain validation.

### Software engineering: 9.5/10

The release candidate provides a pinned bootstrap, content-addressed checker freshness, 180 passing tests including slow tests, deterministic formal outputs, byte-exact seed replay, a mandatory composite release gate, a canonical bootstrap-installed compiler, compiler-aware publication gates, stable packaging, evidence leakage checks, and mutation sensitivity consistent with the committed score. The remaining half-point reflects the artifact's explicitly declared research-demonstrator boundary: production connectors, an evidence-vault service, identity integration, and hosted operations are intentionally outside the shipped artifact rather than missing relative to its claim.

## Remaining deductions and required changes

Every point withheld from 10 is accounted for below. There are no closable deductions and no required changes.

| Lens | Deduction | Classification | Named reason | Mechanically verifiable remedy |
|---|---:|---|---|---|
| Research artifact | 0.5 | **PERMANENT-BY-DESIGN** | Mechanism-not-prevalence scope. The paper explicitly studies mechanisms on open payload data with a declared synthetic metadata layer; it does not claim live operational prevalence or external-domain generality. | None short of changing the research claim and conducting a different empirical study. |
| Software engineering | 0.5 | **PERMANENT-BY-DESIGN** | Research-demonstrator boundary. The artifact explicitly excludes production connectors, evidence-vault services, identity integration, and hosted operations. | None within the claimed artifact; adding those systems would create a broader product rather than repair this release. |

Research closable deductions: **0.0 points**. Software-engineering closable deductions: **0.0 points**.

## Conditional disposition

### Research-artifact lens

The released official research-artifact score is **9.5/10**. It already exceeds 9.0; closable deductions total 0.0, there are no required changes R1..Rk, and no adjudicator compliance action is needed. The sole remaining deduction is PERMANENT-BY-DESIGN and does not hold the lens below 9.0.

### Software-engineering lens

The released official software-engineering score is **9.5/10**. It already exceeds 9.0; closable deductions total 0.0, there are no required changes R1..Rk, and no adjudicator compliance action is needed. The sole remaining deduction is PERMANENT-BY-DESIGN and does not hold the lens below 9.0.

No further reviewer round occurs.

## Author-reuse disclosure

This artifact was independently replicated and adversarially reviewed in four rounds by automated agents following the published protocols in sarc-suite-agent-review.md, sarc-suite-agent-review-r2.md, sarc-suite-agent-review-r3.md, and sarc-suite-agent-review-r4.md; the round-one report and evidence are at review/REVIEW.md and review/review.json, the round-two report and evidence are at review-out-r2/REVIEW-R2.md, review-out-r2/review.json, and review-out-r2/evidence/, the round-three report and evidence are at review-out-r3/REVIEW-R3.md, review-out-r3/review.json, and review-out-r3/evidence/, and the round-four report and evidence are at review-out-r4/REVIEW-R4.md, review-out-r4/review.json, and review-out-r4/evidence/. Automated review complements and does not replace human peer review.

All supporting artifacts are under `review-out-r4/evidence/`. The machine-readable mirror is `review-out-r4/review.json`.
