# CH2 Semantics Redefinition (pre-registration)

Status: PRE-REGISTRATION. Definitions only — no results. This resolves
the prior (9.5) review's major finding on the 8.5 build.

## The finding

In the 8.5 artifact, `ch2_divergent_decisions` counted every S4 decision
where `remediate_regate` (then named `two_phase`) and `single_pass`
produced a different **response string** (e.g. `"admit"` vs
`"substitute"`). Inspecting the actual S4 output showed roughly half of
these divergences were trivial: both protocols executed the decision
(both responses are Exec-class), and the *only* reason the strings
differed is that `remediate_regate`'s Phase II re-evaluates the DQ gate
on the already-clean, already-substituted evidence (so it reads
`"admit"`), while `single_pass` reports its own one-shot `"substitute"`
response directly. Nothing about Proposition 3's cap-based unsoundness
mechanism is present in these cases — `pre_order_value == post_order_value`
for every one of them, and the post-hoc audit never flags them. Folding
these into `ch2_divergent_decisions` alongside the genuine
Proposition-3 cases (`pre_order_value != post_order_value`, real
authority-cap unsoundness) inflated the headline count without being
false — CH2 as originally worded ("verdicts differ on at least one
decision") was technically satisfied either way — but conflated a
structural labeling artifact with the substantive claim the section
argues for.

## Redefinition

A decision is **divergent** (counts toward `ch2_divergent_decisions`)
iff at least one of:

1. **Exec/Held class change**: `remediate_regate`'s `final.admitted`
   differs from `single_pass`'s `final.admitted` (one executes, the
   other holds) — this is the substantive case Definition 1's
   Exec = {admit, substitute, degrade} / Held = {escalate, block}
   partition is built around.
2. **Audited violation**: both protocols execute the decision (same
   Exec/Held class), but the post-hoc audit (R4 mechanism, unchanged)
   flags a violation for `single_pass`'s executed action — this is the
   case where the *value* silently drifted past a gate even though
   both protocols nominally "let it through."

A decision where both protocols are in the same Exec/Held class, the
response *strings* differ (e.g. `admit` vs `substitute`,
or `admit` vs `degrade`), and the audit finds no violation, is a
**label-only difference** — still real (it is an accurate description
of what each protocol's own join produced), but reported as a **separate,
non-CH2 metric**: `label_only_differences` (count, per scenario, in
`out/metrics.json`), not folded into `ch2_divergent_decisions`.

## Direction counts under the new definition

`ch2_direction_counts` keeps its two existing keys
(`single_pass_admits_then_violates`, `single_pass_holds_remediated_compliant`)
with unchanged meaning (both were already audit-based, so the
redefinition does not change how they are computed — it changes what
denominator `ch2_divergent_decisions` counts against). Every decision
that populates either direction key is, by construction, already a
divergent decision under the new rule 1 or rule 2 above, so no direction
count can ever exceed `ch2_divergent_decisions`.

## CH2 decision rule (restated for Phase 3, under the new semantics)

Unchanged from the original wording: "single-pass and two-phase
[remediate_regate] verdicts differ on at least one decision, in the
predicted direction" — but "differ" now means divergent under this
file's definition, and the S4 headline number reported in the paper is
`ch2_divergent_decisions` (substantive) with `label_only_differences`
reported alongside it, not silently absorbed.

## Implementation note (for Phase 3, not executed here)

`metrics._ch2` gains a class-change check
(`tp_line["final"]["admitted"] != sp_line["final"]["admitted"]`) ahead of
the string-equality check, and every S4 line pair that differs only in
response string with matching Exec/Held class and a clean audit is
routed into a new `label_only_differences` counter instead of
`ch2_divergent_decisions`.
