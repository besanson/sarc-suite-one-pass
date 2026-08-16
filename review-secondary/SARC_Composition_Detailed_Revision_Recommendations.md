# Detailed Revision Recommendations  
## *One Gate Is Not Enough: Non-Compensatory Composition of Pre-Action Controls for Agentic AI*

### Purpose of this review

This review focuses on how to strengthen the **paper and companion repository without running new experiments**.

The underlying work is strong. The repository demonstrates unusually high rigor in reproducibility, preregistration, formal checking, statistical replay, publication parity, and automated adversarial review. The remaining opportunity is primarily **conceptual positioning, claim precision, manuscript structure, and reviewer usability**.

The central recommendation is:

> **Do not add more experiments. Reframe the paper around the composition problem created when governance controls can transform actions, alter derived context, and update future governance state.**

The current manuscript contains the necessary evidence already. The goal should now be to make the intellectual contribution easier to recognize and harder to challenge.

---

# 1. Reframe the central contribution

The paper currently risks being interpreted as a paper about combining three SARC-family gates using non-compensatory semantics.

That framing is too narrow and puts disproportionate emphasis on one of the less novel parts of the work.

The stronger contribution is:

> **Once a pre-action control can modify the action it governs, governance stops being a set of independent checks and becomes a composition problem over constraints, transformations, and state.**

This should become the central thesis.

The paper should distinguish three progressively harder composition problems.

## 1.1 Constraint composition

Multiple controls judge the same action.

When controls represent hard requirements, they should behave as constraints rather than compensable preferences.

The conceptual object is a feasible region:

\[
F =
F_{\text{authority}}
\cap
F_{\text{resource}}
\cap
F_{\text{evidence}}.
\]

An action is executable only if it remains inside the intersection of the relevant hard constraints.

This provides the conceptual interpretation for the current non-compensatory join semantics.

## 1.2 Remediation-induced control coupling

The more important problem begins when a control modifies the action.

A remediation applied by one control can change variables consumed by another control.

For example:

- the evidence gate substitutes unit cost;
- unit cost changes order value;
- order value changes the authority decision;
- unit cost also changes predicted spend;
- predicted spend changes the resource decision.

This should be explicitly named.

### Proposed definition

**Remediation-induced control coupling**

Two controls \(G_i\) and \(G_j\) are remediation-coupled under remediation operator \(\rho_i\) if there exists an executable-reachable action \(a\) such that:

\[
G_j(a) \neq G_j(\rho_i(a)).
\]

This gives the paper a reusable concept independent of SARC, Green SARC, and SARC-DQ.

Scenario S4 then becomes a concrete witness of remediation-induced control coupling.

## 1.3 Remediator interaction

The next level occurs when more than one control can transform the action.

The paper already demonstrates:

\[
\rho_{\text{route}}(\rho_{\text{sub}}(a))
\neq
\rho_{\text{sub}}(\rho_{\text{route}}(a)).
\]

This should be presented as a distinct composition problem:

> **Remediation operators can interact non-commutatively, making remediation order part of governance semantics rather than an implementation detail.**

This is one of the strongest results in the current paper.

---

# 2. Change the novelty claim around composition

The introduction should not say or imply that the composition problem itself is untreated.

There is established literature on:

- compositional runtime enforcement;
- serial and parallel monitor composition;
- policy-combining algorithms;
- deny-overrides / permit-overrides;
- non-compensatory decision rules;
- stateful enforcement;
- rewrite systems and confluence.

The paper should acknowledge that directly.

A stronger and safer novelty statement is:

> **Prior research has studied the composition of enforcement monitors and policy decisions. What remains underexplored is the composition of heterogeneous, stateful pre-action controls in which one control's remediation mutates the action, evidence, or derived context evaluated by another control, thereby invalidating previously computed judgments and creating order-dependent behavior.**

This is narrower than saying "composition is untreated," but much more defensible.

It also better reflects what the artifact actually demonstrates.

The paper should be explicit that it is **not** claiming to invent monitor composition.

Instead, it studies a particular class of composition problem characterized by:

- heterogeneous control semantics;
- different control-local state;
- action mutation;
- evidence mutation;
- derived-context recomputation;
- budget state;
- governance-buffer state;
- remediation ordering;
- cross-control lineage;
- execution-time re-evaluation.

