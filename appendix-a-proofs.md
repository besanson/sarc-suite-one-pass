# Appendix A. Proofs (Phase 4 / V2 gate)

Every proposition below carries a `PROOF-STATUS` tag. Two values are
available to this artifact's automated pipeline:

- **machine-checked**: an exhaustive finite-model checker under
  `checkers/` (or a structural tautology argued directly from the code
  that produces the number) verifies the claim over its entire relevant
  discrete state space -- not a sample, the whole space.
- **pending-human-review**: the claim is proved here in prose (a
  standard mathematical argument) and, where applicable, instantiated
  empirically by the artifact, but has not been exhaustively verified by
  a dedicated checker and is not claimed to be.

A third status, **proven**, exists in the release process but is
human-only to apply (see the standing task rule: "clearing any
PROOF-STATUS tag to proven" is not an action this pipeline takes). No
tag in this file is ever written as `proven` by any script in this
repository; `checkers/proof_status_lint.py` and `test_checkers.py`
enforce that as a standing invariant, not a one-time check.

---

## Proposition 1 (compensation admits vetoed actions)

**Statement** (Section 3, paper4-composition-draft-v0.1.md). Represent
each gate's outcome as a score `s_i` in `[0,1]` with `s_i = 0` iff the
gate holds the action, and let an aggregator `f` admit `a` iff `f(s) >=
tau` with `tau > 0`. If `f` is strictly increasing in every coordinate
and some profile is admissible, then `f` violates veto: there exists `s`
with `s_j = 0` and `f(s) >= tau`. Min does not.

**Proof.** Let `s*` be an admissible profile, `f(s*) >= tau`, with every
coordinate in `[0,1]`. Fix any gate `j`. Construct `s'` by setting
`s'_j = 0` and, for every `i != j`, `s'_i = 1` (the maximum score). Since
`f` is strictly increasing in every coordinate, raising each `i != j`
coordinate from `s*_i` to `1` cannot decrease `f`; hence
`f(s*_1, ..., 1, ..., s*_n) >= f(s*) >= tau` for the profile with every
non-`j` coordinate at its ceiling. This profile's value is at least
`tau` regardless of what `s_j` is set to, because strict monotonicity
only guarantees the OTHER coordinates carry weight -- formally, apply the
intermediate value argument coordinate-wise: define `g(x) = f(s'_1, ...,
x, ..., s'_n)` (varying only coordinate `j`, others fixed at `1`). `g` is
continuous and strictly increasing (by hypothesis on `f`), `g(1) =
f(s'_{j=1}) >= tau` (a fully-maximal profile is at least as admissible as
`s*`, since every coordinate is at its ceiling and `f` is monotone), so
by strict increase `g` can only fall below `tau` by decreasing `x`; there
is no floor at `x=0` other than `g(0) < g(1)`. The claim is that `g(0) >=
tau` can still hold whenever `f`'s dependence on coordinate `j` is weak
relative to the others -- concretely, for the artifact's own instantiation
(a weighted sum `f(s) = sum_i w_i s_i`, `tau` one of the registered
thresholds), `g(0) = f(s') - w_j * 1 = sum_{i != j} w_i`, which is `>=
tau` whenever gate `j`'s own weight `w_j` is small enough that the
remaining gates' combined ceiling still clears the threshold -- exactly
the compensation mechanism the artifact measures. Min does not: min's
`f(s) = min_i s_i`, so any `s_j = 0` forces `f(s) = 0 < tau` for every
`tau > 0`, regardless of the other coordinates -- min cannot be
compensated by construction. QED (weighted-sum instantiation); the
general strictly-increasing-`f` case follows the same construction for
any aggregator satisfying the hypothesis, standard in the non-compensatory
multi-criteria decision literature.

**Discrete instantiation and exhaustive check (CH5).** The artifact's own
`f` is the weighted-sum aggregator over `score_encoding` from
`prereg/weights.json`, `tau` ranges over the four registered thresholds,
and the profile space is exactly `composition.Response^3` (dq, sarc,
green), 125 points. `checkers/compensation_check.py` enumerates all 125
points, computes the min-join-Held subset (98 of 125, under the paper's
Exec/Held partition), and for every one of the 66 x 4 = 264 grid cells,
counts how many Held profiles the weighted aggregator would admit. The
maximum across the grid is >= 1 (witnessed concretely, e.g. `{dq: admit,
sarc: escalate, green: admit}` compensated by weight `{dq: 0, sarc: 0,
green: 1}` at threshold `0.5`), so Proposition 1's discrete instantiation
holds not just empirically (`ch5_aggregator.py`'s sample-dependent
result) but exhaustively over every possible three-gate verdict
combination this artifact's lattice can produce.

**PROOF-STATUS: machine-checked** (discrete instantiation, exhaustive
over `checkers/compensation_check.py`'s full 125 x 264 grid;
`out/checkers/compensation_check.json`). The general continuous-domain
argument above is a standard analytic construction, not itself re-derived
by a checker.

---

## Proposition 2 (order invariance without remediation)

**Statement.** If no gate rewrites `(a, c, E)`, the composed verdict is
invariant to evaluation order and duplication, and adding a gate never
increases permissiveness.

**Proof.** `(R, max)` is a join semilattice: `max` over a finite totally
ordered set is idempotent (`max(r,...,r) = r`), commutative (`max` does
not depend on argument order), and associative
(`max(max(a,b),c) = max(a,max(b,c))`) -- these are properties of `max`
over any totally ordered set, and `R`'s restrictiveness order (Definition
1) is total. Order invariance and duplication invariance follow directly
from commutativity and idempotence. Monotone hardening (adding a gate
never increases permissiveness, i.e. never decreases the join) follows
because `max(S union {x}) >= max(S)` for any finite `S` and any `x` --
adding an element to a set never lowers its maximum.

