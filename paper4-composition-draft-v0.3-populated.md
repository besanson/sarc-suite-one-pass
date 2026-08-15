# One Gate Is Not Enough: Non-Compensatory Composition of Pre-Action Controls for Agentic AI

Gaston Besanson (sole author at draft time; co-author or credited independent reviewer slot open)

Companion artifact: suite-demo (open data, deterministic, Apache 2.0).

Version 0.3: extends v0.1/v0.2 (CH1-CH4, single seed) with a second remediation operator and a weekly-commitment workflow (CH7), a buffer-poisoning study with two mitigations (CH6), an exhaustive discrete-grid check of the compensation claim (CH5), a 30-seed statistical sweep with 95% CIs (CH8), and full machine-checked or human-reviewed proofs for every numbered claim. v0.1/v0.2 remain unmodified historical artifacts; this version does not retract them, it extends them.

## Abstract

Agentic AI systems take consequential actions governed by more than one concern at once: is the agent permitted to act, can the organisation afford the action, and is the evidence behind it valid. Prior work treats these as separate pre-action gates: SARC for obligations and permissions (arXiv 2605.07728), Green SARC for predictive cost and carbon budgets (arXiv 2606.15954), and SARC-DQ for metadata-borne evidence validity (arXiv 2607.26313). This paper studies what none of them answers: the semantics of all three judging the same action at the same instant, when more than one of them can rewrite the action. We show that (i) for positive-weight linear (additive-score) aggregation of gate outcomes, an action a member gate vetoed is admitted exactly when the admission threshold does not exceed the aggregator's largest leave-one-out weight sum -- a precise, provable condition, not the universal claim for any strictly increasing aggregator this paper's v0.1/v0.2/early-v0.3 drafts stated (an independent review refuted that universal form with a threshold-at-the-supremum counterexample; Appendix A) -- verified exhaustively over the full discrete verdict grid plus randomized probes, not just a sample; (ii) naive single-pass composition is unsound under remediation, and a remediate-and-regate protocol restores soundness and terminates after one remediation by idempotence; (iii) a second remediation operator (resource-budget downroute) does not commute with the first (evidence substitution) -- a finite-model checker finds concrete non-confluent instances, which is why a fixed operator order is pre-registered rather than left unspecified; (iv) a governed evidence buffer that trusts its own most recent admitted write is vulnerable to poisoning from declared-uncovered defect classes, and two buffer-side mitigations reduce (not eliminate) that exposure; (v) the composed plane can emit one unified Evidence Set per action preserving full lineage across gates; and (vi) composition adds no coverage: classes no member gate covers remain uncovered, reported as a feature. Empirically, on a deterministic open-data artifact composing the three published engines unmodified, over 30 pre-registered seeds and two workflows: CH1 supported; CH2 supported; CH3 supported; CH4 supported; CH5 supported (exhaustive over the discrete grid); CH6 supported on every seed under W1; NOT supported on every seed under W2 (smaller weekly-commitment population); CH7 non-confluent (two remediators do not commute, 86/243 grid points, plus 150/200 off-grid points per an independent-review-promoted probe); CH8 robustness across 30 seeds x 2 workflows holds for CH1-CH5, not for CH6.

## 1. Introduction

A pre-action gate is a deterministic checkpoint between an agent's decision and its execution. Three families of pre-action concern are separately established: authority, resources, and evidence. Deployed systems need all three simultaneously, yet the composition question is untreated: what verdict should the plane return when gates disagree, in what order should gates run when more than one of them can rewrite the action, and what single audit artifact honestly describes the joint decision.

The question is not academic. The evidence gate's designed remediation, quarantine-and-substitute from a governed buffer, changes the acted-on value. A substituted unit cost changes the order quantity a replenishment agent proposes, which changes the order value the authority cap must judge and the predicted spend the resource gate must budget. A plane that evaluates all gates once, in parallel, on the original action is judging an action that will not be the one executed. Once a second remediator is introduced -- a resource gate that, rather than simply blocking an over-budget action, can scale its quantity down to the largest budget-feasible amount -- the same question recurs one level up: does it matter which remediator runs first.