---

# 3. Strengthen the Related Work section

This is probably the most important manuscript revision before peer review.

The current related-work section should be expanded to position the contribution against adjacent areas a formal-methods, security, policy-engine, or runtime-governance reviewer is likely to know.

No new experiment is needed.

## 3.1 Compositional runtime enforcement

Add explicit discussion of work on composing runtime enforcement monitors.

The paper should acknowledge that prior work already studies questions such as:

- whether independently correct monitors remain correct when composed;
- serial composition;
- parallel composition;
- enforcement interference;
- conditions under which composition preserves properties.

Then explain the specific distinction here:

> Traditional runtime-enforcement work commonly reasons over event traces and enforcement policies. This paper studies heterogeneous pre-action controls where a remediation changes the semantic object another control subsequently evaluates.

That is the key differentiation.

## 3.2 Policy-combining algorithms

Add policy-decision composition, particularly Deny-overrides style semantics.

This matters because:

> "one veto dominates other permits"

is already a familiar policy-composition pattern.

Therefore, the paper should avoid presenting the join rule itself as the principal novelty.

The stronger statement is:

> **The difficult composition problem begins when a control response includes a transformation, not merely a decision label.**

## 3.3 Rewrite systems, confluence, and termination

CH7 naturally touches:

- confluence;
- non-commutativity;
- operator ordering;
- fixed points;
- termination;
- normal forms.

The paper does not need to become a term-rewriting paper.

However, it should explicitly state that the current work demonstrates non-commutativity for two concrete remediation operators and does **not** claim a general solution for arbitrary rewrite systems.

That will preempt an obvious theoretical objection.

## 3.4 Stateful enforcement

The resource budget and governed evidence buffer both introduce state.

The paper should connect this to stateful enforcement using a formulation such as:

\[
G(a_t,c_t,E_t,S_t)
\rightarrow
(r_t,S_{t+1}).
\]

This is especially relevant to:

- budget consumption;
- governed-buffer writes;
- future substitutions;
- potential concurrency between multiple actions or agents.

---

# 4. Reduce the emphasis on CH5 as the headline contribution

The corrected linear-family compensation lemma is valid and should remain.

However, it should not lead the paper.

There are two reasons.

First, veto semantics and non-compensatory aggregation already have established antecedents.

Second, the deeper distinction is not simply:

> min versus weighted sum.

It is:

> **constraint satisfaction versus preference aggregation.**

For hard governance requirements, the relevant structure is:

\[
F =
F_{\text{authority}}
\cap
F_{\text{resource}}
\cap
F_{\text{evidence}}.
\]

Weighted aggregation can still be useful when selecting among feasible alternatives, but it should not override hard requirements unless the governance design explicitly allows that.

A better interpretation of CH5 is therefore:

> **Additive preference aggregation is not a substitute for conjunctive feasibility semantics when member controls are intended to have veto authority.**

The existing linear threshold lemma then adds precision by showing exactly when a weighted linear aggregator does or does not preserve veto semantics.

This is a strong supporting result, but it should not dominate the paper.

---

# 5. Move CH7 earlier and give it more prominence

CH7 is one of the strongest results in the manuscript.

The result:

\[
\rho_{\text{route}}(\rho_{\text{sub}}(a))
\neq
\rho_{\text{sub}}(\rho_{\text{route}}(a))
\]

is not merely another empirical observation.

It establishes that:

> **operator ordering becomes part of the control-plane semantics.**

The current evidence is already substantial:

- exhaustive finite-grid analysis;
- concrete counterexample;
- additional fixed off-grid probe;
- direct reuse of the actual remediation functions.

No additional experiment is necessary.

The contribution order should probably become:

1. remediation-induced control coupling;
2. single-pass unsoundness under remediation;
3. remediate-regate semantics;
4. multi-remediator non-commutativity;
5. stateful evidence-buffer contamination;
6. non-compensatory feasibility semantics;
7. unified Evidence Set;
8. no manufactured coverage.

This creates a much more coherent research narrative.

---

# 6. Clarify what fixed remediation ordering solves

The paper correctly shows that the two implemented remediators do not commute.

