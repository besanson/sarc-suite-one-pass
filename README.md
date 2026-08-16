# SARC Suite One-Pass Demo

Companion artifact for the paper *One Gate Is Not Enough: Composing
Stateful Pre-Action Controls for Agentic AI* (`paper4-composition-draft-v0.4-populated.md`, `paper-tex/main.tex`).

Once a pre-action governance control is permitted to transform the
action it governs, governance stops being a set of independent checks
and becomes a composition problem over constraints, transformations,
and state. This artifact composes three published, open Apache 2.0
governance engines — **sarc-governance** (arXiv 2605.07728, authority),
**Greensarc** (arXiv 2606.15954, predictive cost/carbon budget), and
**sarc-dq** (arXiv 2607.26313, evidence quality) — at one pre-action
control point, and demonstrates three consequences of that permission:
**remediation-induced control coupling** (a control that transforms an
action can invalidate another control's earlier judgment on it, formal
witness Proposition 3 / scenario S4), **non-commutative remediators**
(the two implemented remediation operators, evidence substitution and
resource downroute, do not commute — a finite-model checker finds 86
non-confluent grid points among 243, `checkers/remediator_check.py`,
which is the formal justification for a fixed, pre-registered
remediation order rather than an arbitrary implementation choice), and
**governance-state contamination** (an admissible but uncovered defect
can be promoted into a governed buffer's trusted state and reused by
future remediations, `contamination.py`, CH6). See
[`RESEARCH-GUIDE.md`](RESEARCH-GUIDE.md) for the full contribution
statement, the claims-and-evidence table, and the claims-versus-non-claims
table a research reviewer wants before running anything.