Contributions. (1) A compensation lemma for positive-weight linear aggregators, stated with the exact threshold condition under which a vetoed action is admitted (corrected, via independent review, from an earlier universal claim a counterexample refuted), verified exhaustively over the full discrete three-gate verdict grid plus randomized probes rather than argued only in the continuous case. (2) A second remediation operator (downroute, a weekly-commitment workflow's resource-budget quantity scaling) and a finite-model checker showing it does not commute with evidence substitution -- the formal justification for a pre-registered fixed remediation order. (3) A buffer-poisoning study: a declared-uncovered defect class can corrupt the evidence gate's own governed buffer, and two buffer-side mitigations (a consistency-based quarantine window, a rolling median) measurably reduce that exposure, reported with the honest limitation that this holds robustly under the higher-volume daily workflow but not, at this sample size, under the lower-volume weekly one. (4) Composition semantics: a restrictiveness lattice over gate responses, a join rule, and order invariance for remediation-free evaluation, machine-checked exhaustively. (5) The remediation interaction: single-pass unsoundness, a remediate-and-regate protocol, and a termination lemma from idempotent substitution. (6) A unified Evidence Set with cross-gate lineage preservation. (7) A no-manufactured-coverage property, verified by injecting two declared-uncovered classes and reporting that both survive all gates. (8) A deterministic open-data artifact composing the three published Apache 2.0 engines unmodified, with hypotheses CH1 to CH8 pre-registered before the corresponding code ran, and a 30-seed statistical sweep reporting means with 95% confidence intervals.

Scope honesty. This paper claims composition semantics and a mechanism demonstration. It does not claim production prevalence, uses no model calls, and its artifact is not a GIGO-Bench release.

## 2. Setting and definitions

An action a is proposed in context c(a) = (agent, role, parameters, value, predicted resource use). An evidence set E(a) is the finite sequence of records a relies on; each record is a payload plus metadata (source, as-of, retrieval time, version, lineage) with a content-addressed identifier eid(r). A gate G_i maps (a, c, E, s_i) to a response in R = {admit, substitute, degrade, escalate, block}, where s_i is gate-local state (for the resource gate, remaining budgets; for the evidence gate, the governed buffer). Partition R into Exec = {admit, substitute, degrade} and Held = {escalate, block}.

Definition 1 (restrictiveness order). Order R by permissiveness: admit < substitute < degrade < escalate < block; (R, max) is a join semilattice.

Definition 2 (composed verdict). For responses r_1..r_n on the same (a, c, E), the composed response is the join r* = max_i r_i, the composed admitted bit is [r* in Exec], and the winner gate is any argmax (ties recorded).

Definition 3 (per-action soundness). A plane is sound for a if the executed action a_exec satisfies every gate at execution time, on the state in force when a_exec runs.

Remark (sequential coupling). Resource-gate state decrements as actions execute; soundness here is per action given current state; stream-level ordering across actions is out of scope and flagged in Section 12.

## 3. Compensation admits vetoed actions

Represent each gate's outcome as a score s_i in [0,1] with s_i = 0 iff the gate holds the action, and let an aggregator f admit a iff f(s) >= tau with tau > 0. An earlier draft of this paper claimed that any strictly increasing f with some admissible profile violates veto -- an independent review refuted this: for f(s) = s1+s2+s3 and tau = 2.5, f(1,1,1) = 3 is admissible, yet no profile with a coordinate at 0 can reach 2.5 (its maximum there is 2), so veto is fully preserved despite f being strictly increasing and having an admissible profile. The universal form was wrong to treat those two hypotheses as sufficient; whether compensation is possible depends on the relationship between tau and f's own weight structure.

Lemma (linear family; general arbitrary-n statement retagged pending-human-review, finite n=3 encoding split into Corollary 2, per independent review round two finding R2-N2). Let f(s) = sum_i w_i s_i with w_i >= 0, not all zero, and let L_j = sum_{i != j} w_i (the largest score achievable with s_j = 0), L* = max_j L_j. A vetoed profile (s_j = 0 for some j) is admitted by f if and only if tau <= L*. Min never admits a vetoed profile, for any tau > 0, regardless of weights. Full proof, the reviewer's counterexample worked through against this exact condition, and the discrete instantiation's exhaustive machine check (including 200 HEAD-derived random weight-vector probes), in Appendix A.

Consequence: the composed verdict of Definition 2 is the ordinal form of min on admissibility, the cross-gate generalisation of "any failed predicate blocks".

CH5 (compensation is empirically unsafe, discrete grid). Over the pre-registered weight/threshold grid (66 weight vectors x 4 thresholds, 264 cells), does any cell's weighted-score aggregator admit at least one of the 98 min-join-Held profiles out of the full 125-point three-gate verdict space, while the min join admits zero of them by construction. Result: proposition_1_holds_exhaustively = True, with the maximum violation count 48 profiles at a single grid cell.

## 4. Order invariance without remediation

Proposition 2. If no gate rewrites (a, c, E), the composed verdict is invariant to evaluation order and duplication, and adding a gate never increases permissiveness. Proof, and exhaustive machine check over the finite response lattice (17151 individual checks, all_hold = True), in Appendix A.

## 5. The remediation interaction: two operators, one order

The evidence gate is not read-only: on a substitutable violation it returns substitute with a governed value v', defining rho_sub(a) = a[v -> v'], and c(rho_sub(a)) may differ from c(a): order quantity, order value, and predicted spend can all move. A second workflow (W2, weekly commitment) introduces a second remediation operator: rho_route(a), which scales the committed quantity down to the largest quantity whose predicted cost and carbon both fit the remaining weekly budget, then recomputes context from the scaled quantity -- the same remediate-and-regate pattern Theorem 1 establishes for evidence substitution, applied to a different field of the action.

Proposition 3 (single-pass unsoundness, scoped to the implemented construction). For the substituting-DQ-decision construction below, single-pass evaluation on (a, c(a), E(a)) yields a composed Exec verdict whose executed action rho_sub(a) violates the authority or resource gate at execution time; and symmetrically, single-pass holds an action whose remediated form is compliant. Construction: place an authority cap kappa strictly between the order values induced by the corrupted read and by the governed substitute. The artifact instantiates this as scenario S4 across all 30 registered seeds; the claim is not made for arbitrary continuous economics or arbitrary gate implementations beyond this construction (independent review classification: checked-scope-only). Full proof in Appendix A.

Protocol (remediate-regate composition, "rtr" in artifact output). Phase I: evaluate the evidence gate; on substitution form a' = rho_sub(a) and recompute c(a'). Under W2, if the resource gate would otherwise reject a' outright as over budget, apply rho_route(a') and recompute c(a') again. Phase II: evaluate every gate, including the evidence gate, on (a', c(a'), E(a')); return the join of Phase II responses, recording Phase I in the Evidence Set.

Lemma 1 (termination, scoped to the current one-shot composition branch). For the current one-shot composition branch and the DQ-library behavior exercised in this artifact's scenarios/tests, buffer substitution is idempotent, rho_sub(rho_sub(a)) = rho_sub(a), and E(rho_sub(a)) consists of governed records the evidence gate admits by construction; hence no further remediation is generated and the protocol reaches a fixed point after at most one remediation of each operator. The argument depends on an external DQ predicate contract this artifact composes but does not itself prove for every possible governed record (independent review classification: checked-scope-only). Full proof in Appendix A.

Theorem 1 (soundness of remediate-regate composition; general statement retagged checked-scope-only per independent review round two, finite response-lattice encoding split into Corollary 3). Under Lemma 1 and gates that are functions of (action, context, evidence, current state), the remediate-regate protocol satisfies Definition 3: Phase II evaluates every gate on a_exec itself, and the join preserves every Held verdict. Corollary 1 (sufficiency only; retagged checked-scope-only per independent review round two): if the authority and resource gates are invariant under the operators applied on the executed-reachable action set, single-pass is sound. The converse does not hold in general -- an independent review gave a counterexample (a gate that varies only on actions independently held, and so never executed) -- and this paper no longer claims it; an earlier draft's iff overstated what was proved. Full proof, and the counterexample worked through, in Appendix A.

CH7 (multi-remediator order dependence). With both operators active, does a fixed order matter -- is rho_route(rho_sub(a)) always equal to rho_sub(rho_route(a))? A finite-model checker (checkers/remediator_check.py) applies both orders over a grid of (243 points): quantity, corrupted unit cost, governed unit cost, cost budget, carbon budget, reusing the real remediation functions directly. Registered outcome: non_confluent, with 86 disagreeing grid points out of 243. The independent review additionally probed continuous-valued points off this pre-registered grid and found non-confluence there too (review/REVIEW.md Section 5: 144/200 HEAD-derived off-grid points non-confluent); this artifact promotes that probe into the checker itself and reruns it on every checker run, seeded from a fixed declared constant in prereg/probe-seeds.json rather than the current git HEAD, so the published count is commit-stable rather than drifting with every commit (round-two independent review finding R2-N1): 150/200 off-grid points disagree, strengthening CH7 beyond the declared grid. Where the two orders disagree, the mechanism is structurally the same failure Proposition 3 identifies between composition protocols: a budget check run against a not-yet-corrected value never gets re-checked once the value is corrected. This is the formal justification for prereg/w2-workflow.md's fixed ordering (evidence gate first, then resource gate) -- not an arbitrary implementation choice but a consequence of the operators' non-commutativity. Full result in Appendix A.

