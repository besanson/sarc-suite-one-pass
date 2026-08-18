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
SARC Suite One-Pass Demo: paper v0.5 generation (Phase 5, `make paper-v3`
-- the "v3" in the script/phase name is this generator's own script
generation number, unrelated to the paper document's own v0.1-v0.5
version numbering; kept unchanged to avoid an unrequested tooling
rename).

Writes the v0.5 draft verbatim from the embedded template below (never
touches v0.1/v0.2/v0.3/v0.4 -- those stay frozen, per the standing rule), then
populates it from out/metrics.json, out/results/sweep_summary.json
(V3 gate, 30-seed CIs), out/checkers/*.json (V2 gate, exhaustive), the
generated manifest, and appendix-a-proofs.md -- no independent
re-derivation, no placeholder numbers. Runs the V4 citation check and the
PROOF-STATUS lint against the populated output before declaring success.

SEED = 26313
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from checkers import compensation_check, lattice_check, proof_status_lint, remediator_check
from citation_check import check as check_citations
from citation_check import verify_whitelist_schema
from manifest import build_manifest
from paper_tables_v3 import generate_v3_slots
from populate_draft import populate_draft

HONESTY_BANNER = (
    "Mechanism demonstration on open payload data with a declared synthetic "
    "metadata layer. Not a live GIGO-Bench release; live cells come only from "
    "the official harness. Not the proprietary Suite: no connectors, evidence "
    "vault, identity, or hosting. plausible_outlier and plausible_outlier_high "
    "are injected and not caught, by design: declared uncovered. S4 is a "
    "constructed counterexample scenario, declared as such. CH6 is reported "
    "as robust under W1 and NOT robust under W2 (smaller weekly-commitment "
    "population) -- not smoothed into a single number."
)

PAPER_DRAFT_TEXT = """# One Gate Is Not Enough: Composing Stateful Pre-Action Controls for Agentic AI

Gaston Besanson (Universidad Torcuato Di Tella)

Companion artifact: suite-demo (open data, deterministic, Apache 2.0).

## Abstract

Agentic AI systems take consequential actions governed by more than one concern at once: is the agent permitted to act, can the organisation afford the action, and is the evidence behind it valid. Prior work treats these as separate pre-action gates: SARC for obligations and permissions (arXiv 2605.07728), Green SARC for predictive cost and carbon budgets (arXiv 2606.15954), and SARC-DQ for metadata-borne evidence validity (arXiv 2607.26313). Prior research studies composition of enforcement monitors and policy decisions; this paper studies a narrower problem that arises when one control can remediate the action, evidence, or derived context consumed by another control. We formalize remediation-induced control coupling, in which a control transformation invalidates another control's earlier judgment. We show that naive single-pass composition can consequently be unsound, and give a remediate-and-regate protocol that restores per-action soundness in the current bounded, idempotent setting under its stated assumptions. We further show that the two implemented remediation operators, evidence substitution and resource-budget downroute, do not commute -- a finite-model checker finds concrete counterexample instances -- making remediation order part of the control-plane semantics rather than an implementation detail. At the state level, we demonstrate that currently admissible observations can contaminate future governance state when uncovered defects are promoted into a governed evidence buffer; two mitigations reduce, not eliminate, that exposure. Supporting results establish the exact condition under which positive-weight linear aggregation of gate outcomes can compensate a member veto (a vetoed action is admitted exactly when the admission threshold does not exceed the aggregator's largest leave-one-out weight sum), a unified cross-control Evidence Set preserving full lineage across gates, and the fact that composition manufactures no new detection coverage: classes no member gate covers remain uncovered, reported honestly. A deterministic artifact composing the three published engines unmodified validates the mechanisms over 30 pre-registered seeds and two workflows: [GENERATED: abstract_results_sentence_v3] The artifact is a mechanism demonstration, not a production-prevalence study.

## 1. Introduction

A control that changes the action it governs can invalidate the decisions of controls that evaluated the pre-remediation action. A pre-action gate is a deterministic checkpoint between an agent's decision and its execution. Three families of pre-action concern are separately established: authority, resources, and evidence. Deployed systems need all three simultaneously.

Prior research has studied the composition of enforcement monitors and policy decisions: serial and parallel monitor composition, policy-combining algorithms (deny-overrides and related patterns), non-compensatory veto rules in multi-criteria decision analysis, stateful runtime enforcement, and the confluence and termination theory of rewrite systems are all established literatures. This paper does not claim to invent the composition of pre-action controls, and does not claim that the composition question itself is untreated. What remains underexplored is the composition of heterogeneous, stateful pre-action controls in which one control's remediation mutates the action, evidence, or derived context evaluated by another control, thereby invalidating previously computed judgments and creating order-dependent behavior. That distinction -- heterogeneous control semantics, different control-local state, action mutation, evidence mutation, derived-context recomputation, budget state, governance-buffer state, remediation ordering, cross-control lineage, and execution-time re-evaluation, together -- is this paper's actual subject, narrower than a claim that composition per se is untreated, and more defensible.

The question is not academic. The evidence gate's designed remediation, quarantine-and-substitute from a governed buffer, changes the acted-on value. A substituted unit cost changes the order quantity a replenishment agent proposes, which changes the order value the authority cap must judge and the predicted spend the resource gate must budget. A plane that evaluates all gates once, in parallel, on the original action is judging an action that will not be the one executed. Once a second remediator is introduced -- a resource gate that, rather than simply blocking an over-budget action, can scale its quantity down to the largest budget-feasible amount -- the same question recurs one level up: does it matter which remediator runs first.

Contributions. This paper makes four primary contributions. First, it formalizes remediation-induced control coupling: a pre-action control that transforms an action can invalidate another control's earlier judgment (Section 2, Section 4, scenario S4). Second, it gives and evaluates a remediate-regate composition protocol for the current idempotent setting, under which every executing action is re-evaluated by all member controls after remediation (Section 4, Theorem 1, CH1). Third, it shows that heterogeneous remediation operators need not commute, making remediation order part of the control-plane semantics rather than an implementation detail (Section 5, CH7). Fourth, it demonstrates that governance state itself can become contaminated when admissible but uncovered defects are promoted into future remediation state, motivating explicit trust policies for state updates (Section 6, CH6). Non-compensatory join semantics (Section 3, machine-checked exhaustively over the finite response lattice), a unified Evidence Set with cross-gate lineage preservation (Section 7), and a no-manufactured-coverage property verified by injecting two declared-uncovered classes (Section 8, CH4) support these four primary contributions. The empirical artifact underneath all of them is a deterministic open-data composition of the three published Apache 2.0 engines unmodified, with hypotheses CH1 to CH8 pre-registered before the corresponding code ran, and a 30-seed statistical sweep reporting means with 95% confidence intervals (Section 8).

Scope honesty. This paper claims composition semantics and a mechanism demonstration. It does not claim production prevalence, uses no model calls, and its artifact is not a GIGO-Bench release.

## 2. Model and terminology

An action a is proposed in context c(a) = (agent, role, parameters, value, predicted resource use). An evidence set E(a) is the finite sequence of records a relies on; each record is a payload plus metadata (source, as-of, retrieval time, version, lineage) with a content-addressed identifier eid(r). A gate G_i maps (a, c, E, s_i) to a response in R = {admit, substitute, degrade, escalate, block}, where s_i is gate-local state (for the resource gate, remaining budgets; for the evidence gate, the governed buffer). Partition R into Exec = {admit, substitute, degrade} and Held = {escalate, block}: this Exec/Held partition, not the five-level total order below, is the load-bearing distinction for execution safety, and is what a plane's soundness (Definition 3) is stated in terms of.

Definition 3 (per-action soundness). A plane is sound for a if the executed action a_exec satisfies every gate at execution time, on the state in force when a_exec runs.

Remark (sequential coupling). Resource-gate state decrements as actions execute; soundness here is per action given current state; stream-level ordering across actions is out of scope and flagged in Section 10.

A remediation operator rho is a control's own transformation of an action on a violation it is designed to correct rather than merely block: it maps an action a to a remediated action rho(a), typically also changing c(rho(a)). Section 4 introduces the evidence gate's substitution operator rho_sub; Section 5 introduces the resource gate's downroute operator rho_route.

Definition (remediation-induced control coupling). Two controls G_i and G_j are remediation-coupled under remediation operator rho_i if there exists an executable-reachable action a such that G_j(a) != G_j(rho_i(a)). This concept is reusable independently of SARC, Green SARC, or SARC-DQ: any pre-action control whose remediation changes a value another control reads exhibits it. Scenario S4 (Section 4) is this artifact's concrete witness.

Coupling graph. Define a directed graph C = (G, E_C) where (G_i, G_j) is in E_C iff there exists a reachable action a such that G_j(a) != G_j(rho_i(a)); this is the remediation-induced control coupling graph. For the current example: DQ -> Authority and DQ -> Resource. A resource downroute can similarly affect values consumed by other controls.

Design rule (judgment invalidation). If remediation by control G_i can change any input consumed by control G_j, the earlier judgment of G_j must be treated as stale for the remediated action and recomputed before execution. When the dependency graph is incomplete or dynamic, full regating is the conservative strategy.

This paper distinguishes three progressively harder composition problems, in increasing order of difficulty.

Constraint composition. Multiple controls judge the same action without any of them transforming it. When controls represent hard requirements, they behave as constraints rather than compensable preferences: an action is executable only if it remains inside the intersection of the relevant feasible regions, F = F_authority ∩ F_resource ∩ F_evidence. This is the conceptual interpretation for the non-compensatory join semantics of Section 3.

Remediation-induced control coupling. A remediation applied by one control can change variables another control consumes: the evidence gate substitutes unit cost; unit cost changes order value; order value changes the authority decision; unit cost also changes predicted spend; predicted spend changes the resource decision. Section 4 studies this problem for a single remediation operator.

Remediator interaction. When more than one control can transform the action, remediation operators can interact non-commutatively, making remediation order part of governance semantics rather than an implementation detail. Section 5 studies this problem; it is one of this paper's strongest results.

The dependency this creates is the paper's central intuitive argument: remediation changes inputs consumed by other controls.

```text
Evidence
   |
   v
Evidence Gate
   |
   | substitute unit cost
   v
Remediated Action
   |
   +------> recompute order value ------> Authority Gate
   |
   +------> recompute predicted spend --> Resource Gate
   |
   v
Full Regate
   |
   v
Non-compensatory Join
   |
   v
Execute / Hold
```

## 3. Hard constraints versus compensatory aggregation

Definition 1 (restrictiveness order). Order R by permissiveness: admit < substitute < degrade < escalate < block; (R, max) is a join semilattice.

Definition 2 (composed verdict). For responses r_1..r_n on the same (a, c, E), the composed response is the join r* = max_i r_i, the composed admitted bit is [r* in Exec], and the winner gate is any argmax (ties recorded).

Represent each gate's outcome as a score s_i in [0,1] with s_i = 0 iff the gate holds the action, and let an aggregator f admit a iff f(s) >= tau with tau > 0. An earlier draft of this paper claimed that any strictly increasing f with some admissible profile violates veto -- an independent review refuted this: for f(s) = s1+s2+s3 and tau = 2.5, f(1,1,1) = 3 is admissible, yet no profile with a coordinate at 0 can reach 2.5 (its maximum there is 2), so veto is fully preserved despite f being strictly increasing and having an admissible profile. The universal form was wrong to treat those two hypotheses as sufficient; whether compensation is possible depends on the relationship between tau and f's own weight structure. The deeper distinction this section formalizes is not merely min versus weighted sum: it is constraint satisfaction versus preference aggregation. Weighted, additive aggregation can be useful for selecting among already-feasible alternatives, but for hard governance requirements where member controls are meant to hold veto authority, additive preference aggregation is not a substitute for conjunctive feasibility semantics -- the linear-family lemma below gives the exact threshold condition for when a weighted-sum aggregator does or does not preserve that veto property, rather than assuming it either way. This paper is not arguing against weighted aggregation. It is arguing against using compensatory preference aggregation to implement controls whose semantics require independent veto authority.

Lemma (linear family; general arbitrary-n statement retagged pending-human-review, finite n=3 encoding split into Corollary 2, per independent review round two finding R2-N2). Let f(s) = sum_i w_i s_i with w_i >= 0, not all zero, and let L_j = sum_{i != j} w_i (the largest score achievable with s_j = 0), L* = max_j L_j. A vetoed profile (s_j = 0 for some j) is admitted by f if and only if tau <= L*. Min never admits a vetoed profile, for any tau > 0, regardless of weights. Full proof, the reviewer's counterexample worked through against this exact condition, and the discrete instantiation's exhaustive machine check (including 200 HEAD-derived random weight-vector probes), in Appendix A.

Consequence: the composed verdict of Definition 2 is the ordinal form of min on admissibility, the cross-gate generalisation of "any failed predicate blocks". The linear-family lemma above is therefore best read as an exact characterization of when an additive aggregator does or does not preserve the declared veto semantics, not as a claim that additive scoring is inherently unsafe.

CH5 (compensation is empirically unsafe, discrete grid). Over the pre-registered weight/threshold grid (66 weight vectors x 4 thresholds, [GENERATED: checkers.compensation_grid_cells] cells), does any cell's weighted-score aggregator admit at least one of the [GENERATED: checkers.compensation_held_profiles] min-join-Held profiles out of the full 125-point three-gate verdict space, while the min join admits zero of them by construction. Result: proposition_1_holds_exhaustively = [GENERATED: checkers.compensation_holds]. Two distinct quantities are reported here, with distinct labels and distinct denominators, since they are not the same measurement: the **formal result** is the maximum number of compensated response profiles at a single grid cell, [GENERATED: checkers.compensation_max_violations] out of [GENERATED: checkers.compensation_held_profiles] Held response profiles, from the exhaustive discrete checker (`checkers/compensation_check.py`); the **empirical result** is the mean number of compensated held decision instances pooled across scenarios S1-S4, over the 30-seed sweep: [GENERATED: sweep.ch5_empirical_compensated_ci] (`ch5_aggregator.py`, `out/results/sweep_summary.json`). The two are not comparable by denominator (one counts formal response profiles out of the full discrete grid's Held population; the other counts individual decision instances actually produced across four scenarios' worth of simulated traffic), and this paper does not conflate them under one name.

## 4. Single-remediator composition

Proposition 2. If no gate rewrites (a, c, E), the composed verdict is invariant to evaluation order and duplication, and adding a gate never increases permissiveness. Proof, and exhaustive machine check over the finite response lattice ([GENERATED: checkers.lattice_total_checks] individual checks, all_hold = [GENERATED: checkers.lattice_all_hold]), in Appendix A.

The evidence gate is not read-only: on a substitutable violation it returns substitute with a governed value v', defining rho_sub(a) = a[v -> v'], and c(rho_sub(a)) may differ from c(a): order quantity, order value, and predicted spend can all move. This is remediation-induced control coupling (Section 2) in its simplest form: one remediation operator, applied once.

Proposition 3 (single-pass unsoundness, scoped to the implemented construction). For the substituting-DQ-decision construction below, single-pass evaluation on (a, c(a), E(a)) yields a composed Exec verdict whose executed action rho_sub(a) violates the authority or resource gate at execution time; and symmetrically, single-pass holds an action whose remediated form is compliant. Construction: place an authority cap kappa strictly between the order values induced by the corrupted read and by the governed substitute. The artifact instantiates this as scenario S4 across all 30 registered seeds; the claim is not made for arbitrary continuous economics or arbitrary gate implementations beyond this construction (independent review classification: checked-scope-only). Full proof in Appendix A.

Protocol (remediate-regate composition, "rtr" in artifact output). Phase I: evaluate the evidence gate; on substitution form a' = rho_sub(a) and recompute c(a'). Under W2, if the resource gate would otherwise reject a' outright as over budget, apply rho_route(a') and recompute c(a') again. Phase II: evaluate every gate, including the evidence gate, on (a', c(a'), E(a')); return the join of Phase II responses, recording Phase I in the Evidence Set.

Lemma 1 (termination, scoped to the current one-shot composition branch). For the current one-shot composition branch and the DQ-library behavior exercised in this artifact's scenarios/tests, buffer substitution is idempotent, rho_sub(rho_sub(a)) = rho_sub(a), and E(rho_sub(a)) consists of governed records the evidence gate admits by construction; hence no further remediation is generated and the protocol reaches a fixed point after at most one remediation of each operator. The argument depends on an external DQ predicate contract this artifact composes but does not itself prove for every possible governed record (independent review classification: checked-scope-only). Full proof in Appendix A.

Assumptions for the current composition theorem. The soundness result below rests on the following assumptions, made explicit here as first-class objects rather than left implicit in the theorem's proof.

- A1. Determinism. Each member control is deterministic for fixed action, evidence, context, and control-local state.
- A2. Bounded remediation. The remediation branch exercised by the artifact is one-shot or otherwise bounded.
- A3. Idempotence. The evidence substitution operator is idempotent in the modeled branch.
- A4. Governed-record admissibility. The governed substitute satisfies the evidence-predicate contract exercised by the artifact.
- A5. Derived-context recomputation. Every derived value consumed by another control is recomputed after remediation.
- A6. Final regating. Every applicable control is reevaluated on the final remediated action before execution.
- A7. No concurrent state mutation in theorem scope. Relevant control state does not change between final evaluation and execution; stream-level concurrency is outside the theorem's scope.

Read together: A1 and A2 and A3 and A4 and A5 and A6 and A7 imply per-action soundness (Definition 3).

Theorem 1 (soundness of remediate-regate composition; general statement retagged checked-scope-only per independent review round two, finite response-lattice encoding split into Corollary 3). Under Lemma 1 and gates that are functions of (action, context, evidence, current state), the remediate-regate protocol satisfies Definition 3: Phase II evaluates every gate on a_exec itself, and the join preserves every Held verdict. Corollary 1 (sufficiency only; retagged checked-scope-only per independent review round two): if the authority and resource gates are invariant under the operators applied on the executed-reachable action set, single-pass is sound. The converse does not hold in general -- an independent review gave a counterexample (a gate that varies only on actions independently held, and so never executed) -- and this paper no longer claims it; an earlier draft's iff overstated what was proved. Full proof, and the counterexample worked through, in Appendix A.

## 5. Multi-remediator composition

A second workflow (W2, weekly commitment) introduces a second remediation operator: rho_route(a), which scales the committed quantity down to the largest quantity whose predicted cost and carbon both fit the remaining weekly budget, then recomputes context from the scaled quantity -- the same remediate-and-regate pattern Theorem 1 establishes for evidence substitution, applied to a different field of the action. With both operators active, does a fixed order matter -- does remediator interaction (Section 2) actually occur for this artifact's own two operators.

CH7 (multi-remediator order dependence). Is rho_route(rho_sub(a)) always equal to rho_sub(rho_route(a))? A finite-model checker (checkers/remediator_check.py) applies both orders over a grid of ([GENERATED: checkers.remediator_grid_points] points): quantity, corrupted unit cost, governed unit cost, cost budget, carbon budget, reusing the real remediation functions directly. Registered outcome: [GENERATED: checkers.remediator_outcome], with [GENERATED: checkers.remediator_counterexamples] disagreeing grid points out of [GENERATED: checkers.remediator_grid_points]. The independent review additionally probed continuous-valued points off this pre-registered grid and found order-divergent outcomes there too (review/REVIEW.md Section 5: 144/200 HEAD-derived off-grid points order-divergent); this artifact promotes that probe into the checker itself and reruns it on every checker run, seeded from a fixed declared constant in prereg/probe-seeds.json rather than the current git HEAD, so the published count is commit-stable rather than drifting with every commit (round-two independent review finding R2-N1): [GENERATED: checkers.remediator_offgrid_non_confluent]/[GENERATED: checkers.remediator_offgrid_probes] off-grid points disagree, strengthening CH7 beyond the declared grid. Where the two orders disagree, the mechanism is structurally the same failure Proposition 3 identifies between composition protocols: a budget check run against a not-yet-corrected value never gets re-checked once the value is corrected. This is the formal justification for prereg/w2-workflow.md's fixed ordering (evidence gate first, then resource gate) -- not an arbitrary implementation choice but a consequence of the operators' non-commutativity. Full result in Appendix A.

Design rule (remediation order). When remediation operators do not commute, their ordering is part of governance policy and must be specified, versioned, and auditable rather than left to implementation accident.

```text
rho_sub
  -> unit_cost
      -> order_value
          -> authority
      -> predicted_cost
          -> resource

rho_route
  -> quantity
      -> order_value
          -> authority
      -> predicted_cost
          -> resource
```

Both remediators affect variables downstream controls consume, which is exactly why they can fail to commute. A fixed order is required for the two operators this artifact implements, and CH7 above is the formal justification for pre-registering it rather than leaving it unspecified. A fixed order is not, however, a general solution to arbitrary multi-remediator composition: with three or more operators, applying one can make an earlier one relevant again, and this artifact does not solve arbitrary non-idempotent remediators, cycles, global termination, unique fixed points, confluence across arbitrary operators, concurrent state updates, or serializability across multiple agents for that general case. This work establishes a sound one-shot composition protocol for the implemented idempotent setting and demonstrates why general multi-remediator systems require an explicit termination and confluence theory; see [`docs/generalized-composition.md`](docs/generalized-composition.md) for that theory's open properties, stated as future work rather than an additional claim of this paper.

## 6. Stateful governance and evidence-buffer contamination

Admission and promotion into governance state are different decisions. Admission determines whether a record may participate in the current action. Promotion into persistent remediation state is a stronger decision because that record can influence future actions. Therefore, current admissibility does not imply future reference trustworthiness. The evidence gate's governed buffer (Section 4) trusts its own most recent admitted write when substituting for a later violation. This is sound against the covered defect classes (stale, superseded, contradictory, malformed evidence) because the gate's own predicates catch them before they can corrupt the buffer. It is not sound against a declared-uncovered class: a corrupted value that the gate's predicates never flag is admitted, and admitted values are exactly what the buffer trusts. The mechanism is: (1) the governance buffer accepts writes from admitted observations; (2) an uncovered defect can therefore enter trusted state; (3) future substitutions can reuse that contaminated state; (4) the vulnerability is created by the interaction between incomplete coverage and stateful remediation, not by either alone; (5) quarantine and median filtering, below, are example mitigation strategies against it, not a claim that the underlying vulnerability is eliminated. This generalizes the mechanism conceptually to caches, agent memories, feature stores, retrieval memories, policy state, and evidence registries, without claiming that the observed prevalence applies to those systems. The quarantine and median-of-three strategies below remain mechanism demonstrations, not the main scientific claim.

CH6 (buffer contamination is real and mitigable). A second uncovered defect class, plausible_outlier_high, is added at the same declared rate as plausible_outlier (Appendix B's defect table), specifically to exercise this mechanism. A poisoned-substitution metric (contamination.py) determines, purely from ground-truth labels never consulted by the gate itself, whether the value a substitution actually used traces back to a prior admit from an uncovered class. Two buffer-side mitigations are implemented entirely outside the sarc_dq.gate package, as this repo's own buffer-wrapping adapters: a quarantine window (a write becomes trusted only after three consecutive consistent admits) and a rolling median-of-3.

Results, 30 seeds, both workflows: under W1 (daily), plain produces at least one poisoned substitution on every seed ([GENERATED: sweep.ch6_w1_plain_poisoned_ci]), and both mitigations produce a strictly lower count than plain on every seed (mitigations hold: [GENERATED: sweep.ch6_w1_mitigations_hold]). The preregistered seed-by-seed decision rule is not supported under W2 because the lower substitution population produces seeds with zero baseline poisoning events, making strict per-seed reduction impossible to satisfy on those seeds ([GENERATED: sweep.ch6_w2_plain_has_poisoning_every_seed]; mean [GENERATED: sweep.ch6_w2_plain_poisoned_ci]; mitigations hold on every seed: [GENERATED: sweep.ch6_w2_mitigations_hold]). This limits the robustness claim for W2; it does not establish that the mitigation mechanism is ineffective -- see Table 6 and Section 9.

## 7. The unified Evidence Set

Each decision emits one record: action context; per-gate sections (authority constraints and verdicts; resource predicted cost, carbon, budget state, verdict; evidence predicate results, verdict, substitution with pre and post values and buffer key, record eids); the final join, winner gate, and the remediation record (which operators fired, in which order, for this decision). Ground-truth labels are never present; they live in a separate run log. The line's JSON shape is fixed by schemas/evidence_line.schema.json (Draft 2020-12), pre-registered before any Phase 3 result existed.

Proposition 4 (identity commitment and integrity, relative to a content-addressed store; retagged checked-scope-only per independent review round two). From an executed action's unified Evidence Set line alone, one can identify -- by content-addressed id -- every record each phase relied on, including the Phase I evidence before substitution and the specific governed-buffer write a substitution drew from, and verify those identities given access to the record store and buffer write history; the line does not, by itself, reconstruct the original bytes, and this paper no longer claims that it does (an earlier draft did; an independent review correctly refuted the byte-reconstruction reading -- Appendix A). A durable, run-scoped buffer write-history log (composition.py's write_log, persisted as buffer-writes.jsonl next to the evidence lines) now backs "the specific governed-buffer write a substitution drew from": each substitution resolves to exactly one write event, closing the round-two independent review's provenance finding that 3,478 real substitution occurrences resolved to only 62 unique ids under the prior key+value-only hash. Extends the single-gate lineage result of arXiv 2607.26313. Full proof in Appendix A.

Proposition 4 assumes that the content-addressing function provides collision resistance at the security level required by the deployment and that the referenced record store or write history remains available and integrity-protected. The Evidence Set provides an identity commitment and lineage binding; it does not independently establish source authenticity, semantic truth, or permanent availability of the referenced bytes.

Proposition 5 (no manufactured coverage). The composed plane's detected class set equals the union of member gates' detected class sets; composition never detects a class no member covers. Corollary: declared uncovered classes remain uncovered, and an honest composed readout must say so. Full proof (a structural tautology, machine-verified across every swept seed) in Appendix A.

## 8. Empirical validation

Artifact: suite-demo composes the three published engines, installed unmodified (repositories verifiably untouched), over open payload data (UCI Online Retail, CC BY 4.0) with a declared synthetic metadata layer and a declared eight-class injector at declared rates; 30 pre-registered seeds (prereg/seeds.json, first seed 26313); zero model calls; zero source writes, hash-proven. Scenarios: S1 baseline, S2 tight budgets, S3 unauthorised burst with a low authority cap, S4 the Proposition 3 construction with the cap between pre- and post-substitution order values (all W1); W2-S1 baseline and W2-S2 tight weekly budgets (both W2); CONTAM-W1 and CONTAM-W2, one per buffer strategy (plain, quarantine, median_of_3), for the CH6 study.

Every definition used below (hypotheses, seeds, weights, the W2 workflow, the contamination metric and mitigations, the CH2 semantics redefinition) was committed and tagged prereg-v1 before any corresponding result entered this repository's history -- the gated-generation discipline this artifact follows throughout.

This section brings CH1-CH8 together as evidence for the mechanisms Sections 2-7 introduce; it is the artifact's evidence base, not the paper's conceptual narrative.

Hypotheses, stated before the corresponding code ran:

- CH1 (veto soundness). Post-hoc audit finds zero executed actions violating any gate at execution time under remediate-regate, re-evaluated against the exact Phase II evidence records the decision executed on (independent review finding F4 -- an earlier draft's audit re-derived a synthetic clean record from the executed action's own numbers instead; the audit now persists and loads the real records). Single-seed result: [GENERATED: metrics.ch1_violations]. 30-seed result: [GENERATED: sweep.ch1_supported_seed_count] seeds with zero violations.
- CH2 (single-pass unsoundness is real, new semantics). Single-pass unsoundness *can occur* after remediation, demonstrated for this artifact's own construction (Section 4); this does not establish how frequently production systems suffer this failure. In S4, remediate-regate and single-pass verdicts differ in Exec/Held class, or agree in class with an audited violation, on at least one decision, in the predicted direction; response-string-only differences with a clean audit are reported separately as label_only_differences, not folded in (prereg/ch2-semantics.md). Single-seed result: [GENERATED: metrics.ch2_divergent_decisions] divergent decisions ([GENERATED: metrics.label_only_differences] additional label-only differences); directions [GENERATED: metrics.ch2_direction_counts]. 30-seed result: [GENERATED: sweep.ch2_divergent_decisions_ci] divergent, [GENERATED: sweep.label_only_differences_ci] label-only.
- CH3 (deterministic selectivity). False-hold rate on clean, authorised, in-budget decisions is exactly zero. Single-seed result: [GENERATED: metrics.ch3_false_hold]. 30-seed result: [GENERATED: sweep.ch3_false_hold_ci].
- CH4 (coverage honesty). plausible_outlier and plausible_outlier_high detection is zero at every gate and in composition; covered-class detection equals the union of member coverages. Single-seed result: [GENERATED: metrics.ch4_matrix]. 30-seed result: union_ok on [GENERATED: sweep.ch4_union_ok_seed_count] seeds.
- CH5 (compensation is empirically unsafe). Section 3.
- CH6 (buffer contamination is real and mitigable). Buffer poisoning *can propagate* through governed remediation state, demonstrated for the two implemented mitigations; this does not establish enterprise prevalence of such poisoning. Section 6.
- CH7 (multi-remediator order dependence). These two remediation operators *do not commute*; this does not establish that arbitrary remediation operators are non-commutative. Section 5.
- CH8 (robustness across 30 seeds x 2 workflows). Table 7.

Table 1. Decisions, per-gate veto counts, winner-gate distribution, by scenario (single seed, S1-S4). [GENERATED: table1]

Table 2. Cross-gate matrix: injected class by winner gate (single seed, S1). [GENERATED: table2]

Table 3. Remediate-regate versus single-pass divergences in S4, with pre and post order values and the cap (single seed). [GENERATED: table3]

Table 4. Loss versus clean counterfactual, executed versus held split (single seed, S1-S4). [GENERATED: table4]

Table 5. CH2/CH3/CH5 means with 95% confidence intervals, 30 seeds. [GENERATED: table5_ci]

Table 6. CH6 buffer contamination and mitigation, 30 seeds, both workflows. [GENERATED: table6_ch6]

Table 7. CH8 robustness readout: does each hypothesis's registered decision rule hold on every one of the 30 seeds (and, for CH6, both workflows). [GENERATED: table7_ch8]

Negative-results commitment. Any CH not supported as written is reported as NOT SUPPORTED as written, following the practice of the prior papers -- CH6 under W2 is the concrete instance of this commitment in this version.

### Claims to evidence

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
| C9 | Full reproducibility | seed list, hashes, provenance; public repository; archival identifier when assigned | artifact; public repository URL included |
| C10 | Compensation admits vetoed actions over the full discrete grid | CH5, checkers/compensation_check.py | machine-checked, exhaustive |
| C11 | Buffer contamination exists and both mitigations reduce it | CH6, contamination.py | generated; 30-seed CI; W2 exception reported honestly |
| C12 | The two remediators do not commute; fixed order is justified | CH7, checkers/remediator_check.py | machine-checked, exhaustive |
| C13 | CH1-CH5 meet their registered decision rules across all 30 seeds; CH6 does so under W1 but not W2 | CH8, Table 7 | generated; 30-seed sweep |

### Claims versus non-claims

| The paper claims | The paper does not claim |
|---|---|
| Single-pass can be unsound after remediation | All single-pass systems are unsound |
| The implemented remediators are non-commutative | All remediation operators are non-commutative |
| Remediate-regate is sound in the current one-shot setting | General convergence of arbitrary remediator systems |
| Buffer poisoning exists in the demonstrated mechanism | Production prevalence |
| Composition preserves only member-control coverage | Composition guarantees complete safety |
| Evidence Sets preserve identity commitments | Hashes alone reconstruct source bytes |
| Hard controls require non-compensatory feasibility semantics | Weighted scoring is never useful |

## 9. Related work

Eleven citation gaps were resolved via the V4 pipeline (fetch, verify, record in verified-citations.json) across this response to the independent review's finding F5 and this section's subsequent expansion following a commissioned second (positioning) review; none were invented, and any that could not have been verified would have stayed an honestly unresolved citation gap, counted rather than guessed, per this artifact's own citation-gate discipline.

Compositional runtime enforcement. Prior work on compositional runtime enforcement studies when multiple enforcement monitors preserve correctness under serial or parallel composition (Pinisetty & Tripakis, doi 10.1007/978-3-319-40648-0_7, extended in Pinisetty, Pradhan, Roop & Tripakis, doi 10.1007/s10703-022-00401-y). That literature establishes that enforcement composition itself is not a new problem. Our object is narrower and structurally different: heterogeneous pre-action controls evaluate different dimensions of the same proposed action, maintain different control-local state, and may remediate the action, evidence, or derived context consumed by another control. The resulting problem is therefore not only whether enforcement monitors compose, but whether a prior control judgment remains valid after another control has transformed the semantic object that judgment was made about. We call this remediation-induced control coupling. Existing work studies composition of enforcement monitors. This paper studies invalidation of heterogeneous control judgments caused by cross-control remediation of the governed action, evidence, or derived context. Edit automata (Ligatti, Bauer & Walker, doi 10.1007/s10207-004-0046-8) are the canonical mechanism for enforcement that can suppress, insert, or substitute actions in a trace, the same suppress/insert/substitute vocabulary this paper's remediation operators instantiate at the level of a single pre-action decision rather than a trace.

Runtime verification and enforcement monitors. The composed plane's gates are exactly the "monitor that examines a sequence of actions and can transform or block them" mechanism Schneider's security automata formalize (doi 10.1145/353323.353382); this paper's contribution is the composition semantics across several such monitors judging the same action, not the single-monitor enforcement question itself.

Policy-combining algorithms. "One veto dominates other permits" is already a familiar policy-composition pattern: XACML's deny-overrides rule- and policy-combining algorithms make exactly this rule a named, standardized primitive (OASIS XACML 3.0, https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html), and Bonatti, di Vimercati & Samarati give an algebra for composing access-control policies under such combinators more generally (doi 10.1145/504909.504910). This paper therefore does not present the join rule itself as its principal novelty; the difficult composition problem it studies begins when a control's response includes a transformation, not merely a decision label.

Non-compensatory and veto rules in multi-criteria decision analysis: veto thresholds, where one criterion can block an otherwise-acceptable alternative regardless of the others' scores, are an established mechanism in outranking-based MCDA (Nowak, doi 10.1016/j.ejor.2003.06.008); the linear-family lemma in Section 3 gives an exact threshold condition for when a weighted-sum aggregator does or does not have this property, rather than assuming it.

Rewrite systems, confluence, and termination. CH7 (Section 5) naturally touches confluence, non-commutativity, operator ordering, fixed points, termination, and normal forms -- the core vocabulary of term-rewriting theory, whose confluence-plus-termination-implies-unique-normal-form result traces to Newman's original combinatorial argument (doi 10.2307/1968867). This paper does not become a term-rewriting paper: it demonstrates non-commutativity for two concrete remediation operators and does not claim a general solution for arbitrary rewrite systems; see [`docs/generalized-composition.md`](docs/generalized-composition.md) for the open properties such a solution would require.

Stateful enforcement. The resource budget and governed evidence buffer both introduce state consumed and updated across decisions, in the sense of a general stateful-enforcement formulation G(a_t,c_t,E_t,S_t) -> (r_t,S_{t+1}); Fong's shallow-execution-history model is the same kind of state-carrying enforcement decision, tracking a bounded summary of prior events rather than the full trace (doi 10.1109/secpri.2004.1301314). Budget governors for autonomous systems: the resource gate's predictive cost/carbon budgeting is one instance of the broader resource-bounded-agent governance problem Agent Contracts formalizes with conservation laws across delegation hierarchies (arXiv 2601.08815); this paper's downroute operator is a single-agent, single-budget-window mechanism, not a multi-agent conservation guarantee.

Guardrail and policy-engine frameworks for LLM agents: LlamaFirewall (arXiv 2505.03574) is a recent example of a unified guardrail system for LLM agents and describes detector pipelines. To our reading, its stated scope does not analyze the non-compensatory-join or remediation-reordering questions Sections 3 and 5 study; this comparison distinguishes problem formulations rather than claiming superiority or complete coverage of the guardrail literature.

Separation of duties and multi-party authorisation: the authority gate's role-allowlist mechanism is a narrow instance of the separation-of-duty concept Clark and Wilson introduced for commercial integrity policies (doi 10.1109/SP.1987.10001); this paper does not implement multi-party (dual-control) authorisation, only single-role admission checks.

Cache/buffer poisoning and trust-on-first-use vulnerabilities in adjacent systems: Wendlandt, Andersen, and Perrig's analysis of SSH host-key caching (https://www.usenix.org/legacy/event/usenix08/tech/full_papers/wendlandt/wendlandt.pdf) offers a structural analogy for the governed-buffer vulnerability in Section 6 and CH6: a value admitted without independent corroboration can influence future trust decisions. The quarantine-window mitigation applies a related multi-observation-before-trust principle to a numeric buffer rather than claiming the two threat models are identical.

What existed and what this paper adds, summarized across the related work above:

| Existing concept | Established literature | What this paper adds |
|---|---|---|
| Runtime enforcement | Security/edit automata | Heterogeneous enterprise pre-action controls |
| Enforcement composition | Compositional runtime enforcement | Cross-control invalidation caused by action/evidence remediation |
| Deny-overrides / veto | XACML / policy algebra / MCDA | Not claimed as novelty; used as hard-feasibility semantics |
| Rewrite ordering | Rewriting / confluence theory | Concrete order-sensitive governance remediators |
| Stateful enforcement | History/state-based policy | Promotion of uncovered-but-admitted evidence into future remediation state |
| Audit provenance | Existing provenance mechanisms | One cross-control Evidence Set binding pre/post-remediation decisions |

The contribution is not that each ingredient above is new; it is the specific composition problem created by their interaction.

Nothing above is load-bearing for the propositions. Every citation this draft relies on is checked against a verified whitelist (verified-citations.json) by citation_check.py (V4 gate) on every population run.

## 10. Limitations and open theory

Synthetic metadata layer over open payloads; declared injection rates; no prevalence claims. Resource-gate estimates are cold-start. Stream-level budget ordering effects are defined away per action. Single author at draft time; see the validation note. S4 is a constructed scenario, declared as such. CH6's mitigation-holds-on-every-seed claim is supported under W1 but not under W2, where the weekly-commitment workflow's much smaller per-seed substitution population sometimes produces zero poisoning events by chance, making "strictly lower than plain" impossible to satisfy on those seeds -- this is a sample-size limitation of the weekly workflow, not evidence against the mitigations' mechanism, and it is reported rather than resolved by re-weighting or dropping seeds. CH7's non-commuting-operators result is a property of this artifact's two specific remediation operators (evidence substitution, resource downroute); it does not generalise to remediators with different structure without re-deriving the checker. The artifact is a mechanism demonstration, not a benchmark release.

The five-level response order (admit < substitute < degrade < escalate < block, Definition 1) is this composition plane's own operational policy for producing a single response from several gate verdicts, not a claimed universal semantic ordering; other systems could use a different or partially ordered response structure while preserving the same Exec/Held execution-safety requirement (Section 2). A fixed remediation order (Section 5) is required for the two operators this artifact implements and is not a general solution to arbitrary multi-remediator composition; general termination, confluence, and concurrency for arbitrary stateful remediation systems remain open, and [`docs/generalized-composition.md`](docs/generalized-composition.md) states precisely what establishing them would require: fixed-point semantics, termination, confluence, cycle detection, state consistency, serialization, and concurrent multi-agent coordination, none of it attempted here.

Some symmetric t-intervals for low non-negative-count metrics (e.g., Table 6's quarantine and median_of_3 mitigation counts under W1/W2) extend slightly below zero; this is a property of a symmetric interval around a small non-negative sample mean, not evidence of a negative measurement, and is presented as computed, without truncation or bootstrap re-estimation (Appendix C).

## 11. Conclusion

The central result of this work is not that multiple governance gates should simply be aggregated conservatively. It is that once one governance control is permitted to transform the action, evidence, or context consumed by another, prior control judgments become contingent on the version of the governed object they evaluated. Correct pre-action governance therefore requires explicit semantics for invalidating and recomputing dependent judgments after remediation. When several remediation operators exist, their ordering can itself affect the final governed action, making remediation order part of governance semantics. When admitted information is promoted into persistent governance state, admission and future trust must likewise be distinguished. These results establish a bounded compositional semantics for the current setting while leaving general convergence, concurrency, delegation, and arbitrary stateful remediation as open problems.

## Appendix A. Proofs

[GENERATED: appendixA_proofs]

## Appendix B. Artifact manifest. [GENERATED: appendixB_manifest]

## Appendix C. Statistical methodology (V3 gate)

30 seeds (prereg/seeds.json, first seed 26313, generated by `random.Random(26313)` sampling without replacement from [1, 2^31-1], frozen before any Phase 3 code ran). Confidence intervals are two-tailed 95% t-intervals, mean +/- t_crit(df=29, alpha=0.05) * (stdev / sqrt(30)), t_crit = scipy.stats.t.ppf(0.975, 29), computed exactly at runtime (fixed per independent review finding F6: the prior rounded constant 2.045230 diverged from the exact value by up to 3.77e-6 in some CI endpoints -- see review/REVIEW.md); implementation in sweep.py's mean_ci95, using math.fsum over explicitly sorted inputs for mean and variance (fixed per independent review round-two finding R2-N3: naive sum()/len() is order-dependent at the ULP level, unlike fsum) and scipy (pinned in bootstrap.sh) for the t-critical value. Scenario economics (budgets, caps) are calibrated once from the registered baseline seed and held fixed across the sweep; only each scenario's decision-stream seed varies -- the same "treatment", repeated draws, which is the design this kind of robustness claim requires. Per-seed summaries (no raw per-decision data) are checkpointed under out/results/sweep/ and are part of this artifact's committed history. Some symmetric t-intervals for low non-negative-count metrics extend slightly below zero (Section 10); this is presented as computed, without truncation or bootstrap re-estimation. The confidence intervals are descriptive summaries of between-seed variation and are not the basis of the paper's formal correctness claims or preregistered Boolean support decisions; exhaustive/model-checked claims and seed-level decision rules are evaluated independently of these intervals.

## Validation note

The artifact underwent four commissioned adversarial automated review rounds under published protocols. Those reviews informed corrections to claims, proofs, provenance, and reproducibility checks. Automated review does not substitute for human peer review; full reports, protocols, evidence, and process provenance are available in the companion repository.

The round-four terminal review report states, verbatim: "This artifact was independently replicated and adversarially reviewed in four rounds by automated agents following the published protocols in sarc-suite-agent-review.md, sarc-suite-agent-review-r2.md, sarc-suite-agent-review-r3.md, and sarc-suite-agent-review-r4.md; the round-one report and evidence are at review/REVIEW.md and review/review.json, the round-two report and evidence are at review-out-r2/REVIEW-R2.md, review-out-r2/review.json, and review-out-r2/evidence/, the round-three report and evidence are at review-out-r3/REVIEW-R3.md, review-out-r3/review.json, and review-out-r3/evidence/, and the round-four report and evidence are at review-out-r4/REVIEW-R4.md, review-out-r4/review.json, and review-out-r4/evidence/. Automated review complements and does not replace human peer review." (review-r4/REVIEW-R4.md, Author-reuse disclosure.)

The quotation preserves the report exactly. In this release repository, the imported round-two, round-three, and round-four reports and JSON mirrors are packaged under review-r2/, review-r3/, and review-r4/ respectively; the original review-out-r2/, review-out-r3/, and review-out-r4/ names refer to the external review workspaces in which those reports were issued.

Process provenance: the review protocols were authored by the author's AI assistant before each round and are committed in this repository; the reviews were commissioned by the author and executed by a separate vendor's automated agent in fresh sessions with access only to this public repository; adjudication between rounds was performed by the same assistant that authored the protocols and is not independent; every mechanical claim in the review reports is re-runnable from this repository.

Version 0.4 revises framing, positioning, and related-work coverage following a commissioned second review (review-secondary/), with all measured results, claim semantics, PROOF-STATUS tags, and the four-round review chain unchanged. Version 0.5 is a final scholarly-positioning, formal-precision, and terminology pass following a third commissioned review round (review-secondary/), with all measured results, claim semantics, PROOF-STATUS tags, and counts unchanged from v0.4. Versions 0.1 to 0.4 remain recoverable as immutable historical revisions in repository history.

This draft is the artifact's response to that review: findings F1-F6 (review/REVIEW.md Section 4) are fixed or weakened per the review's own binding-unless-fixed policy, never argued with in this text; the proof-tag reclassifications in Appendix A (checked-scope-only for Proposition 3 and Lemma 1, sufficiency-only for Corollary 1) follow the review's Section 3 proof-tag policy exactly, and no tag here claims more than that review certified.

**Acknowledgements.** Drafting, engineering, review automation, and a positioning review were AI-assisted (Claude, Perplexity, and OpenAI GPT systems); the author is solely responsible for all claims.
"""


def _read_appendix_a() -> str:
    text = Path("appendix-a-proofs.md").read_text()
    # Drop the file's own top-level H1 (the draft supplies its own
    # "## Appendix A. Proofs" heading) so the embedded content starts at
    # the first proposition.
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def main():
    print("=" * 70)
    print("SARC SUITE ONE-PASS DEMO: paper v0.5 generation (Phase 5)")
    print("=" * 70)

    metrics_path = Path("out/metrics.json")
    sweep_path = Path("out/results/sweep_summary.json")
    if not metrics_path.exists():
        raise SystemExit("out/metrics.json not found — run `make suite` first.")
    if not sweep_path.exists():
        raise SystemExit("out/results/sweep_summary.json not found — run `make sweep` first.")
    metrics = json.loads(metrics_path.read_text())
    sweep = json.loads(sweep_path.read_text())

    print("\n[1] Re-running the V2-gate checkers...")
    lattice_result = lattice_check.run()
    compensation_result = compensation_check.run()
    remediator_result = remediator_check.run()
    lint_result = proof_status_lint.lint()
    if not lint_result["all_clean"]:
        raise SystemExit(f"PROOF-STATUS lint FAILED: {lint_result}")
    print(f"  lattice all_hold={lattice_result['all_hold']}, "
          f"compensation holds={compensation_result['proposition_1_holds_exhaustively']}, "
          f"remediator outcome={remediator_result['ch7_registered_outcome']}, "
          f"proof-status lint clean={lint_result['all_clean']}")

    manifest = build_manifest(data_sha256=hashlib.sha256(Path("data/open_retail_daily.csv").read_bytes()).hexdigest(), seed=26313)

    slots = generate_v3_slots(metrics, manifest, sweep, lattice_result, compensation_result, remediator_result)
    slots["appendixA_proofs"] = _read_appendix_a()

    print("\n[2] Writing v0.5 draft verbatim...")
    draft_path = Path("paper4-composition-draft-v0.5.md")
    draft_path.write_text(PAPER_DRAFT_TEXT)
    print(f"  wrote {draft_path}")

    print("\n[3] Writing v0.5 tables...")
    paper_dir = Path("out/paper")
    paper_dir.mkdir(parents=True, exist_ok=True)
    for key in ("table1", "table2", "table3", "table4", "table5_ci", "table6_ch6", "table7_ch8"):
        (paper_dir / f"{key}.md").write_text(slots[key])
    (paper_dir / "slots_v3.json").write_text(json.dumps(slots, indent=2))
    print(f"  wrote {paper_dir}/slots_v3.json")

    print("\n[4] Populating v0.5 draft...")
    output_draft = Path("paper4-composition-draft-v0.5-populated.md")
    unfilled = populate_draft(str(draft_path), slots, str(output_draft))

    print("\n[5] V4 gate: citation verification...")
    schema_result = verify_whitelist_schema()
    if not schema_result["clean"]:
        raise SystemExit(f"verified-citations.json is missing required fields: {schema_result}")
    citation_result = check_citations(str(output_draft))
    print(json.dumps({k: v for k, v in citation_result.items()}, indent=2))
    if not citation_result["clean"]:
        raise SystemExit(f"citation check FAILED: {citation_result}")

    print("\n[6] PROOF-STATUS lint on the populated draft itself...")
    populated_lint = proof_status_lint.lint([str(output_draft)])
    if not populated_lint["all_clean"]:
        raise SystemExit(f"PROOF-STATUS lint FAILED on populated draft: {populated_lint}")
    print(f"  {populated_lint['total_tags']} tags, all clean")

    print("\n" + "=" * 70)
    print("HONESTY BANNER")
    print("=" * 70)
    print(HONESTY_BANNER)

    print("\n" + "=" * 70)
    print("ARTIFACT PATHS")
    print("=" * 70)
    for p in (draft_path, output_draft, metrics_path, sweep_path, paper_dir / "slots_v3.json"):
        print(f"  {p}")

    if unfilled:
        raise SystemExit(f"paper v0.5 generation FAILED: unfilled slots {unfilled}")
    print(f"\n[CITE-NEEDED] placeholders remaining (honest, not fabricated): {citation_result['cite_needed_placeholder_count']}")
    print("make paper-v3: zero unfilled slots, citations verified, PROOF-STATUS lint clean.")


if __name__ == "__main__":
    main()
