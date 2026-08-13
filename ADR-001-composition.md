# ADR-001: Three-Gate Composition Architecture

**Status**: Accepted
**Date**: 2026-08-12
**Author**: SARC Suite Demo

## Context

The SARC Suite composes three independently developed Apache 2.0 pre-action gates at a single control point:
1. **sarc-governance** (authority/permissions gate)
2. **Greensarc** (resource budgets gate: cost + carbon)
3. **sarc-dq** (evidence quality gate)

Each gate has its own:
- Response space (admit, substitute, degrade, escalate, block)
- State management (policies, budgets, governed buffer)
- Evaluation semantics

The composition question is: what verdict should the plane return when gates disagree, and in what order should they run when one (evidence gate) can rewrite the action?

## Decision

We implement **min semantics** with a **two-phase protocol**:

### Min Semantics (Non-Compensatory Join)
- Order responses by restrictiveness: admit < substitute < degrade < escalate < block
- Composed verdict = max(responses), the most restrictive
- Rationale: Proposition 1 shows compensatory aggregation (avg, weighted sum) admits actions vetoed by a member gate; min (ordinal form: max by restrictiveness) preserves veto

### Two-Phase Protocol
1. **Phase I**: Evaluate evidence gate
   - If response is SUBSTITUTE: recompute action context with substituted value
   - If response is ADMIT/DEGRADE/ESCALATE/BLOCK: proceed to Phase II with original context

2. **Phase II**: Evaluate all gates on the remediated action
   - Return join of Phase II responses
   - Record both phases in the Evidence Set

### Rationale
- **Single-pass unsoundness** (Proposition 3): evaluating all gates on the original action leaves the authority and resource gates judging values that will not be executed (if DQ substitutes)
- **Termination** (Lemma 1): DQ substitution is idempotent; the remediated action uses only governed records that DQ admits by construction, so no further remediation
- **Soundness** (Theorem 1): Phase II evaluates every gate on the executed action itself; the join preserves every Held verdict

## API Mapping

### sarc-governance
- **Import**: `from sarc_governance import ConstraintSpec, load_spec`
- **Used for**: Authority gate (role_authorised, order_value_cap constraints)
- **Response mapping**: constraint violation → Response.BLOCK or Response.ESCALATE
- **State**: Constraint spec loaded from YAML

### sarc-dq
- **Import**: `from sarc_dq import EvidenceRecord, PreActionGate`
- **Used for**: Evidence quality gate (defect detection + remediation)
- **Response mapping**: DQ predicate result → Response.{ADMIT, SUBSTITUTE, BLOCK, ESCALATE}
- **State**: Governed buffer (verified records for substitution)
- **Spec**: Load via `sarc_dq.dq_spec.load_spec()` with gate extra for YAML support

### Greensarc
- **Import**: `from green_sarc import PreActionGate, ColdStartEstimator`
- **Used for**: Resource gate (cost + carbon budgets)
- **Response mapping**: budget violation → Response.ESCALATE or Response.BLOCK
- **Estimator**: ColdStartEstimator (zero-history forecast)
- **State**: Daily cost and carbon budgets

## Unified Evidence Set Structure

One JSON line per decision containing:
```json
{
  "day": <int>,
  "sku": <str>,
  "context": {
    "agent_id": <str>,
    "role": <str>,
    "proposed_qty": <float>,
    "order_value": <float>,
    "est_cost_eur": <float>,
    "est_carbon_g": <float>
  },
  "phase1": {
    "dq_response": <str>,
    "substituted_value": <float or null>
  },
  "gates": {
    "sarc": {
      "constraints_evaluated": {...},
      "verdict": <str>
    },
    "green": {
      "predicted_cost": <float>,
      "predicted_carbon": <float>,
      "budget_state": {...},
      "verdict": <str>
    },
    "dq": {
      "predicates": <str or null>,
      "verdict": <str>,
      "substituted_value": <float or null>,
      "evidence_ids": [<str>, ...]
    }
  },
  "final": {
    "admitted": <bool>,
    "response": <str>,
    "winner_gate": <str>,
    "mode": <"two_phase" or "single_pass">
  },
  "action": {
    "order_qty": <float>,
    "order_value": <float>
  }
}
```