## 6. Buffer poisoning: a governed value is only as good as its last admit

The evidence gate's governed buffer (Section 5) trusts its own most recent admitted write when substituting for a later violation. This is sound against the covered defect classes (stale, superseded, contradictory, malformed evidence) because the gate's own predicates catch them before they can corrupt the buffer. It is not sound against a declared-uncovered class: a corrupted value that the gate's predicates never flag is admitted, and admitted values are exactly what the buffer trusts.

CH6 (buffer contamination is real and mitigable). A second uncovered defect class, plausible_outlier_high, is added at the same declared rate as plausible_outlier (Appendix B's defect table), specifically to exercise this mechanism. A poisoned-substitution metric (contamination.py) determines, purely from ground-truth labels never consulted by the gate itself, whether the value a substitution actually used traces back to a prior admit from an uncovered class. Two buffer-side mitigations are implemented entirely outside the sarc_dq.gate package, as this repo's own buffer-wrapping adapters: a quarantine window (a write becomes trusted only after three consecutive consistent admits) and a rolling median-of-3.

Results, 30 seeds, both workflows: under W1 (daily), plain produces at least one poisoned substitution on every seed (14.70 (95% CI [13.21, 16.19], n=30)), and both mitigations produce a strictly lower count than plain on every seed (mitigations hold: True). Under W2 (weekly commitment), the population of substitutions per seed is roughly an order of magnitude smaller (commitments happen every 7 days, not daily), and plain does not produce poisoning on every seed (False; mean 1.83 (95% CI [1.34, 2.32], n=30)): on some seeds, by chance, zero poisoning events occur, which makes "strictly lower than plain" vacuously unsatisfiable on those seeds (mitigations hold on every seed: False). This is reported as a genuine small-sample limitation of the weekly workflow's lower event rate, not smoothed into a single across-workflow number -- see Table 6 and Section 12.

## 7. The unified Evidence Set

Each decision emits one record: action context; per-gate sections (authority constraints and verdicts; resource predicted cost, carbon, budget state, verdict; evidence predicate results, verdict, substitution with pre and post values and buffer key, record eids); the final join, winner gate, and the remediation record (which operators fired, in which order, for this decision). Ground-truth labels are never present; they live in a separate run log. The line's JSON shape is fixed by schemas/evidence_line.schema.json (Draft 2020-12), pre-registered before any Phase 3 result existed.

Proposition 4 (identity commitment and integrity, relative to a content-addressed store; retagged checked-scope-only per independent review round two). From an executed action's unified Evidence Set line alone, one can identify -- by content-addressed id -- every record each phase relied on, including the Phase I evidence before substitution and the specific governed-buffer write a substitution drew from, and verify those identities given access to the record store and buffer write history; the line does not, by itself, reconstruct the original bytes, and this paper no longer claims that it does (an earlier draft did; an independent review correctly refuted the byte-reconstruction reading -- Appendix A). A durable, run-scoped buffer write-history log (composition.py's write_log, persisted as buffer-writes.jsonl next to the evidence lines) now backs "the specific governed-buffer write a substitution drew from": each substitution resolves to exactly one write event, closing the round-two independent review's provenance finding that 3,478 real substitution occurrences resolved to only 62 unique ids under the prior key+value-only hash. Extends the single-gate lineage result of arXiv 2607.26313. Full proof in Appendix A.

Proposition 5 (no manufactured coverage). The composed plane's detected class set equals the union of member gates' detected class sets; composition never detects a class no member covers. Corollary: declared uncovered classes remain uncovered, and an honest composed readout must say so. Full proof (a structural tautology, machine-verified across every swept seed) in Appendix A.

## 8. Pre-registered empirical protocol

Artifact: suite-demo composes the three published engines, installed unmodified (repositories verifiably untouched), over open payload data (UCI Online Retail, CC BY 4.0) with a declared synthetic metadata layer and a declared eight-class injector at declared rates; 30 pre-registered seeds (prereg/seeds.json, first seed 26313); zero model calls; zero source writes, hash-proven. Scenarios: S1 baseline, S2 tight budgets, S3 unauthorised burst with a low authority cap, S4 the Proposition 3 construction with the cap between pre- and post-substitution order values (all W1); W2-S1 baseline and W2-S2 tight weekly budgets (both W2); CONTAM-W1 and CONTAM-W2, one per buffer strategy (plain, quarantine, median_of_3), for the CH6 study.

Every definition used below (hypotheses, seeds, weights, the W2 workflow, the contamination metric and mitigations, the CH2 semantics redefinition) was committed and tagged prereg-v1 before any corresponding result entered this repository's history -- the gated-generation discipline this artifact follows throughout.

Hypotheses, stated before the corresponding code ran:

- CH1 (veto soundness). Post-hoc audit finds zero executed actions violating any gate at execution time under remediate-regate, re-evaluated against the exact Phase II evidence records the decision executed on (independent review finding F4 -- an earlier draft's audit re-derived a synthetic clean record from the executed action's own numbers instead; the audit now persists and loads the real records). Single-seed result: 0. 30-seed result: 30/30 seeds with zero violations.
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
| C1 | Linear-family compensation lemma (tau <= L*) for arbitrary n; universal claim retracted per independent review F1; general lemma retagged pending-human-review, finite n=3 encoding split into Corollary 2 per independent review R2-N2 | Lemma (linear family) + Corollary 2, Appendix A | Lemma pending-human-review; Corollary 2 machine-checked, 1,064 cases (n=3 declared grid + 200 HEAD-derived probes) |
| C2 | Join composition order-invariant absent remediation | Proposition 2, Appendix A | machine-checked |
| C3 | Single-pass unsound under substitution, scoped to the implemented construction (independent review classification: checked-scope-only) | Proposition 3 + Table 3 | checked-scope-only (REVIEW.md); generated |
| C4 | Remediate-regate sound (Theorem 1, general statement retagged checked-scope-only, finite response-lattice encoding split into Corollary 3, per independent review R2-N2); single-pass sound under gate invariance, sufficiency only, necessity retracted per independent review F3 (Corollary 1, retagged checked-scope-only per independent review round two); Lemma 1 scoped to the current one-shot composition branch (checked-scope-only) | Lemma 1, Theorem 1, Corollary 1, Corollary 3, Appendix A | Theorem 1 checked-scope-only (REVIEW.md); Corollary 3 machine-checked, 17,151 cases; Lemma 1 checked-scope-only (REVIEW.md); Corollary 1 checked-scope-only (REVIEW.md) |
| C5 | Evidence Set gives identity commitment + integrity relative to a content-addressed store (not byte reconstruction; retracted per independent review F2); retagged checked-scope-only per independent review round two (R2-N2: schema field presence and hash commitments are checker-adjacent unit tests, not an exhaustive finite-model checker) | Proposition 4, schema v2, Appendix A | checked-scope-only (REVIEW.md) |
| C6 | No manufactured coverage | Proposition 5 + CH4, Appendix A | machine-checked (tautology) + generated |
| C7 | Zero false holds on clean, authorised, in-budget | CH3 | generated; 30-seed CI |
| C8 | Engines compose unmodified | editable installs; git-clean test | artifact test |
| C9 | Full reproducibility | seed list, hashes, provenance; DOI on release | artifact; DOI TODO (human-only) |
| C10 | Compensation admits vetoed actions over the full discrete grid | CH5, checkers/compensation_check.py | machine-checked, exhaustive |
| C11 | Buffer contamination exists and both mitigations reduce it | CH6, contamination.py | generated; 30-seed CI; W2 exception reported honestly |
| C12 | The two remediators do not commute; fixed order is justified | CH7, checkers/remediator_check.py | machine-checked, exhaustive |
| C13 | CH1-CH5 robust across all seeds/workflows; CH6 robust under W1 only | CH8, Table 7 | generated; 30-seed sweep |

