# SARC Suite Independent Automated Review, Round 2

This is an automated agent review, not human peer review. It independently re-executed the round-two protocol against a fresh clone of `https://github.com/besanson/sarc-suite-one-pass`, audited the response to findings F1–F6, reran the mechanical, statistical, formal, mutation, citation, and adversarial checks, and made no source changes to the reviewed repository.

## Identity and provenance

- **Reviewer:** automated agent, Perplexity Computer
- **Review round:** 2
- **Date:** 2026-08-15
- **Protocol:** `sarc-suite-agent-review-r2.md`
- **Reviewed HEAD:** `af4a3f019128de569708ff5fe83c900701aa865e`
- **Pre-registration tag:** `prereg-v1` at `31552b2ee6548787e766b0253498014eb0a5093c`; its tree contains no `out/` or populated result artifacts.
- **Commit order:** the history ends with review commit `514f0160cdda2b67994586d2eb23b681824763b5`, followed by response commit `af4a3f019128de569708ff5fe83c900701aa865e`.
- **Round-one integrity:** `review/REVIEW.md` hashes to `e11dbfdc574820c096dbcf968547b7e3298add4d9fbff852a4c1665d2e57441d`; `review/review.json` hashes to `55a02026644195e7ecfac32eed993dc799537dc628b58c036e8a0719713ad37d`. Both match the protocol references.

The pinned engines bootstrapped at the declared SHAs and remained git-clean: SARC-DQ `db6c396128a4df7fe12d13be163b1e7d32087177`, SARC Governance `74df5de29a305a76bf3cc97a185ece2f11b1b833`, and Green SARC `8482226b461ccbf91971f90ea6de42cd7a931e5c`. The source data remained unchanged at SHA-256 `4f637bc36ba5cffb56c31cd2b8273a135f89cc65448b28929ee71e73ded8f1d9`.

## Response audit

| Finding | Verdict | Evidence checked | Note |
|---|---|---|---|
| F1 | PARTIALLY-RESOLVED | Restated Proposition 1; checker grid and randomized probes; acknowledged counterexample; independent exact-arithmetic family of 200 weight vectors and 800 threshold checks | The false universal claim is retracted and the replacement linear-family theorem is correct. The residual is proof labeling: the executable checker covers finite \(n=3\) cases, while `machine-checked` is attached to an arbitrary-\(n\), continuous theorem. |
| F2 | PARTIALLY-RESOLVED | Schema v2; all 3,478 substituted lines; `_buffer_write_eid`; Proposition 4; duplicate-ID and store probe | Substituted lines now include Phase I IDs and substitute key/value commitments, and byte reconstruction is explicitly disclaimed. However, the “write ID” is recomputed at substitution, no durable write history or store locator exists, and 3,478 substitutions collapse to 62 IDs, so a specific repeated write event cannot be identified or resolved in this artifact. |
| F3 | RESOLVED | Abstract, body, claims table, Appendix A, and grep for `iff`, `only if`, and necessity language | The live claim is sufficiency-only. Necessity appears only in explicit retraction and counterexample discussion. |
| F4 | PARTIALLY-RESOLVED | `run_scenario`, `audit_executed`, output writer, execution-evidence tests, generated `*-exec-evidence.jsonl` | CH1 now audits the exact in-memory Phase II `EvidenceRecord` objects and persists those same full records. It does not load the persisted JSONL: audit occurs before `_write_outputs`, so the round-two requirement for a persisted-evidence replay remains unmet. |
| F5 | RESOLVED | All ten `verified-citations.json` entries re-fetched; publisher, arXiv, UCI, Crossref, and registered alternate pages; populated-paper token scan | All ten titles and first authors match. DOI pages that blocked extraction were resolved through Crossref. The populated paper contains zero `[CITE:` placeholders. |
| F6 | RESOLVED | Runtime SciPy critical value; all per-seed artifacts; independent recomputation of every sweep mean and interval | The runtime value is \(t_{0.975,29}=2.045229642132703\). The maximum absolute delta from the committed summary is \(1.11\times10^{-16}\), passing the strict \(10^{-6}\) tolerance. |

## Current claim verdicts