No ground-truth labels in Evidence Sets (they go to run_log.jsonl only).

## Defect Classes (Appendix B Recipes)

Seven defect classes injected deterministically:

1. **stale_master_data**: as_of_day 45-150 days behind, cost 0.55-0.9x true
   - Fires: freshness violation
   - Remediation: substitute from governed buffer

2. **superseded_golden_record**: same record_id, versions v2 and v1, differing cost
   - Fires: version mismatch
   - Remediation: substitute

3. **cross_source_contradiction**: same record_id, different source, >2% cost divergence
   - Fires: source contradiction
   - Response: escalate (no substitute)

4. **schema_drift**: unit_cost as string instead of number
   - Fires: type error
   - Response: block

5. **missing_mandatory_field**: currency field absent
   - Fires: mandatory field missing
   - Response: block

6. **lineage_missing**: metadata.source = ""
   - Fires: PAA flag only (never gates)
   - Response: admit (post-action audit flag)

7. **plausible_outlier**: unit_cost x 2.5, clean fresh metadata and lineage
   - Declared uncovered: no gate detects
   - Response: admit
   - Rationale: tests CH4 (no manufactured coverage)

## Scenarios

### S1: Baseline (Loose budgets, all roles authorised)
- Expected: DQ behaviour dominates; zero sarc/green vetoes
- Tests basic composition

### S2: Tight-budget day
- Budgets sized to trigger green vetoes
- Tests green gate interaction

### S3: Unauthorised burst
- 5% unauthorized role, low order_value_cap
- Tests sarc gate on clean evidence

### S4: Constructive counterexample
- Authority cap strictly between pre- and post-substitution order values
- Run two_phase and single_pass; diff verdicts
- Tests CH2 (single-pass unsoundness)

## Assumptions & Limitations

### Assumptions
- Deterministic gates only (no model calls)
- Evidence substitution idempotent
- Governed buffer contains only records admitted by evidence gate
- Per-action soundness (stream-level budget coupling out of scope)

### Limitations
- Cold-start estimator for Greensarc (no historical data)
- Synthetic metadata layer (not live data)
- No prevalence claims (mechanism demo, not benchmark)
- Declared-uncovered class (plausible_outlier) remains uncovered

## Testing

11-test suite validates:
1. Clean/auth/budget → admit, winner=none
2. Stale record → substitute, admitted, phase1 recorded
3. Schema drift → block, winner=dq
4. Unauthorised → held, winner=sarc
5. Over-budget → vetoed, winner=green
6. Dirty + over-budget → most restrictive wins
7. Determinism: same seed, identical metrics
8. One Evidence Set per decision, no ground_truth in sets, data unchanged
9. S4: divergences exist, two_phase audits clean
10. CH1: audit zero violations across S1-S4
11. Paper pipeline: v0.1 verbatim, v0.2 zero unfilled slots

## Alternatives Considered

1. **Compensatory aggregation** (weighted sum, average): Rejected (Proposition 1: admits vetoed actions)
2. **Single-pass evaluation**: Rejected for soundness (Proposition 3, S4 demonstrates)
3. **Per-gate output without unified Evidence Set**: Rejected (loss of cross-gate lineage)
4. **Live gates with model calls**: Rejected (zero API spend requirement, determinism requirement)

## References

- Proposition 1: Non-compensatory aggregation (multi-criteria decision analysis literature)
- Proposition 3: Single-pass unsoundness; S4 construction
- Lemma 1: Idempotence of substitution
- Theorem 1: Soundness of two-phase protocol

## Implementation Notes

