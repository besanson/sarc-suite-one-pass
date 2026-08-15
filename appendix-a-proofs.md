# Appendix A. Proofs (Phase 4 / V2 gate)

Every proposition below carries a `PROOF-STATUS` tag. Three values are
available to this artifact's automated pipeline:

- **machine-checked**: an exhaustive finite-model checker under
  `checkers/` (or a structural tautology argued directly from the code
  that produces the number) verifies the claim over its entire relevant
  discrete state space -- not a sample, the whole space. Per round-two
  independent review finding R2-N2 (general Proposition/Theorem
  statements were tagged `machine-checked` when only a narrower finite
  instantiation was actually executable-verified): a statement's own
  `PROOF-STATUS` line must name the specific checker module and the
  enumerated domain it covers (a concrete count, grid, or state-space
  size), not just assert the claim is machine-checked in general.
  `checkers/proof_status_lint.py` enforces this mechanically. A
  statement whose true generality (arbitrary `n`, arbitrary gates,
  arbitrary action spaces) exceeds what any checker enumerates gets
  `pending-human-review` or `checked-scope-only` instead, plus a
  sibling finite-encoding Corollary stated at exactly the checker's
  scope and tagged `machine-checked` there (Corollary 2 and Corollary 3
  below are the two introduced for this reason).
- **pending-human-review**: the claim is proved here in prose (a
  standard mathematical argument) and, where applicable, instantiated
  empirically by the artifact, but has not been exhaustively verified by
  a dedicated checker and is not claimed to be.
- **checked-scope-only (REVIEW.md)**: the independent review
  (`review/REVIEW.md`, Section 3) found the statement's general prose
  claim broader than what this artifact actually certifies; the tag and
  the statement's wording are narrowed to exactly the scope the review
  lists as "largest scope certified" for that statement -- no broader.