| Claim | Evidence checked | Verdict | Note |
|---|---|---|---|
| C1 | Corrected linear lemma; 264 declared cells; 800 checker random cells; 800 independent exact-arithmetic adversarial checks | CONFIRMED-WITH-CAVEAT | The theorem is true, including zero, unnormalized, extreme, and dimensions up to seven in the independent family. The executable checker does not justify the broad `machine-checked` tag. |
| C2 | Lattice checker, 17,151 checks | CONFIRMED | Idempotence, commutativity, associativity, monotone hardening, duplication invariance, and the empty join all pass. |
| C3 | S4 construction; single-seed metrics; 30-seed artifacts | CONFIRMED-WITH-CAVEAT | The implemented existential construction reproduces and is now properly scoped away from arbitrary remediators. |
| C4 | Lemma 1; Phase II code path; join checker; CH1 audits | CONFIRMED-WITH-CAVEAT | Soundness is supported for the current branch under Lemma 1. Theorem 1’s tag exceeds the lattice checker’s scope, and the audit does not reload persisted evidence. |
| C5 | Schema v2; all substituted lines; Proposition 4; provenance probe | CONFIRMED-WITH-CAVEAT | Identity commitments are present and byte reconstruction is no longer claimed. Store-backed resolution and specific write-event identity remain conditional and unimplemented. |
| C6 | `metrics._ch4_matrix`; all 30 seeds | CONFIRMED-WITH-CAVEAT | The equality holds, but composition detection is definitionally built as the union of member flags. |
| C7 | CH3 metrics and 30 seed artifacts | CONFIRMED-WITH-CAVEAT | Zero false holds reproduces for the declared synthetic, label-derived population, not as a general selectivity theorem. |
| C8 | Fresh bootstrap, pinned SHAs, engine git status | CONFIRMED | The three engines compose unmodified at their declared commits. |
| C9 | Fresh build; generated paper; current formal outputs; three isolated seed replays | REFUTED | “Full reproducibility” fails on current HEAD: committed formal artifacts retain the prior review SHA, the populated paper says 140/200 where HEAD produces 145/200, and one selected seed differs by one ULP. |
| CH1 | 30-seed summary; exact in-memory executed-evidence audit; persisted output inspection | CONFIRMED-WITH-CAVEAT | Zero violations reproduces. Exact Phase II records are audited, but the persisted representation is not reloaded. |
| CH2 | S4 metrics; all 30 seeds; recomputed intervals | CONFIRMED | Every seed has registered divergence and at least one `single_pass_admits_then_violates` observation. |
| CH3 | CH3 metric and all 30 seeds | CONFIRMED-WITH-CAVEAT | The rate is zero within the declared simulator population. |
| CH4 | CH4 matrix and all 30 seeds | CONFIRMED-WITH-CAVEAT | The readout reproduces but is definitionally constructed from member flags. |
| CH5 | Compensation checker, 125 profiles × 264 cells | CONFIRMED | The exhaustive grid has 98 Held profiles and a maximum of 48 compensatory admissions in one cell. |
| CH6 | W1/W2 contamination results and all intervals | CONFIRMED-WITH-CAVEAT | W1 support reproduces. W2 fails the every-seed criterion, and the paper states that limitation. |
| CH7 | 243-point checker; concrete counterexample; current 145/200 formal probe; independent 159/200 actual-code probe | CONFIRMED-WITH-CAVEAT | Non-confluence is robust and the registered order had 0/200 feasibility failures. The populated paper’s current-HEAD off-grid number is stale. |
| CH8 | Thirty per-seed artifacts and independent aggregation | CONFIRMED | The registered readout reproduces: CH1–CH5 are robust and CH6 is not robust under the all-workflows rule. |

## Delta from round one