## 10. Related work

Six citation gaps were resolved via the V4 pipeline (fetch, verify, record in verified-citations.json) for this response to the independent review's finding F5; none were invented, and any that could not have been verified would have stayed an honestly unresolved placeholder, counted rather than guessed.

Non-compensatory and veto rules in multi-criteria decision analysis: veto thresholds, where one criterion can block an otherwise-acceptable alternative regardless of the others' scores, are an established mechanism in outranking-based MCDA (Nowak, doi 10.1016/j.ejor.2003.06.008); the linear-family lemma in Section 3 gives an exact threshold condition for when a weighted-sum aggregator does or does not have this property, rather than assuming it.

Runtime verification and enforcement monitors: the composed plane's gates are exactly the "monitor that examines a sequence of actions and can transform or block them" mechanism Schneider's security automata formalize (doi 10.1145/353323.353382); this paper's contribution is the composition semantics across several such monitors judging the same action, not the single-monitor enforcement question itself.

Guardrail and policy-engine frameworks for LLM agents: LlamaFirewall (arXiv 2505.03574) is a recent example of a unified guardrail/policy-engine system for LLM agents; it composes detectors into pipelines but does not treat the non-compensatory-join and remediation-reordering questions Sections 3 and 5 study, and (like most guardrail systems) is positioned as monitoring rather than pre-action placement specifically.

Separation of duties and multi-party authorisation: the authority gate's role-allowlist mechanism is a narrow instance of the separation-of-duty concept Clark and Wilson introduced for commercial integrity policies (doi 10.1109/SP.1987.10001); this paper does not implement multi-party (dual-control) authorisation, only single-role admission checks.

Budget governors for autonomous systems: the resource gate's predictive cost/carbon budgeting is one instance of the broader resource-bounded-agent governance problem Agent Contracts formalizes with conservation laws across delegation hierarchies (arXiv 2601.08815); this paper's downroute operator is a single-agent, single-budget-window mechanism, not a multi-agent conservation guarantee.

Cache/buffer poisoning and trust-on-first-use vulnerabilities in adjacent systems: the governed buffer's vulnerability (Section 6, CH6) is structurally the same trust-on-first-use problem Wendlandt, Andersen, and Perrig named for SSH host-key caching (https://www.usenix.org/legacy/event/usenix08/tech/full_papers/wendlandt/wendlandt.pdf) -- a value admitted without independent corroboration is trusted for all future reads until it is overwritten; the quarantine-window mitigation (Section 6) is a direct application of their multi-observation-before-trust idea to a numeric buffer rather than a host key.

Nothing above is load-bearing for the propositions. Every citation this draft relies on is checked against a verified whitelist (verified-citations.json) by citation_check.py (V4 gate) on every population run.

## 11. Limitations

Synthetic metadata layer over open payloads; declared injection rates; no prevalence claims. Resource-gate estimates are cold-start. Stream-level budget ordering effects are defined away per action. Single author at draft time; see the validation note. S4 is a constructed scenario, declared as such. CH6's mitigation-holds-on-every-seed claim is supported under W1 but not under W2, where the weekly-commitment workflow's much smaller per-seed substitution population sometimes produces zero poisoning events by chance, making "strictly lower than plain" impossible to satisfy on those seeds -- this is a sample-size limitation of the weekly workflow, not evidence against the mitigations' mechanism, and it is reported rather than resolved by re-weighting or dropping seeds. CH7's non-confluence result is a property of this artifact's two specific remediation operators (evidence substitution, resource downroute); it does not generalise to remediators with different structure without re-deriving the checker. The artifact is a mechanism demonstration, not a benchmark release.

## 12. Validation note

This artifact was independently replicated and adversarially reviewed in two rounds by automated agents following the published protocols in sarc-suite-agent-review.md and sarc-suite-agent-review-r2.md; the round-one report and evidence are at review/REVIEW.md and review/review.json, and the round-two report and evidence are at review-out-r2/REVIEW-R2.md, review-out-r2/review.json, and review-out-r2/evidence/. Automated review complements and does not replace human peer review.

This draft is the artifact's response to that review: findings F1-F6 (review/REVIEW.md Section 4) are fixed or weakened per the review's own binding-unless-fixed policy, never argued with in this text; the proof-tag reclassifications in Appendix A (checked-scope-only for Proposition 3 and Lemma 1, sufficiency-only for Corollary 1) follow the review's Section 3 proof-tag policy exactly, and no tag here claims more than that review certified.

## Appendix A. Proofs

Every proposition below carries a `PROOF-STATUS` tag. Three values are
available to this artifact's automated pipeline:

