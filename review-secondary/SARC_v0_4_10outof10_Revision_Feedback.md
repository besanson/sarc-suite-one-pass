# Final Revision Feedback: Path to a 10/10 Manuscript

The current v0.4 is substantially stronger than the earlier versions. The central contribution is now correctly framed around **remediation-induced control coupling**, remediate-regate semantics, remediation ordering, and governance-state contamination. The artifact and reproducibility package are already exceptional.

The remaining weaknesses are not experimental. They are primarily about ensuring that a formal-methods or systems reviewer cannot misunderstand, overread, or trivially challenge the manuscript.

## Recommendation

**Do not add new experiments.**

Do not add another workflow, another seed, another remediation operator, concurrency, delegation, a production dataset, or new LLM experiments.

The path from the current manuscript to something approaching 10/10 is now almost entirely:

- scholarly positioning;
- formal precision;
- narrative hierarchy;
- terminology discipline;
- reviewer-proof threat and scope boundaries;
- publication polish.

---

# 1. Add the closest compositional runtime-enforcement prior art explicitly

This is the single most important remaining change.

The Related Work section now covers:

- edit automata;
- Schneider;
- XACML;
- policy algebra;
- MCDA veto rules;
- Newman/confluence;
- stateful enforcement;
- Agent Contracts;
- LlamaFirewall;
- separation of duties;
- TOFU.

However, the paper should directly discuss:

- Pinisetty & Tripakis, **Compositional Runtime Enforcement**;
- the later **Compositional Runtime Enforcement Revisited** work.

A knowledgeable formal-methods reviewer is likely to know this literature.

The issue is not that this prior work destroys the novelty. It does not.

The issue is that omitting the most direct prior art creates an unnecessary reviewer vulnerability.

Do not simply add it to the bibliography. Add an explicit differentiation paragraph.

### Suggested text

> **Compositional runtime enforcement.** Prior work on compositional runtime enforcement studies when multiple enforcement monitors preserve correctness under serial or parallel composition. That literature establishes that enforcement composition itself is not a new problem. Our object is narrower and structurally different: heterogeneous pre-action controls evaluate different dimensions of the same proposed action, maintain different control-local state, and may remediate the action, evidence, or derived context consumed by another control. The resulting problem is therefore not only whether enforcement monitors compose, but whether a prior control judgment remains valid after another control has transformed the semantic object that judgment was made about. We call this remediation-induced control coupling.

The novelty position should become:

> **Existing work studies composition of enforcement monitors. This paper studies invalidation of heterogeneous control judgments caused by cross-control remediation of the governed action, evidence, or derived context.**

That is much harder to attack.

---

# 2. Reorder the manuscript abstract to match the real contribution hierarchy

The paper now correctly says the four primary contributions are:

1. remediation-induced control coupling;
2. remediate-regate;
3. non-commutative remediation;
4. governance-state contamination.

However, the full manuscript abstract still gives the positive-weight aggregation result too much prominence.

The manuscript abstract should follow the same hierarchy as the stronger arXiv abstract.

### Recommended abstract structure

1. remediation-induced control coupling;
2. single-pass unsoundness;
3. remediate-regate;
4. non-commutative remediators;
5. governance-state contamination;
6. supporting aggregation result;
7. Evidence Set / no-manufactured-coverage;
8. empirical artifact and scope limitation.

### Suggested rewrite

> Agentic AI systems increasingly execute actions subject to multiple heterogeneous pre-action controls, including authority, resource, and evidence controls. Prior research has studied composition of enforcement monitors and policy decisions; we study a narrower problem that arises when one control can remediate the action, evidence, or derived context consumed by another control. We formalize **remediation-induced control coupling**, in which a control transformation invalidates another control's earlier judgment. We show that naive single-pass composition can consequently be unsound and give a remediate-and-regate protocol that restores per-action soundness in the current bounded, idempotent setting. We further show that the two implemented remediation operators, evidence substitution and resource-budget downroute, do not commute, making remediation order part of the control-plane semantics rather than an implementation detail. At the state level, we demonstrate that currently admissible observations can contaminate future governance state when uncovered defects are promoted into a governed evidence buffer. Supporting results establish the conditions under which positive-weight additive aggregation can compensate a member veto, unified cross-control evidence lineage, and the fact that composition manufactures no new detection coverage. A deterministic artifact composing three published engines unmodified validates the mechanisms across 30 preregistered seeds and two workflows; all registered hypotheses except the W2 buffer-mitigation robustness criterion are supported as written. The artifact is a mechanism demonstration, not a production-prevalence study.

