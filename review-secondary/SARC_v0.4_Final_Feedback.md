# Final Feedback on v0.4

I reviewed the latest repository state and paper revision again.

The **main conceptual issue from the previous review has been fixed**. The paper is now much stronger intellectually. The revised framing around remediation-induced control coupling, remediate-regate, non-commutative remediation operators, and governance-state contamination is substantially better than positioning the work primarily around non-compensatory gate aggregation.

The new `RESEARCH-GUIDE.md`, generalized-composition note, claims-versus-non-claims table, and clearer mechanism-versus-prevalence language all improve the paper and repository significantly.

I would **not run any new experiments**. The remaining work is publication cleanup rather than research redesign.

## 1. Fix the remaining CH5 Table 5 inconsistency

Section 3 now correctly distinguishes:

- **Formal quantity:** 98 Held response profiles; maximum compensated profiles = **48 / 98**.
- **Empirical quantity:** actual Held decision instances pooled across S1-S4; mean maximum compensated decisions across seeds = approximately **13,775**.

However, Table 5 still labels the empirical number as:

`ch5_max_violations (of 98 held profiles) = 13775.1`

That is visibly inconsistent because 13,775 cannot be a count “of 98 profiles.”

### Recommendation

Change the Table 5 row to something such as:

`CH5 empirical compensated held decision instances, pooled S1-S4`

or:

`Empirical max compensated held decisions, pooled S1-S4`

Keep the formal result separately as:

`Formal max compensated response profiles: 48 / 98`

No experiment or code logic needs to change. This is a labeling/presentation correction.

## 2. Complete the new Related Work citations

The new Related Work framing is much stronger, but the paper is not publication-ready while `[CITE-NEEDED]` placeholders remain.

The remaining gaps cover roughly:

- compositional runtime enforcement;
- policy-combining algorithms / Deny-overrides;
- confluence and termination in rewrite systems;
- stateful runtime enforcement.

These should be resolved through the same verified-citation pipeline already used elsewhere.

The key positioning to preserve is:

> Prior work already studies monitor composition. This paper addresses a narrower problem: heterogeneous stateful controls where one remediation changes the semantic object another control evaluates.

Likewise, XACML-style Deny-overrides helps establish that veto-style policy composition itself is prior art, reinforcing the decision not to claim the join rule as the main novelty.

### Repository recommendation

Make unresolved `[CITE-NEEDED]` placeholders a **release-check failure** for release candidates.

Ideally:

```text
cite_needed_placeholder_count == 0
```

should be mandatory before release.

## 3. Update the arXiv abstract sidecar

The main manuscript now has the correct v0.4 novelty positioning, but `paper-tex/arxiv-abstract.txt` still contains the older statement:

> “This paper studies what none answer...”

That wording reintroduces exactly the novelty problem v0.4 fixed.

### Recommendation

Regenerate `paper-tex/arxiv-abstract.txt` from the new manuscript abstract, or generate the sidecar directly from the manuscript source so the two cannot drift.

Also add a release check ensuring the sidecar abstract and manuscript abstract remain synchronized.

## 4. Update the arXiv metadata positioning

`paper-tex/arxiv-metadata.txt` still reflects the older intellectual positioning.

It should now describe the four primary contributions as:

1. remediation-induced control coupling;
2. remediate-regate under the scoped one-shot/idempotent setting;
3. non-commutative remediation operators;
4. governance-state contamination.

The join-semilattice and non-compensatory semantics should be supporting contributions.

Also remove the word **“completeness”** unless there is a precisely stated completeness theorem in the manuscript.

## 5. Consider changing the title

Current title:

> **One Gate Is Not Enough: Non-Compensatory Composition of Pre-Action Controls for Agentic AI**

The subtitle now slightly misrepresents the paper because non-compensatory aggregation is no longer the central contribution.

### Preferred title

> **One Gate Is Not Enough: Composing Stateful Pre-Action Controls for Agentic AI**

This preserves the memorable first half and aligns the subtitle with the actual paper.

Another option:

> **When Governance Controls Rewrite Actions: Composition Semantics for Agentic AI**

My preference is the first.

## 6. Clean up the v0.3 / v0.4 file-version semantics

The manuscript says v0.1/v0.2/v0.3 remain unmodified historical artifacts, but current v0.4 content lives in files still named:

- `paper4-composition-draft-v0.3.md`
- `paper4-composition-draft-v0.3-populated.md`

Git history preserves the earlier state, so this is not a scientific-integrity problem, but it is unnecessarily confusing.

### Best option

Create:

- `paper4-composition-draft-v0.4.md`
- `paper4-composition-draft-v0.4-populated.md`

and freeze v0.3 permanently.

### Minimal alternative

Change the wording to:

> “v0.1-v0.3 remain recoverable as immutable historical revisions in repository history.”

## 7. Keep the current central framing

Do **not** undo or significantly change the new framing.

The following are strong and should remain:

### Remediation-induced control coupling

The definition

\[
G_j(a) \neq G_j(\rho_i(a))
\]

for an executable-reachable action is a useful reusable concept. S4 now has a clearer conceptual role as a witness of that phenomenon.

### Three-level composition structure

The distinction between:

1. constraint composition;
2. remediation-induced control coupling;
3. remediator interaction;

gives the paper a clear intellectual progression.

### CH7 prominence

Moving non-commutativity toward the center of the argument was correct.

The architectural conclusion:

> **remediation order becomes governance semantics**

is one of the paper’s strongest messages.

### CH6 interpretation

The formulation:

> current admissibility does not imply future reference trustworthiness

is much stronger than treating CH6 only as a buffer-algorithm comparison.

### Claims-versus-non-claims

Keep this in both the paper and repository. It materially reduces reviewer misinterpretation.

### Generalized composition note

`docs/generalized-composition.md` is useful and appropriately scoped. Do not expand the current paper to solve arbitrary fixed-point convergence, general confluence, cycles, serialization, or concurrent multi-agent state. Those are appropriate future-work topics.

# Final recommendation

I would **not run more experiments** and I would **not perform another large conceptual rewrite**.

Before submission:

1. Fix the CH5 Table 5 label.
2. Resolve all new `[CITE-NEEDED]` references.
3. Update `arxiv-abstract.txt`.
4. Update `arxiv-metadata.txt`.
5. Consider changing the title to **One Gate Is Not Enough: Composing Stateful Pre-Action Controls for Agentic AI**.
6. Clean up the v0.3/v0.4 file-version convention.
7. Ideally make unresolved citations and stale arXiv sidecars detectable by `make release-check`.

After those changes, I would consider the manuscript **ready for arXiv/SSRN and appropriate for peer-review submission**.

The core research story is now:

> **Once governance controls can transform the action, evidence, or state consumed by other controls, agentic governance becomes a composition problem over constraints, transformations, and state. Correct execution therefore requires explicit semantics for re-evaluation, remediation ordering, state trust, and cross-control lineage.**

That is now the paper's real contribution, and the latest revision makes it clear.