A fourth status, **proven**, exists in the release process but is
human-only to apply (see the standing task rule: "clearing any
PROOF-STATUS tag to proven" is not an action this pipeline takes). No
tag in this file is ever written as `proven` by any script in this
repository; `checkers/proof_status_lint.py` and `test_checkers.py`
enforce that as a standing invariant, not a one-time check.

---

## Proposition 1 (linear-family compensation lemma) -- restated per independent review finding F1

**Why this changed.** The original statement here claimed that *any*
strictly increasing aggregator `f` with `tau > 0` and some admissible
profile violates veto. The independent review (`review/REVIEW.md`,
finding F1) refuted this with a concrete counterexample: for
`f(s) = s1 + s2 + s3` on `[0,1]^3` and `tau = 2.5`, `f(1,1,1) = 3` is
admissible, yet every profile with a zero coordinate scores at most `2`,
so **no vetoed profile is ever admitted** -- veto is fully preserved even
though `f` is strictly increasing and has an admissible profile. The
universal claim was false as written; the error was treating "strictly
increasing plus some admissible profile" as sufficient, when whether
compensation can occur actually depends on the relationship between
`tau` and the aggregator's own weight structure. This section replaces
it with two claims that are both true: a precise lemma covering the
linear (additive-score) family the artifact actually measures, stated
with the exact threshold condition that determines when compensation is
and is not possible; and the exhaustive discrete-grid result exactly as
CH5 measured it.

**Lemma (linear family).** Let `f(s) = sum_i w_i s_i` on `[0,1]^n` with
weights `w_i >= 0`, not all zero, and let `f` admit `s` iff `f(s) >=
tau` for `tau > 0`. A profile `s` is *vetoed* iff `s_j = 0` for some
`j`. For each `j`, define the leave-one-out sum `L_j = sum_{i != j}
w_i` -- the largest score `f` can assign to any profile with `s_j = 0`
(achieved by setting every other coordinate to its ceiling `1`). Let
`L* = max_j L_j = W - min_i w_i`, where `W = sum_i w_i`. **Then: there
exists a vetoed profile that `f` admits if and only if `tau <= L*`.**
Min never admits a vetoed profile, for any `tau > 0` and any weights --
`min(s) = 0` whenever any coordinate is `0`, unconditionally.

**Proof.**
*Sufficiency (`tau <= L*` implies a vetoed profile is admitted).* Let
`j* = argmin_i w_i`, so `L_{j*} = L*`. Define `s*` by `s*_{j*} = 0` and
`s*_i = 1` for every `i != j*`. Then `f(s*) = sum_{i != j*} w_i =
L_{j*} = L* >= tau`, and `s*` is vetoed (`s*_{j*} = 0`). So `f` admits a
vetoed profile.
*Necessity (`tau > L*` implies no vetoed profile is admitted).* Let `s`
be any vetoed profile, `s_j = 0` for some `j`. Since every `w_i >= 0`
and every `s_i <= 1`: `f(s) = sum_{i != j} w_i s_i <= sum_{i != j} w_i =
L_j <= L* < tau`. So `f(s) < tau`: `s` is not admitted. Since `s` was an
arbitrary vetoed profile, no vetoed profile is admitted.
*Min.* `min(s) = 0` whenever any `s_j = 0`, and `tau > 0`, so
`min(s) < tau` unconditionally -- min preserves veto regardless of `tau`
or any weight structure, in sharp contrast to the linear family above,
where veto preservation is conditional on `tau > L*` and can fail.

**Applying this to the reviewer's counterexample.** `w = (1,1,1)`,
`W = 3`, `min_i w_i = 1`, so `L* = 2`. Their `tau = 2.5 > L* = 2`: by
the necessity direction, no vetoed profile is admitted -- exactly what
they demonstrated by direct computation. The lemma's threshold condition
correctly classifies this instance as a *non*-compensable regime; the
old universal statement had no such condition and was wrong to treat it
as compensable-by-hypothesis.

**"Vetoed" is `s_j = 0` exactly -- not the artifact's broader Held
class.** The Lemma's hypothesis, following Proposition 1's own original
setup, defines vetoed as `s_j = 0`. Under this artifact's five-level
`score_encoding` (`admit=1.0, substitute=0.75, degrade=0.5,
escalate=0.25, block=0.0`), only `block` scores exactly `0`; `escalate`
is Held under Definition 3's Exec/Held partition (`{escalate, block}`)
but scores `0.25`, not `0`. The Lemma is therefore verified below
against the "at least one `block`" population (61 of 125 profiles) --
a strict subset of the 98 Held profiles CH5's own exhaustive check
already covers. This distinction was not academic: an earlier draft of
this section verified the Lemma against the full Held population and
found 25 of 800 random-probe cells disagreeing with the Lemma's
prediction, all traced to escalate-only-held profiles whose nonzero
`0.25 * w_j` contribution let them clear a threshold `L*` alone would
have predicted they couldn't. Restricting the Lemma's own verification
to the `s_j = 0` population it actually characterizes resolved every
disagreement (`checkers/compensation_check.py`'s `all_vetoed_profiles`
vs `all_held_profiles`). CH5's own existing result -- compensation over
the full Held set, not just the block-only subset -- is unaffected by
this correction and continues to hold via the unchanged exhaustive
enumeration below; if anything, escalate's nonzero score only makes
compensation *easier* to achieve on the broader Held set than the
Lemma's `L*` threshold alone would suggest.

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
green: 1}` at threshold `0.5`), so the discrete instantiation holds not
just empirically (`ch5_aggregator.py`'s sample-dependent result) but
exhaustively over every possible three-gate verdict combination this
artifact's lattice can produce. `compensation_check.py` additionally
verifies the Lemma's `tau <= L*` characterization against brute-force
ground truth over its own `s_j = 0` ("vetoed", i.e. at-least-one-block,
61 of 125 profiles) population -- see the note above on why this differs
from the 98-profile Held population CH5 itself measures -- on the same
264 declared grid cells, plus 200 HEAD-derived random positive-weight
vectors (deterministically seeded from the current commit, per the
independent review's own probe methodology) at the same four thresholds
-- 1,064 consistency checks in total, all agreeing with the Lemma's
prediction (`out/checkers/compensation_check.json`).

**PROOF-STATUS: pending-human-review.** Retagged per round-two
independent review finding R2-N2 (`review-r2/REVIEW-R2.md`): the Lemma
above (Sufficiency/Necessity/Min) is a general algebraic argument, true
for arbitrary `n` and arbitrary nonnegative weights on the continuous
cube `[0,1]^n`, but that generality is exactly what no executable
checker in this repository verifies. `checkers/compensation_check.py`
enumerates only this artifact's own finite `n = 3` instantiation
(Corollary 2 immediately below) -- correct and machine-checked at that
scope, but not a machine check of the continuous arbitrary-`n`
statement itself. Largest certified scope per the review: "analytic
arbitrary-n proof plus finite executable checks at n=3."

---

## Corollary 2 (finite three-gate encoding of the linear-family lemma)

**Statement.** For this artifact's own finite encoding of the Lemma
above -- `n = 3` gates (`dq`, `sarc`, `green`), profiles drawn from
`composition.Response^3` (125 points, `|Response| = 5`), scored via
`prereg/weights.json`'s `score_encoding`, `tau` ranging over the four
registered thresholds -- the `tau <= L*` characterization holds exactly
on every one of 1,064 checked cases: the 264 declared grid cells (every
combination of the artifact's registered weight vectors and thresholds)
plus 200 HEAD-derived random positive-weight vectors at those same four
thresholds, each verified against brute-force ground truth over the
`s_j = 0` ("vetoed") population. The algebraic proof above is elementary
(linearity plus the `[0,1]` bound), and the checker confirms it holds on
every case actually computed, not just the ones the hand proof covers
analytically.

**PROOF-STATUS: machine-checked** (`checkers/compensation_check.py`;
enumerated domain: `n = 3` gates, the 125-point `composition.Response^3`
profile space, 264 declared grid cells plus 200 HEAD-derived random
probe vectors x 4 thresholds = 1,064 cases, all agreeing with the
Lemma's prediction; `out/checkers/compensation_check.json`).

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

## Proposition 3 (single-pass unsoundness, scoped to the implemented construction) -- retagged per independent review finding (Section 3)

**Why this changed.** The independent review (`review/REVIEW.md`,
Section 3) classified this proposition `checked-scope-only`: the
argument below is a valid existential construction, but no executable
checker in this repository covers arbitrary continuous economics or
arbitrary gate implementations, so the claim is restated to name exactly
what is certified -- "conditional algebraic construction with a
substituting DQ decision and cap strictly between pre/post values;
implemented S4 across 30 registered seeds" -- rather than an unscoped
"there exist configurations" claim.

**Statement (scoped).** For the substituting-DQ-decision construction
below -- a corrupted unit cost `v0` substituted for a governed value
`v'`, with an authority cap `kappa` placed strictly between `qty * v0`
and `qty * v'` -- single-pass evaluation on `(a, c(a), E(a))` yields a
composed Exec verdict whose executed action `rho(a)` violates the
authority or resource gate at execution time; and symmetrically,
single-pass holds an action whose remediated form is compliant. This
construction is implemented as scenario S4 and instantiated across all
30 registered seeds (`prereg/seeds.json`); the statement is not claimed
for arbitrary continuous economics or arbitrary gate implementations
beyond this construction.

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

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Largest scope
certified (`review/REVIEW.md`, Section 3): a conditional algebraic
construction with a substituting DQ decision and cap strictly between
pre/post values; implemented S4 across 30 registered seeds. The
construction is exhaustive over the two symmetric cases by the
intermediate-value structure of the cap placement (there is no third
case: `kappa` is either between the two values, or outside both, and
outside-both never diverges by construction), but this is an
existence/construction proof over continuous-valued economics, not a
finite discrete space a checker enumerates, and it does not cover
arbitrary gate implementations. CH1's 30-seed empirical audit (zero
violations under `remediate_regate`, `out/results/sweep_summary.json`'s
`ch1_supported_seed_count == n_seeds`) and CH2's realized S4 divergences
(`ch2_divergent_decisions`, non-zero on every one of the 30 seeds)
corroborate the construction on real data within this scope, without
extending the claim beyond it.