| Claim | Round 1 | Round 2 | Reason for change |
|---|---|---|---|
| C1 | REFUTED | CONFIRMED-WITH-CAVEAT | The false universal theorem was replaced by a correct linear-family threshold theorem; only the proof tag remains too broad. |
| C2 | CONFIRMED | CONFIRMED | No substantive change; exhaustive lattice result reproduces. |
| C3 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | The claim is now explicitly limited to the implemented construction. |
| C4 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | Necessity was removed and exact in-memory evidence is audited; proof-tag and persisted-reload caveats remain. |
| C5 | REFUTED | CONFIRMED-WITH-CAVEAT | The claim was weakened to identity commitment and schema v2 adds provenance fields, but no resolvable store/write history is implemented. |
| C6 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | The definitional-union caveat is unchanged. |
| C7 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | The population-scope caveat is unchanged. |
| C8 | CONFIRMED | CONFIRMED | Fresh bootstrap and clean engines reproduce. |
| C9 | CONFIRMED-WITH-CAVEAT | REFUTED | Current formal artifacts and populated paper are stale, and one selected replay is not byte-exact. |
| CH1 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | The synthetic-evidence defect is fixed in memory; persisted evidence is still not loaded for audit. |
| CH2 | CONFIRMED | CONFIRMED | Registered divergence reproduces. |
| CH3 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | Simulator-population limitation is unchanged. |
| CH4 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | Definitional-union limitation is unchanged. |
| CH5 | CONFIRMED | CONFIRMED | Exhaustive finite-grid result reproduces. |
| CH6 | CONFIRMED-WITH-CAVEAT | CONFIRMED-WITH-CAVEAT | W1/W2 split remains honestly reported. |
| CH7 | CONFIRMED | CONFIRMED-WITH-CAVEAT | Qualitative and finite-grid results reproduce, but the populated current-HEAD off-grid count is stale. |
| CH8 | CONFIRMED | CONFIRMED | Independent aggregation reproduces the registered readout. |

## Proof classifications

- **Proposition 1:** `pending-human-review` for the arbitrary-\(n\) analytic theorem; the executable certification is finite \(n=3\). The algebraic proof is correct, but the `machine-checked` tag overstates executable scope.
- **Lemma 1:** `checked-scope-only` for the current one-shot branch and exercised pinned DQ behavior. Its dependence on the external predicate contract is now stated.
- **Theorem 1:** `checked-scope-only` for the current implementation under Lemma 1 and the five-response join. The lattice checker proves join hardening, not all arbitrary gate/state premises in the theorem.
- **Corollary 1:** `checked-scope-only` for sufficiency on executed-reachable actions under Lemma 1 and downstream-gate invariance. The false necessity direction is properly retracted.
- **Proposition 4:** `checked-scope-only` for schema-v2 field presence and deterministic content commitments. Store-backed resolution and specific write-event identity are not machine-checked.

## New findings

### Severity 2: current-HEAD formal artifacts and paper are stale

The response commit changed HEAD-derived checkers but committed outputs generated at the preceding review commit. Rerunning `make formal` changes `out/checkers/compensation_check.json` from HEAD `514f016…` to `af4a3f0…` and changes CH7 off-grid non-confluence from 140/200 to 145/200. Because `make paper` depends on `suite`, not `formal`, the normal paper target embeds the stale 140/200 value.

Reproduce:

1. At `af4a3f019128de569708ff5fe83c900701aa865e`, run `make paper`.
2. Run `make formal`.
3. Inspect `git diff -- out/checkers/compensation_check.json out/checkers/remediator_check.json`.
4. Compare `out/paper/slots_v3.json` with the freshly generated remediator checker.

### Severity 2: proof tags exceed executable scope

Proposition 1 calls the arbitrary-\(n\), continuous linear theorem `machine-checked`, but the checker samples the real three-gate encoding over 1,064 finite cells. Theorem 1 similarly derives `machine-checked` from a finite response-lattice hardening check, which does not execute arbitrary gates, action spaces, current-state transitions, or Lemma 1’s external predicate premise. These claims are defensible mathematical or structural arguments, but under the round-one taxonomy they are not fully machine-checked.

### Severity 3: one selected seed is not byte-reproducible

Isolated replay of seed `1028331701` differs from the committed artifact only at `ch6.W1.plain.poisoned_mean_abs_value_delta`: committed `2.3614615384615383`, replayed `2.361461538461538`. The delta is one ULP, \(4.44\times10^{-16}\), and does not affect displayed results, but it fails the required byte comparison.

### Severity 3: Phase II predicate emptiness is undocumented

Across 81,312 unified lines, `gates.dq.predicates` is empty on 74,995 and non-empty on 6,317. Empty Phase II lists are expected after successful remediation and on clean evidence, but `schemas/evidence_line.schema.json` merely permits an array; it does not document why empty differs from missing or how Phase I predicates should be read alongside it.

### Severity 3: disclosure is not byte-verbatim

