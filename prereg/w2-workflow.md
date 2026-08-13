# W2: Weekly Commitment Workflow (pre-registration)

Status: PRE-REGISTRATION. Definitions only — no results.

The existing decision stream (W1) commits a replenishment quantity once
per (day, SKU). W2 is a second, structurally different workflow used to
test CH7 (multi-remediator order dependence) and CH8 (robustness across
workflows).

## Action

Once per 7 simulated days, per SKU, commit a **weekly** order quantity: a
7-day-ahead newsvendor quantity computed from the same trailing demand
history used by W1 (unchanged quantile rule), evaluated once at the start
of each 7-day window rather than daily. All other days in the window
produce no W2 decision for that SKU.

## Authority

A weekly order-value cap (distinct numeric value from W1's daily cap,
calibrated the same generated way — from the real weekly order-value
distribution, not hand-picked) and a role allowlist **distinct from W1**
(different role names), so W2's authority axis is independently
verifiable from W1's.

## Resource

Weekly cost and carbon budgets, sized (generated from the real weekly
predicted-cost/-carbon distribution, as W1's scenario budgets are) so
that Green SARC's **downroute** path fires on a known subset — this is
new: W1 never produces `downroute` because nothing in W1 scales quantity
down. W2 is the vehicle for exercising the second remediation operator.

## Evidence

The same unit-cost record family and injector as W1 (all seven declared
classes, including the new `plausible_outlier_high` from
`contamination.md`), applied identically per decision.

## The second remediation operator: downroute

`green_sarc`'s `Verdict.DOWNROUTE` ("too expensive for this route, try a
cheaper one") is realized here as: **scale the committed quantity down to
the largest quantity whose predicted cost and carbon both fit the
remaining weekly budget**, recompute context from the scaled quantity,
and re-gate all three gates on the scaled action — the same
remediate-and-re-gate pattern Theorem 1 already establishes for evidence
substitution, applied to a second, independent remediator.

This makes W2 the substrate where **two** remediators can both fire on
the same decision: DQ substitution (evidence gate, corrects a value) and
downroute (resource gate, corrects a quantity). CH7 asks whether
composing them is order-independent.

## Interaction with the rename

Per `renaming.md`, the two-phase protocol is renamed `remediate_regate`
("rtr") throughout. Under W2, `remediate_regate` generalizes from
"evaluate the evidence gate, remediate once, re-gate everything" to
"evaluate remediating gates in a fixed declared order (evidence gate,
then resource gate), remediate at each stage that fires, re-gate
everything on the final remediated action." `checkers/remediator_check.py`
(Phase 4) checks whether this fixed order matters (confluence) or not.