This makes the abstract tell the same story as the paper.

---

# 3. Be precise about non-commutativity versus non-confluence

This is the most important terminology issue to clean up.

The strongest CH7 result is:

\[
\rho_i(\rho_j(a))
\neq
\rho_j(\rho_i(a)).
\]

That directly proves **non-commutativity**.

It does not automatically prove non-confluence in the full rewriting-theoretic sense.

Two immediate outcomes may differ while still being joinable by later reductions.

### Recommendation

Use one of these terms for CH7 unless the checker establishes terminal unjoinable outcomes:

- **non-commuting outcomes**;
- **order-divergent outcomes**;
- **order-sensitive remediation**.

Reserve **non-confluence** for cases where the modeled outcomes are explicitly terminal and non-joinable.

If terminality makes the result non-confluent within the bounded model, say so precisely:

> “Because both remediation orderings terminate at protocol-terminal outcomes in the bounded transition model, the divergent outcomes are non-joinable within that model.”

Otherwise do not use the stronger term.

A formal-methods reviewer may challenge this distinction immediately.

---

# 4. Make the theorem assumptions explicit first-class objects

The current claim discipline is already excellent.

The manuscript should go one step further and collect the assumptions supporting remediate-regate soundness into one explicit block before the theorem.

### Suggested assumptions

> **Assumptions for the current composition theorem**
>
> **A1. Determinism.** Each member control is deterministic for fixed action, evidence, context, and control-local state.
>
> **A2. Bounded remediation.** The remediation branch exercised by the artifact is one-shot or otherwise bounded.
>
> **A3. Idempotence.** The evidence substitution operator is idempotent in the modeled branch.
>
> **A4. Governed-record admissibility.** The governed substitute satisfies the evidence-predicate contract exercised by the artifact.
>
> **A5. Derived-context recomputation.** Every derived value consumed by another control is recomputed after remediation.
>
> **A6. Final regating.** Every applicable control is reevaluated on the final remediated action before execution.
>
> **A7. No concurrent state mutation in theorem scope.** Relevant control state does not change between final evaluation and execution; stream-level concurrency is outside the theorem's scope.

Then the theorem can be read as:

\[
A_1\land A_2\land\cdots\land A_7
\Rightarrow
PerActionSoundness.
\]

This makes the theoretical boundary immediately understandable.

It also creates a clean bridge to the next SARC paper, where A7 is deliberately relaxed.

Do not broaden the theorem. Clarify its assumptions.

---

# 5. Add a lightweight remediation-dependency graph

The paper already contains the conceptual dependency diagram.

Add one minimal formal abstraction.

Define a directed graph:

\[
\mathcal C=(\mathcal G,\mathcal E_C)
\]

where:

\[
(G_i,G_j)\in\mathcal E_C
\]

iff there exists a reachable action \(a\) such that:

\[
G_j(a)\neq G_j(\rho_i(a)).
\]

This is the **remediation-induced control coupling graph**.

For the current example:

\[
DQ\rightarrow Authority
\]

and:

\[
DQ\rightarrow Resource.
\]

A resource downroute can similarly affect values consumed by other controls.

### Practical implication

Add a design rule:

> **If remediation by control \(G_i\) can change any input consumed by control \(G_j\), the earlier judgment of \(G_j\) must be treated as stale for the remediated action and recomputed before execution. When the dependency graph is incomplete or dynamic, full regating is the conservative strategy.**

No new experiment is needed.

This makes the concept more reusable for system architects.

---

# 6. Make the feasibility-versus-preference distinction explicit

The positive-weight aggregation result is useful, but it must remain subordinate to the paper's central thesis.

The conceptual logic should be:

\[
Feasible(a)
=
F_A(a)
\land
F_R(a)
\land
F_E(a)
\]

before preference optimization or ranking is applied.

Weighted aggregation can be useful **inside the feasible region**.

### Add this sentence explicitly

> **This paper is not arguing against weighted aggregation. It is arguing against using compensatory preference aggregation to implement controls whose semantics require independent veto authority.**

That eliminates an easy strawman.

Then the weighted-sum lemma becomes:

> an exact characterization of when an additive aggregator does or does not preserve the declared veto semantics.

That is a stronger and more disciplined framing than implying additive scoring is inherently unsafe.

---

# 7. Clarify the Evidence Set threat model

