# Buffer Contamination Study (pre-registration)

Status: PRE-REGISTRATION. Definitions only — no results.

ADR-001's Repair section already documented an emergent property of the
8.5 build: the governed buffer refreshes on any DQ "admit" response, and
`plausible_outlier` is *designed* to admit while carrying a corrupted
value — so an uncovered-class admit can transiently write a wrong value
into the buffer, which a later substitution then reads back out. This
study promotes that observation from an ADR footnote to a registered,
measured hypothesis (CH6), with a new declared defect class that makes
the effect deliberately easy to trigger, a defined metric, and two
candidate mitigations.

## New declared class: `plausible_outlier_high`

`unit_cost x 2.5`, clean fresh metadata (`as_of_day == retrieved_day`),
clean lineage (non-empty `source`) — structurally identical to the
existing `plausible_outlier` recipe (Appendix B), added as a **second,
independent** declared-uncovered class at the same per-class injection
probability (0.02) alongside the existing seven, so its contamination
effect can be measured without perturbing the existing CH4 per-class
rates for the original seven. (The existing `plausible_outlier` also
contaminates the buffer identically; `plausible_outlier_high` is
registered separately so the contamination scenarios can isolate the
mechanism without touching the CH4-measuring S1 scenario's class mix.)

## Poisoned-substitution metric

For every decision whose evidence gate response is `quarantine_substitute`
(a "substitution" in composed-response terms), the metric asks: does the
buffer value used for that substitution trace back to a *prior* admitted
decision, for the same SKU, whose own injected class was an
uncovered-by-DQ class (`plausible_outlier` or `plausible_outlier_high`)?

Formally: the buffer write history for a SKU is a sequence of
`(decision_id, injected_defect, written_value)` tuples, one per admitted
decision for that SKU, in decision order. A substitution at decision `d`
is **poisoned** iff the most recent buffer write for that SKU strictly
before `d` came from a decision whose `injected_defect` was
`plausible_outlier` or `plausible_outlier_high`. This is computable
purely from `run_log.jsonl`'s ground-truth labels — never from inside
the gate itself (the gate never reads ground truth; the metric is a
post-hoc audit over the run log, exactly like the CH1 post-hoc audit is
computed outside the gate).

Reported per scenario: poisoned-substitution **count**, and the mean
absolute value delta (`|poisoned_buffer_value - true_cost|`) of the
poisoned substitutions, both with 95% CIs over the 30-seed list (V3).

## Mitigations (registered, to be implemented in Phase 3)

1. **Quarantine window**: a buffer write becomes eligible for
   substitution only after K=3 subsequent *consistent* clean admitted
   reads for that SKU (consistent: within a small declared tolerance of
   each other, since floating-point reads of the same true cost are
   exactly equal in this simulation's economics — any deviation signals
   a different value was read). Until eligible, substitution falls back
   to the prior eligible value (or blocks, if none exists yet — the same
   "no governed substitute available" fallback the real
   `sarc_dq.gate.GovernedBuffer` already exhibits).
2. **Median-of-3**: substitute the median of the last three *eligible*
   buffer values for that SKU (eligible meaning: written by an admitted
   decision), rather than only the most recent one. Requires keeping a
   short rolling history per SKU instead of a single scalar.

Both mitigations are implemented **outside** the real `sarc_dq.gate`
package (as this repo's own buffer-wrapping adapter, clearly labelled as
such, not as a modification to the engine) — the engine repos remain
untouched per the standing invariant.

## Scenarios

`plain` (existing refresh-on-admit `GovernedBuffer`, unmodified),
`quarantine` (mitigation 1), `median_of_3` (mitigation 2) — each run over
the full 30-seed list, both workflows.

## Decision rule (CH6, restated from hypotheses.md)

Registered: `plain` produces >= 1 poisoned substitution (existence
claim, direction of the *contamination* finding). Registered: both
`quarantine` and `median_of_3` produce a strictly lower poisoned-
substitution count than `plain` on every one of the 30 seeds (direction
of the *mitigation* finding). NOT registered: which mitigation performs
better than the other, or by how much — those are descriptive, reported
with CIs.
