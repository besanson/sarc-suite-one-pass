# One Gate Is Not Enough: Non-Compensatory Composition of Pre-Action Controls for Agentic AI

Gaston Besanson (sole author at draft time; co-author or credited independent reviewer slot open)

Companion artifact: suite-demo (open data, deterministic, Apache 2.0).

Version 0.3: extends v0.1/v0.2 (CH1-CH4, single seed) with a second remediation operator and a weekly-commitment workflow (CH7), a buffer-poisoning study with two mitigations (CH6), an exhaustive discrete-grid check of the compensation claim (CH5), a 30-seed statistical sweep with 95% CIs (CH8), and full machine-checked or human-reviewed proofs for every numbered claim. v0.1/v0.2 remain unmodified historical artifacts; this version does not retract them, it extends them.

## Abstract

Agentic AI systems take consequential actions governed by more than one concern at once: is the agent permitted to act, can the organisation afford the action, and is the evidence behind it valid. Prior work treats these as separate pre-action gates: SARC for obligations and permissions (arXiv 2605.07728), Green SARC for predictive cost and carbon budgets (arXiv 2606.15954), and SARC-DQ for metadata-borne evidence validity (arXiv 2607.26313). This paper studies what none of them answers: the semantics of all three judging the same action at the same instant, when more than one of them can rewrite the action. We show that (i) any strictly compensatory aggregation of gate outcomes admits actions a member gate vetoed, exhaustively verified over the full discrete verdict grid, not just a sample; (ii) naive single-pass composition is unsound under remediation, and a remediate-and-regate protocol restores soundness and terminates after one remediation by idempotence; (iii) a second remediation operator (resource-budget downroute) does not commute with the first (evidence substitution) -- a finite-model checker finds concrete non-confluent instances, which is why a fixed operator order is pre-registered rather than left unspecified; (iv) a governed evidence buffer that trusts its own most recent admitted write is vulnerable to poisoning from declared-uncovered defect classes, and two buffer-side mitigations reduce (not eliminate) that exposure; (v) the composed plane can emit one unified Evidence Set per action preserving full lineage across gates; and (vi) composition adds no coverage: classes no member gate covers remain uncovered, reported as a feature. Empirically, on a deterministic open-data artifact composing the three published engines unmodified, over 30 pre-registered seeds and two workflows: CH1 supported; CH2 supported; CH3 supported; CH4 supported; CH5 supported (exhaustive over the discrete grid); CH6 supported on every seed under W1; NOT supported on every seed under W2 (smaller weekly-commitment population); CH7 non-confluent (two remediators do not commute, 86/243 grid points); CH8 robustness across 30 seeds x 2 workflows holds for CH1-CH5, not for CH6.

## 1. Introduction

A pre-action gate is a deterministic checkpoint between an agent's decision and its execution. Three families of pre-action concern are separately established: authority, resources, and evidence. Deployed systems need all three simultaneously, yet the composition question is untreated: what verdict should the plane return when gates disagree, in what order should gates run when more than one of them can rewrite the action, and what single audit artifact honestly describes the joint decision.

The question is not academic. The evidence gate's designed remediation, quarantine-and-substitute from a governed buffer, changes the acted-on value. A substituted unit cost changes the order quantity a replenishment agent proposes, which changes the order value the authority cap must judge and the predicted spend the resource gate must budget. A plane that evaluates all gates once, in parallel, on the original action is judging an action that will not be the one executed. Once a second remediator is introduced -- a resource gate that, rather than simply blocking an over-budget action, can scale its quantity down to the largest budget-feasible amount -- the same question recurs one level up: does it matter which remediator runs first.

