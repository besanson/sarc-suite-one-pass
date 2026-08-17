# Research Guide

Companion guide for the paper *One Gate Is Not Enough: Composing
Stateful Pre-Action Controls for Agentic AI*.

The [README](README.md) is artifact-oriented: it gets a reproduction
environment running. This file is reviewer-oriented: it answers the
questions a research reviewer asks before running anything at all.

## Research question

Once a pre-action governance control is permitted to transform the
action it governs -- not just approve or block it -- governance stops
being a set of independent checks and becomes a composition problem
over constraints, transformations, and state. What are the correct
semantics when one control's remediation changes the action, evidence,
or derived context another control evaluates; when more than one
control can remediate the same action; and when governance state
itself persists and can be corrupted by an earlier admitted decision?

## What is new

Prior work studies the composition of enforcement monitors and policy
decisions. This artifact studies a narrower, underexplored problem:
composition of heterogeneous, stateful pre-action controls, where one
control's remediation mutates the action, evidence, or derived context
another control evaluates -- invalidating earlier judgments and
creating order-dependent behavior. Monitor composition itself is not
claimed as an invention; see the paper's Related Work section and the
claims-versus-non-claims table below for the precise boundary.

## Novelty comparison

What existed and what this paper adds, summarized across the paper's
Related Work section:

| Existing concept | Established literature | What this paper adds |
|---|---|---|
| Runtime enforcement | Security/edit automata | Heterogeneous enterprise pre-action controls |
| Enforcement composition | Compositional runtime enforcement | Cross-control invalidation caused by action/evidence remediation |
| Deny-overrides / veto | XACML / policy algebra / MCDA | Not claimed as novelty; used as hard-feasibility semantics |
| Rewrite ordering | Rewriting / confluence theory | Concrete order-sensitive governance remediators |
| Stateful enforcement | History/state-based policy | Promotion of uncovered-but-admitted evidence into future remediation state |
| Audit provenance | Existing provenance mechanisms | One cross-control Evidence Set binding pre/post-remediation decisions |

The contribution is not that each ingredient above is new; it is the
specific composition problem created by their interaction.

## What is not claimed

- Production prevalence of any mechanism this artifact demonstrates.
- General termination, confluence, or convergence for arbitrary
  multi-operator remediation systems (see
  [`docs/generalized-composition.md`](docs/generalized-composition.md)
  for what such a claim would require).
- That the implemented five-level response ordering
  (`admit < substitute < degrade < escalate < block`) is a universal
  semantic ordering; it is this composition plane's own operational
  policy for producing a single response, and the `Exec`/`Held`
  partition is the load-bearing execution-safety distinction.
- That weighted/additive scoring is never useful; only that it is not
  a substitute for conjunctive feasibility semantics when member
  controls are meant to hold veto authority.

## Primary contributions

1. **Remediation-induced control coupling, formalized.** A pre-action
   control that transforms an action can invalidate another control's
   earlier judgment on that action. Scenario S4 is a concrete witness.
2. **Remediate-regate composition protocol**, evaluated for the
   current idempotent setting: every executing action is re-evaluated
   by every member control after remediation, restoring per-action
   soundness that single-pass evaluation lacks.
3. **Remediator non-commutativity**: heterogeneous remediation
   operators need not commute, making remediation order part of the
   control-plane semantics rather than an implementation detail (CH7).
4. **Governance-state contamination**: governance state can become
   contaminated when an admissible but uncovered defect is promoted
   into future remediation state, motivating explicit state-trust
   policies rather than treating "currently admissible" as
   "trustworthy forever" (CH6).

Non-compensatory join semantics, unified evidence lineage, and
coverage-preservation results support these four primary contributions
without being the paper's central claim.

## Claims and evidence

| Claim | Research question | Evidence |
|---|---|---|
| Remediation-induced coupling | Can one control invalidate another control's prior decision? | S4 + Proposition 3 |
| Remediate-regate | Can the implemented one-shot protocol restore per-action soundness? | Theorem 1 + CH1 |
| Non-commutativity | Does remediation order matter? | CH7 checker (`checkers/remediator_check.py`) |
| Buffer poisoning | Can uncovered defects contaminate future governance state? | CH6 (`contamination.py`) |
| Non-compensation | Can additive aggregation violate hard-veto semantics? | Lemma (linear family) + CH5 (`checkers/compensation_check.py`) |
| Unified lineage | Can one record preserve cross-control decision identity? | `schemas/evidence_line.schema.json` + Evidence Set |

This table names research questions and their evidence at a glance; the
paper's own Claims to Evidence table (Section 8) is the authoritative,
tag-carrying version -- every `machine-checked`, `checked-scope-only`,
and `pending-human-review` classification lives there and in
`appendix-a-proofs.md`, verified by `checkers/proof_status_lint.py` on
every build.

## Claims versus non-claims

| The paper claims | The paper does not claim |
|---|---|
| Single-pass can be unsound after remediation | All single-pass systems are unsound |
| The implemented remediators are non-commutative | All remediation operators are non-commutative |
| Remediate-regate is sound in the current one-shot setting | General convergence of arbitrary remediator systems |
| Buffer poisoning exists in the demonstrated mechanism | Production prevalence |
| Composition preserves only member-control coverage | Composition guarantees complete safety |
| Evidence Sets preserve identity commitments | Hashes alone reconstruct source bytes |
| Hard controls require non-compensatory feasibility semantics | Weighted scoring is never useful |

## Scope boundaries

- Two remediation operators, fixed order, one-shot (not iterated to a
  general fixed point).
- Per-action soundness, not stream-level ordering across actions.
- A mechanism demonstration on open payload data with a declared
  synthetic metadata layer -- not a prevalence study, not a live
  GIGO-Bench release, not the proprietary Suite.
- See `docs/generalized-composition.md` for the generalized model this
  scope stops short of, and why.

## Reproduction entry points

What a reviewer should run, in order:

```
make bootstrap       # pin the three engines + toolchain
make test             # full test suite
make suite             # the four scenarios, both composition modes
make formal            # V2 gate: exhaustive checkers
make paper              # regenerate the populated paper from committed outputs
make release-check       # the mandatory composite gate -- run this last
```

`make release-check` is the single command that verifies everything
this guide claims is checkable: the full test suite (including
inputs-hash freshness and seed replay against committed artifacts), a
formal-checker double-run byte-identity check, and the arXiv build gate
(compiler-aware publication parity, G1-G6). See the paper's own
Publication Integrity discussion in the README for what each of those
gates actually verifies.
