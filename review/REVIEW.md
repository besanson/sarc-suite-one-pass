# Independent Automated Review: sarc-suite-one-pass

## 1. Reviewer identity

| Field | Value |
|---|---|
| Reviewer | Automated agent |
| Model | Perplexity Computer |
| Date | 2026-08-13 |
| Protocol version | sarc-suite-one-pass attached protocol |
| Repository HEAD reviewed | `2009890eded25c0dd30df2e4f541073c3cfd9ef5` |

This report is an automated review and is not human peer review.

### Environment and provenance

- `prereg-v1` was verified remotely; its tree contained no `out/` or results paths, and commit order was verified as P0, preregistration, P2 hardening, P3 results, P4 formal, P5 paper.
- Fresh `make bootstrap` succeeded at the three `engines.lock` SHAs. `make test` passed 135 tests; `make suite` and `make paper` each exited 0.
- Engine clones and repository tracked state were clean after runs; source-data SHA-256 was unchanged. A HEAD-derived sample of 200 Evidence Set lines validated against the schema.
- All 81,312 Evidence Set lines had no ground-truth leakage. All four verified citation URLs were re-fetched and their title/first-author pairs matched. The populated paper still contains six `[CITE]` placeholders.

## 2. Verdict table

| Claim | Evidence checked | Verdict | Note |
|---|---|---|---|
| C1 | Appendix Proposition 1; compensation checker; analytical counterexample | REFUTED | Compensatory aggregation violates veto: the stated continuous universal claim is false; the finite-grid result holds. |
| C2 | Lattice checker rerun: 17,151 exhaustive checks | CONFIRMED | Join composition is order-invariant absent remediation for the implemented Response join. |
| C3 | S4 construction; metrics; 30-seed sweep; exact replay | CONFIRMED-WITH-CAVEAT | Single-pass unsoundness is established for the implemented gates, not arbitrary remediators. |
| C4 | Composition path; audit tests; 30-seed output | CONFIRMED-WITH-CAVEAT | Remediate-regate evaluates the remediated action; termination relies on the external DQ predicate contract. |
| C5 | Evidence-line schema/output; substituted-line inspection | REFUTED | Unified Evidence Set does not reconstruct original bytes or substitution provenance from hashes and numeric values alone. |
| C6 | metrics._ch4_matrix; 30-seed sweep | CONFIRMED-WITH-CAVEAT | No manufactured coverage holds by the coded union-of-member-flags definition. |
| C7 | CH3 metrics and all 30 seed artifacts | CONFIRMED-WITH-CAVEAT | Zero false holds applies to the defined synthetic, label-derived population only. |
| C8 | Fresh make bootstrap at engines.lock SHAs; clean engine clones; make test/suite/paper | CONFIRMED | Engines compose unmodified at the pinned SHAs. |
| C9 | Fresh bootstrap; make test/suite/paper; three byte-exact seed replays; provenance | CONFIRMED-WITH-CAVEAT | Build and selected artifacts reproduce; release-level provenance remains qualified. |
| CH1 | 30-seed sweep; post-hoc audit; CH1 metrics | CONFIRMED-WITH-CAVEAT | Zero audited violations; audit rebuilds synthetic clean evidence rather than the exact executed evidence. |
| CH2 | S4; 30 seed artifacts; recomputed statistics | CONFIRMED | Single-pass unsoundness is realized in every registered seed. |
| CH3 | CH3 metrics; 30 seed artifacts | CONFIRMED-WITH-CAVEAT | Deterministic selectivity is limited to the declared simulator population. |
| CH4 | CH4 matrix; 30-seed summary | CONFIRMED-WITH-CAVEAT | Coverage equality reproduces but is directly constructed from member detector flags. |
| CH5 | Compensation checker: 125 profiles × 264 cells | CONFIRMED | Compensation is unsafe on the declared discrete grid. |
| CH6 | Contamination metrics; 30-seed W1/W2 sweep | CONFIRMED-WITH-CAVEAT | W1 is supported; W2 fails its every-seed criterion and is reported as unsupported. |
| CH7 | Remediator checker; actual remediation replay; off-grid probe | CONFIRMED | The two implemented remediators are order-dependent. |
| CH8 | Sweep aggregation and 30 seed artifacts | CONFIRMED | Registered robustness across seeds/workflows reproduces (CH1–CH5 true, CH6 false). |

## 3. Pending-human-review proof classifications

| Statement | Classification | Largest scope certified | Reason |
|---|---|---|---|
| Proposition 3 (Appendix A, lines 112–158) | `checked-scope-only` | Conditional algebraic construction with a substituting DQ decision and cap strictly between pre/post values; implemented S4 across 30 registered seeds. | Valid existential construction, but no executable checker covers arbitrary continuous economics or arbitrary gate implementations. |
| Lemma 1 (Appendix A, lines 162–195) | `checked-scope-only` | Current one-shot composition branch and exercised DQ-library behavior in scenarios/tests. | The argument depends on an external DQ predicate contract; the repository does not prove every possible governed record cannot retrigger substitution. |
| Theorem 1 and Corollary 1 (Appendix A, lines 199–233) | `insufficient` | Phase-II re-evaluation and restrictive join are structurally sufficient for current code, conditional on gate semantics. | The iff corollary’s necessity direction does not follow: a non-invariant gate can vary only on actions independently held and never executed. |
| Proposition 4 (Appendix A, lines 237–268) | `error-found` | Evidence-line JSON shape and presence of post-Phase-II evidence IDs. | Content hashes cannot reconstruct bytes absent a separate record store, and output omits original evidence and substitute provenance. |