---

## Lemma 1 (termination, scoped to the current one-shot composition branch) -- retagged per independent review finding (Section 3)

**Why this changed.** The independent review (`review/REVIEW.md`,
Section 3) classified this lemma `checked-scope-only`: the argument
depends on an external DQ predicate contract (`sarc_dq.gate.PreActionGate`'s
own guarantee), which this repository composes but does not itself
prove for every possible governed record. The claim is restated to name
exactly what is certified -- "current one-shot composition branch and
exercised DQ-library behavior in scenarios/tests" -- rather than an
unscoped termination claim over all possible buffer substitutions.

**Statement (scoped).** For the current one-shot composition branch and
the DQ-library behavior exercised in this artifact's scenarios/tests,
buffer substitution is idempotent, `rho(rho(a)) = rho(a)`, and
`E(rho(a))` consists of governed records the evidence gate admits by
construction; hence no further remediation is generated and the
protocol reaches a fixed point after at most one remediation. This is
not claimed to hold for every possible governed record or for any DQ
predicate contract beyond what this artifact exercises.

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

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Largest scope
certified (`review/REVIEW.md`, Section 3): the current one-shot
composition branch and exercised DQ-library behavior in
scenarios/tests. The argument depends on `sarc_dq.gate.PreActionGate`'s
own predicate contract (that a governed, freshly-dated, complete,
single-source record cannot re-trigger the predicates that produced the
substitution) -- an external engine guarantee this repo composes but
does not itself re-verify from the engine's internals, per the standing
"engines are installed libraries, not modified" invariant. No dedicated
checker in this repository proves the engine's predicate contract for
every possible governed record; the repository verifies its OWN
one-shot (never looping) remediation code path and the DQ-library
behavior it actually exercises in scenarios/tests
(`test_audit_unit.py`'s W2/downroute and evidence-substitution tests).

---

## Theorem 1 (soundness of remediate_regate composition)

**Statement.** Under Lemma 1 and gates that are functions of `(action,
context, evidence, current state)`, the remediate_regate protocol
satisfies Definition 3 (per-action soundness): Phase II evaluates every
gate on `a_exec` itself, and the join preserves every Held verdict.

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
produced that join, because they are the SAME evaluation.

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Retagged per
round-two independent review finding R2-N2 (`review-r2/REVIEW-R2.md`).
Largest scope certified: current code path under Lemma 1 and the
five-response join. `checkers/lattice_check.py` exhaustively certifies
Proposition 2's monotone-hardening law -- the join mechanism this proof
leans on -- over the full finite `Response` lattice (17,151 checks), but
that certifies the join mechanism, not Theorem 1's own premises for
arbitrary gates, arbitrary action spaces, or arbitrary current-state
transitions, nor Lemma 1's external DQ predicate contract this theorem
also depends on. Corollary 3 immediately after Corollary 1 below states
precisely what the lattice checker does certify. CH1's 30-seed empirical
audit (zero violations on every seed, `out/results/sweep_summary.json`)
corroborates this on real data without substituting for the proof.

---

## Corollary 1 (single-pass soundness, sufficiency only -- weakened per independent review finding F3)

**Statement.** If the authority and resource gates are invariant under
`rho` (the remediation map) on the executed-reachable action set, then
single-pass is sound. **The converse ("only if") is dropped, not
proved.**

**Why this changed.** The prior draft stated this as an iff. The
independent review (`review/REVIEW.md`, finding F3) gave a concrete
counterexample to the necessity direction: let the authority gate vary
under `rho` only on actions DQ independently holds -- those actions
never execute (Held subsumes them regardless of what the authority gate
would have said), so single-pass can be fully sound in practice while
the gate is, strictly speaking, non-invariant under `rho`. Non-invariance
restricted to never-executed actions costs nothing observable; the
necessity direction implicitly assumed invariance was required
everywhere `rho` is defined, not just on the actions that can actually
reach execution, and that assumption is false. No reachability/
executability condition is added to recover the iff here -- the simpler,
honest fix is to state only what is actually proved.

**Proof (sufficiency).** From Theorem 1's join argument: Phase II
evaluates every gate on `rho(a)`, and the join preserves every Held
verdict there. If the authority/resource gates are invariant under `rho`
on the actions that end up executed, their single-pass verdicts
(computed on the original action `a`) equal their remediate-regate
verdicts (computed on `rho(a)`) for exactly those actions, so
single-pass inherits soundness on them from Theorem 1.

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Retagged per
round-two independent review (`review-r2/REVIEW-R2.md`): largest scope
certified is sufficiency on executed-reachable actions under Lemma 1 and
invariance of downstream gates. The necessity direction is properly
retracted above, not weakly supported under any tag. The sufficiency
proof is a structural argument from the code path via Theorem 1's
join argument -- not itself exhaustively re-derived over an unbounded
arbitrary action space, but resting on the same finite lattice-backed
join mechanism Corollary 3 below certifies, which is why this carries
`checked-scope-only` rather than the more generic `pending-human-review`
it carried before this round's retag.

---

## Corollary 3 (finite response-lattice encoding of remediate_regate soundness)

**Statement.** For this artifact's finite `Response` lattice
(`|Response| = 5`) and the join-hardening property `checkers/
lattice_check.py` exhaustively verifies (17,151 checks over tuples of
length 1 through 4): no combination of Phase-II per-gate responses drawn
from this five-value lattice can have its join equal `ADMIT` while any
individual response in that combination is Held (`escalate` or
`block`). This is the exact finite mechanism Theorem 1's join argument
invokes, verified over its entire domain -- not an instantiation of it,
the full domain the checker enumerates.

**PROOF-STATUS: machine-checked** (`checkers/lattice_check.py`;
enumerated domain: `Response^k` for `k = 1..4`, `|Response| = 5`,
17,151 total law checks across idempotence, commutativity,
associativity, monotone hardening, duplication invariance, and the
empty-join case; `out/checkers/lattice_check.json`).

---

## Proposition 4 (identity commitment and integrity, relative to a content-addressed store) -- restated per independent review finding F2

**Why this changed.** The prior statement here claimed the unified
Evidence Set line lets one "reconstruct, content-addressed, exactly the
records each gate relied on" -- language that reads as byte
reconstruction. The independent review (`review/REVIEW.md`, finding F2)
correctly refuted that: a substituted line carried a post-Phase-II
`evidence_id` and a numeric `substituted_value`, but no original bytes,
no original metadata, and no record of which prior buffer write the
substituted value came from. A content-addressed hash is not invertible
-- it commits to content, it does not carry the content. The claim was
materially stronger than what the emitted evidence actually supported.

**Fix (schema v2, `pre_evidence_ids` / `substitute_source`).** Every
substituted line now additionally records `pre_evidence_ids` (the
Phase I evidence ids the gate actually evaluated before substitution)
and `substitute_source` (`buffer_key`, plus `buffer_write_eid` -- a
content-addressed id for the specific `(key, value)` governed-buffer
write the substituted value came from; `composition._buffer_write_eid`,
`schemas/evidence_line.schema.json` v2). This does not make hashes
reversible. It makes the claim about what they *do* provide precise
instead of overstated.

**Statement.** From an executed action's unified Evidence Set line
alone, one can (a) **identify** -- by content-addressed id, not by
opaque reference -- every record each phase relied on, including the
Phase I evidence the gate evaluated before any substitution
(`pre_evidence_ids`) and the specific governed-buffer write a
substitution drew from (`substitute_source.buffer_write_eid`); (b)
**verify** those ids, given access to the record store and the
governed buffer's write history (not from the line alone): recomputing
`EvidenceRecord.evidence_id()` over a candidate record and comparing it
to the id in the line either confirms or refutes that the candidate is
the exact record relied on, since `evidence_id()` is a deterministic
function of content and two records sharing an id are byte-identical by
construction; and (c) **resolve** the original bytes, given that same
store access -- the line is the pointer and the integrity check, the
store is where the bytes live. The line alone, with no store, gives
identity and an integrity check; it does not give bytes.

**Proof.** `composition.evaluate_dq` -> `GateDecision.evidence_ids`
already recorded the content-addressed ids of every record passed to
`spec.evaluate`, unchanged from v1 -- see `gates.dq.evidence_ids`. Schema
v2 additionally requires `pre_evidence_ids` (Phase I ids, before
substitution) and `substitute_source` inside
`remediation.evidence_substitution` whenever it is non-null
(`schemas/evidence_line.schema.json`, `required` on both fields,
`additionalProperties: false` throughout so no undeclared channel exists
to smuggle in inconsistent data). `_buffer_write_eid(key, value)` is a
pure SHA-256 function of exactly the two values that determine a
governed-buffer write's content, so identical writes always yield
identical ids and distinct writes (by key or value) always yield
distinct ids with overwhelming probability (`test_buffer_write_eid_is_content_addressed`,
`test_audit_unit.py`) -- the same content-addressing property
`EvidenceRecord.evidence_id()` already has. Given a store keyed by these
ids (the record store for `evidence_ids`/`pre_evidence_ids`, the
buffer's own write log for `buffer_write_eid`), a verifier recomputes
each id from a candidate stored object and compares; a match is proof of
identity (collision resistance of SHA-256 makes a false match
computationally infeasible), a mismatch is proof of divergence. Nothing
above claims the id determines the content in the other direction --
hashes are one-way by construction, so bytes are never recoverable from
the id alone. Authority and resource gate sections are unchanged from
v1 (`constraints_evaluated`, `predicted_cost`/`predicted_carbon`/`budget_state`)
and were never part of the refuted claim.

**Update (R2-F6(a), durable buffer write-history log).** Since the
round-two review ran, `substitute_source.buffer_write_eid` no longer
identifies a write by content hash alone. Every `evaluate_dq` admit now
appends an event to a run-scoped, append-only write log
(`composition._record_buffer_write`: `write_seq`, `key`, `value`, `day`,
and an `event_id` hashing all four), seeded with one genesis entry per
SKU from the buffer's pre-run known-good values
(`composition._seed_genesis_writes`) so even a substitution that traces
back to the buffer's initial state -- possible on a SKU's very first
decision -- resolves to a real entry, not nothing. A substitution's
`buffer_write_eid` is resolved against this log
(`composition._resolve_buffer_write_event`: most recent prior write to
the same key with the same value) and persisted alongside the evidence
lines as `<scenario>-<mode>-buffer-writes.jsonl`. This directly answers
the review's own provenance probe (3,478 substitution occurrences
resolving to only 62 unique ids under the old key+value-only hash):
`test_repeated_identical_writes_stay_individually_resolvable`
(`test_audit_unit.py`) reproduces that exact repeated-write pattern and
asserts each substitution still resolves to exactly one write-log entry.

**PROOF-STATUS: checked-scope-only (REVIEW.md).** Retagged per
round-two independent review (`review-r2/REVIEW-R2.md`): largest scope
certified is schema-v2 field presence and deterministic key/value hash
commitments. Schema v2's `required` fields on
`remediation.evidence_substitution` are confirmed present and
well-formed on real substituted lines by
`test_provenance_fields_validate_against_schema_v2` and the fuzzed
`test_randomly_sampled_lines_validate_against_schema_v2`, and the write
log's content-addressing property is directly unit tested -- these are
not exhaustive-finite-model checks under `checkers/`, so this does not
carry `machine-checked` (round-two finding R2-N2's linter rule: that tag
requires a named executable checker module and enumerated domain). The
durable write-history log above resolves the specific-write-event-
identity residual the round-two review flagged, but store-backed
resolution (verifying a candidate record/write against an actual
persistent store, not just this run's own JSONL log) remains outside
what any test here exercises; this tag is not retroactively upgraded to
`machine-checked` on the strength of this repo's own unit tests without
a further review certifying it. This tag covers the identity-commitment
and schema-shape claim specifically -- it does not and cannot cover
"bytes are recoverable from hashes," because that claim is explicitly
disclaimed rather than made.

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

**Off-grid probe (promoted per independent review; seed fixed per
round-two review finding R2-N1/R2-F1).** The 243-point grid above is a
finite lattice of round numbers. The independent review
(`review/REVIEW.md`, Section 5) additionally probed continuous-valued
points off that lattice and found 144/200 non-confluent.
`checkers/remediator_check.py` runs this class of probe itself on every
invocation (`random_off_grid_points`): 200 continuous points strictly
inside the grid's outer bounds, never on a grid coordinate, checked with
the same real remediation functions. This probe's seed was originally
HEAD-derived (`sha256(git HEAD)`), the same technique established for
the F1 lemma verification in `checkers/compensation_check.py` -- but
that made the published non-confluent count drift with every commit,
which the round-two independent review caught (`review-r2/REVIEW-R2.md`,
finding R2-N1: the response commit's paper reported 140/200 while a
`make formal` rerun at the same commit produced 145/200). The seed is
now a fixed constant declared in `prereg/probe-seeds.json` (dated after
`prereg-v1`, since this probe itself postdates `prereg-v1`), so the
published count is commit-stable: `out/checkers/remediator_check.json`'s
`off_grid_probe.non_confluent_count` out of `off_grid_probe.n_probes` =
200. It does not reproduce the reviewer's own exact 144/200 (a
different, independently drawn probe), but confirms the same off-grid
non-confluence beyond the pre-registered grid, and no longer drifts on
rerun at a fixed commit or across commits.

**PROOF-STATUS: machine-checked** (`checkers/remediator_check.py`;
enumerated domain: the 243-point finite grid,
`out/checkers/remediator_check.json`; the sample counterexample is
independently re-derived, not just read back from the checker's own
report, in `test_checkers.py::test_remediator_check_non_confluent_counterexample_is_reproducible`;
the off-grid probe above is a supplementary, non-exhaustive finite
sample and does not itself extend the machine-checked scope beyond the
243-point grid).