**Verify everything yourself:** `make release-check`. That single
command runs the full test suite (inputs-hash freshness, byte-exact
seed replay against committed artifacts), a formal-checker double-run
byte-identity check, and the arXiv publication-parity gate, and prints
`release-check: ALL CHECKS PASS` when everything holds. Nothing below
is asked to be taken on faith — see [Publication integrity](#publication-integrity).

## Key results

- **Min-semantics composition is machine-checked exhaustively.** The
  restrictiveness join (`admit < substitute < degrade < escalate <
  block`) is order-invariant and duplication-invariant absent
  remediation — `checkers/lattice_check.py`, every case in the finite
  response lattice, not a sample.
- **Remediate-regate restores soundness single-pass composition lacks.**
  Phase I evaluates the evidence gate and recomputes context on
  substitution; Phase II re-evaluates every gate on the remediated
  action. A post-hoc audit finds zero executed actions violating any
  gate at execution time (CH1) — `composition.py`, `runner.py`.
- **The two implemented remediators do not commute.** Evidence
  substitution and resource-budget downroute, applied in opposite
  orders, disagree at 86 of 243 grid points, with a concrete
  counterexample and an additional fixed-seed off-grid probe —
  `checkers/remediator_check.py`, CH7.
- **A weighted-sum aggregator can admit a vetoed action; min never does.**
  The linear-family compensation lemma gives the exact threshold
  condition, verified over the full discrete three-gate verdict grid
  plus randomized probes — `checkers/compensation_check.py`, CH5.
- **A governed buffer can be poisoned by an uncovered defect, and two
  mitigations measurably reduce it.** Quarantine-window and
  rolling-median-of-3 buffer adapters both produce a strictly lower
  poisoned-substitution count than plain buffering on every seed under
  the daily workflow (W1); this does not hold on every seed under the
  weekly-commitment workflow (W2), where the smaller per-seed
  substitution population sometimes produces zero baseline poisoning
  events by chance — reported as a real limitation, not smoothed away
  — `contamination.py`, CH6, Table 6.
- **Composition adds no coverage.** The composed plane's detected class
  set is exactly the union of member gates' detected class sets; two
  declared-uncovered defect classes remain uncovered through every
  gate and through composition, by design — CH4, Proposition 5.
- **All eight hypotheses are pre-registered and swept across 30 seeds
  and two workflows**, with 95% confidence intervals and a
  robustness readout per hypothesis — `sweep.py`,
  `out/results/sweep_summary.json`'s `ch8_robustness` block.

### Architecture: real engines, not a simulation of them

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

### Scenarios

- **S1: Baseline** — loose budgets, all roles authorised. Expected: zero
  sarc and zero green vetoes; DQ behaviour dominates.
- **S2: Tight-budget day** — budgets sized to trigger green vetoes.
  Expected: green veto rate > 0 on known subset.
- **S3: Unauthorised burst** — 5% decisions from non-allowlisted role,
  low `order_value_cap`. Expected: sarc vetoes > 0 including on clean
  evidence.
- **S4: Constructive counterexample (Proposition 3)** — authority cap
  kappa strictly between pre- and post-substitution order values, run
  in both `remediate_regate` and `single_pass` modes. Expected:
  divergent verdicts, CH2 confirmed. This scenario is the concrete
  witness of remediation-induced control coupling.

### Composition protocols

**Remediate-Regate (sound).** Phase I evaluates the evidence gate; on
substitution, recompute context. Phase II evaluates all gates on the
remediated action; return the join. Termination: idempotent
substitution guarantees a fixed point after at most one remediation.

**Single-Pass (measurement).** Evaluate all gates once on the original
action. The executed action still uses the remediated value if DQ
substituted. Used to measure divergence versus `remediate_regate`
(CH2).

### Hypotheses (pre-registered)

- **CH1** (veto soundness): post-hoc audit finds zero violations under
  `remediate_regate`.
- **CH2** (single-pass unsoundness is real): S4 divergences observed.
- **CH3** (deterministic selectivity): zero false holds on
  clean/authorised/in-budget decisions.
- **CH4** (coverage honesty): `plausible_outlier` stays uncovered; the
  union property holds.
- **CH5** (compensation is empirically unsafe): over
  `prereg/weights.json`'s grid, at least one weight vector admits a
  decision the min join held — see `ch5_aggregator.py`.
- **CH6** (buffer contamination is real and mitigable): the plain
  buffer produces poisoned substitutions; both mitigations reduce the
  count — see `contamination.py`, `prereg/contamination.md`.
- **CH7** (multi-remediator order dependence): formal-track only
  (Phase 4), decided by `checkers/remediator_check.py`.
- **CH8** (robustness across 30 seeds x 2 workflows): see `sweep.py` /
  `out/results/sweep_summary.json`'s `ch8_robustness` block.

## Reproduce

Three commands, from a bare clone with the three engine repos as
siblings:

```bash
make bootstrap        # pin the three engines (engines.lock) + install toolchain
make all               # suite + formal + paper + test, regenerated coherently
make release-check      # the mandatory composite gate — verifies everything above
```

`make bootstrap` clones `dqSarc`, `sarc-governance`, and `Greensarc` at
their pinned commits and installs the test/quality toolchain, including
the canonical Tectonic 0.17.0 LaTeX compiler (see
[Publication integrity](#publication-integrity)). Pre-registration
(CH5-CH8, seeds, weights, the W2 workflow, the contamination study, the
`remediate_regate` rename, Evidence Set schema v1) lives under
`prereg/` and `schemas/`, tagged `prereg-v1` — see
`prereg/hypotheses.md`.

### Full command reference

```bash
make bootstrap Clone the three engines at their pinned commits (engines.lock) + install pytest/hypothesis/mutmut/jsonschema
make ci-local  bootstrap + test + suite (local acceptance for .github/workflows/ci.yml)
make test      # Run the test suite (all must pass)
make suite     # Run all four scenarios S1-S4 in both modes (~15-20 seconds)
make sweep     # V3 gate: 30-seed statistical sweep, CH1-CH6 means + 95% CIs
make formal    # V2 gate: exhaustive checkers (lattice, CH5, CH7) + proof lint
make paper     # Generate the v0.4 paper (depends on suite, sweep, formal, in that order)
make paper-legacy  # Superseded v0.1/v0.2 paper pipeline (main.py), kept for its own tests only
make arxiv     # Build paper-tex/main.tex (Tectonic canonical, latexmk alternative), run parity gates G1-G6, package arxiv.tar.gz
make release-check  # MANDATORY before any release: full tests + formal double-run identity + arXiv build gate
make mutate    # Mutation testing on composition.py + metrics.py (V5 gate, target >=0.85; see ADR-002)
make latency   # Per-gate + composed latency microbenchmark, stored in out/quality.json
make clean     # Remove outputs
```

### Prerequisites

Clone the three engines as siblings of this repo (see Step 0), then:
```bash
python3 --version                      # need 3.11+
pip install -e "../dqSarc[gate]"
pip install -e ../sarc-governance
pip install -e ../Greensarc
pip install pytest
```

### Determinism & reproducibility

- **SEED = 26313** everywhere.
- **Deterministic predicates**: no LLM calls, no API spend.
- **Zero source writes**: proven by SHA256 before/after.
- **Downstream-only remediation**: governed buffer substitution only.
- All randomness seeded: same runs produce byte-identical metrics.

### Data

**Source**: UCI Online Retail (CC BY 4.0)
- Citation: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. doi 10.24432/C5BW33.
- Filtered to UK, Quantity > 0, UnitPrice > 0.
- Aggregated per (SKU, date): 40 top SKUs by active days.
- Provenance: `data/PROVENANCE.md`.

## Repository map

```text
Paper
  paper4-composition-draft-v0.4-populated.md   (v0.1-v0.3 frozen historical, recoverable in repo history)
  paper-tex/

Research guide
  RESEARCH-GUIDE.md
  docs/generalized-composition.md

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
  review-secondary/

Review protocols (published, referenced by the paper's disclosure)
  sarc-suite-agent-review.md
  sarc-suite-agent-review-r2.md
  sarc-suite-agent-review-r3.md
  sarc-suite-agent-review-r4.md
```

### Detailed file reference

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
- **checkers/**: Phase 4 (V2 gate) exhaustive finite-model checkers — `lattice_check.py` (join-semilattice laws), `compensation_check.py` (Proposition 1 / CH5 over the full discrete verdict grid), `remediator_check.py` (CH7's order-dependence decision rule), `proof_status_lint.py` (enforces every `PROOF-STATUS` tag is `machine-checked` or `pending-human-review` — never `proven`, which is human-only)
- **appendix-a-proofs.md**: full proofs for every numbered claim, each tagged `PROOF-STATUS`
- **paper_v3.py** / **paper_tables_v3.py**: Phase 5 — writes and populates the paper draft, extending `paper_tables.py`'s CH1-CH4 slots with CH5-CH8 numbers from the sweep and the checkers
- **citation_check.py** / **verified-citations.json**: V4 gate — every arXiv ID/DOI in a paper draft must match an entry fetched live (url, title, first author, year) via WebFetch; `[CITE: ...]`/`[CITE-NEEDED: ...]` gaps are counted, never fabricated
- **test_suite_sim.py**: test suite, including the anti-mock tripwires
- **data/**: UCI Online Retail dataset (CC BY 4.0)
- **out/**: output artifacts (evidence sets, run logs, metrics, paper, sweep results)

### Phase notes

- **Phase 3** (`prereg/w2-workflow.md`, `prereg/contamination.md`,
  `prereg/weights.json`): the W2 weekly-commitment workflow and its
  downroute remediator (`build_w2_scenarios` in `runner.py`); the
  `plausible_outlier_high` second uncovered defect class and the
  poisoned-substitution metric (`contamination.py`); the CH5 aggregator
  harness (`ch5_aggregator.py`); `make sweep` runs `sweep.py`'s 30-seed
  statistical sweep, checkpointed per seed
  (`out/results/sweep/seed_<seed>.json`, safe to resume).
- **Phase 4** (`make formal`): the three exhaustive checkers under
  `checkers/` plus the PROOF-STATUS lint. Their outputs
  (`out/checkers/*.json`) back the `machine-checked` proofs in
  `appendix-a-proofs.md`; the checkers verify their claims over the
  *entire* relevant finite state space (the 5-element response lattice,
  the 125-point three-gate verdict grid, or a 243-point remediation-order
  grid), not a sample.
- **Phase 5** (`make paper`): the paper draft is populated from
  `out/metrics.json` + `out/results/sweep_summary.json` +
  `out/checkers/*.json` + `appendix-a-proofs.md` — no independent
  re-derivation. `citation_check.py` (V4 gate) verifies every citation
  against `verified-citations.json` before the run is considered clean.
- **Phase 6** (`make arxiv`, `make release-check`): see
  [Publication integrity](#publication-integrity).

## Publication integrity

Every claim above is checkable, not asserted. This section lists the
mechanism for each:

- **Preregistration tag.** `prereg-v1` fixes hypotheses, seeds, weights,
  the W2 workflow, the contamination study, and the Evidence Set schema
  before any corresponding result entered this repository's history —
  `git ls-tree -r prereg-v1` shows no result artifacts under its tree.
- **Pinned engines.** The three composed engines are cloned at commits
  fixed in `engines.lock`, installed editable, and verified git-clean
  after every run — `bootstrap.sh`.
- **Generated result tables.** Every number in the paper comes from a
  `[GENERATED: ...]` slot filled from `out/metrics.json`,
  `out/results/sweep_summary.json`, or `out/checkers/*.json` — never
  typed. `populate_draft.py` verifies only slot spans changed.
- **Formal checkers.** `checkers/lattice_check.py`,
  `checkers/compensation_check.py`, and `checkers/remediator_check.py`
  verify their claims over the entire relevant finite state space, not
  a sample; `checkers/proof_status_lint.py` enforces that no tag can be
  written as `proven` — that value is human-only.
- **Citation validation.** `citation_check.py` (V4 gate) checks every
  arXiv ID/DOI/URL a paper draft cites against a live-fetched,
  human-verified whitelist (`verified-citations.json`); anything
  unverifiable becomes an honest `[CITE-NEEDED]` placeholder, counted
  rather than guessed.
- **Markdown/LaTeX parity.** `paper-tex/main.tex` is checked
  word-for-word and number-for-number against the markdown source by
  six parity gates (`paper-tex/gates/run_gates.py`, G1-G6; results in
  `paper-tex/parity-report.json`) under the canonical, bootstrap-pinned
  Tectonic 0.17.0 compiler.
- **Automated external review disclosure.** The paper's Validation note
  states plainly which parts of the review chain were and were not
  independent; see [Review chain](#review-chain) below.
- **`make release-check`.** The mandatory, composite pre-release gate:
  the full test suite (inputs-hash checker freshness, byte-exact seed
  replay against committed artifacts), a formal-checker double-run
  byte-identity check, and the arXiv build gate, in one command. Run it
  before any release and confirm it prints
  `release-check: ALL CHECKS PASS`.

Known, non-blocking issues in this package are tracked in
[`KNOWN-ISSUES.md`](KNOWN-ISSUES.md).

### Definition of Done

- `make test` green.
- `make suite` completes in under about 20s, prints scenario summaries and the CH1-CH4 line.
- `make paper` produces the paper with zero unfilled slots, sourced solely from `out/metrics.json`, `out/results/sweep_summary.json`, `out/checkers/*.json`, `appendix-a-proofs.md`, and the generated manifest (`make paper-legacy` still produces v0.2 the same way, from `out/metrics.json` and the manifest alone).
- ADR-001-composition.md written, including the Repair section.
- Apache-2.0 headers on all new files; LICENSE at repo root.
- Three engine repos untouched (`git -C <repo> status --porcelain` empty).
- `composition.py` contains no gate-internal defect logic (verified by test).
- Final console lists all artifact paths.

### Artifact scope

**Mechanism demonstration on open payload data with a declared synthetic metadata layer. Not a live GIGO-Bench release; live cells come only from the official harness. Not the proprietary Suite: no connectors, evidence vault, identity, or hosting. plausible_outlier is injected and not caught, by design: declared uncovered. S4 is a constructed counterexample scenario, declared as such.**

## Review chain

This work was stress-tested through four rounds of commissioned
adversarial review by an independent automated agent; every finding
was fixed and every fix verified. Each round's protocol document was
written in advance by the author's AI assistant and committed to this
repository alongside the report it produced; the review itself,
against that protocol, was executed independently by a separate
vendor's automated agent (a Perplexity product), run by the author in
a fresh session with access only to this public repository. A fifth,
commissioned positioning review (scholarly framing, not verification)
is recorded at [`review-secondary/`](review-secondary/); it recommended
manuscript reframing, not new experiments, and produced the v0.4
revision this README describes.

Final-round reviewer scores by round (research-artifact lens /
software-engineering lens):

| Round | Research artifact | Software engineering | Disposition |
|---|---:|---:|---|
| 1 | 5.5/10 | 8.0/10 | -- |
| 2 | 7.5/10 | 7.5/10 | -- |
| 3 | 8.5/10 | 8.0/10 | -- |
| 4 (terminal) | 9.5/10 | 9.5/10 | **RELEASE** |

Reports and their protocols:

- Round 1: [`review/REVIEW.md`](review/REVIEW.md) / [`review/review.json`](review/review.json) — protocol [`sarc-suite-agent-review.md`](sarc-suite-agent-review.md)
- Round 2: [`review-r2/REVIEW-R2.md`](review-r2/REVIEW-R2.md) / [`review-r2/review.json`](review-r2/review.json) — protocol [`sarc-suite-agent-review-r2.md`](sarc-suite-agent-review-r2.md)
- Round 3: [`review-r3/REVIEW-R3.md`](review-r3/REVIEW-R3.md) / [`review-r3/review.json`](review-r3/review.json) — protocol [`sarc-suite-agent-review-r3.md`](sarc-suite-agent-review-r3.md)
- Round 4 (terminal): [`review-r4/REVIEW-R4.md`](review-r4/REVIEW-R4.md) / [`review-r4/review.json`](review-r4/review.json) — protocol [`sarc-suite-agent-review-r4.md`](sarc-suite-agent-review-r4.md)
- Positioning (secondary, framing only): [`review-secondary/SARC_Composition_Detailed_Revision_Recommendations.md`](review-secondary/SARC_Composition_Detailed_Revision_Recommendations.md)

See the paper's Validation note for the full disclosure and its
process-provenance note: the review *protocols*, and the *adjudication*
of each round's findings between rounds, were not independent of the
author's own AI assistant; only the review *execution* against each
committed protocol was performed independently.

Automated review complements and does not replace human peer review.

## License

Apache License 2.0 — see LICENSE.

All new files: Apache-2.0 headers present.
Data: CC BY 4.0 (UCI Online Retail).
Composed engines: Apache-2.0 (sarc-governance, Greensarc, sarc-dq).