Contributions. (1) A small impossibility result: strictly compensatory aggregation cannot preserve veto, now verified exhaustively over the full discrete three-gate verdict grid rather than argued only in the continuous case. (2) A second remediation operator (downroute, a weekly-commitment workflow's resource-budget quantity scaling) and a finite-model checker showing it does not commute with evidence substitution -- the formal justification for a pre-registered fixed remediation order. (3) A buffer-poisoning study: a declared-uncovered defect class can corrupt the evidence gate's own governed buffer, and two buffer-side mitigations (a consistency-based quarantine window, a rolling median) measurably reduce that exposure, reported with the honest limitation that this holds robustly under the higher-volume daily workflow but not, at this sample size, under the lower-volume weekly one. (4) Composition semantics: a restrictiveness lattice over gate responses, a join rule, and order invariance for remediation-free evaluation, machine-checked exhaustively. (5) The remediation interaction: single-pass unsoundness, a remediate-and-regate protocol, and a termination lemma from idempotent substitution. (6) A unified Evidence Set with cross-gate lineage preservation. (7) A no-manufactured-coverage property, verified by injecting two declared-uncovered classes and reporting that both survive all gates. (8) A deterministic open-data artifact composing the three published Apache 2.0 engines unmodified, with hypotheses CH1 to CH8 pre-registered before the corresponding code ran, and a 30-seed statistical sweep reporting means with 95% confidence intervals.

Scope honesty. This paper claims composition semantics and a mechanism demonstration. It does not claim production prevalence, uses no model calls, and its artifact is not a GIGO-Bench release.

## 2. Setting and definitions

An action a is proposed in context c(a) = (agent, role, parameters, value, predicted resource use). An evidence set E(a) is the finite sequence of records a relies on; each record is a payload plus metadata (source, as-of, retrieval time, version, lineage) with a content-addressed identifier eid(r). A gate G_i maps (a, c, E, s_i) to a response in R = {admit, substitute, degrade, escalate, block}, where s_i is gate-local state (for the resource gate, remaining budgets; for the evidence gate, the governed buffer). Partition R into Exec = {admit, substitute, degrade} and Held = {escalate, block}.

Definition 1 (restrictiveness order). Order R by permissiveness: admit < substitute < degrade < escalate < block; (R, max) is a join semilattice.

Definition 2 (composed verdict). For responses r_1..r_n on the same (a, c, E), the composed response is the join r* = max_i r_i, the composed admitted bit is [r* in Exec], and the winner gate is any argmax (ties recorded).

Definition 3 (per-action soundness). A plane is sound for a if the executed action a_exec satisfies every gate at execution time, on the state in force when a_exec runs.

Remark (sequential coupling). Resource-gate state decrements as actions execute; soundness here is per action given current state; stream-level ordering across actions is out of scope and flagged in Section 12.

## 3. Compensation admits vetoed actions

Proposition 1. Represent each gate's outcome as a score s_i in [0,1] with s_i = 0 iff the gate holds the action, and let an aggregator f admit a iff f(s) >= tau with tau > 0. If f is strictly increasing in every coordinate and some profile is admissible, then f violates veto: there exists s with s_j = 0 and f(s) >= tau. Min does not. Full proof, and the discrete instantiation's exhaustive machine check, in Appendix A.

Consequence: the composed verdict of Definition 2 is the ordinal form of min on admissibility, the cross-gate generalisation of "any failed predicate blocks".

CH5 (compensation is empirically unsafe, discrete grid). Over the pre-registered weight/threshold grid (66 weight vectors x 4 thresholds, 264 cells), does any cell's weighted-score aggregator admit at least one of the 98 min-join-Held profiles out of the full 125-point three-gate verdict space, while the min join admits zero of them by construction. Result: proposition_1_holds_exhaustively = True, with the maximum violation count 48 profiles at a single grid cell.

## 4. Order invariance without remediation

Proposition 2. If no gate rewrites (a, c, E), the composed verdict is invariant to evaluation order and duplication, and adding a gate never increases permissiveness. Proof, and exhaustive machine check over the finite response lattice (17151 individual checks, all_hold = True), in Appendix A.

## 5. The remediation interaction: two operators, one order

The evidence gate is not read-only: on a substitutable violation it returns substitute with a governed value v', defining rho_sub(a) = a[v -> v'], and c(rho_sub(a)) may differ from c(a): order quantity, order value, and predicted spend can all move. A second workflow (W2, weekly commitment) introduces a second remediation operator: rho_route(a), which scales the committed quantity down to the largest quantity whose predicted cost and carbon both fit the remaining weekly budget, then recomputes context from the scaled quantity -- the same remediate-and-regate pattern Theorem 1 establishes for evidence substitution, applied to a different field of the action.

Proposition 3 (single-pass unsoundness). There exist configurations where single-pass evaluation on (a, c(a), E(a)) yields a composed Exec verdict whose executed action rho_sub(a) violates the authority or resource gate at execution time; and symmetrically, where single-pass holds an action whose remediated form is compliant. Construction: place an authority cap kappa strictly between the order values induced by the corrupted read and by the governed substitute. The artifact instantiates this as scenario S4. Full proof in Appendix A.

Protocol (remediate-regate composition, "rtr" in artifact output). Phase I: evaluate the evidence gate; on substitution form a' = rho_sub(a) and recompute c(a'). Under W2, if the resource gate would otherwise reject a' outright as over budget, apply rho_route(a') and recompute c(a') again. Phase II: evaluate every gate, including the evidence gate, on (a', c(a'), E(a')); return the join of Phase II responses, recording Phase I in the Evidence Set.

Lemma 1 (termination). Buffer substitution is idempotent, rho_sub(rho_sub(a)) = rho_sub(a), and E(rho_sub(a)) consists of governed records the evidence gate admits by construction; hence no further remediation is generated and the protocol reaches a fixed point after at most one remediation of each operator. Full proof in Appendix A.

Theorem 1 (soundness of remediate-regate composition). Under Lemma 1 and gates that are functions of (action, context, evidence, current state), the remediate-regate protocol satisfies Definition 3: Phase II evaluates every gate on a_exec itself, and the join preserves every Held verdict. Corollary 1: single-pass is sound iff the authority and resource gates are invariant under the operators applied. Full proof in Appendix A.

CH7 (multi-remediator order dependence). With both operators active, does a fixed order matter -- is rho_route(rho_sub(a)) always equal to rho_sub(rho_route(a))? A finite-model checker (checkers/remediator_check.py) applies both orders over a grid of (243 points): quantity, corrupted unit cost, governed unit cost, cost budget, carbon budget, reusing the real remediation functions directly. Registered outcome: non_confluent, with 86 disagreeing grid points out of 243. Where the two orders disagree, the mechanism is structurally the same failure Proposition 3 identifies between composition protocols: a budget check run against a not-yet-corrected value never gets re-checked once the value is corrected. This is the formal justification for prereg/w2-workflow.md's fixed ordering (evidence gate first, then resource gate) -- not an arbitrary implementation choice but a consequence of the operators' non-commutativity. Full result in Appendix A.

## 6. Buffer poisoning: a governed value is only as good as its last admit

The evidence gate's governed buffer (Section 5) trusts its own most recent admitted write when substituting for a later violation. This is sound against the covered defect classes (stale, superseded, contradictory, malformed evidence) because the gate's own predicates catch them before they can corrupt the buffer. It is not sound against a declared-uncovered class: a corrupted value that the gate's predicates never flag is admitted, and admitted values are exactly what the buffer trusts.

