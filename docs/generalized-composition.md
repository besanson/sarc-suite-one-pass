# Generalized composition: a future-work design note

This note is deliberately framed as future work, not an additional
claim. It describes a generalization of the composition model this
artifact certifies, and the open theoretical properties that
generalization would require. Nothing in this document is checked,
proven, or measured by this artifact; it changes no result, no claim
semantics, and no PROOF-STATUS tag anywhere else in the repository.

## What the current artifact certifies

Paper v0.4 (`paper4-composition-draft-v0.3-populated.md`, filename kept
by policy) is precise about the scope it has actually machine-checked
or construction-verified:

- a **finite response lattice** (`composition.Response`, five values,
  the `Exec`/`Held` partition and the total order over it), exhaustively
  checked (`checkers/lattice_check.py`);
- **one-shot evidence substitution**: the evidence gate's remediation
  operator, applied at most once per action per the termination lemma's
  idempotence argument;
- **one resource-budget downroute operator**, the second remediation
  operator introduced for the W2 workflow;
- a **fixed remediation order** (evidence gate, then resource gate),
  justified precisely because the checker shows the two implemented
  operators do not commute (CH7);
- **per-action soundness** (Definition 3): every gate is satisfied by
  the executed action at execution time, for that action, given the
  state in force when it runs;
- **no general concurrency, termination, or confluence theorem** for
  systems with more than these two remediation operators.

## The generalized model

Where the current artifact tracks one action through at most two
remediation operators applied in a fixed, pre-registered order, a
generalized composition model would instead iterate a remediation
function over an action-and-state pair until it reaches a fixed point
or a Held verdict:

```text
(a_t, S_t) -> R(a_t, S_t)
```

applied repeatedly until either

```text
(a_{t+1}, S_{t+1}) = (a_t, S_t)
```

(a fixed point) or the composed verdict reaches a Held state (the
process stops because the action is no longer executable, not because
it converged).

This is a strict generalization of the current artifact's setting:
setting `R` to the two-operator, fixed-order remediate-regate protocol
this artifact implements and proves per-action sound recovers exactly
the certified scope above.

## Open properties for future work

None of the following is established by this artifact, certified by
any checker in `checkers/`, or claimed by any tagged statement in the
paper. They are the properties a generalized, multi-operator,
possibly-concurrent composition system would need a separate theory
to establish:

- **Fixed-point semantics.** Under what conditions does iterating `R`
  reach a fixed point at all, as opposed to cycling or diverging?
- **Termination.** A bound on the number of remediation rounds before
  either a fixed point or a Held verdict is reached.
- **Confluence.** Whether every remediation order reachable from the
  same starting state converges to the same fixed point -- the
  question this artifact's CH7 checker answers *negatively* for its
  own two specific operators, motivating rather than assuming this
  property in general.
- **Cycle detection.** Whether a remediation sequence can return to an
  action-and-state pair visited earlier without reaching a fixed
  point, and how such a cycle would be detected and handled.
- **State consistency.** Whether concurrent updates to shared
  governance state (budgets, governed buffers) from remediation of
  different actions can themselves be composed soundly.
- **Serialization.** Whether a schedule of remediations across
  multiple concurrently governed actions can be given a serial
  equivalent, in the sense classical concurrency control gives
  transaction schedules.
- **Concurrent multi-agent coordination.** Whether the single-agent,
  single-action model here extends to multiple agents whose actions
  contend for the same governance state (shared budgets, a shared
  evidence buffer) without an explicit coordination protocol.

## Why this is out of scope for the current artifact

Establishing any of the properties above would require: new
operators beyond the two this artifact implements; a formal semantics
for concurrent state updates that the current single-threaded,
one-action-at-a-time simulation does not model; and a termination or
confluence proof technique (e.g., a well-founded ordering, or a
critical-pairs argument in the term-rewriting sense) that has not been
attempted here. None of this is implied by, or required to support,
any claim this artifact currently makes. The current artifact's own
claims-versus-non-claims table (in `RESEARCH-GUIDE.md` and the paper's
empirical-validation section) already states plainly that "general
convergence of arbitrary remediator systems" is not claimed; this note
exists to describe, precisely, what such a claim would need.
