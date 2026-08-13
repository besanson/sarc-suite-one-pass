# SARC Suite One-Pass Demo

## Honesty Banner

**Mechanism demonstration on open payload data with a declared synthetic metadata layer. Not a live GIGO-Bench release; live cells come only from the official harness. Not the proprietary Suite: no connectors, evidence vault, identity, or hosting. plausible_outlier is injected and not caught, by design: declared uncovered. S4 is a constructed counterexample scenario, declared as such.**

## Overview

This demo composes three open Apache 2.0 governance engines at one Pre-Action control point over an open-data replenishment stream:

- **sarc-governance** (arXiv 2605.07728): obligations and permissions gate
- **Greensarc** (arXiv 2606.15954): predictive cost and carbon budgets gate
- **sarc-dq** (arXiv 2607.26313): metadata evidence-quality gate

The composition demonstrates:
1. **Min semantics** across gates (restrictiveness join: admit < substitute < degrade < escalate < block)
2. **Remediate-regate ("rtr") protocol** for sound remediation under evidence substitution
3. **Unified Evidence Set** per decision preserving cross-gate lineage
4. **Declared-uncovered coverage**: plausible_outlier is injected and remains uncovered

## Architecture: real engines, not a simulation of them

This artifact does not reimplement gate logic. It imports and calls the
three published packages directly:

- **Evidence gate**: `sarc_dq.gate.PreActionGate` + `sarc_dq.dq_spec.load_spec()`
  (the packaged default `dq_predicates.yaml`) evaluate real
  `sarc_dq.records.EvidenceRecord` / `RecordMetadata` objects. Freshness,
  schema, completeness, cross-source, and golden-record checks are the
  engine's own predicates — this repo contains none of that logic.
- **Authority gate**: a `sarc_governance.ConstraintSpec` loaded from
  `specs/authority.yaml` via `sarc_governance.load_spec`, with two custom
  predicates (`role_unauthorised`, `order_value_over_cap`) registered into
  the engine's own predicate registry. Evaluation walks
  `ConstraintSpec.at(EnforcementPoint.PAG)` and calls each
  `Constraint.predicate(ctx)` — the same loop
  `GovernanceToolset.call_tool` runs internally at PAG.
- **Resource gate**: `green_sarc.PreActionGate` + `ColdStartEstimator`
  against a per-SKU `TableCostModel` / `TableCarbonModel`, so predicted
  cost and carbon are computed by the engine's own
  `carbon_for_tokens()` pipeline, not by this repo.

See `ADR-001-composition.md` for the exact field mappings and the
rationale for every place this repo had to adapt to the engines' real
APIs (declared explicitly — nothing here silently reimplements a gate).

## Running the Demo

### Prerequisites

Clone the three engines as siblings of this repo (see Step 0), then:
```bash
python3 --version                      # need 3.11+
pip install -e "../dqSarc[gate]"
pip install -e ../sarc-governance
pip install -e ../Greensarc
pip install pytest
```

### Build and Test
```bash
make bootstrap Clone the three engines at their pinned commits (engines.lock) + install pytest/hypothesis/mutmut/jsonschema
make ci-local  bootstrap + test + suite (local acceptance for .github/workflows/ci.yml)
make test      # Run the test suite (all must pass)
make suite     # Run all four scenarios S1-S4 in both modes (~15-20 seconds)
make paper     # Generate paper draft v0.2 with filled slots
make mutate    # Mutation testing on composition.py + metrics.py (V5 gate, target >=0.85; see ADR-002)
make latency   # Per-gate + composed latency microbenchmark, stored in out/quality.json
make clean     # Remove outputs
```

Pre-registration (CH5-CH8, seeds, weights, W2 workflow, contamination
study, the `remediate_regate` rename, Evidence Set schema v1) lives under
`prereg/` and `schemas/`, tagged `prereg-v1` — see `prereg/hypotheses.md`.

## Files