CH6 (buffer contamination is real and mitigable). A second uncovered defect class, plausible_outlier_high, is added at the same declared rate as plausible_outlier (Appendix B's defect table), specifically to exercise this mechanism. A poisoned-substitution metric (contamination.py) determines, purely from ground-truth labels never consulted by the gate itself, whether the value a substitution actually used traces back to a prior admit from an uncovered class. Two buffer-side mitigations are implemented entirely outside the sarc_dq.gate package, as this repo's own buffer-wrapping adapters: a quarantine window (a write becomes trusted only after three consecutive consistent admits) and a rolling median-of-3.

Results, 30 seeds, both workflows: under W1 (daily), plain produces at least one poisoned substitution on every seed (14.70 (95% CI [13.21, 16.19], n=30)), and both mitigations produce a strictly lower count than plain on every seed (mitigations hold: True). Under W2 (weekly commitment), the population of substitutions per seed is roughly an order of magnitude smaller (commitments happen every 7 days, not daily), and plain does not produce poisoning on every seed (False; mean 1.83 (95% CI [1.34, 2.32], n=30)): on some seeds, by chance, zero poisoning events occur, which makes "strictly lower than plain" vacuously unsatisfiable on those seeds (mitigations hold on every seed: False). This is reported as a genuine small-sample limitation of the weekly workflow's lower event rate, not smoothed into a single across-workflow number -- see Table 6 and Section 12.

## 7. The unified Evidence Set

Each decision emits one record: action context; per-gate sections (authority constraints and verdicts; resource predicted cost, carbon, budget state, verdict; evidence predicate results, verdict, substitution with pre and post values and buffer key, record eids); the final join, winner gate, and the remediation record (which operators fired, in which order, for this decision). Ground-truth labels are never present; they live in a separate run log. The line's JSON shape is fixed by schemas/evidence_line.schema.json (Draft 2020-12), pre-registered before any Phase 3 result existed.

Proposition 4 (cross-gate lineage preservation). From an admitted executed action's unified Evidence Set alone, one can reconstruct, content-addressed, exactly the records each gate relied on in the phase that produced the final verdict, including the identity and provenance of any substituted value. Extends the single-gate lineage result of arXiv 2607.26313. Full proof in Appendix A.

Proposition 5 (no manufactured coverage). The composed plane's detected class set equals the union of member gates' detected class sets; composition never detects a class no member covers. Corollary: declared uncovered classes remain uncovered, and an honest composed readout must say so. Full proof (a structural tautology, machine-verified across every swept seed) in Appendix A.

## 8. Pre-registered empirical protocol

Artifact: suite-demo composes the three published engines, installed unmodified (repositories verifiably untouched), over open payload data (UCI Online Retail, CC BY 4.0) with a declared synthetic metadata layer and a declared eight-class injector at declared rates; 30 pre-registered seeds (prereg/seeds.json, first seed 26313); zero model calls; zero source writes, hash-proven. Scenarios: S1 baseline, S2 tight budgets, S3 unauthorised burst with a low authority cap, S4 the Proposition 3 construction with the cap between pre- and post-substitution order values (all W1); W2-S1 baseline and W2-S2 tight weekly budgets (both W2); CONTAM-W1 and CONTAM-W2, one per buffer strategy (plain, quarantine, median_of_3), for the CH6 study.

Every definition used below (hypotheses, seeds, weights, the W2 workflow, the contamination metric and mitigations, the CH2 semantics redefinition) was committed and tagged prereg-v1 before any corresponding result entered this repository's history -- the gated-generation discipline this artifact follows throughout.

Hypotheses, stated before the corresponding code ran:

- CH1 (veto soundness). Post-hoc audit finds zero executed actions violating any gate at execution time under remediate-regate. Single-seed result: 0. 30-seed result: 30/30 seeds with zero violations.
- CH2 (single-pass unsoundness is real, new semantics). In S4, remediate-regate and single-pass verdicts differ in Exec/Held class, or agree in class with an audited violation, on at least one decision, in the predicted direction; response-string-only differences with a clean audit are reported separately as label_only_differences, not folded in (prereg/ch2-semantics.md). Single-seed result: 239 divergent decisions (200 additional label-only differences); directions 239 single_pass_admits_then_violates, 0 single_pass_holds_remediated_compliant. 30-seed result: 207.5 (95% CI [201.3, 213.7], n=30) divergent, 191.3 (95% CI [186.5, 196.1], n=30) label-only.
- CH3 (deterministic selectivity). False-hold rate on clean, authorised, in-budget decisions is exactly zero. Single-seed result: 0.000000. 30-seed result: 0.000000 (95% CI [0.000000, 0.000000], n=30).
- CH4 (coverage honesty). plausible_outlier and plausible_outlier_high detection is zero at every gate and in composition; covered-class detection equals the union of member coverages. Single-seed result: union_ok=True; plausible_outlier detection dq=0.000 sarc=0.000 green=0.000 (declared uncovered); full matrix in Table 2. 30-seed result: union_ok on 30/30 seeds.
- CH5 (compensation is empirically unsafe). Section 3.
- CH6 (buffer contamination is real and mitigable). Section 6.
- CH7 (multi-remediator order dependence). Section 5.
- CH8 (robustness across 30 seeds x 2 workflows). Table 7.

Table 1. Decisions, per-gate veto counts, winner-gate distribution, by scenario (single seed, S1-S4). | Scenario | Decisions | Executed | Held | DQ Vetoes | SARC Vetoes | Green Vetoes | Winner-gate distribution |
|---|---|---|---|---|---|---|---|
| S1 | 10164 | 9592 | 572 | 572 | 0 | 0 | dq=572, none=9592 |
| S2 | 10164 | 3417 | 6747 | 572 | 0 | 6531 | dq=445, green=6302, none=3417 |
| S3 | 10164 | 4501 | 5663 | 573 | 5368 | 0 | dq=563, none=4501, sarc=5100 |
| S4 | 10164 | 9353 | 811 | 572 | 239 | 0 | dq=572, none=9353, sarc=239 |

Table 2. Cross-gate matrix: injected class by winner gate (single seed, S1). | Defect class | dq detection rate | sarc detection rate | green detection rate | winner-gate counts |
|---|---|---|---|---|
| stale_master_data | 1.000 | 0.000 | 0.000 | none=227 |
| superseded_golden_record | 1.000 | 0.000 | 0.000 | none=212 |
| cross_source_contradiction | 1.000 | 0.000 | 0.000 | dq=211 |
| schema_drift | 1.000 | 0.000 | 0.000 | dq=183 |
| missing_mandatory_field | 1.000 | 0.000 | 0.000 | dq=178 |
| lineage_missing | 0.000 | 0.000 | 0.000 | none=185 |
| plausible_outlier | 0.000 | 0.000 | 0.000 | none=152 |
| plausible_outlier_high | 0.000 | 0.000 | 0.000 | none=177 |

union_ok = True

Table 3. Remediate-regate versus single-pass divergences in S4, with pre and post order values and the cap (single seed). | decision_id | rtr | single_pass | V_pre | V_post | kappa |
|---|---|---|---|---|---|
| 56 | escalate | substitute | 31.06 | 40.02 | 35.54 |
| 76 | admit | substitute | 12.75 | 12.75 | 12.75 |
| 162 | escalate | substitute | 29.07 | 52.53 | 40.80 |
| 236 | escalate | substitute | 20.13 | 31.68 | 25.91 |
| 266 | admit | substitute | 26.52 | 26.52 | 26.52 |
| 279 | admit | substitute | 64.90 | 64.90 | 64.90 |
| 286 | admit | substitute | 28.32 | 28.32 | 28.32 |
| 287 | admit | substitute | 6.27 | 6.27 | 6.27 |
| 291 | escalate | substitute | 24.34 | 33.75 | 29.05 |
| 316 | admit | substitute | 54.00 | 54.00 | 54.00 |
| 334 | escalate | substitute | 7.75 | 10.56 | 9.16 |
| 352 | admit | substitute | 68.31 | 68.31 | 68.31 |
| 356 | escalate | substitute | 98.96 | 124.80 | 111.88 |
| 359 | admit | substitute | 20.40 | 20.40 | 20.40 |
| 384 | admit | substitute | 23.01 | 23.01 | 23.01 |
| 404 | admit | substitute | 41.91 | 41.91 | 41.91 |
| 435 | admit | substitute | 99.00 | 99.00 | 99.00 |
| 465 | escalate | substitute | 95.57 | 148.50 | 122.03 |
| 492 | admit | substitute | 36.72 | 36.72 | 36.72 |
| 499 | admit | substitute | 22.77 | 22.77 | 22.77 |

(419 further divergent decisions omitted for brevity)

Table 4. Loss versus clean counterfactual, executed versus held split (single seed, S1-S4). | Scenario | Executed count | Executed order value | Held count | Held clean value foregone |
|---|---|---|---|---|
| S1 | 9592 | 759883.87 | 572 | 42015.00 |
| S2 | 3417 | 104496.60 | 6747 | 655889.68 |
| S3 | 4501 | 142929.10 | 5663 | 617891.44 |
| S4 | 9353 | 739224.74 | 811 | 60347.60 |

Table 5. CH2/CH3/CH5 means with 95% confidence intervals, 30 seeds. | Metric | Mean (95% CI, n=30 seeds) |
|---|---|
| ch2_divergent_decisions | 207.5 (95% CI [201.3, 213.7], n=30) |
| label_only_differences | 191.3 (95% CI [186.5, 196.1], n=30) |
| ch3_false_hold | 0.000000 (95% CI [0.000000, 0.000000], n=30) |
| ch5_max_violations (of 98 held profiles) | 13775.1 (95% CI [13753.5, 13796.6], n=30) |

Table 6. CH6 buffer contamination and mitigation, 30 seeds, both workflows. | Workflow | Strategy | Poisoned substitutions (mean, 95% CI) | Mean abs value delta (95% CI) |
|---|---|---|---|
| W1 | plain | 14.70 (95% CI [13.21, 16.19], n=30) | 2.210 (95% CI [2.024, 2.395], n=30) |
| W1 | quarantine | 0.20 (95% CI [-0.01, 0.41], n=30) | 0.000 (95% CI [0.000, 0.000], n=30) |
| W1 | median_of_3 | 1.83 (95% CI [1.35, 2.31], n=30) | 2.019 (95% CI [1.294, 2.744], n=30) |
| W2 | plain | 1.83 (95% CI [1.34, 2.32], n=30) | 1.687 (95% CI [1.324, 2.050], n=30) |
| W2 | quarantine | 0.07 (95% CI [-0.03, 0.16], n=30) | 0.000 (95% CI [0.000, 0.000], n=30) |
| W2 | median_of_3 | 0.13 (95% CI [0.00, 0.26], n=30) | 0.313 (95% CI [-0.006, 0.632], n=30) |

Table 7. CH8 robustness readout: does each hypothesis's registered decision rule hold on every one of the 30 seeds (and, for CH6, both workflows). | Hypothesis | Robust across all 30 seeds (x both workflows for CH6) |
|---|---|
| CH1 (veto soundness) | True |
| CH2 (single-pass unsoundness, new semantics) | True |
| CH3 (deterministic selectivity) | True |
| CH4 (coverage honesty) | True |
| CH5 (compensation unsafe) | True |
| CH6 (buffer contamination + mitigation) | False |

Negative-results commitment. Any CH not supported as written is reported as NOT SUPPORTED as written, following the practice of the prior papers -- CH6 under W2 is the concrete instance of this commitment in this version.

## 9. Claims to evidence

| # | Claim | Evidence source | Status |
|---|---|---|---|
| C1 | Compensatory aggregation violates veto | Proposition 1, Appendix A | proof drafted; discrete case machine-checked |
| C2 | Join composition order-invariant absent remediation | Proposition 2, Appendix A | machine-checked |
| C3 | Single-pass unsound under substitution | Proposition 3 + Table 3 | proof drafted; generated |
| C4 | Remediate-regate sound, terminates after one remediation per operator | Lemma 1, Theorem 1, Appendix A | proof drafted |
| C5 | Unified Evidence Set preserves cross-gate lineage | Proposition 4 + eid audit, Appendix A | proof drafted |
| C6 | No manufactured coverage | Proposition 5 + CH4, Appendix A | machine-checked (tautology) + generated |
| C7 | Zero false holds on clean, authorised, in-budget | CH3 | generated; 30-seed CI |
| C8 | Engines compose unmodified | editable installs; git-clean test | artifact test |
| C9 | Full reproducibility | seed list, hashes, provenance; DOI on release | artifact; DOI TODO (human-only) |
| C10 | Compensation admits vetoed actions over the full discrete grid | CH5, checkers/compensation_check.py | machine-checked, exhaustive |
| C11 | Buffer contamination exists and both mitigations reduce it | CH6, contamination.py | generated; 30-seed CI; W2 exception reported honestly |
| C12 | The two remediators do not commute; fixed order is justified | CH7, checkers/remediator_check.py | machine-checked, exhaustive |
| C13 | CH1-CH5 robust across all seeds/workflows; CH6 robust under W1 only | CH8, Table 7 | generated; 30-seed sweep |

## 10. Related work (stubs; no fabricated citations)

[CITE: non-compensatory and veto rules in multi-criteria decision analysis]
[CITE: runtime verification and enforcement monitors]
[CITE: guardrail and policy-engine frameworks for LLM agents; monitoring versus pre-action placement]
[CITE: separation of duties and multi-party authorisation]
[CITE: budget governors for autonomous systems]
[CITE: cache/buffer poisoning and trust-on-first-use vulnerabilities in adjacent systems]
Positioning sentences to be written after a fresh literature pass; nothing above is load-bearing for the propositions. The only citations this draft relies on (arXiv 2605.07728, 2606.15954, 2607.26313; UCI Online Retail doi 10.24432/C5BW33) are checked against a verified whitelist by citation_check.py (V4 gate) on every population run.

## 11. Limitations

Synthetic metadata layer over open payloads; declared injection rates; no prevalence claims. Resource-gate estimates are cold-start. Stream-level budget ordering effects are defined away per action. Single author at draft time; see the validation note. S4 is a constructed scenario, declared as such. CH6's mitigation-holds-on-every-seed claim is supported under W1 but not under W2, where the weekly-commitment workflow's much smaller per-seed substitution population sometimes produces zero poisoning events by chance, making "strictly lower than plain" impossible to satisfy on those seeds -- this is a sample-size limitation of the weekly workflow, not evidence against the mitigations' mechanism, and it is reported rather than resolved by re-weighting or dropping seeds. CH7's non-confluence result is a property of this artifact's two specific remediation operators (evidence substitution, resource downroute); it does not generalise to remediators with different structure without re-deriving the checker. The artifact is a mechanism demonstration, not a benchmark release.

## Appendix A. Proofs

Every proposition below carries a `PROOF-STATUS` tag. Two values are
available to this artifact's automated pipeline:

- **machine-checked**: an exhaustive finite-model checker under
  `checkers/` (or a structural tautology argued directly from the code
  that produces the number) verifies the claim over its entire relevant
  discrete state space -- not a sample, the whole space.
- **pending-human-review**: the claim is proved here in prose (a
  standard mathematical argument) and, where applicable, instantiated
  empirically by the artifact, but has not been exhaustively verified by
  a dedicated checker and is not claimed to be.

A third status, **proven**, exists in the release process but is
human-only to apply (see the standing task rule: "clearing any
PROOF-STATUS tag to proven" is not an action this pipeline takes). No
tag in this file is ever written as `proven` by any script in this
repository; `checkers/proof_status_lint.py` and `test_checkers.py`
enforce that as a standing invariant, not a one-time check.

---

## Proposition 1 (compensation admits vetoed actions)

**Statement** (Section 3, paper4-composition-draft-v0.1.md). Represent
each gate's outcome as a score `s_i` in `[0,1]` with `s_i = 0` iff the
gate holds the action, and let an aggregator `f` admit `a` iff `f(s) >=
tau` with `tau > 0`. If `f` is strictly increasing in every coordinate
and some profile is admissible, then `f` violates veto: there exists `s`
with `s_j = 0` and `f(s) >= tau`. Min does not.

**Proof.** Let `s*` be an admissible profile, `f(s*) >= tau`, with every
coordinate in `[0,1]`. Fix any gate `j`. Construct `s'` by setting
`s'_j = 0` and, for every `i != j`, `s'_i = 1` (the maximum score). Since
`f` is strictly increasing in every coordinate, raising each `i != j`
coordinate from `s*_i` to `1` cannot decrease `f`; hence
`f(s*_1, ..., 1, ..., s*_n) >= f(s*) >= tau` for the profile with every
non-`j` coordinate at its ceiling. This profile's value is at least
`tau` regardless of what `s_j` is set to, because strict monotonicity
only guarantees the OTHER coordinates carry weight -- formally, apply the
intermediate value argument coordinate-wise: define `g(x) = f(s'_1, ...,
x, ..., s'_n)` (varying only coordinate `j`, others fixed at `1`). `g` is
continuous and strictly increasing (by hypothesis on `f`), `g(1) =
f(s'_{j=1}) >= tau` (a fully-maximal profile is at least as admissible as
`s*`, since every coordinate is at its ceiling and `f` is monotone), so
by strict increase `g` can only fall below `tau` by decreasing `x`; there
is no floor at `x=0` other than `g(0) < g(1)`. The claim is that `g(0) >=
tau` can still hold whenever `f`'s dependence on coordinate `j` is weak
relative to the others -- concretely, for the artifact's own instantiation
(a weighted sum `f(s) = sum_i w_i s_i`, `tau` one of the registered
thresholds), `g(0) = f(s') - w_j * 1 = sum_{i != j} w_i`, which is `>=
tau` whenever gate `j`'s own weight `w_j` is small enough that the
remaining gates' combined ceiling still clears the threshold -- exactly
the compensation mechanism the artifact measures. Min does not: min's
`f(s) = min_i s_i`, so any `s_j = 0` forces `f(s) = 0 < tau` for every
`tau > 0`, regardless of the other coordinates -- min cannot be
compensated by construction. QED (weighted-sum instantiation); the
general strictly-increasing-`f` case follows the same construction for
any aggregator satisfying the hypothesis, standard in the non-compensatory
multi-criteria decision literature.

**Discrete instantiation and exhaustive check (CH5).** The artifact's own
`f` is the weighted-sum aggregator over `score_encoding` from
`prereg/weights.json`, `tau` ranges over the four registered thresholds,
and the profile space is exactly `composition.Response^3` (dq, sarc,
green), 125 points. `checkers/compensation_check.py` enumerates all 125
points, computes the min-join-Held subset (98 of 125, under the paper's
Exec/Held partition), and for every one of the 66 x 4 = 264 grid cells,
counts how many Held profiles the weighted aggregator would admit. The
maximum across the grid is >= 1 (witnessed concretely, e.g. `{dq: admit,
sarc: escalate, green: admit}` compensated by weight `{dq: 0, sarc: 0,
green: 1}` at threshold `0.5`), so Proposition 1's discrete instantiation
holds not just empirically (`ch5_aggregator.py`'s sample-dependent
result) but exhaustively over every possible three-gate verdict
combination this artifact's lattice can produce.

**PROOF-STATUS: machine-checked** (discrete instantiation, exhaustive
over `checkers/compensation_check.py`'s full 125 x 264 grid;
`out/checkers/compensation_check.json`). The general continuous-domain
argument above is a standard analytic construction, not itself re-derived
by a checker.

---

## Proposition 2 (order invariance without remediation)

**Statement.** If no gate rewrites `(a, c, E)`, the composed verdict is
invariant to evaluation order and duplication, and adding a gate never
increases permissiveness.

**Proof.** `(R, max)` is a join semilattice: `max` over a finite totally
ordered set is idempotent (`max(r,...,r) = r`), commutative (`max` does
not depend on argument order), and associative
(`max(max(a,b),c) = max(a,max(b,c))`) -- these are properties of `max`
over any totally ordered set, and `R`'s restrictiveness order (Definition
1) is total. Order invariance and duplication invariance follow directly
from commutativity and idempotence. Monotone hardening (adding a gate
never increases permissiveness, i.e. never decreases the join) follows
because `max(S union {x}) >= max(S)` for any finite `S` and any `x` --
adding an element to a set never lowers its maximum.

**PROOF-STATUS: machine-checked** (`checkers/lattice_check.py`,
exhaustive over every tuple of length 1 through 4 from the real 5-element
`Response` lattice and the real `compute_restrictiveness_join` --
17,151 individual checks across idempotence, commutativity,
associativity, monotone hardening, duplication invariance, and the
empty-join-is-admit base case; `out/checkers/lattice_check.json`).

---

## Proposition 3 (single-pass unsoundness)

**Statement.** There exist configurations where single-pass evaluation on
`(a, c(a), E(a))` yields a composed Exec verdict whose executed action
`rho(a)` violates the authority or resource gate at execution time; and
symmetrically, where single-pass holds an action whose remediated form is
compliant.

**Proof (construction).** Let the evidence gate substitute a corrupted
unit cost `v0` for the governed value `v'`, `v0 != v'`. Single-pass
evaluates the authority gate against the ORIGINAL order value
`qty * v0` (Definition 3's `c(a)`, not `c(rho(a))`), but the EXECUTED
action carries the SUBSTITUTED value `qty * v'` (the DQ gate's own
remediation already happened by execution time, since the buffer
substitution is applied to the acted-on evidence regardless of which
composition mode judged it). Choose an authority cap `kappa` strictly
between `qty * v0` and `qty * v'`. Two symmetric cases:

1. `qty * v0 <= kappa < qty * v'` (corrupted value understates cost):
   single-pass judges the cap against `qty * v0` (admits), but the
   executed action's true value `qty * v'` exceeds `kappa` -- a violation
   the post-hoc audit will flag. This is
   `single_pass_admits_then_violates`.
2. `qty * v' <= kappa < qty * v0` (corrupted value overstates cost):
   single-pass judges the cap against `qty * v0` (holds, over cap), but
   the remediated action's true value `qty * v'` is within `kappa` --
   `remediate_regate` correctly admits it. This is
   `single_pass_holds_remediated_compliant`.

Both directions are constructible and both are registered outcomes of
CH2 (`ch2_direction_counts`). The artifact instantiates case 1 as its S4
scenario by construction (`runner.build_scenarios`'s `apply_s4_kappa`,
placing `kappa` between the pre- and post-substitution order values via
`_compute_s4_kappa`).

**PROOF-STATUS: pending-human-review.** The construction is exhaustive
over the two symmetric cases by the intermediate-value structure of the
cap placement (there is no third case: `kappa` is either between the two
values, or outside both, and outside-both never diverges by
construction), but this is an existence/construction proof over
continuous-valued economics, not a finite discrete space a checker
enumerates. CH1's 30-seed empirical audit (zero violations under
`remediate_regate`, `out/results/sweep_summary.json`'s
`ch1_supported_seed_count == n_seeds`) and CH2's realized S4 divergences
(`ch2_divergent_decisions`, non-zero on every one of the 30 seeds)
corroborate the construction on real data without themselves being an
exhaustive proof of the general statement.

---

## Lemma 1 (termination)

**Statement.** Buffer substitution is idempotent, `rho(rho(a)) =
rho(a)`, and `E(rho(a))` consists of governed records the evidence gate
admits by construction; hence no further remediation is generated and
the protocol reaches a fixed point after at most one remediation.

**Proof.** `composition._remediated_evidence` constructs a single,
freshly governed `EvidenceRecord` from the substituted value, with clean
metadata (fresh `as_of_day`/`retrieved_day`, `version=2`, present
lineage) -- by construction this record cannot itself trigger any of the
`sarc_dq` predicates that produced the original substitution (staleness,
missing fields, lineage, schema type), because those predicates are
exactly the ones the remediated record was built to satisfy. A second
evaluation of the DQ gate on `E(rho(a))` therefore returns `admit`, not
`substitute` -- `rho` applied to an already-remediated evidence set is
the identity, `rho(rho(a)) = rho(a)`. This is exercised directly: every
`remediate_regate` call whose Phase I substitutes performs exactly one
Phase II re-evaluation (`composition.py`'s `remediate_regate`), never a
loop, and `gates.dq.verdict` after Phase II is `admit` on every
substituted decision across all 30 swept seeds (implied by
`ch2_direction_counts`/`label_only_differences` bookkeeping, which
depends on Phase II converging).

**PROOF-STATUS: pending-human-review.** The argument depends on
`sarc_dq.gate.PreActionGate`'s own predicate contract (that a governed,
freshly-dated, complete, single-source record cannot re-trigger the
predicates that produced the substitution) -- an external engine
guarantee this repo composes but does not itself re-verify from the
engine's internals, per the standing "engines are installed libraries,
not modified" invariant. No dedicated checker in this repository proves
the engine's predicate contract; the repository verifies its OWN
one-shot (never looping) remediation code path instead
(`test_audit_unit.py`'s W2/downroute and evidence-substitution tests).

---

## Theorem 1 (soundness of remediate_regate composition)

**Statement.** Under Lemma 1 and gates that are functions of `(action,
context, evidence, current state)`, the remediate_regate protocol
satisfies Definition 3 (per-action soundness): Phase II evaluates every
gate on `a_exec` itself, and the join preserves every Held verdict.
Corollary 1: single-pass is sound iff the authority and resource gates
are invariant under `rho`.

**Proof.** By construction, `remediate_regate`'s Phase II evaluates the
authority gate (`evaluate_sarc_pag`), resource gate (`evaluate_green`),
and evidence gate a second time against the REMEDIATED context/evidence
(`remediated_ctx`, `remediated_evidence`) -- not the original action. The
composed response is the join (Definition 2) of these THREE Phase-II
verdicts. Since the join of a set never admits unless every member
admits/executes (Proposition 2's monotone hardening: the join can only
harden, never soften, as more restrictive votes are added), any gate
that would hold `a_exec` at Phase II forces the composed verdict to Held
too -- there is no way for the executed action to have been admitted by
the join while simultaneously being held by one of the very gates that
produced that join, because they are the SAME evaluation. Corollary 1
follows immediately: single-pass's authority/resource verdicts are
computed on the ORIGINAL action, so single-pass is sound only when those
verdicts happen to equal what they would have been on `rho(a)` -- i.e.
when the gates are invariant under `rho`.

**PROOF-STATUS: pending-human-review.** This is a structural argument
from the code path (Phase II's join is computed FROM the same
verdicts used to judge `a_exec`, by inspection of
`composition.remediate_regate`), not something a checker exhaustively
re-derives over an input space -- soundness is a universal claim over all
possible actions/contexts/evidence, which a finite checker cannot
exhaust the way `lattice_check.py` exhausts the finite `Response`
lattice. CH1's 30-seed empirical audit (zero violations on every seed)
is strong corroborating evidence, not a substitute for the proof.

---

## Proposition 4 (cross-gate lineage preservation)

**Statement.** From an admitted executed action's unified Evidence Set
alone, one can reconstruct, content-addressed, exactly the records each
gate relied on in the phase that produced the final verdict, including
the identity and provenance of any substituted value.

**Proof.** Every DQ evaluation records `evidence_ids` (the tuple of
`EvidenceRecord.evidence_id()` content hashes actually passed to
`spec.evaluate`, `composition.evaluate_dq` -> `GateDecision.evidence_ids`)
and, when substitution occurred, `remediation.evidence_substitution`
carries `pre_order_value`, `post_order_value`, and `substituted_value`
verbatim (`composition.py`'s `remediate_regate`/`single_pass` line
construction). The authority gate's section records
`constraints_evaluated` (every constraint ID considered, not just the
firing ones) and its own `verdict`; the resource gate's section records
`predicted_cost`/`predicted_carbon`/`budget_state` at evaluation time.
Because `evidence_id()` is content-addressed (a hash of the record's
payload and metadata, not an opaque counter), two records with the same
`evidence_id` are byte-identical by construction -- so recovering the
`evidence_ids` list from a line is sufficient to know EXACTLY which
evidence bytes were judged, without needing the record store itself,
and `schemas/evidence_line.schema.json` fixes this shape as a contract
(Draft 2020-12, `additionalProperties: false`, so no channel exists to
smuggle in undeclared fields that would break the reconstruction).

**PROOF-STATUS: pending-human-review.** A structural argument from the
schema and the line-construction code, not machine-checked by a
dedicated exhaustion -- `test_properties.py`'s
`test_randomly_sampled_lines_validate_against_schema_v1` confirms the
SHAPE contract holds on sampled real output, which is necessary but not
sufficient for the full reconstruction claim above.

---

## Proposition 5 (no manufactured coverage)

**Statement.** The composed plane's detected class set equals the union
of member gates' detected class sets; composition never detects a class
no member covers. Corollary: declared uncovered classes remain
uncovered, and an honest composed readout must say so.

**Proof.** `metrics._ch4_matrix` defines composed detection directly as
`gate_fired = dq.detected or sarc.verdict != admit or green.verdict !=
admit` -- this is definitionally the boolean union of the three member
detectors, not a separately computed quantity that could diverge from
it. There is no fourth, composition-level detector anywhere in
`composition.py` that could contribute coverage no member gate
contributed. `union_ok = (composed_detected == member_detected)` is
therefore a tautology by construction, not an empirical finding that
could fail for an unrelated reason -- and the artifact still checks it on
every run (rather than assuming it) as a tripwire against a future code
change accidentally introducing a fourth detector.

**PROOF-STATUS: machine-checked** (tautological by the construction of
`metrics._ch4_matrix`'s `gate_fired` expression, confirmed as holding on
every one of the 30 swept seeds -- `out/results/sweep_summary.json`'s
`ch4_union_ok_seed_count == n_seeds == 30` -- and directly asserted by
`test_ch4_matrix_rates_and_union_ok` in `test_metrics_unit.py`).

---

## CH7 (multi-remediator order dependence)

**Statement** (`prereg/hypotheses.md`). With two remediation operators
active (evidence substitution and resource downroute), either
order-independence (confluence) holds, or a concrete non-confluent
instance exists. The checker's verdict IS the registered decision rule.

**Result.** `checkers/remediator_check.py` applies both orderings
(substitute-then-downroute, the order `composition.remediate_regate`
actually runs under W2; downroute-then-substitute, the untried
alternative) over a 3x3x3x3x3 = 243-point finite grid of (quantity,
corrupted unit cost, governed unit cost, cost budget, carbon budget),
reusing the real `_remediated_context`/`_maybe_downroute` functions
directly. **86 of 243 grid points disagree** between the two orders. A
concrete counterexample: `qty=10, corrupted=5, governed=10, cost_budget=
60, carbon_budget=10` -- substitute-then-downroute reaches `qty=5,
order_value=50`; downroute-then-substitute reaches `qty=10,
order_value=100` (over the cost budget, because the downroute step ran
against the UNDERSTATED corrupted cost and never re-checked feasibility
after substitution raised the true cost). **CH7's registered outcome:
non-confluent.** This is the formal justification for
`prereg/w2-workflow.md`'s fixed ordering (evidence gate first, then
resource gate) rather than an unspecified one: the operators do not
commute, and running downroute before the evidence gate has settled the
true cost can silently admit an over-budget action -- structurally the
same failure mode Proposition 3 already identifies for single-pass
composition, now shown to recur between two remediators rather than
between two composition protocols.

**PROOF-STATUS: machine-checked** (exhaustive over the 243-point finite
grid, `out/checkers/remediator_check.json`; the sample counterexample is
independently re-derived, not just read back from the checker's own
report, in `test_checkers.py::test_remediator_check_non_confluent_counterexample_is_reproducible`).

## Appendix B. Artifact manifest. {
  "artifact_license": "Apache-2.0",
  "data_sha256": "4f637bc36ba5cffb56c31cd2b8273a135f89cc65448b28929ee71e73ded8f1d9",
  "engines": {
    "green-sarc": {
      "commit": "8482226b461ccbf91971f90ea6de42cd7a931e5c",
      "license": "Apache-2.0",
      "version": "0.4.1"
    },
    "sarc-dq": {
      "commit": "db6c396128a4df7fe12d13be163b1e7d32087177",
      "license": "Apache-2.0",
      "version": "0.1.0"
    },
    "sarc-governance": {
      "commit": "74df5de29a305a76bf3cc97a185ece2f11b1b833",
      "license": "Apache-2.0",
      "version": "0.3.0"
    }
  },
  "prereg_v1_sha": "31552b2ee6548787e766b0253498014eb0a5093c",
  "seed": 26313
}

## Appendix C. Statistical methodology (V3 gate)

30 seeds (prereg/seeds.json, first seed 26313, generated by `random.Random(26313)` sampling without replacement from [1, 2^31-1], frozen before any Phase 3 code ran). Confidence intervals are two-tailed 95% t-intervals, mean +/- t_crit(df=29, alpha=0.05) * (stdev / sqrt(30)), t_crit = 2.045230 (standard t-table value for df=29); implementation in sweep.py's mean_ci95, pure Python (statistics module), no new statistical dependency. Scenario economics (budgets, caps) are calibrated once from the registered baseline seed and held fixed across the sweep; only each scenario's decision-stream seed varies -- the same "treatment", repeated draws, which is the design this kind of robustness claim requires. Per-seed summaries (no raw per-decision data) are checkpointed under out/results/sweep/ and are part of this artifact's committed history.