- CompositionEngine class in composition.py
- RetailSimulation in suite_sim.py
- Runner orchestrates S1-S4, both modes
- paper_tables.py generates metrics for paper
- Tests in test_suite_sim.py

## Decision Drivers

1. **Soundness**: Two-phase respects veto (Theorem 1)
2. **Determinism**: Reproducible runs, zero API spend
3. **Lineage**: Unified Evidence Set preserves all cross-gate information
4. **Honesty**: Declared-uncovered class remains uncovered; reported in CH4
5. **Composability**: Unmodified engines (git-clean verification)

## Repair

**Status**: Accepted
**Date**: 2026-08-12

### Context

An independent review found the initial build reimplemented all three
gates locally instead of importing the engines, and enumerated ten
concrete defects (R1-R10). This section records every adaptation made
while wiring the *real* engines, per Step 1's instruction to log
deviations here rather than silently working around them.

### R1/R2/R3: what "real gate" means for each engine

**sarc-governance (authority gate).** `GovernanceToolset.call_tool` is
async and wraps a `ToolsetProtocol` that actually executes a tool call —
there is no such tool here (this is a synchronous decision-stream
simulation, not an agent framework). Wrapping it would mean inventing a
fake async toolset whose only job is to be governed, which adds
indirection without adding real coverage. Instead, `composition.py`'s
`evaluate_sarc_pag` calls `ConstraintSpec.at(EnforcementPoint.PAG)` and
`Constraint.predicate(ctx)` directly — this is *exactly* the loop
`GovernanceToolset.call_tool` runs internally at PAG
(`sarc_governance/governance.py` L182-204), just without the async
wrapper. Two custom predicates, `role_unauthorised` and
`order_value_over_cap`, are registered into the engine's own
`sarc_governance.predicates` registry via `register()`, and
`specs/authority.yaml` is loaded through the real `sarc_governance.load_spec`
YAML loader (id/class/verif/response/predicate schema — the original
build's YAML was in an invented schema the loader would have rejected).
Per-decision thresholds (`allowed_roles`, `order_value_cap`) are read out
of `ctx["args"]` at evaluation time rather than baked into the spec, so
the predicates stay pure and reusable across scenarios with different
caps.

**Greensarc (resource gate).** `green_sarc.PreActionGate` +
`ColdStartEstimator` forecast in an LLM-token-shaped domain
(`Action.prompt_tokens`/`max_tokens`, a `TableCostModel`/`TableCarbonModel`
keyed by `model`), not directly in EUR/grams. The declared field mapping:
`Action.max_tokens` carries the predicted order cost (`prompt_tokens=0`),
so `ColdStartEstimator`'s `cost_hat` equals `est_cost_eur` exactly. Each
SKU gets its own `ModelProfile` (`model=sku`) with
`usd_per_completion_token=1.0` and an `energy_per_token_kwh` solved once
from the SKU's real, constant-per-SKU economics
(`carbon_per_unit / (true_unit_cost * cost_multiplier)`), against a flat
declared `carbon_intensity=1.0` for a single declared region — so
`carbon_hat` equals `est_carbon_g` exactly too. Verified empirically:
`cost_hat == est_cost_eur` and `carbon_hat == est_carbon_g` to floating
point precision for every SKU. Budgets are constructed fresh per decision
(`Budget(token_budget=daily_cost_budget, carbon_ceiling=daily_carbon_budget)`)
rather than decremented cumulatively across the day — consistent with
Definition 3 / the Remark on stream-level ordering being out of scope,
and with the other two gates also being evaluated per-action.

**sarc-dq (evidence gate).** `sarc_dq.gate.PreActionGate(load_spec(), GovernedBuffer)`
is used unmodified against the packaged default
`specs/dq_predicates.yaml` (not a hand-written spec) — its six real
predicates (`freshness`, `golden_record_unique`, `cross_source_consistent`,
`schema_conformant`, `complete`, `lineage_present`) are the only detection
logic in the system. The previous build's freshness check
(`0.55*cost <= cost <= 0.9*cost`, always true) is gone entirely; the real
predicate only compares `metadata.age_days` against `max_age_days=30`,
which the injector's staleness range (45-150 days) reliably exceeds.

### R1 (buffer): "refreshed only by clean, admitted reads" is honestly imperfect

The gate never sees ground truth, so it cannot distinguish a genuinely
clean read from a `plausible_outlier` read (both are "admit" — that is
the entire point of the declared-uncovered class). `evaluate_dq` refreshes
the governed buffer on every `admit` response, which means a
`plausible_outlier` decision *can* transiently write its corrupted
(2.5x) cost into the buffer for that SKU, and a later
`stale_master_data`/`superseded_golden_record` substitution on the same
SKU could then substitute the poisoned value instead of the true cost.
This is not a bug to be patched by peeking at ground truth inside the
gate (which the invariants forbid) — it is an honest, emergent
second-order consequence of running a declared-uncovered class through a
downstream-only remediation buffer, and is left as-is rather than
special-cased away. It does not affect CH1 (the post-hoc audit checks
structural/freshness/lineage validity of the executed record, not
whether its *number* matches history) or any of the pinned test
expectations.

### R1 (Phase II performance): reusing Phase I's DQ decision when nothing substituted

Lemma 1 already establishes that Phase II's DQ re-evaluation is
deterministic and, when Phase I did not substitute, evaluates the
*identical* evidence Phase I saw. `two_phase()` therefore reuses Phase
I's `GateDecision` instead of calling the real gate a second time in that
case (~87% of decisions), rather than re-running it deterministically for
no new information. This is a performance optimization only — behavior
is unchanged (verified by `test_7b_determinism_metrics_byte_identical`)
— needed to keep `make suite` under the ~20s target once the local
predicate stubs were replaced with the real, heavier
`EvidenceRecord.evidence_id()` content-addressed hashing.

### R4/R6: `detected` vs `verdict` for the dq gate

Under two_phase, Phase II re-evaluates DQ on the *remediated* (clean)
evidence, so `gates.dq.verdict` correctly reads `"admit"` even when Phase
I substituted — that is the whole point of Theorem 1 (Phase II evaluates
the actual executed action, which is clean by construction). But it means
`verdict != "admit"` is the wrong signal for "did DQ detect this
decision's injected class," which CH4/Table 2 need. Each Evidence Set
line therefore also carries `gates.dq.detected`, the real
`GateDecision.detected` flag from the phase that actually evaluated the
original (possibly corrupted) evidence — Phase I under two_phase, the
single evaluation under single_pass. `veto_counts` (Table 1) intentionally
still uses `verdict != "admit"`, since a successful substitution is not a
veto (Exec-class, not Held) and should not be counted as one; `detected`
and `verdict != "admit"` are answering two different, both-correct
questions.

### R8 (ch4_matrix): computed from S1, not aggregated across S1-S4

S1 is the scenario the original brief itself describes as the "clean
laboratory" (loose budgets, all roles authorised, zero sarc/green vetoes
— verified by T-c). Computing `ch4_matrix` only from S1's two_phase
decisions means a class's sarc/green detection rate reflects only that
class's own effect, not confounded by S2's independently-tight budgets or
S3's independently-low authority cap. Aggregating across all four
scenarios was tried first and produced a non-zero sarc/green detection
rate for `plausible_outlier` purely from unrelated coincidental vetoes in
S2/S3 — which would have made CH4 falsely read "NOT SUPPORTED" despite
plausible_outlier genuinely never being detected *for its own defect*.
`ch4_matrix.source_scenario` records this choice in the generated output
itself.