Proposition 4 is now appropriately narrowed to identity commitment and integrity relative to a content-addressed record store.

Add one explicit security-boundary paragraph.

### Suggested text

> Proposition 4 assumes that the content-addressing function provides collision resistance at the security level required by the deployment and that the referenced record store or write history remains available and integrity-protected. The Evidence Set provides an identity commitment and lineage binding; it does not independently establish source authenticity, semantic truth, or permanent availability of the referenced bytes.

This prevents three overreadings:

\[
Integrity \neq Authenticity
\]

\[
IdentityCommitment \neq Truth
\]

\[
Hash \neq Storage
\]

No experiment is required.

---

# 8. Strengthen CH6 as a governance-state result

CH6 is more valuable scientifically when framed as a **state trust problem** rather than only a poisoning problem.

The key principle should be:

\[
AdmissibleNow(r)
\not\Rightarrow
TrustedFutureState(r).
\]

### Suggested conceptual text

> Admission and promotion into governance state are different decisions. Admission determines whether a record may participate in the current action. Promotion into persistent remediation state is a stronger decision because that record can influence future actions. Therefore, current admissibility does not imply future reference trustworthiness.

This generalizes the mechanism conceptually to:

- caches;
- agent memories;
- feature stores;
- retrieval memories;
- policy state;
- evidence registries.

Without claiming that the observed prevalence applies to those systems.

The quarantine and median-of-three strategies should remain **mechanism demonstrations**, not the main scientific claim.

---

# 9. Defuse the confidence-interval criticism proactively

The manuscript correctly reports symmetric t-intervals that sometimes extend slightly below zero for sparse non-negative count metrics.

Add one sentence to the statistical methodology section:

> “The confidence intervals are descriptive summaries of between-seed variation and are not the basis of the paper's formal correctness claims or preregistered Boolean support decisions; exhaustive/model-checked claims and seed-level decision rules are evaluated independently of these intervals.”

This makes the statistical role completely clear.

A reviewer can no longer reasonably interpret a value such as:

\[
[-0.03,0.16]
\]

as implying that the study believes negative event counts are physically possible.

No reanalysis is necessary.

---

# 10. Reduce emphasis on automated review inside the manuscript

Keep the complete review chain, protocols, hashes, reports, evidence, and provenance in the repository.

That material is excellent.

But the manuscript itself should not make the automated review process feel like part of the scientific evidence.

The scientific case should rest on:

\[
Definitions
+
Proofs
+
MachineChecks
+
EmpiricalEvidence
\]

not on:

\[
NumberOfAutomatedReviewRounds.
\]

### Suggested concise disclosure

> “The artifact underwent four commissioned adversarial automated review rounds under published protocols. Those reviews informed corrections to claims, proofs, provenance, and reproducibility checks. Automated review does not substitute for human peer review; full reports, protocols, evidence, and process provenance are available in the companion repository.”

Move detailed:

- hashes;
- review-chain mechanics;
- report paths;
- session provenance;

to the artifact appendix or repository.

This makes the paper feel more like a research paper and less like an audit report.

---

# 11. Add two explicit design rules

These would improve the practical value of the paper significantly.

## Design Rule 1: Judgment invalidation

> **If remediation by control \(G_i\) can change any input consumed by control \(G_j\), the earlier judgment of \(G_j\) must be treated as invalid for the remediated action and recomputed before execution.**

## Design Rule 2: Remediation order

> **When remediation operators do not commute, their ordering is part of governance policy and must be specified, versioned, and auditable rather than left to implementation accident.**

These two sentences translate the formal contribution into architecture guidance.

---

# 12. Sharpen the conclusion around one central result

The final conclusion should not read like a list of six results.

It should tell the reader one thing to remember.

### Suggested conclusion

> The central result of this work is not that multiple governance gates should simply be aggregated conservatively. It is that once one governance control is permitted to transform the action, evidence, or context consumed by another, prior control judgments become contingent on the version of the governed object they evaluated. Correct pre-action governance therefore requires explicit semantics for invalidating and recomputing dependent judgments after remediation. When several remediation operators exist, their ordering can itself affect the final governed action, making remediation order part of governance semantics. When admitted information is promoted into persistent governance state, admission and future trust must likewise be distinguished. These results establish a bounded compositional semantics for the current setting while leaving general convergence, concurrency, delegation, and arbitrary stateful remediation as open problems.

This gives the paper a memorable conceptual center.

---