A fixed order is therefore required for deterministic behavior.

However:

> **A fixed order is not a general solution to arbitrary multi-remediator composition.**

Suppose the system contains:

\[
\rho_1,\rho_2,\rho_3.
\]

It is possible that applying \(\rho_3\) makes \(\rho_1\) relevant again.

The resulting sequence could be:

\[
a_0
\rightarrow
\rho_1(a_0)
\rightarrow
\rho_2(a_1)
\rightarrow
\rho_3(a_2)
\rightarrow
\rho_1(a_3)
\rightarrow \dots
\]

The current paper does not solve:

- arbitrary non-idempotent remediators;
- cycles;
- global termination;
- unique fixed points;
- confluence across arbitrary operators;
- concurrent state updates;
- serializability across multiple agents.

That is acceptable.

The manuscript should make the boundary explicit:

> **This work establishes a sound one-shot composition protocol for the implemented idempotent setting and demonstrates why general multi-remediator systems require an explicit termination and confluence theory.**

That is a strong research boundary.

### Suggested future-work formulation

Generalized remediation could be written as:

\[
a_{t+1}=R(a_t)
\]

until either:

\[
a_{t+1}=a_t
\]

or the action reaches a Held state.

The natural properties for future work are:

- termination;
- cycle detection;
- confluence;
- unique normal forms;
- monotonicity;
- state serializability;
- concurrent-agent coordination.

Again, none of this requires new experiments for the current paper.

---

# 7. Clarify the five-response lattice

The current operational ordering is:

\[
admit < substitute < degrade < escalate < block.
\]

This works for the implementation, but it should not be presented as a universal semantic ordering.

A reviewer can reasonably challenge whether:

\[
substitute < degrade
\]

is always meaningful.

In one domain, substitution may represent a major intervention while degradation may be minor.

For the main safety property, the most important distinction is:

\[
Exec=\{admit, substitute, degrade\}
\]

versus:

\[
Held=\{escalate,block\}.
\]

The manuscript should therefore state explicitly:

1. the Exec/Held partition is the load-bearing distinction for execution safety;
2. the five-level total order is an operational policy used by this composition plane to produce a single response;
3. other systems could use a different or partially ordered response structure while preserving the same execution-safety requirement.

This makes the model harder to attack without changing the implementation or results.

---

# 8. Fix the CH5 formal-versus-empirical metric presentation

This should be corrected before publication.

There are currently two different CH5 quantities.

## 8.1 Formal checker quantity

The formal response space contains:

- 125 total three-gate response profiles;
- 98 Held profiles.

The maximum number of Held response profiles compensated by one weight/threshold cell is:

> **48 out of 98 Held profiles.**

## 8.2 Empirical sweep quantity

The statistical sweep runs CH5 against actual held **decision instances** pooled across S1-S4.

That produces a mean around:

> **13,775 compensated held decision instances.**

Both quantities are valid.

However, they should not be labeled as though they use the same denominator.

### Recommended paper-facing terminology

Use two separate labels:

**Formal result**

> Maximum compensated response profiles: **48 / 98 Held response profiles**

**Empirical result**

> Maximum compensated held decision instances, pooled S1-S4: **approximately 13,775 mean across seeds**

Avoid using the same manuscript-facing name for both.

For example:

- `formal_compensated_profiles`
- `empirical_compensated_decisions`

The code does not need to change if that would create unnecessary churn.

The paper and generated table labels should change.

---

# 9. Improve the interpretation of CH6

The strongest conceptual point in the buffer-poisoning section is not simply that two mitigation strategies reduce poisoning.

It is:

> **A record can be admissible under current predicates without being safe to promote into future governance state.**

Formally:

\[
\text{current admissibility}
\not\Rightarrow
\text{future reference trustworthiness}.
\]

That is an important architecture-level observation.

The section should be structured around the mechanism:

1. the governance buffer accepts writes from admitted observations;
2. an uncovered defect can therefore enter trusted state;
3. future substitutions can reuse that contaminated state;
4. the vulnerability is created by the interaction between incomplete coverage and stateful remediation;
5. quarantine and median filtering are example mitigation strategies.

This interpretation is broader and stronger than presenting CH6 as a comparison of buffering algorithms.

---