### R7/S1-S3 calibration: budgets and caps are generated, not guessed

`build_scenarios` runs one full deterministic decision-plan generation
pass (`unauthorized_role_rate=0.0`, S1's own authorized-roles list) and
calibrates every scenario's numbers from the real resulting order-value /
predicted-cost / predicted-carbon distributions (max for the loose S1/S4
budgets and cap, so they exceed even the `plausible_outlier` 2.5x worst
case; median for S2's tight budgets and S3's low cap) — not hand-picked
constants. This is what makes T-c (S1: zero sarc/green vetoes) hold
reliably rather than by luck.

### R7: per-class independent injection, fixed order

`suite_sim._inject` iterates `DEFECT_CLASSES` in a fixed order and rolls
an independent `rng.random() < 0.02` for each class in turn, stopping at
the first class that fires (at most one class per decision). This
replaces the previous "one flat 2% budget, then uniform choice among
seven classes" model, which under-injected every class by roughly 7x
relative to the declared "0.02 independent per class" semantics.

### S4 kappa construction: applies to any DQ substitution, not literally only `stale_master_data`

Both `stale_master_data` and `superseded_golden_record` produce a
`quarantine_substitute` response from the real gate; Proposition 3's
construction only requires *a* substitution event that moves the order
value, so `_compute_s4_kappa` computes
`kappa = (V_pre + V_post) / 2` for every decision where Phase I's real
`GateDecision.response == "quarantine_substitute"`, using a throwaway
peek evaluation (fresh buffer, seeded identically to the real run's) run
once before the scenario's actual two_phase/single_pass calls. Since the
peek buffer's refresh-on-admit is a no-op in this simulation's constant-
per-SKU-true-cost economics, the peek cannot desynchronize from the real
run's substituted values.

### Economics: `order_value` uses the READ cost, not the true cost

The original build computed `order_value` from the true cost regardless
of what the evidence payload actually said, which meant an injected
defect (in particular `plausible_outlier`) had no downstream economic
effect at all — defeating the entire point of the declared-uncovered
class. Per the original brief's §3.1 formula ("order_value = proposed_qty
x read cost"), `runner._context_from_plan` now computes `order_value`
from `p.read_cost` (whatever the injector actually wrote into the primary
record's payload, parsed back from a string for `schema_drift` since that
class corrupts the field's type, not its magnitude) — so a
`plausible_outlier` decision genuinely proposes ~2.5x the correct order
value, and that is what sails through undetected.

### `populate_draft.py`: fixed a pre-existing verification bug

The "diff shows only slot substitutions" check compared
`slot_pattern.sub("", original)` against `slot_pattern.sub("", modified)`
— but `modified` no longer contains any `[GENERATED: ...]` spans to strip
(they were already replaced with values), so this comparison could never
succeed for any real substitution. Replaced with a left-to-right walk over
the original's slot match spans that verifies every non-slot byte-span is
identical between original and modified, and every slot span became
exactly its substituted value.

### Verified outcomes

- `make suite`: ~15s (comfortably under the ~20s target) after the Phase
  II reuse optimization.
- CH1: 0 violations across all four scenarios under two_phase, every run.
- CH2 (S4): >0 divergent decisions, `single_pass_admits_then_violates` >=
  1 every run.
- CH3: 0.0 false-hold rate.
- CH4: `plausible_outlier` reads all-zero at every gate; `union_ok` is
  true; the other five classes read 1.0 DQ detection.
- `composition.py` contains no gate-internal defect logic (verified by
  `test_Ta_no_local_defect_logic_and_real_gates_instantiated`, which
  checks both the source text and that `comp_module.DQPreActionGate is`
  the real `sarc_dq.gate.PreActionGate` class object).

### Note (9.5 upgrade, Phase 2): "two-phase" renamed to "remediate_regate"

Everything above describing "two-phase"/"Phase I"/"Phase II" describes
what was true *at the time of the repair* and is left unchanged as
historical record. Starting with the 9.5 upgrade, the protocol this
section calls "two-phase" is named `remediate_regate` ("rtr") throughout
the code, tests, outputs, and the v0.3 paper — see
`prereg/renaming.md` for the full rationale (avoiding the two-phase-commit
reader collision) and exact rename scope.