# 13. Add a “What existed / What this paper adds” novelty table

This may be the strongest defensive device against a skeptical reviewer.

| Existing concept | Established literature | What this paper adds |
|---|---|---|
| Runtime enforcement | Security/edit automata | Heterogeneous enterprise pre-action controls |
| Enforcement composition | Compositional runtime enforcement | Cross-control invalidation caused by action/evidence remediation |
| Deny-overrides / veto | XACML / policy algebra / MCDA | Not claimed as novelty; used as hard-feasibility semantics |
| Rewrite ordering | Rewriting / confluence theory | Concrete order-sensitive governance remediators |
| Stateful enforcement | History/state-based policy | Promotion of uncovered-but-admitted evidence into future remediation state |
| Audit provenance | Existing provenance mechanisms | One cross-control Evidence Set binding pre/post-remediation decisions |

This table says:

> **The contribution is not that each ingredient is new. The contribution is the specific composition problem created by their interaction.**

That is the right novelty story.

---

# 14. Get one focused human formal-methods review

This is not a request for another broad peer review.

Ask one qualified human formal-methods reviewer to challenge only three things.

## A. Arbitrary-\(n\) weighted aggregation lemma

Can the proof move from:

`pending-human-review`

to a clean human-verified proof?

## B. Theorem 1

Does the theorem state exactly what the proof establishes under A1-A7?

## C. CH7 terminology

Does the artifact establish:

- non-commutativity;
- bounded-model non-confluence;
- or both?

This is where expert human judgment adds the most value beyond automated artifact checking.

---

# 15. What NOT to add

Do not add:

- more seeds;
- another workflow;
- a third remediation operator;
- concurrent agents;
- multi-agent delegation;
- a production dataset;
- LLM experiments;
- new contamination mitigations;
- more defect classes;
- another SARC engine;
- generalized fixed-point iteration;
- arbitrary-remediator convergence;
- distributed execution.

These belong in the next SARC paper.

The current limitation that:

> stream-level concurrency and arbitrary stateful remediation remain open

is valuable.

It creates the next research question cleanly.

---

# 16. Recommended Priority

| Priority | Change | Impact |
|---|---|---|
| **P0** | Add Pinisetty/Tripakis and explicit differentiation | Very high |
| **P0** | Fix non-commutativity vs non-confluence terminology | Very high |
| **P0** | Reorder manuscript abstract | High |
| **P0** | Explicit theorem assumptions A1-A7 | High |
| **P1** | Add novelty-comparison table | High |
| **P1** | Strengthen CH6 as a state-trust result | Medium-high |
| **P1** | Add architecture design rules | Medium-high |
| **P1** | Clarify Evidence Set threat assumptions | Medium |
| **P1** | Add CI-purpose clarification | Medium |
| **P2** | Reduce automated-review narrative in manuscript | Medium |
| **P2** | Add coupling graph notation | Medium |
| **P2** | Sharpen conclusion | Medium |
| **Final** | Focused human formal proof review | Very high |

---

# 17. Target Intellectual Position

Today, the paper can still be interpreted as:

> “A very rigorous composition artifact containing several interesting governance results.”

The final version should instead read as:

> **“A paper that identifies a specific formal problem in agentic governance: governance controls become semantically coupled when one control can transform the object another already judged. It then establishes the bounded semantics needed to execute safely in that setting.”**

Every section should support that thesis.

The conceptual core is:

\[
\boxed{
\text{Remediation changes the governed object}
\Rightarrow
\text{prior judgments can become stale}
\Rightarrow
\text{dependent controls must be reevaluated}
}
\]

And with multiple remediators:

\[
\boxed{
\rho_i\circ\rho_j
\neq
\rho_j\circ\rho_i
\Rightarrow
\text{remediation order is governance semantics}
}
\]

---

# 18. Final Recommendation

No new experiments are required.

The manuscript already has enough empirical and artifact evidence for the claims it makes.

The remaining path to a 10/10 submission is to make every element of the paper point toward the same central contribution:

> **Once governance controls can transform the action, evidence, context, or state consumed by other controls, control composition becomes a semantic problem rather than merely an aggregation problem.**

If the revisions above are implemented, the manuscript should move from approximately **9.2–9.4/10** to approximately **9.7–9.8/10 before external human peer review**.

The final difference to a literal 10/10 is not another experiment. It is independent expert confirmation that the novelty boundary, terminology, and formal proofs survive serious human scrutiny.