- **machine-checked**: an exhaustive finite-model checker under
  `checkers/` (or a structural tautology argued directly from the code
  that produces the number) verifies the claim over its entire relevant
  discrete state space -- not a sample, the whole space. Per round-two
  independent review finding R2-N2 (general Proposition/Theorem
  statements were tagged `machine-checked` when only a narrower finite
  instantiation was actually executable-verified): a statement's own
  `PROOF-STATUS` line must name the specific checker module and the
  enumerated domain it covers (a concrete count, grid, or state-space
  size), not just assert the claim is machine-checked in general.
  `checkers/proof_status_lint.py` enforces this mechanically. A
  statement whose true generality (arbitrary `n`, arbitrary gates,
  arbitrary action spaces) exceeds what any checker enumerates gets
  `pending-human-review` or `checked-scope-only` instead, plus a
  sibling finite-encoding Corollary stated at exactly the checker's
  scope and tagged `machine-checked` there (Corollary 2 and Corollary 3
  below are the two introduced for this reason).
- **pending-human-review**: the claim is proved here in prose (a
  standard mathematical argument) and, where applicable, instantiated
  empirically by the artifact, but has not been exhaustively verified by
  a dedicated checker and is not claimed to be.
- **checked-scope-only (REVIEW.md)**: the independent review
  (`review/REVIEW.md`, Section 3) found the statement's general prose
  claim broader than what this artifact actually certifies; the tag and
  the statement's wording are narrowed to exactly the scope the review
  lists as "largest scope certified" for that statement -- no broader.

A fourth status, **proven**, exists in the release process but is
human-only to apply (see the standing task rule: "clearing any
PROOF-STATUS tag to proven" is not an action this pipeline takes). No
tag in this file is ever written as `proven` by any script in this
repository; `checkers/proof_status_lint.py` and `test_checkers.py`
enforce that as a standing invariant, not a one-time check.

---

## Proposition 1 (linear-family compensation lemma) -- restated per independent review finding F1

**Why this changed.** The original statement here claimed that *any*
strictly increasing aggregator `f` with `tau > 0` and some admissible
profile violates veto. The independent review (`review/REVIEW.md`,
finding F1) refuted this with a concrete counterexample: for
`f(s) = s1 + s2 + s3` on `[0,1]^3` and `tau = 2.5`, `f(1,1,1) = 3` is
admissible, yet every profile with a zero coordinate scores at most `2`,
so **no vetoed profile is ever admitted** -- veto is fully preserved even
though `f` is strictly increasing and has an admissible profile. The
universal claim was false as written; the error was treating "strictly
increasing plus some admissible profile" as sufficient, when whether
compensation can occur actually depends on the relationship between
`tau` and the aggregator's own weight structure. This section replaces
it with two claims that are both true: a precise lemma covering the
linear (additive-score) family the artifact actually measures, stated
with the exact threshold condition that determines when compensation is
and is not possible; and the exhaustive discrete-grid result exactly as
CH5 measured it.

**Lemma (linear family).** Let `f(s) = sum_i w_i s_i` on `[0,1]^n` with
weights `w_i >= 0`, not all zero, and let `f` admit `s` iff `f(s) >=
tau` for `tau > 0`. A profile `s` is *vetoed* iff `s_j = 0` for some
`j`. For each `j`, define the leave-one-out sum `L_j = sum_{i != j}
w_i` -- the largest score `f` can assign to any profile with `s_j = 0`
(achieved by setting every other coordinate to its ceiling `1`). Let
`L* = max_j L_j = W - min_i w_i`, where `W = sum_i w_i`. **Then: there
exists a vetoed profile that `f` admits if and only if `tau <= L*`.**
Min never admits a vetoed profile, for any `tau > 0` and any weights --
`min(s) = 0` whenever any coordinate is `0`, unconditionally.

**Proof.**
*Sufficiency (`tau <= L*` implies a vetoed profile is admitted).* Let
`j* = argmin_i w_i`, so `L_{j*} = L*`. Define `s*` by `s*_{j*} = 0` and
`s*_i = 1` for every `i != j*`. Then `f(s*) = sum_{i != j*} w_i =
L_{j*} = L* >= tau`, and `s*` is vetoed (`s*_{j*} = 0`). So `f` admits a
vetoed profile.
*Necessity (`tau > L*` implies no vetoed profile is admitted).* Let `s`
be any vetoed profile, `s_j = 0` for some `j`. Since every `w_i >= 0`
and every `s_i <= 1`: `f(s) = sum_{i != j} w_i s_i <= sum_{i != j} w_i =
L_j <= L* < tau`. So `f(s) < tau`: `s` is not admitted. Since `s` was an
arbitrary vetoed profile, no vetoed profile is admitted.
*Min.* `min(s) = 0` whenever any `s_j = 0`, and `tau > 0`, so
`min(s) < tau` unconditionally -- min preserves veto regardless of `tau`
or any weight structure, in sharp contrast to the linear family above,
where veto preservation is conditional on `tau > L*` and can fail.

**Applying this to the reviewer's counterexample.** `w = (1,1,1)`,
`W = 3`, `min_i w_i = 1`, so `L* = 2`. Their `tau = 2.5 > L* = 2`: by
the necessity direction, no vetoed profile is admitted -- exactly what
they demonstrated by direct computation. The lemma's threshold condition
correctly classifies this instance as a *non*-compensable regime; the
old universal statement had no such condition and was wrong to treat it
as compensable-by-hypothesis.

**"Vetoed" is `s_j = 0` exactly -- not the artifact's broader Held
class.** The Lemma's hypothesis, following Proposition 1's own original
setup, defines vetoed as `s_j = 0`. Under this artifact's five-level
`score_encoding` (`admit=1.0, substitute=0.75, degrade=0.5,
escalate=0.25, block=0.0`), only `block` scores exactly `0`; `escalate`
is Held under Definition 3's Exec/Held partition (`{escalate, block}`)
but scores `0.25`, not `0`. The Lemma is therefore verified below
against the "at least one `block`" population (61 of 125 profiles) --
a strict subset of the 98 Held profiles CH5's own exhaustive check
already covers. This distinction was not academic: an earlier draft of
this section verified the Lemma against the full Held population and
found 25 of 800 random-probe cells disagreeing with the Lemma's
prediction, all traced to escalate-only-held profiles whose nonzero
`0.25 * w_j` contribution let them clear a threshold `L*` alone would
have predicted they couldn't. Restricting the Lemma's own verification
to the `s_j = 0` population it actually characterizes resolved every
disagreement (`checkers/compensation_check.py`'s `all_vetoed_profiles`
vs `all_held_profiles`). CH5's own existing result -- compensation over
the full Held set, not just the block-only subset -- is unaffected by
this correction and continues to hold via the unchanged exhaustive
enumeration below; if anything, escalate's nonzero score only makes
compensation *easier* to achieve on the broader Held set than the
Lemma's `L*` threshold alone would suggest.

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
green: 1}` at threshold `0.5`), so the discrete instantiation holds not
just empirically (`ch5_aggregator.py`'s sample-dependent result) but
exhaustively over every possible three-gate verdict combination this
artifact's lattice can produce. `compensation_check.py` additionally
verifies the Lemma's `tau <= L*` characterization against brute-force
ground truth over its own `s_j = 0` ("vetoed", i.e. at-least-one-block,
61 of 125 profiles) population -- see the note above on why this differs
from the 98-profile Held population CH5 itself measures -- on the same
264 declared grid cells, plus 200 HEAD-derived random positive-weight
vectors (deterministically seeded from the current commit, per the
independent review's own probe methodology) at the same four thresholds
-- 1,064 consistency checks in total, all agreeing with the Lemma's
prediction (`out/checkers/compensation_check.json`).

**PROOF-STATUS: pending-human-review.** Retagged per round-two
independent review finding R2-N2 (`review-r2/REVIEW-R2.md`): the Lemma
above (Sufficiency/Necessity/Min) is a general algebraic argument, true
for arbitrary `n` and arbitrary nonnegative weights on the continuous
cube `[0,1]^n`, but that generality is exactly what no executable
checker in this repository verifies. `checkers/compensation_check.py`
enumerates only this artifact's own finite `n = 3` instantiation
(Corollary 2 immediately below) -- correct and machine-checked at that
scope, but not a machine check of the continuous arbitrary-`n`
statement itself. Largest certified scope per the review: "analytic
arbitrary-n proof plus finite executable checks at n=3."

---

## Corollary 2 (finite three-gate encoding of the linear-family lemma)

**Statement.** For this artifact's own finite encoding of the Lemma
above -- `n = 3` gates (`dq`, `sarc`, `green`), profiles drawn from
`composition.Response^3` (125 points, `|Response| = 5`), scored via
`prereg/weights.json`'s `score_encoding`, `tau` ranging over the four
registered thresholds -- the `tau <= L*` characterization holds exactly
on every one of 1,064 checked cases: the 264 declared grid cells (every
combination of the artifact's registered weight vectors and thresholds)
plus 200 HEAD-derived random positive-weight vectors at those same four
thresholds, each verified against brute-force ground truth over the
`s_j = 0` ("vetoed") population. The algebraic proof above is elementary
(linearity plus the `[0,1]` bound), and the checker confirms it holds on
every case actually computed, not just the ones the hand proof covers
analytically.

**PROOF-STATUS: machine-checked** (`checkers/compensation_check.py`;
enumerated domain: `n = 3` gates, the 125-point `composition.Response^3`
profile space, 264 declared grid cells plus 200 HEAD-derived random
probe vectors x 4 thresholds = 1,064 cases, all agreeing with the
Lemma's prediction; `out/checkers/compensation_check.json`).

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

## Proposition 3 (single-pass unsoundness, scoped to the implemented construction) -- retagged per independent review finding (Section 3)

**Why this changed.** The independent review (`review/REVIEW.md`,
Section 3) classified this proposition `checked-scope-only`: the
argument below is a valid existential construction, but no executable
checker in this repository covers arbitrary continuous economics or
arbitrary gate implementations, so the claim is restated to name exactly
what is certified -- "conditional algebraic construction with a
substituting DQ decision and cap strictly between pre/post values;
implemented S4 across 30 registered seeds" -- rather than an unscoped
"there exist configurations" claim.

**Statement (scoped).** For the substituting-DQ-decision construction
below -- a corrupted unit cost `v0` substituted for a governed value
`v'`, with an authority cap `kappa` placed strictly between `qty * v0`
and `qty * v'` -- single-pass evaluation on `(a, c(a), E(a))` yields a
composed Exec verdict whose executed action `rho(a)` violates the
authority or resource gate at execution time; and symmetrically,
single-pass holds an action whose remediated form is compliant. This
construction is implemented as scenario S4 and instantiated across all
30 registered seeds (`prereg/seeds.json`); the statement is not claimed
for arbitrary continuous economics or arbitrary gate implementations
beyond this construction.

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

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Largest scope
certified (`review/REVIEW.md`, Section 3): a conditional algebraic
construction with a substituting DQ decision and cap strictly between
pre/post values; implemented S4 across 30 registered seeds. The
construction is exhaustive over the two symmetric cases by the
intermediate-value structure of the cap placement (there is no third
case: `kappa` is either between the two values, or outside both, and
outside-both never diverges by construction), but this is an
existence/construction proof over continuous-valued economics, not a
finite discrete space a checker enumerates, and it does not cover
arbitrary gate implementations. CH1's 30-seed empirical audit (zero
violations under `remediate_regate`, `out/results/sweep_summary.json`'s
`ch1_supported_seed_count == n_seeds`) and CH2's realized S4 divergences
(`ch2_divergent_decisions`, non-zero on every one of the 30 seeds)
corroborate the construction on real data within this scope, without
extending the claim beyond it.