# 10. Preserve the W2 negative result, but sharpen the language

The W2 negative result is a strength.

It demonstrates that the paper is willing to report when a preregistered decision rule does not hold.

The wording should remain precise.

Recommended formulation:

> **The preregistered seed-by-seed decision rule is not supported under W2 because the lower substitution population produces seeds with zero baseline poisoning events, making strict per-seed reduction impossible to satisfy on those seeds. This limits the robustness claim for W2; it does not establish that the mitigation mechanism is ineffective.**

Avoid wording that sounds as though the negative result has been explained away.

The result should remain a real limitation of the registered robustness claim.

---

# 11. Clarify confidence intervals for low non-negative counts

Some symmetric t-intervals for low-count non-negative metrics extend slightly below zero.

This is mathematically possible for a symmetric confidence interval around a sample mean.

It can nevertheless look odd to reviewers because the underlying metric cannot be negative.

No new experiment is required.

Possible options:

1. keep the current intervals and explicitly note that symmetric t-intervals can extend below the support boundary;
2. truncate the displayed interval at zero, clearly labeling that as presentation-only truncation;
3. compute a bootstrap interval from the already committed 30 seed summaries.

Option 3 would be a recomputation, not a new experiment.

If avoiding any regeneration is important, Option 1 is completely acceptable.

---

# 12. Strengthen mechanism-versus-prevalence language

The paper already acknowledges that it is a mechanism demonstration.

This distinction should be made systematic.

### CH2 supports

> Single-pass unsoundness **can occur** after remediation.

It does not establish:

> how frequently production systems suffer this failure.

### CH6 supports

> buffer poisoning **can propagate** through governed remediation state.

It does not establish:

> enterprise prevalence of such poisoning.

### CH7 supports

> these two remediation operators **do not commute**.

It does not establish:

> arbitrary remediation operators are non-commutative.

This distinction should be maintained consistently across:

- abstract;
- contributions;
- empirical results;
- limitations;
- conclusion.

---

# 13. Strengthen the conclusion

The conclusion should not primarily recap CH1-CH8.

It should state the architecture lesson.

A stronger conclusion would be structurally similar to:

> **Pre-action governance cannot be treated as a bag of independent checks once controls are permitted to transform the proposed action or update shared governance state. Correct composition must distinguish hard feasibility from preference aggregation, reevaluate dependent controls after remediation, define remediation order when operators do not commute, and preserve the provenance of the action and evidence actually executed.**

Then state the open theory:

> **General termination, confluence, and concurrency for arbitrary stateful remediation systems remain open.**

That is a much stronger ending than a result inventory.

---

# 14. Recommended paper structure

The CH numbering should not drive the intellectual structure of the manuscript.

A stronger structure would be:

## 1. Introduction

Lead with the key problem:

> **A control that changes the action can invalidate the decisions of controls that evaluated the pre-remediation action.**

## 2. Model and terminology

Define:

- action;
- derived context;
- evidence;
- state;
- control/gate;
- execution status;
- remediation operator;
- remediation-induced control coupling.

## 3. Hard constraints versus compensatory aggregation

Keep the compensation lemma here as supporting theory.

## 4. Single-remediator composition

Introduce the single-pass failure and S4.

Then introduce remediate-regate.

## 5. Multi-remediator composition

Make CH7 a major section.

## 6. Stateful governance and evidence-buffer contamination

CH6.

## 7. Unified Evidence Set

Provenance and integrity.

## 8. Empirical validation

Bring together CH1-CH8 as evidence for mechanisms introduced earlier.

Do not make CH1-CH8 themselves the conceptual narrative.

## 9. Related work

Expand around:

- runtime enforcement;
- compositional runtime enforcement;
- policy combination;
- veto/non-compensatory decision rules;
- rewrite systems/confluence;
- stateful enforcement;
- trust-on-first-use / poisoning analogies.

## 10. Limitations and open theory

Include:

- arbitrary remediator convergence;
- concurrency;
- state serialization;
- external validity;
- prevalence.

## 11. Conclusion

End on the architectural principle, not the experiment list.

---

# 15. Suggested revised contribution statement

The current contribution list can be simplified substantially.

A stronger version would be:

> **This paper makes four primary contributions. First, it formalizes remediation-induced control coupling: a pre-action control that transforms an action can invalidate another control's earlier judgment. Second, it gives and evaluates a remediate-regate composition protocol for the current idempotent setting, under which every executing action is re-evaluated by all member controls after remediation. Third, it shows that heterogeneous remediation operators need not commute, making remediation order part of the control-plane semantics rather than an implementation detail. Fourth, it demonstrates that governance state itself can become contaminated when admissible but uncovered defects are promoted into future remediation state, motivating explicit trust policies for state updates. Non-compensatory join semantics, unified evidence lineage, and coverage-preservation results support these primary contributions.**

This is more coherent than presenting eight contributions at equal conceptual weight.

---

# Repository recommendations

The repository is already strong.

The goal should not be to add more validation machinery.

The goal should be to make the intellectual structure easier for an external reviewer to inspect.

---

# 16. Add a reviewer-oriented research guide

Create:

`RESEARCH-GUIDE.md`

The README is primarily artifact-oriented.

The new file should be research-reviewer-oriented.

It should answer:

- What is the research question?
- What is new?
- What is not claimed?
- Which claims are formal?
- Which claims are construction-only?
- Which claims are empirical?
- What file supports each claim?
- What should a reviewer run first?
- What remains out of scope?

Suggested structure:

## Research question

One paragraph.

## Primary contributions

Four contributions, following the revised framing above.

## Claims and evidence

| Claim | Research question | Evidence |
|---|---|---|
| Remediation-induced coupling | Can one control invalidate another control's prior decision? | S4 + Proposition 3 |
| Remediate-regate | Can the implemented one-shot protocol restore per-action soundness? | Theorem 1 + CH1 |
| Non-commutativity | Does remediation order matter? | CH7 checker |
| Buffer poisoning | Can uncovered defects contaminate future governance state? | CH6 |
| Non-compensation | Can additive aggregation violate hard-veto semantics? | Lemma + CH5 |
| Unified lineage | Can one record preserve cross-control decision identity? | schema + Evidence Set |

## Scope boundaries

Short list.

## Reproduction entry points

- `make test`
- `make suite`
- `make formal`
- `make paper`
- `make release-check`

This will dramatically reduce external reviewer effort.

---

# 17. Add a claims-versus-non-claims table

This should exist in both the paper and repository.

Example:

| The paper claims | The paper does not claim |
|---|---|
| Single-pass can be unsound after remediation | All single-pass systems are unsound |
| The implemented remediators are non-commutative | All remediation operators are non-commutative |
| Remediate-regate is sound in the current one-shot setting | General convergence of arbitrary remediator systems |
| Buffer poisoning exists in the demonstrated mechanism | Production prevalence |
| Composition preserves only member-control coverage | Composition guarantees complete safety |
| Evidence Sets preserve identity commitments | Hashes alone reconstruct source bytes |
| Hard controls require non-compensatory feasibility semantics | Weighted scoring is never useful |

This table would materially reduce reviewer misunderstanding.

---

# 18. Improve result terminology

Several internal metric names are correct for code but potentially confusing in the manuscript.

Paper-facing terminology should distinguish:

- response-string difference;
- Exec/Held divergence;
- audited execution violation;
- label-only difference;
- formal response profile;
- empirical decision instance.

CH2 already makes this distinction internally.

The manuscript should make it visually explicit.

For CH5 in particular, distinguish:

- formal compensated profiles;
- empirical compensated decisions.

---

# 19. Add a composition-dependency diagram

A conceptual diagram would improve the paper substantially without adding any experiment.

Suggested structure:

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

For W2:

```text
Evidence substitution
        |
        v
Recompute context
        |
        v
Resource feasibility
        |
        v
Downroute if required
        |
        v
Recompute context
        |
        v
Full regate
```

The visual should emphasize:

> **remediation changes inputs consumed by other controls.**

That is the paper's strongest intuitive argument.

---

# 20. Add a remediator dependency graph

A second, simpler design diagram could expose why non-commutativity occurs.

Example:

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

This shows immediately that both remediators affect variables consumed by downstream controls.

The graph also suggests a more general future architecture:

> remediation order should be derived from dependency relationships rather than treated as arbitrary orchestration.