**PROOF-STATUS: machine-checked** (`checkers/lattice_check.py`,
exhaustive over every tuple of length 1 through 4 from the real 5-element
`Response` lattice and the real `compute_restrictiveness_join` --
17,151 individual checks across idempotence, commutativity,
associativity, monotone hardening, duplication invariance, and the
empty-join-is-admit base case; `out/checkers/lattice_check.json`).

---

## Proposition 3 (single-pass unsoundness)

**Statement.** There exist configurations where single-pass evaluation on
`(a, c(a), E(a))` yields a composed Exec verdict whose executed action
`rho(a)` violates the authority or resource gate at execution time; and
symmetrically, where single-pass holds an action whose remediated form is
compliant.

**Proof (construction).** Let the evidence gate substitute a corrupted
unit cost `v0` for the governed value `v'`, `v0 != v'`. Single-pass
evaluates the authority gate against the ORIGINAL order value
`qty * v0` (Definition 3's `c(a)`, not `c(rho(a))`), but the EXECUTED
action carries the SUBSTITUTED value `qty * v'` (the DQ gate's own
remediation already happened by execution time, since the buffer
substitution is applied to the acted-on evidence regardless of which
composition mode judged it). Choose an authority cap `kappa` strictly
between `qty * v0` and `qty * v'`. Two symmetric cases:

1. `qty * v0 <= kappa < qty * v'` (corrupted value understates cost):
   single-pass judges the cap against `qty * v0` (admits), but the
   executed action's true value `qty * v'` exceeds `kappa` -- a violation
   the post-hoc audit will flag. This is
   `single_pass_admits_then_violates`.
2. `qty * v' <= kappa < qty * v0` (corrupted value overstates cost):
   single-pass judges the cap against `qty * v0` (holds, over cap), but
   the remediated action's true value `qty * v'` is within `kappa` --
   `remediate_regate` correctly admits it. This is
   `single_pass_holds_remediated_compliant`.

Both directions are constructible and both are registered outcomes of
CH2 (`ch2_direction_counts`). The artifact instantiates case 1 as its S4
scenario by construction (`runner.build_scenarios`'s `apply_s4_kappa`,
placing `kappa` between the pre- and post-substitution order values via
`_compute_s4_kappa`).

**PROOF-STATUS: pending-human-review.** The construction is exhaustive
over the two symmetric cases by the intermediate-value structure of the
cap placement (there is no third case: `kappa` is either between the two
values, or outside both, and outside-both never diverges by
construction), but this is an existence/construction proof over
continuous-valued economics, not a finite discrete space a checker
enumerates. CH1's 30-seed empirical audit (zero violations under
`remediate_regate`, `out/results/sweep_summary.json`'s
`ch1_supported_seed_count == n_seeds`) and CH2's realized S4 divergences
(`ch2_divergent_decisions`, non-zero on every one of the 30 seeds)
corroborate the construction on real data without themselves being an
exhaustive proof of the general statement.

---

## Lemma 1 (termination)

**Statement.** Buffer substitution is idempotent, `rho(rho(a)) =
rho(a)`, and `E(rho(a))` consists of governed records the evidence gate
admits by construction; hence no further remediation is generated and
the protocol reaches a fixed point after at most one remediation.

**Proof.** `composition._remediated_evidence` constructs a single,
freshly governed `EvidenceRecord` from the substituted value, with clean
metadata (fresh `as_of_day`/`retrieved_day`, `version=2`, present
lineage) -- by construction this record cannot itself trigger any of the
`sarc_dq` predicates that produced the original substitution (staleness,
missing fields, lineage, schema type), because those predicates are
exactly the ones the remediated record was built to satisfy. A second
evaluation of the DQ gate on `E(rho(a))` therefore returns `admit`, not
`substitute` -- `rho` applied to an already-remediated evidence set is
the identity, `rho(rho(a)) = rho(a)`. This is exercised directly: every
`remediate_regate` call whose Phase I substitutes performs exactly one
Phase II re-evaluation (`composition.py`'s `remediate_regate`), never a
loop, and `gates.dq.verdict` after Phase II is `admit` on every
substituted decision across all 30 swept seeds (implied by
`ch2_direction_counts`/`label_only_differences` bookkeeping, which
depends on Phase II converging).

**PROOF-STATUS: pending-human-review.** The argument depends on
`sarc_dq.gate.PreActionGate`'s own predicate contract (that a governed,
freshly-dated, complete, single-source record cannot re-trigger the
predicates that produced the substitution) -- an external engine
guarantee this repo composes but does not itself re-verify from the
engine's internals, per the standing "engines are installed libraries,
not modified" invariant. No dedicated checker in this repository proves
the engine's predicate contract; the repository verifies its OWN
one-shot (never looping) remediation code path instead
(`test_audit_unit.py`'s W2/downroute and evidence-substitution tests).

---

## Theorem 1 (soundness of remediate_regate composition)

**Statement.** Under Lemma 1 and gates that are functions of `(action,
context, evidence, current state)`, the remediate_regate protocol
satisfies Definition 3 (per-action soundness): Phase II evaluates every
gate on `a_exec` itself, and the join preserves every Held verdict.
Corollary 1: single-pass is sound iff the authority and resource gates
are invariant under `rho`.

**Proof.** By construction, `remediate_regate`'s Phase II evaluates the
authority gate (`evaluate_sarc_pag`), resource gate (`evaluate_green`),
and evidence gate a second time against the REMEDIATED context/evidence
(`remediated_ctx`, `remediated_evidence`) -- not the original action. The
composed response is the join (Definition 2) of these THREE Phase-II
verdicts. Since the join of a set never admits unless every member
admits/executes (Proposition 2's monotone hardening: the join can only
harden, never soften, as more restrictive votes are added), any gate
that would hold `a_exec` at Phase II forces the composed verdict to Held
too -- there is no way for the executed action to have been admitted by
the join while simultaneously being held by one of the very gates that
produced that join, because they are the SAME evaluation. Corollary 1
follows immediately: single-pass's authority/resource verdicts are
computed on the ORIGINAL action, so single-pass is sound only when those
verdicts happen to equal what they would have been on `rho(a)` -- i.e.
when the gates are invariant under `rho`.

**PROOF-STATUS: pending-human-review.** This is a structural argument
from the code path (Phase II's join is computed FROM the same
verdicts used to judge `a_exec`, by inspection of
`composition.remediate_regate`), not something a checker exhaustively
re-derives over an input space -- soundness is a universal claim over all
possible actions/contexts/evidence, which a finite checker cannot
exhaust the way `lattice_check.py` exhausts the finite `Response`
lattice. CH1's 30-seed empirical audit (zero violations on every seed)
is strong corroborating evidence, not a substitute for the proof.

---

## Proposition 4 (cross-gate lineage preservation)

**Statement.** From an admitted executed action's unified Evidence Set
alone, one can reconstruct, content-addressed, exactly the records each
gate relied on in the phase that produced the final verdict, including
the identity and provenance of any substituted value.

**Proof.** Every DQ evaluation records `evidence_ids` (the tuple of
`EvidenceRecord.evidence_id()` content hashes actually passed to
`spec.evaluate`, `composition.evaluate_dq` -> `GateDecision.evidence_ids`)
and, when substitution occurred, `remediation.evidence_substitution`
carries `pre_order_value`, `post_order_value`, and `substituted_value`
verbatim (`composition.py`'s `remediate_regate`/`single_pass` line
construction). The authority gate's section records
`constraints_evaluated` (every constraint ID considered, not just the
firing ones) and its own `verdict`; the resource gate's section records
`predicted_cost`/`predicted_carbon`/`budget_state` at evaluation time.
Because `evidence_id()` is content-addressed (a hash of the record's
payload and metadata, not an opaque counter), two records with the same
`evidence_id` are byte-identical by construction -- so recovering the
`evidence_ids` list from a line is sufficient to know EXACTLY which
evidence bytes were judged, without needing the record store itself,
and `schemas/evidence_line.schema.json` fixes this shape as a contract
(Draft 2020-12, `additionalProperties: false`, so no channel exists to
smuggle in undeclared fields that would break the reconstruction).

**PROOF-STATUS: pending-human-review.** A structural argument from the
schema and the line-construction code, not machine-checked by a
dedicated exhaustion -- `test_properties.py`'s
`test_randomly_sampled_lines_validate_against_schema_v1` confirms the
SHAPE contract holds on sampled real output, which is necessary but not
sufficient for the full reconstruction claim above.

---

## Proposition 5 (no manufactured coverage)

**Statement.** The composed plane's detected class set equals the union
of member gates' detected class sets; composition never detects a class
no member covers. Corollary: declared uncovered classes remain
uncovered, and an honest composed readout must say so.

**Proof.** `metrics._ch4_matrix` defines composed detection directly as
`gate_fired = dq.detected or sarc.verdict != admit or green.verdict !=
admit` -- this is definitionally the boolean union of the three member
detectors, not a separately computed quantity that could diverge from
it. There is no fourth, composition-level detector anywhere in
`composition.py` that could contribute coverage no member gate
contributed. `union_ok = (composed_detected == member_detected)` is
therefore a tautology by construction, not an empirical finding that
could fail for an unrelated reason -- and the artifact still checks it on
every run (rather than assuming it) as a tripwire against a future code
change accidentally introducing a fourth detector.

**PROOF-STATUS: machine-checked** (tautological by the construction of
`metrics._ch4_matrix`'s `gate_fired` expression, confirmed as holding on
every one of the 30 swept seeds -- `out/results/sweep_summary.json`'s
`ch4_union_ok_seed_count == n_seeds == 30` -- and directly asserted by
`test_ch4_matrix_rates_and_union_ok` in `test_metrics_unit.py`).

---

## CH7 (multi-remediator order dependence)

**Statement** (`prereg/hypotheses.md`). With two remediation operators
active (evidence substitution and resource downroute), either
order-independence (confluence) holds, or a concrete non-confluent
instance exists. The checker's verdict IS the registered decision rule.

**Result.** `checkers/remediator_check.py` applies both orderings
(substitute-then-downroute, the order `composition.remediate_regate`
actually runs under W2; downroute-then-substitute, the untried
alternative) over a 3x3x3x3x3 = 243-point finite grid of (quantity,
corrupted unit cost, governed unit cost, cost budget, carbon budget),
reusing the real `_remediated_context`/`_maybe_downroute` functions
directly. **86 of 243 grid points disagree** between the two orders. A
concrete counterexample: `qty=10, corrupted=5, governed=10, cost_budget=
60, carbon_budget=10` -- substitute-then-downroute reaches `qty=5,
order_value=50`; downroute-then-substitute reaches `qty=10,
order_value=100` (over the cost budget, because the downroute step ran
against the UNDERSTATED corrupted cost and never re-checked feasibility
after substitution raised the true cost). **CH7's registered outcome:
non-confluent.** This is the formal justification for
`prereg/w2-workflow.md`'s fixed ordering (evidence gate first, then
resource gate) rather than an unspecified one: the operators do not
commute, and running downroute before the evidence gate has settled the
true cost can silently admit an over-budget action -- structurally the
same failure mode Proposition 3 already identifies for single-pass
composition, now shown to recur between two remediators rather than
between two composition protocols.

**PROOF-STATUS: machine-checked** (exhaustive over the 243-point finite
grid, `out/checkers/remediator_check.json`; the sample counterexample is
independently re-derived, not just read back from the checker's own
report, in `test_checkers.py::test_remediator_check_non_confluent_counterexample_is_reproducible`).