---

## Lemma 1 (termination, scoped to the current one-shot composition branch) -- retagged per independent review finding (Section 3)

**Why this changed.** The independent review (`review/REVIEW.md`,
Section 3) classified this lemma `checked-scope-only`: the argument
depends on an external DQ predicate contract (`sarc_dq.gate.PreActionGate`'s
own guarantee), which this repository composes but does not itself
prove for every possible governed record. The claim is restated to name
exactly what is certified -- "current one-shot composition branch and
exercised DQ-library behavior in scenarios/tests" -- rather than an
unscoped termination claim over all possible buffer substitutions.

**Statement (scoped).** For the current one-shot composition branch and
the DQ-library behavior exercised in this artifact's scenarios/tests,
buffer substitution is idempotent, `rho(rho(a)) = rho(a)`, and
`E(rho(a))` consists of governed records the evidence gate admits by
construction; hence no further remediation is generated and the
protocol reaches a fixed point after at most one remediation. This is
not claimed to hold for every possible governed record or for any DQ
predicate contract beyond what this artifact exercises.

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

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Largest scope
certified (`review/REVIEW.md`, Section 3): the current one-shot
composition branch and exercised DQ-library behavior in
scenarios/tests. The argument depends on `sarc_dq.gate.PreActionGate`'s
own predicate contract (that a governed, freshly-dated, complete,
single-source record cannot re-trigger the predicates that produced the
substitution) -- an external engine guarantee this repo composes but
does not itself re-verify from the engine's internals, per the standing
"engines are installed libraries, not modified" invariant. No dedicated
checker in this repository proves the engine's predicate contract for
every possible governed record; the repository verifies its OWN
one-shot (never looping) remediation code path and the DQ-library
behavior it actually exercises in scenarios/tests
(`test_audit_unit.py`'s W2/downroute and evidence-substitution tests).

---

## Theorem 1 (soundness of remediate_regate composition)

**Statement.** Under Lemma 1 and gates that are functions of `(action,
context, evidence, current state)`, the remediate_regate protocol
satisfies Definition 3 (per-action soundness): Phase II evaluates every
gate on `a_exec` itself, and the join preserves every Held verdict.

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
produced that join, because they are the SAME evaluation.

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Retagged per
round-two independent review finding R2-N2 (`review-r2/REVIEW-R2.md`).
Largest scope certified: current code path under Lemma 1 and the
five-response join. `checkers/lattice_check.py` exhaustively certifies
Proposition 2's monotone-hardening law -- the join mechanism this proof
leans on -- over the full finite `Response` lattice (17,151 checks), but
that certifies the join mechanism, not Theorem 1's own premises for
arbitrary gates, arbitrary action spaces, or arbitrary current-state
transitions, nor Lemma 1's external DQ predicate contract this theorem
also depends on. Corollary 3 immediately after Corollary 1 below states
precisely what the lattice checker does certify. CH1's 30-seed empirical
audit (zero violations on every seed, `out/results/sweep_summary.json`)
corroborates this on real data without substituting for the proof.

---

## Corollary 1 (single-pass soundness, sufficiency only -- weakened per independent review finding F3)

**Statement.** If the authority and resource gates are invariant under
`rho` (the remediation map) on the executed-reachable action set, then
single-pass is sound. **The converse ("only if") is dropped, not
proved.**

**Why this changed.** The prior draft stated this as an iff. The
independent review (`review/REVIEW.md`, finding F3) gave a concrete
counterexample to the necessity direction: let the authority gate vary
under `rho` only on actions DQ independently holds -- those actions
never execute (Held subsumes them regardless of what the authority gate
would have said), so single-pass can be fully sound in practice while
the gate is, strictly speaking, non-invariant under `rho`. Non-invariance
restricted to never-executed actions costs nothing observable; the
necessity direction implicitly assumed invariance was required
everywhere `rho` is defined, not just on the actions that can actually
reach execution, and that assumption is false. No reachability/
executability condition is added to recover the iff here -- the simpler,
honest fix is to state only what is actually proved.

**Proof (sufficiency).** From Theorem 1's join argument: Phase II
evaluates every gate on `rho(a)`, and the join preserves every Held
verdict there. If the authority/resource gates are invariant under `rho`
on the actions that end up executed, their single-pass verdicts
(computed on the original action `a`) equal their remediate-regate
verdicts (computed on `rho(a)`) for exactly those actions, so
single-pass inherits soundness on them from Theorem 1.

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Retagged per
round-two independent review (`review-r2/REVIEW-R2.md`): largest scope
certified is sufficiency on executed-reachable actions under Lemma 1 and
invariance of downstream gates. The necessity direction is properly
retracted above, not weakly supported under any tag. The sufficiency
proof is a structural argument from the code path via Theorem 1's
join argument -- not itself exhaustively re-derived over an unbounded
arbitrary action space, but resting on the same finite lattice-backed
join mechanism Corollary 3 below certifies, which is why this carries
`checked-scope-only` rather than the more generic `pending-human-review`
it carried before this round's retag.

---

## Corollary 3 (finite response-lattice encoding of remediate_regate soundness)

**Statement.** For this artifact's finite `Response` lattice
(`|Response| = 5`) and the join-hardening property `checkers/
lattice_check.py` exhaustively verifies (17,151 checks over tuples of
length 1 through 4): no combination of Phase-II per-gate responses drawn
from this five-value lattice can have its join equal `ADMIT` while any
individual response in that combination is Held (`escalate` or
`block`). This is the exact finite mechanism Theorem 1's join argument
invokes, verified over its entire domain -- not an instantiation of it,
the full domain the checker enumerates.

**PROOF-STATUS: machine-checked** (`checkers/lattice_check.py`;
enumerated domain: `Response^k` for `k = 1..4`, `|Response| = 5`,
17,151 total law checks across idempotence, commutativity,
associativity, monotone hardening, duplication invariance, and the
empty-join case; `out/checkers/lattice_check.json`).

---

## Proposition 4 (identity commitment and integrity, relative to a content-addressed store) -- restated per independent review finding F2

**Why this changed.** The prior statement here claimed the unified
Evidence Set line lets one "reconstruct, content-addressed, exactly the
records each gate relied on" -- language that reads as byte
reconstruction. The independent review (`review/REVIEW.md`, finding F2)
correctly refuted that: a substituted line carried a post-Phase-II
`evidence_id` and a numeric `substituted_value`, but no original bytes,
no original metadata, and no record of which prior buffer write the
substituted value came from. A content-addressed hash is not invertible
-- it commits to content, it does not carry the content. The claim was
materially stronger than what the emitted evidence actually supported.

**Fix (schema v2, `pre_evidence_ids` / `substitute_source`).** Every
substituted line now additionally records `pre_evidence_ids` (the
Phase I evidence ids the gate actually evaluated before substitution)
and `substitute_source` (`buffer_key`, plus `buffer_write_eid` -- a
content-addressed id for the specific `(key, value)` governed-buffer
write the substituted value came from; `composition._buffer_write_eid`,
`schemas/evidence_line.schema.json` v2). This does not make hashes
reversible. It makes the claim about what they *do* provide precise
instead of overstated.

**Statement.** From an executed action's unified Evidence Set line
alone, one can (a) **identify** -- by content-addressed id, not by
opaque reference -- every record each phase relied on, including the
Phase I evidence the gate evaluated before any substitution
(`pre_evidence_ids`) and the specific governed-buffer write a
substitution drew from (`substitute_source.buffer_write_eid`); (b)
**verify** those ids, given access to the record store and the
governed buffer's write history (not from the line alone): recomputing
`EvidenceRecord.evidence_id()` over a candidate record and comparing it
to the id in the line either confirms or refutes that the candidate is
the exact record relied on, since `evidence_id()` is a deterministic
function of content and two records sharing an id are byte-identical by
construction; and (c) **resolve** the original bytes, given that same
store access -- the line is the pointer and the integrity check, the
store is where the bytes live. The line alone, with no store, gives
identity and an integrity check; it does not give bytes.

**Proof.** `composition.evaluate_dq` -> `GateDecision.evidence_ids`
already recorded the content-addressed ids of every record passed to
`spec.evaluate`, unchanged from v1 -- see `gates.dq.evidence_ids`. Schema
v2 additionally requires `pre_evidence_ids` (Phase I ids, before
substitution) and `substitute_source` inside
`remediation.evidence_substitution` whenever it is non-null
(`schemas/evidence_line.schema.json`, `required` on both fields,
`additionalProperties: false` throughout so no undeclared channel exists
to smuggle in inconsistent data). `_buffer_write_eid(key, value)` is a
pure SHA-256 function of exactly the two values that determine a
governed-buffer write's content, so identical writes always yield
identical ids and distinct writes (by key or value) always yield
distinct ids with overwhelming probability (`test_buffer_write_eid_is_content_addressed`,
`test_audit_unit.py`) -- the same content-addressing property
`EvidenceRecord.evidence_id()` already has. Given a store keyed by these
ids (the record store for `evidence_ids`/`pre_evidence_ids`, the
buffer's own write log for `buffer_write_eid`), a verifier recomputes
each id from a candidate stored object and compares; a match is proof of
identity (collision resistance of SHA-256 makes a false match
computationally infeasible), a mismatch is proof of divergence. Nothing
above claims the id determines the content in the other direction --
hashes are one-way by construction, so bytes are never recoverable from
the id alone. Authority and resource gate sections are unchanged from
v1 (`constraints_evaluated`, `predicted_cost`/`predicted_carbon`/`budget_state`)
and were never part of the refuted claim.

**Update (R2-F6(a), durable buffer write-history log).** Since the
round-two review ran, `substitute_source.buffer_write_eid` no longer
identifies a write by content hash alone. Every `evaluate_dq` admit now
appends an event to a run-scoped, append-only write log
(`composition._record_buffer_write`: `write_seq`, `key`, `value`, `day`,
and an `event_id` hashing all four), seeded with one genesis entry per
SKU from the buffer's pre-run known-good values
(`composition._seed_genesis_writes`) so even a substitution that traces
back to the buffer's initial state -- possible on a SKU's very first
decision -- resolves to a real entry, not nothing. A substitution's
`buffer_write_eid` is resolved against this log
(`composition._resolve_buffer_write_event`: most recent prior write to
the same key with the same value) and persisted alongside the evidence
lines as `<scenario>-<mode>-buffer-writes.jsonl`. This directly answers
the review's own provenance probe (3,478 substitution occurrences
resolving to only 62 unique ids under the old key+value-only hash):
`test_repeated_identical_writes_stay_individually_resolvable`
(`test_audit_unit.py`) reproduces that exact repeated-write pattern and
asserts each substitution still resolves to exactly one write-log entry.

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Retagged per
round-two independent review (`review-r2/REVIEW-R2.md`): largest scope
certified is schema-v2 field presence and deterministic key/value hash
commitments. Schema v2's `required` fields on
`remediation.evidence_substitution` are confirmed present and
well-formed on real substituted lines by
`test_provenance_fields_validate_against_schema_v2` and the fuzzed
`test_randomly_sampled_lines_validate_against_schema_v2`, and the write
log's content-addressing property is directly unit tested -- these are
not exhaustive-finite-model checks under `checkers/`, so this does not
carry `machine-checked` (round-two finding R2-N2's linter rule: that tag
requires a named executable checker module and enumerated domain). The
durable write-history log above resolves the specific-write-event-
identity residual the round-two review flagged, but store-backed
resolution (verifying a candidate record/write against an actual
persistent store, not just this run's own JSONL log) remains outside
what any test here exercises; this tag is not retroactively upgraded to
`machine-checked` on the strength of this repo's own unit tests without
a further review certifying it. This tag covers the identity-commitment
and schema-shape claim specifically -- it does not and cannot cover
"bytes are recoverable from hashes," because that claim is explicitly
disclaimed rather than made.

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

**Off-grid probe (promoted per independent review; seed fixed per
round-two review finding R2-N1/R2-F1).** The 243-point grid above is a
finite lattice of round numbers. The independent review
(`review/REVIEW.md`, Section 5) additionally probed continuous-valued
points off that lattice and found 144/200 non-confluent.
`checkers/remediator_check.py` runs this class of probe itself on every
invocation (`random_off_grid_points`): 200 continuous points strictly
inside the grid's outer bounds, never on a grid coordinate, checked with
the same real remediation functions. This probe's seed was originally
HEAD-derived (`sha256(git HEAD)`), the same technique established for
the F1 lemma verification in `checkers/compensation_check.py` -- but
that made the published non-confluent count drift with every commit,
which the round-two independent review caught (`review-r2/REVIEW-R2.md`,
finding R2-N1: the response commit's paper reported 140/200 while a
`make formal` rerun at the same commit produced 145/200). The seed is
now a fixed constant declared in `prereg/probe-seeds.json` (dated after
`prereg-v1`, since this probe itself postdates `prereg-v1`), so the
published count is commit-stable: `out/checkers/remediator_check.json`'s
`off_grid_probe.non_confluent_count` out of `off_grid_probe.n_probes` =
200. It does not reproduce the reviewer's own exact 144/200 (a
different, independently drawn probe), but confirms the same off-grid
non-confluence beyond the pre-registered grid, and no longer drifts on
rerun at a fixed commit or across commits.

**PROOF-STATUS: machine-checked** (`checkers/remediator_check.py`;
enumerated domain: the 243-point finite grid,
`out/checkers/remediator_check.json`; the sample counterexample is
independently re-derived, not just read back from the checker's own
report, in `test_checkers.py::test_remediator_check_non_confluent_counterexample_is_reproducible`;
the off-grid probe above is a supplementary, non-exhaustive finite
sample and does not itself extend the machine-checked scope beyond the
243-point grid).

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

30 seeds (prereg/seeds.json, first seed 26313, generated by `random.Random(26313)` sampling without replacement from [1, 2^31-1], frozen before any Phase 3 code ran). Confidence intervals are two-tailed 95% t-intervals, mean +/- t_crit(df=29, alpha=0.05) * (stdev / sqrt(30)), t_crit = scipy.stats.t.ppf(0.975, 29), computed exactly at runtime (fixed per independent review finding F6: the prior rounded constant 2.045230 diverged from the exact value by up to 3.77e-6 in some CI endpoints -- see review/REVIEW.md); implementation in sweep.py's mean_ci95, using math.fsum over explicitly sorted inputs for mean and variance (fixed per independent review round-two finding R2-N3: naive sum()/len() is order-dependent at the ULP level, unlike fsum) and scipy (pinned in bootstrap.sh) for the t-critical value. Scenario economics (budgets, caps) are calibrated once from the registered baseline seed and held fixed across the sweep; only each scenario's decision-stream seed varies -- the same "treatment", repeated draws, which is the design this kind of robustness claim requires. Per-seed summaries (no raw per-decision data) are checkpointed under out/results/sweep/ and are part of this artifact's committed history.