The current paper does not need to solve that generalized problem.

---

# 21. Add a generalization design note

Create:

`docs/generalized-composition.md`

This should be deliberately framed as future work, not an additional claim.

Describe the current certified scope:

- finite response lattice;
- one-shot evidence substitution;
- one resource downroute operator;
- fixed remediation order;
- per-action soundness;
- no general concurrency theorem.

Then describe the generalized model:

\[
(a_t,S_t)
\rightarrow
R(a_t,S_t)
\]

and identify the future properties:

- fixed-point semantics;
- termination;
- confluence;
- cycle detection;
- state consistency;
- serialization;
- concurrent multi-agent coordination.

This strengthens the research program without changing the paper's current evidence.

---

# 22. Add a concise repository map

The repository is rigorous but cognitively dense.

Add a simple map to the README:

```text
Paper
  paper4-composition-draft-v0.3-populated.md
  paper-tex/

Formal claims
  appendix-a-proofs.md
  checkers/

Composition implementation
  composition.py

Experiments
  runner.py
  sweep.py
  contamination.py
  ch5_aggregator.py

Pre-registration
  prereg/

Generated results
  out/

Independent automated reviews
  review/
  review-r2/
  review-r3/
  review-r4/
```

This will help a human reviewer orient immediately.

---

# 23. Make publication integrity easier to inspect

Add a short README section titled:

## Publication integrity

Keep it brief.

Include:

- preregistration tag;
- pinned engines;
- generated result tables;
- formal checkers;
- citation validation;
- Markdown/LaTeX parity;
- automated external review disclosure;
- mandatory `make release-check`.

Do not overemphasize automated review in the paper itself.

The existing disclosure that automated review complements rather than replaces human peer review is the right posture.

The automated review chain is valuable evidence of reproducibility, but it should not appear to substitute for scholarly peer review.

---

# 24. What should *not* be done

The following changes are **not recommended** at this stage:

- no additional stochastic seeds;
- no third workflow;
- no extra defect classes;
- no additional remediation operator;
- no new benchmark;
- no production connector;
- no LLM-based experiment;
- no broader enterprise simulation merely to increase paper size;
- no attempt to generalize the current theorem beyond what is actually certified;
- no attempt to turn CH7 into a full rewriting-systems theory in this manuscript.

Those additions would increase complexity without addressing the main reviewer risk.

The paper already has enough evidence.

The next improvement should come from better theoretical framing and scholarly positioning.

---

# 25. Priority order

If time is limited, make the changes in this order.

## Priority 1 — Must fix before peer-review submission

1. Remove any broad claim that the composition problem is untreated.
2. Expand related work on compositional runtime enforcement and policy combination.
3. Fix the CH5 formal-versus-empirical metric labeling.
4. Elevate remediation-induced coupling and CH7.
5. Clarify that the response lattice is an operational ordering.
6. Strengthen mechanism-versus-prevalence language.

## Priority 2 — Strongly recommended

7. Rewrite the contribution list around four primary contributions.
8. Strengthen the conclusion.
9. Add a claims-versus-non-claims table.
10. Add the composition-dependency diagram.
11. Add `RESEARCH-GUIDE.md`.

## Priority 3 — Useful repository improvements

12. Add the remediator-dependency graph.
13. Add `docs/generalized-composition.md`.
14. Add the concise repository map.
15. Add the Publication Integrity README section.

---

# Final assessment

The underlying research does **not** need another experiment.

The artifact already demonstrates:

- strong preregistration discipline;
- deterministic replay;
- exhaustive finite checks;
- multi-seed robustness;
- explicit negative results;
- durable lineage;
- automated adversarial replication;
- publication-generation integrity.

The remaining issue is intellectual positioning.

The strongest version of the paper is not:

> **Three governance gates should be combined using min semantics.**

It is:

> **Once governance controls can transform the action, evidence, or state on which other controls depend, agentic governance becomes a composition problem over constraints, transformations, and state. Correct execution therefore requires explicit semantics for re-evaluation, remediation ordering, state trust, and cross-control lineage.**

That is the contribution around which the paper should now be organized.

With those changes, the paper becomes narrower in claim scope but substantially stronger in novelty, coherence, and defensibility.
