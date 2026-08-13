# Protocol Rename: `two_phase` -> `remediate_regate` ("rtr")

Status: PRE-REGISTRATION. Definitions only — no code changed yet (executed
in Phase 2, per this document).

## Rationale

"Two-phase" collides in readers' minds with two-phase *commit* (the
distributed-transactions protocol), which this is not — there is no
coordinator, no prepare/commit handshake across participants, and no
distributed-consensus concern. The actual mechanism is: evaluate the
remediating gate(s), apply remediation where one fires, then re-gate the
remediated action against every gate. `remediate_regate` names that
mechanism directly; `rtr` is the short form used in code identifiers,
CLI flags, and output filenames where `remediate_regate` is unwieldy.

`single_pass` is unaffected by this rename — it already names its own
mechanism plainly and does not collide with anything.

## Scope of the rename

Renamed everywhere `two_phase` currently appears:

- **Code**: `CompositionEngine.two_phase()` -> `.remediate_regate()` (and
  the module-level references to it in `runner.py`, `metrics.py`); the
  `mode` field's value `"two_phase"` in every Evidence Set line ->
  `"remediate_regate"`; local variable and parameter names that spell out
  `two_phase`.
- **Tests**: `test_suite_sim.py` function/variable names and fixture
  data.
- **Outputs**: file name components (`two_phase-evidence.jsonl` ->
  `rtr-evidence.jsonl`, etc.), the `mode` value inside `out/metrics.json`
  and every Evidence Set line, `ch2_direction_counts` key text stays as
  registered in `ch2-semantics.md` (the keys themselves are not renamed,
  only the internal `two_phase`/`single_pass` mode label they compare
  against).
- **Paper**: every prose and table reference to "two-phase" ->
  "remediate-regate", "Protocol (two-phase composition)" heading ->
  "Protocol (remediate-regate composition)". Proposition/theorem/lemma
  *numbers* and their formal statements are unaffected; only the
  protocol's name changes. `paper4-composition-draft` v0.3 (Phase 5)
  uses the new name throughout; v0.1/v0.2 (the 8.5 artifact's frozen
  history) are left untouched as historical record.
- **README / ADR-001**: updated to the new name; ADR-001 keeps its
  historical "two-phase" wording inside the pre-repair and repair
  sections unchanged (those describe what was true *at the time*), and
  gains a short note in the Repair section pointing at this file for the
  rename's rationale and date.

## What does NOT change

- The mathematical content of Definition 2, Lemma 1 (idempotent
  substitution), and Theorem 1 (soundness) — only the protocol's name in
  prose and code.
- `single_pass`'s name, semantics, or file-name components.
- The restrictiveness lattice, the join, or any response string other
  than the `mode` field.

## Acceptance

After the rename executes (Phase 2), `grep -ri "two_phase" composition.py
runner.py metrics.py test_suite_sim.py` returns nothing except this
file's own historical-context references and ADR-001's dated Repair
section (both explicitly exempted above).
