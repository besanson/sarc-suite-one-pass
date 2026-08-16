# INDEPENDENT AGENT REVIEW PROTOCOL: sarc-suite-one-pass

You are an independent reviewer agent. You did not build this artifact, you
have no access to its build transcripts, and your job is to try to break
it, then report what survived. You are reviewing, not fixing: you never
edit the repository under review. Evidence beats prose: README and ADR
narratives are claims to test, not facts to accept. Anything you cannot
verify is reported UNVERIFIED, never passed. Stop when the report is
written.

## Ground rules

1. Fresh, empty working directory. Clone only from
   https://github.com/besanson/sarc-suite-one-pass. No other inputs.
2. Read-only review: all your outputs go to a sibling directory
   ./review-out, never into the repo. If something is broken, you report
   it with reproduction steps; you do not patch it.
3. Determinism of your own probes: any random choice you make must be
   derived from the repo HEAD sha so the author could not have
   precomputed it and you can be replayed. Record every derivation.
4. No LLM or network calls except: cloning, installing pinned
   dependencies, and re-fetching the citation source URLs listed in
   verified-citations.json.
5. Your report states plainly that you are an automated reviewer. Nothing
   you write may be phrased to pass as human peer review.

## Phase R0: environment and provenance

Clone the repo; record HEAD sha, tag list, and full commit-order listing
with dates. Verify: the prereg-v1 tag exists on origin and its tree
contains no results (git ls-tree -r prereg-v1, assert nothing under out/
or results paths); commit order is P0, prereg, P2 hardening, P3 results,
P4 formal, P5 paper, with results entering history only after the prereg
tag's commit. Bootstrap exactly per the repo's own instructions and
engines.lock: clone the three engines at the pinned shas, editable
install, install test dependencies. Any deviation you need to make to get
it running is itself a finding.

## Phase R1: mechanical replication

Run the full test suite; record counts, failures, skips with reasons.
Run make suite and make paper; record runtimes and exit codes. Assert
after all runs: the three engine clones are git-clean; the source data
file's sha256 is unchanged; the schema in schemas/ validates a random
sample of 200 Evidence Set lines (sample indices derived from HEAD sha).

## Phase R2: statistics audit

From out/results/sweep/seed_*.json recompute every mean and CI reported
in out/results/sweep_summary.json using a t-interval with n minus 1
degrees of freedom; assert agreement to 1e-6 or report the delta.
Randomly select three seeds, the first registered seed plus two chosen by
hashing HEAD, and recompute them from scratch through the library path
(bypass any cache; verify by wall-clock time being non-trivial and by
writing to your own directory); compare byte-for-byte to the committed
per-seed artifacts. Cross-check every number that appears in
paper4-composition-draft-v0.3-populated.md against out/metrics.json,
sweep_summary.json, out/quality.json, or the checker outputs; any number
in the paper with no machine source is a severity-1 finding.

## Phase R3: formal claims audit

Rerun the three checkers; confirm the lattice laws pass exhaustively,
Proposition 1 confirms on the declared encoding, and the CH7
counterexample replays: instantiate the recorded non-confluent instance
through the actual composition code and confirm the two remediation
orders reach different executed actions. Then classify each
PROOF-STATUS: pending-human-review statement in the paper's appendix,
one by one, as exactly one of:
- verified-by-agent: you independently re-derived the argument AND its
  general form is fully covered by an executable check you ran;
- checked-scope-only: the machine check covers a finite model but the
  stated theorem is broader; state the largest scope you can certify;
- insufficient: the argument has a gap; identify the exact step;
- error-found: the statement is wrong; give the counterexample.
You never edit tags in the paper. Classification goes in your report;
resolution is the author's follow-up under the policy in Appendix A.

## Phase R4: adversarial probes

Design and execute at least three falsification probes of your own
beyond this checklist, chosen after reading the code, and report each
with outcome. Mandatory probes in addition: grep the entire repo for
hand-entered result-like numerals in code that feed any reported metric
(constants must be declared parameters, not results); attempt a
ground-truth leakage scan across every Evidence Set line in every
scenario; verify the mutation kill score by rerunning mutation testing
on a HEAD-sha-derived sample of at least 150 mutants of composition.py
and comparing the sampled kill rate to out/quality.json within a
binomial 95 percent interval; re-fetch each URL in
verified-citations.json and confirm title and first author match; count
[CITE tokens in the populated paper and confirm the count matches what
the repo's own release output claims.

## Phase R5: the report

Write review-out/REVIEW.md and review-out/review.json (machine-readable
mirror). REVIEW.md structure, fixed:
1. Reviewer identity: automated agent, model name, date, protocol
   version, repo HEAD sha reviewed.
2. Verdict table: one row per claim C1 to C9 and hypothesis CH1 to CH8,
   columns claim, evidence checked, verdict in {CONFIRMED,
   CONFIRMED-WITH-CAVEAT, UNVERIFIED, REFUTED}, note.
3. Proof classification table for every pending-human-review statement.
4. Findings ranked by severity with reproduction steps.
5. Statistics audit summary including your three-seed replications with
   wall-clock times and hash comparisons.
6. Two scores with one-paragraph justifications: research-artifact lens
   and software-engineering lens, out of 10, calibrated so that 10
   requires zero severity-1 or severity-2 findings and all claims
   CONFIRMED.
7. Disclosure paragraph, verbatim, for the author to reuse: "This
   artifact was independently replicated and adversarially reviewed by
   an automated agent following the published protocol in
   sarc-suite-agent-review.md; the full report and evidence are at
   <path/link>. Automated review complements and does not replace human
   peer review."
Attach in review-out/evidence/: run logs, recomputed CI table, replay
hashes, mutation sample results, citation fetch records, probe scripts.

## Appendix A: author follow-up policy (not the reviewer's job)

For the author's builder agent after the review lands: commit REVIEW.md
and evidence into the repo unedited; address severity-1 and severity-2
findings; PROOF-STATUS tags may change only as follows:
verified-by-agent becomes "independently agent-verified (REVIEW.md)";
checked-scope-only requires weakening the stated theorem to the
certified scope or leaving the pending tag; insufficient or error-found
requires fixing or retracting the statement. Update the release
checklist: the named-human-validator item and the ownership-confirmation
item are recorded as waived by the founder and replaced by this
disclosed automated review, per ADR-003 and the founder's decision of
2026-08-13. The disclosure paragraph must appear in the paper's
validation note and in any announcement that cites this review.
