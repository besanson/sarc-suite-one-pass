# INDEPENDENT AGENT REVIEW PROTOCOL, ROUND 2: sarc-suite-one-pass

You are an independent reviewer agent conducting the SECOND review of this
repository. Round one produced findings F1 to F6; the author claims a
response commit fixed them. Your job: re-execute the full review battery
on the current HEAD, audit the response finding by finding with your own
probes, and report deltas against round one. You are reviewing, not
fixing. Evidence beats prose. Anything you cannot verify is UNVERIFIED,
never passed. You never edit the repository.

## Ground rules

1. Fresh, empty working directory. Clone only from
   https://github.com/besanson/sarc-suite-one-pass. No other inputs.
2. The repo now contains review/ (the round-one report). Treat its
   FINDINGS as the author's fix obligations to verify, and its VERDICTS
   as claims about an older commit, not as facts about this one. Do not
   let it substitute for your own probes.
3. All outputs to a sibling ./review-out-r2, never into the repo.
4. Any randomness you use derives from the current HEAD sha; record the
   derivations.
5. No LLM or network calls except cloning, installing pinned
   dependencies, and re-fetching every URL in verified-citations.json.
6. Your report states it is an automated review, round 2, and may not be
   phrased to pass as human peer review.

## Phase R0: provenance, including review integrity

Record HEAD sha, tags, and the full commit-order listing. Verify:
prereg-v1 tree still contains no results; the commit sequence now ends
with the review commit followed by the response commit; and the
committed round-one report is byte-unedited by hashing it against these
reference values, which were computed from the reviewer's original
package before the author touched it:

- review/REVIEW.md sha256 must equal
  e11dbfdc574820c096dbcf968547b7e3298add4d9fbff852a4c1665d2e57441d
- review/review.json sha256 must equal
  55a02026644195e7ecfac32eed993dc799537dc628b58c036e8a0719713ad37d

A mismatch is an automatic severity-1 finding. Then bootstrap exactly
per the repo's own instructions and engines.lock at the pinned shas.

## Phase R1: full mechanical replication (same as round one)

Full test suite with counts and skip reasons; make suite and make paper
with runtimes and exit codes; engine clones git-clean after runs; source
data sha unchanged; schema validation of a HEAD-derived sample of 200
Evidence Set lines against the CURRENT schema version, and confirm the
schema version bump is coherent (every line carries the same declared
version and validates against it).

## Phase R2: statistics audit (same as round one)

Recompute every mean and interval in the sweep summary from the
per-seed artifacts; the repo now computes the t-critical value at
runtime, so apply the protocol tolerance of 1e-6 strictly and report any
residual deltas. Replay three seeds from scratch through the library
path, the first registered seed plus two HEAD-derived from the
registered list, with wall-clock evidence, byte-compared to committed
artifacts. Cross-check every number in the populated paper against a
machine source; any number without one is severity 1.

## Phase R3: formal claims audit (updated targets)

Rerun all checkers. Verify specifically: the restated Proposition 1
lemma holds on the declared grid AND on the recorded randomized probes,
and design one additional adversarial weight-vector family of your own
to attack it; the CH7 counterexample and the off-grid probe replay
through the actual composition code; the retracted necessity claim is
genuinely absent from the paper body, abstract, and claims table, not
merely footnoted. Classify every remaining pending-human-review
statement under the round-one taxonomy, and flag any statement whose
tag claims more than an executable check certifies.

## Phase R4: adversarial probes

At least three falsification probes of your own design, chosen after
reading the response diff (git show the response commit). Mandatory in
addition: hand-entered-number scan; ground-truth leakage scan across all
lines of all scenarios; mutation sampling of at least 150 HEAD-derived
mutants of composition.py compared to the committed kill score with a
binomial interval; re-fetch and match every entry in
verified-citations.json, now ten entries, title and first author; count
[CITE tokens in the populated paper and reconcile with the repo's own
claims; verify the disclosure paragraph appears verbatim in the paper's
validation note.

## Phase R5: response audit, finding by finding

For each of F1 to F6 in review/REVIEW.md, verify the fix with your own
probes on the current code and paper, and issue exactly one verdict:
RESOLVED, PARTIALLY-RESOLVED, UNRESOLVED, or REGRESSED, with evidence.
Specifically probe, at minimum: F1, the new lemma's statement matches
what the checker checks and the acknowledged counterexample is cited;
F2, substituted lines carry original evidence ids and content-addressed
substitute provenance, and Proposition 4's wording claims identity
commitment relative to a store, not byte reconstruction; also examine
whether Phase II predicate lists are populated or their emptiness is
documented in the schema, and report which; F3, sufficiency-only
wording everywhere the old iff appeared; F4, the audit loads persisted
exact executed evidence rather than reconstructing synthetic records,
and CH1's reported value comes from that audit; F5, all ten citations
re-fetched and matched; F6, runtime t-critical and interval agreement.

## Phase R6: the report

Write review-out-r2/REVIEW-R2.md and review.json mirror. Structure:
1. Identity: automated agent, round 2, model, date, HEAD sha, protocol
   file name.
2. Response-audit table: F1 to F6, verdict, evidence.
3. Fresh verdict table for C1 to C9 and CH1 to CH8 on the current HEAD,
   same verdict vocabulary as round one.
4. Delta table: round-one verdict versus round-two verdict per claim,
   with one-line reasons for every change.
5. New findings ranked by severity, if any, with reproduction steps.
6. Statistics audit summary with the three replays.
7. Fresh scores under the same calibration as round one: research lens
   and engineering lens out of 10, where 10 requires zero severity-1 or
   severity-2 findings and all claims CONFIRMED or
   CONFIRMED-WITH-CAVEAT with caveats the paper itself states.
8. The disclosure paragraph, verbatim, updated to reference both
   rounds.
Attach all evidence under review-out-r2/evidence/. Stop when the report
is written.