The paper’s validation note is substantively equivalent to the round-one disclosure, but it replaces the literal `<path/link>` token in `review/review.json` with concrete paths. It also states that the response has not been re-reviewed, which becomes stale once this round-two report is incorporated. This is a protocol-format issue, not a scientific-result defect.

## Mechanical and adversarial evidence

- **Tests:** 155 passed, 0 failed, 0 skipped; 40.54 seconds.
- **Suite:** exit 0; 8.14 seconds. Each S1–S4 run produced 10,164 decisions; single-seed CH1 = 0, CH2 = 239, label-only = 200, CH3 = 0, CH4 union = true.
- **Paper:** exit 0; 8.56 seconds.
- **Formal:** exit 0; 1.14 seconds. Lattice 17,151/17,151; compensation 125 profiles × 264 cells, maximum 48; CH7 86/243 and current HEAD off-grid 145/200.
- **Schema:** a 200-line HEAD-derived sample validates with zero errors against schema v2; all 81,312 unified lines declare version 2.
- **Leakage:** zero ground-truth/label-pattern hits in all 81,312 unified Evidence Set lines.
- **Mutation sample:** 150 HEAD-derived mutants selected from 808 `composition.py` mutants; 127 killed and 23 survived, rate 0.8467, Wilson 95% interval [0.7804, 0.8956]. The committed 0.8804 score lies inside the interval.
- **Independent compensation family:** 200 HEAD-derived families, including zero weights, unnormalized weights, extreme scales, and dimensions 2–7; 800 exact-rational checks and zero mismatches.
- **Independent CH7 family:** 159/200 off-grid points were non-confluent through the actual remediation functions; substitute-then-downroute had 0/200 budget-feasibility violations.
- **Provenance probe:** 3,478 substitution occurrences produced 62 unique buffer write IDs and 3,416 duplicate occurrences; no durable write-history implementation was found.
- **Citations:** all ten registry entries were re-fetched and matched on title and first author; zero `[CITE:` placeholders remain.

Evidence is under `review-out-r2/evidence/`, including command logs and runtimes, provenance and response diffs, schema sample results, checker diffs, exact statistical recomputation, replay artifacts, mutation selection/results, citation fetches, numeral scan, and adversarial probes. The machine-readable mirror is `review-out-r2/review.json`.

## Statistics and replay audit

Every sweep mean and interval was independently recomputed from the 30 per-seed JSON artifacts using the runtime SciPy critical value. The maximum absolute difference from the committed summary was \(1.11\times10^{-16}\), so all statistics pass the protocol’s strict \(10^{-6}\) threshold.

| Seed | Selection | Wall seconds | Byte comparison | Detail |
|---|---|---:|---|---|
| 26313 | First registered | 9.59 | Exact | SHA-256 `7c922b783c270fdbd0cbbfecb852cd4f6c706971063479709e5927dc2bdb5820` |
| 1028331701 | HEAD-derived | 9.41 | Not exact | One-ULP delta in one CH6 W1 floating mean; all other content agrees |
| 84716818 | HEAD-derived | 9.23 | Exact | SHA-256 `b263821a9ad5cef57d1b40f9e212f52b5629dd5db04ce304395f2acf848560b9` |

## Scores

- **Research-artifact lens: 7.5/10.** The two severity-1 overclaims were substantively corrected, the revised central theorem is true, citations are complete, and the statistical/formal evidence is strong. Deductions reflect two severity-2 issues: proof labels that exceed executable scope and stale current-HEAD formal evidence in the populated paper.
- **Software-engineering lens: 7.5/10.** The pinned build, 155-test suite, schema validation, source integrity, mutation calibration, and exact in-memory evidence audit are strong. Deductions reflect artifact-generation ordering, failure to reload persisted audit evidence, and the one-ULP byte-replay miss.

Under the round-one calibration, a 10 requires no severity-1 or severity-2 findings and every claim to be confirmed or confirmed-with-caveat with the caveat already stated by the paper. This HEAD does not meet that bar.

## Disclosure

This artifact was independently replicated and adversarially reviewed in two rounds by automated agents following the published protocols in sarc-suite-agent-review.md and sarc-suite-agent-review-r2.md; the round-one report and evidence are at review/REVIEW.md and review/review.json, and the round-two report and evidence are at review-out-r2/REVIEW-R2.md, review-out-r2/review.json, and review-out-r2/evidence/. Automated review complements and does not replace human peer review.