- **suite_sim.py**: decision stream, economics, and the declared per-class defect injector (builds real `EvidenceRecord`/`RecordMetadata` objects); `workflow`/`commitment_period_days` implement W2 (weekly commitment)
- **composition.py**: three-gate orchestration composing the real engines (remediate_regate and single_pass protocols); `_maybe_downroute` is the second (W2-only) remediator; no gate-internal defect logic
- **runner.py**: scenario runner (S1-S4, W2-S1/W2-S2, contamination scenario configurations), post-hoc audit, `out/` writer
- **metrics.py**: aggregates CH1-CH4 from the actual recorded gate decisions, under the `prereg/ch2-semantics.md` CH2 redefinition
- **contamination.py**: CH6 — the poisoned-substitution metric plus the `QuarantineWindowBuffer`/`MedianOf3Buffer` mitigation adapters (buffer-wrapping, outside `sarc_dq.gate`)
- **ch5_aggregator.py**: CH5 — the weighted-score compensatory aggregator harness against `prereg/weights.json`'s grid
- **sweep.py**: the V3-gate 30-seed statistical sweep (`prereg/seeds.json`); checkpointed per-seed under `out/results/sweep/`, aggregated with 95% CIs into `out/results/sweep_summary.json`
- **manifest.py**: generated artifact manifest (`importlib.metadata` + `git rev-parse` + data sha256 + licences — nothing hard-coded)
- **paper_tables.py**: builds every `[GENERATED: ...]` slot solely from `out/metrics.json` + the manifest
- **populate_draft.py**: fills the paper draft template, verifying only slot spans changed
- **specs/authority.yaml**: sarc-governance constraint spec (real YAML schema: id/class/verif/response/predicate)
- **prereg/**: pre-registered (tagged `prereg-v1`) hypotheses, seeds, weights, and workflow/contamination/semantics definitions — Phase 3 experiments implement these verbatim
- **test_suite_sim.py**: test suite, including the anti-mock tripwires
- **data/**: UCI Online Retail dataset (CC BY 4.0)
- **out/**: output artifacts (evidence sets, run logs, metrics, paper, sweep results)

## Data

**Source**: UCI Online Retail (CC BY 4.0)
- Citation: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. doi 10.24432/C5BW33.
- Filtered to UK, Quantity > 0, UnitPrice > 0
- Aggregated per (SKU, date): 40 top SKUs by active days
- PROVENANCE: data/PROVENANCE.md

## Scenarios

### S1: Baseline
- Loose budgets, all roles authorised
- Expected: zero sarc and zero green vetoes; DQ behaviour dominates

### S2: Tight-budget day
- Budgets sized to trigger green vetoes
- Expected: green veto rate > 0 on known subset

### S3: Unauthorised burst
- 5% decisions from non-allowlisted role
- Low order_value_cap
- Expected: sarc vetoes > 0 including on clean evidence

### S4: Constructive counterexample (Proposition 3)
- Authority cap kappa strictly between pre- and post-substitution order values
- Run in both remediate_regate and single_pass modes
- Expected: divergent verdicts, CH2 confirmed

## Composition Protocols

### Remediate-Regate (Sound)
1. **Phase I**: Evaluate evidence gate; on substitution, recompute context
2. **Phase II**: Evaluate all gates on remediated action; return join
3. **Termination**: Idempotent substitution guarantees fixed point after ≤1 remediation

### Single-Pass (Measurement)
- Evaluate all gates once on original action
- Executed action still uses remediated value if DQ substituted
- Used to measure divergence vs remediate_regate (CH2)

## Hypotheses (Pre-registered)

- **CH1** (veto soundness): Post-hoc audit finds zero violations under remediate_regate
- **CH2** (single-pass unsoundness is real): S4 divergences observed
- **CH3** (deterministic selectivity): Zero false holds on clean/auth/budget decisions
- **CH4** (coverage honesty): plausible_outlier stays uncovered; union property holds
- **CH5** (compensation is empirically unsafe): over `prereg/weights.json`'s grid, at least one weight vector admits a decision the min join held — see `ch5_aggregator.py`
- **CH6** (buffer contamination is real and mitigable): the plain buffer produces poisoned substitutions; both mitigations reduce the count — see `contamination.py`, `prereg/contamination.md`
- **CH7** (multi-remediator order dependence): formal-track only (Phase 4), decided by `checkers/remediator_check.py`
- **CH8** (robustness across 30 seeds x 2 workflows): see `sweep.py` / `out/results/sweep_summary.json`'s `ch8_robustness` block

## Phase 3: W2, contamination, CH5, and the 30-seed sweep

- **W2** (`prereg/w2-workflow.md`): a weekly-commitment workflow with its
  own role namespace and a second remediator, downroute (scale the
  committed quantity to the largest budget-feasible amount, then
  re-gate) — `build_w2_scenarios` in `runner.py`.
- **Contamination study** (`prereg/contamination.md`): `plausible_outlier_high`
  is a second uncovered-by-DQ defect class; `contamination.py` computes
  the poisoned-substitution metric purely from ground-truth labels and
  implements the two mitigation buffer adapters, entirely outside
  `sarc_dq.gate`.
- **CH5 aggregator** (`prereg/weights.json`): `ch5_aggregator.py` compares
  the min-join composed result against a weighted-score compensatory
  aggregator over the pre-registered weight/threshold grid.
- **`make sweep`**: runs `sweep.py`, the V3-gate statistical sweep over
  all 30 registered seeds — recomputes CH1-CH4 (new CH2 semantics), CH5,
  and CH6 (both workflows x plain/quarantine/median_of_3) per seed, then
  aggregates means and 95% CIs. Checkpointed per seed
  (`out/results/sweep/seed_<seed>.json`), safe to resume.

## Determinism & Reproducibility

- **SEED = 26313** everywhere
- **Deterministic predicates**: no LLM calls, no API spend
- **Zero source writes**: proven by SHA256 before/after
- **Downstream-only remediation**: governed buffer substitution only
- All randomness seeded: same runs produce byte-identical metrics

## Definition of Done

✓ `make test` green
✓ `make suite` completes in under about 20s, prints scenario summaries and the CH1-CH4 line
✓ `make paper` produces v0.2 with zero unfilled slots, sourced solely from `out/metrics.json` and the generated manifest
✓ Honesty banners verbatim in README, readouts, and the populated draft's Appendix B
✓ ADR-001-composition.md written, including the Repair section
✓ Apache-2.0 headers on all new files; LICENSE at repo root
✓ Three engine repos untouched (`git -C <repo> status --porcelain` empty)
✓ `composition.py` contains no gate-internal defect logic (verified by test)
✓ Final console lists all artifact paths

## License

Apache License 2.0 — see LICENSE.

All new files: Apache-2.0 headers present
Data: CC BY 4.0 (UCI Online Retail)
Composed engines: Apache-2.0 (sarc-governance, Greensarc, sarc-dq)