## 4. Findings ranked by severity

### Severity 1

#### F1: Proposition 1/C1 is false as stated

**Impact.** The paper overclaims a universal continuous-domain veto theorem beyond the finite grid actually checked.

**Reproduction.** Set f(s)=s1+s2+s3 and tau=2.5 on [0,1]^3. f(1,1,1)=3 is admissible; with any coordinate 0, f≤2, so no vetoed profile is admitted.

**Recommended follow-up.** Retract or weaken the universal proposition, or add a condition ensuring a vetoed profile can meet the threshold.

#### F2: Proposition 4/C5 cannot reconstruct records or substitution provenance from Evidence Set alone

**Impact.** The lineage claim is materially stronger than the emitted evidence supports.

**Reproduction.** Inspect any substituted remediate-regate line: it contains a post-remediation evidence_id and numeric substituted_value, but no original bytes/metadata or buffer-write provenance. Hashes are not reversible.

**Recommended follow-up.** Store immutable content/provenance objects or durable resolvable references for original and remediated evidence, or weaken the claim to identity commitment.

### Severity 2

#### F3: Theorem 1 iff corollary has an unproved and generally false necessity direction

**Impact.** The paper treats gate invariance as necessary for single-pass soundness without an executability/reachability condition.

**Reproduction.** Let authority vary under rho only for actions independently held by DQ. Those actions never execute, so single-pass can remain sound despite non-invariance.

**Recommended follow-up.** State only sufficiency, or add and prove explicit universal reachability/executability assumptions.

#### F4: CH1 post-hoc audit does not re-evaluate exact executed evidence

**Impact.** The zero-violation claim is weaker than its DQ wording suggests.

**Reproduction.** composition._audit_clean_evidence_record rebuilds a clean governed-buffer record from action values; audit_executed uses that synthetic record rather than the execution evidence/metadata.

**Recommended follow-up.** Persist and audit the exact Phase-II evidence or a lossless canonical representation.

#### F5: Six unresolved [CITE] placeholders remain in the populated paper

**Impact.** The paper is not bibliographically complete for release.

**Reproduction.** Count [CITE tokens in the populated paper: 6. The local release output reports the same count.

**Recommended follow-up.** Replace placeholders with verified citations before release.

### Severity 3

#### F6: Exact scipy t-intervals exceed the protocol 1e-6 tolerance for two endpoint pairs

**Impact.** Displayed paper rounding is unaffected, but the stated exact-tolerance audit criterion is not met.

**Reproduction.** Recompute with scipy t(df=29): CH2 divergent endpoints differ by up to 1.085566964e-6 and CH5 max-violations endpoints by up to 3.767356247e-6 because sweep.py uses rounded T_CRIT_DF29=2.045230. All other intervals are within tolerance.

**Recommended follow-up.** Compute the critical value from scipy (or relax/document the tolerance for the rounded constant).

## 5. Statistics audit

All reported means and intervals were recomputed from the 30 seed artifacts using 29 degrees of freedom. The following exact library-path reruns bypassed cached per-seed results and matched their committed artifacts byte-for-byte:

| Seed | Wall-clock seconds | SHA-256 (produced = committed) | Byte-exact |
|---:|---:|---|---|
| 26313 | 10.328566951 | `7c922b783c270fdbd0cbbfecb852cd4f6c706971063479709e5927dc2bdb5820` | Yes |
| 84716818 | 9.882554574 | `b263821a9ad5cef57d1b40f9e212f52b5629dd5db04ce304395f2acf848560b9` | Yes |
| 1146288088 | 9.784135801 | `1fd6963d22802c71a025c88ee887c53777e7175c81e5ea11c50db41cc77c7b46` | Yes |

- Mutation sample: 127 killed and 23 survived of 150 HEAD-derived mutants, kill rate 0.8467. Wilson 95% interval `[0.7804, 0.8956]` contains the committed 0.8804 rate.
- Exact scipy t(df=29) comparison exceeded the protocol 1e-6 threshold only for CH2 divergent endpoints (maximum delta `1.085566964e-6`) and CH5 max-violations endpoints (`3.767356247e-6`), due to rounded `T_CRIT_DF29=2.045230`. All other intervals were within tolerance, and displayed paper rounding is unaffected.
- Extra falsification probes: the general C1 counterexample was found; 144/200 HEAD-derived off-grid points were non-confluent; and downroute feasibility found 0/200 violations.
- Mandatory source and leakage audit: no hand-entered result-like literal was found feeding a checked reported metric; all reported paper numbers had a machine source. Ground-truth labels are absent from all 81,312 Evidence Set lines, although the current separation is by API/data flow rather than a hard runtime-isolation boundary.

## 6. Scores

### Research-artifact lens — 5.5/10

The artifact has strong preregistration, determinism, build, replay, and measurement mechanics. It cannot score highly because two severity-1 findings invalidate a stated universal theorem and an Evidence Set reconstruction claim. A score of 10 requires zero severity-1 or severity-2 findings and all claims confirmed; this review does not meet either condition.

### Software-engineering lens — 8.0/10

Fresh bootstrap, tests, suite, paper generation, exact replays, clean-engine and source-integrity checks, schema validation, and mutation sampling are strong. Deductions remain for the synthetic-evidence audit gap, rounded t-critical precision discrepancy, and unresolved citation placeholders.

## 7. Disclosure paragraph

This artifact was independently replicated and adversarially reviewed by an automated agent following the published protocol in sarc-suite-agent-review.md; the full report and evidence are at <path/link>. Automated review complements and does not replace human peer review.
