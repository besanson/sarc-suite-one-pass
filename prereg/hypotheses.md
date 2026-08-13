# Pre-registered Hypotheses CH5-CH8

Status: PRE-REGISTRATION. Definitions only — no results. Tagged `prereg-v1`.

CH1-CH4 carry over unchanged from the prior (8.5) artifact, under the
CH2 semantics redefinition in `ch2-semantics.md`. This file adds CH5-CH8,
transcribed verbatim from the task specification that pre-registered them.

## CH5 (compensation is empirically unsafe)

Decision rule: over the declared weight grid, there exists at least one
weight vector whose weighted-score aggregator admits at least one decision
that a member gate held, while the min join admits zero such decisions.
Report the violation count surface over the grid.

Grid, score encoding, and thresholds: `weights.json`.

## CH6 (buffer contamination is real and mitigable)

With the new upward-corruption class active, the plain refresh-on-admit
buffer produces at least one poisoned substitution (a substitution whose
value derives from an uncovered-class admit). Direction registered: both
mitigations reduce the poisoned-substitution count relative to plain;
magnitudes are reported with CIs, not registered.

Definitions: `contamination.md`.

## CH7 (multi-remediator order dependence)

With two remediation operators active, evidence substitution and resource
downroute quantity scaling, either order-independence (confluence) holds
across the exhaustive finite model and the empirical grid, or at least
one concrete non-confluent instance exists. Two-sided registration; the
decision rule is the checker's output; report whichever obtains with the
instance or the coverage of the check.

Checker: `checkers/remediator_check.py` (Phase 4). The checker's verdict
IS CH7's registered decision rule — this is not a claim the paper argues
for informally, it is read off the checker's output.

## CH8 (robustness)

The CH1 to CH4 qualitative conclusions hold in both workflows across all
30 seeds; report CIs. The threshold sensitivity study (freshness
max_age_days and authority cap sweeps) is registered as descriptive:
report the false-hold versus missed-defect frontier without a directional
bet.

Seeds: `seeds.json`. Workflows: W1 (existing daily replenishment) and W2
(`w2-workflow.md`).

## Registration discipline

- No experiment code implementing CH5-CH8 may run before this file, plus
  `seeds.json`, `weights.json`, `w2-workflow.md`, `contamination.md`,
  `renaming.md`, `ch2-semantics.md`, and `schemas/evidence_line.schema.json`
  are committed and tagged `prereg-v1`.
- Every later result's manifest records the `prereg-v1` commit sha
  (`manifest.py` / `out/metrics.json`).
- A test asserts the `prereg-v1` tag's tree contains no results (no
  `out/`, no populated paper draft, no `out/quality.json` at that commit).
- CH8's sensitivity study and CH6's mitigation magnitudes are explicitly
  registered as descriptive / non-directional — reported with CIs, not
  claimed as a specific effect size ahead of time.
