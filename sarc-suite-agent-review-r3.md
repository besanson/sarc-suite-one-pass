# INDEPENDENT AGENT REVIEW PROTOCOL, ROUND 3 (CLOSURE): sarc-suite-one-pass

You are an independent reviewer agent conducting the THIRD and final
scheduled review. Round two issued findings R2-F1 to R2-F6 and scored the
repo 7.5 and 7.5; the author claims three subsequent commits resolved
everything and added an arXiv LaTeX package no reviewer has seen. Your
job: re-run the full battery on current HEAD, audit the round-two
response finding by finding, audit the LaTeX package for the first time,
and issue fresh scores under the same calibration as rounds one and two.
You review, you never fix, you never edit the repo. Evidence beats
prose. Anything unverifiable is UNVERIFIED, never passed.

## Closure rule (binding, stated up front)

This is the closure round. In your report, severity-1 and severity-2
findings are fix obligations. Severity-3 and below are recorded as known
issues for the repo's issue list and explicitly do NOT block release and
do NOT trigger a further round. Say this in your report's header.

## Ground rules

Fresh empty directory; clone only from
https://github.com/besanson/sarc-suite-one-pass. Outputs to sibling
./review-out-r3 only. All randomness derived from current HEAD sha,
derivations recorded. Network only for cloning, pinned installs, and
re-fetching verified-citations.json URLs. Treat committed review/ and
review-r2/ as prior findings to audit, not as facts about this commit.
Your report states it is an automated review, round 3.

## Phase R0: provenance and review-chain integrity

Record HEAD sha, tags, commit-order listing. Verify prereg-v1 tree still
contains no results. Verify the committed round-two report is unedited:
sha256(review-r2/REVIEW-R2.md) must equal
411c05f0efe7676fee2acb3dfdb099163d383b54b7dd547bb93765b0226b6a94, and
sha256(review-r2/review.json) must equal the value recorded in the
review-r2 commit message. Mismatch is automatic severity 1. Bootstrap at
the pinned engine shas per engines.lock.

## Phase R1: mechanical replication

Full test suite including slow-marked tests, with counts and skip
reasons; make all; runtimes; engines git-clean after; source data sha
unchanged; schema validation on a HEAD-derived sample of 200 lines.
Replay three seeds through the library path, the first registered seed,
seed 1028331701 explicitly, and one HEAD-derived from the registered
list, comparing byte-for-byte AGAINST THE COMMITTED per-seed artifacts,
not run-versus-run; the committed-artifact comparison is the point of
the round-two staleness fix and you are testing that it holds.

## Phase R2: statistics audit

Recompute every mean and interval in sweep_summary.json from per-seed
artifacts at 1e-6 tolerance. Cross-check every number in the populated
markdown paper against a machine source. Verify the freshness guarantee:
run make formal twice, outputs identical, values equal to what the paper
and slots embed.

## Phase R3: formal claims and tag scope

Rerun all checkers; replay the CH7 counterexample and the fixed-seed
off-grid probe through the composition code; verify the retracted
necessity claim remains absent; verify every machine-checked tag
attaches only to statements whose scope line names an executable checker
and its domain, and that checked-scope-only and pending-human-review
tags match the round-two taxonomy. Attack the restated Proposition 1
lemma with one adversarial weight family of your own design.

## Phase R4: response audit and adversarial probes

For each of R2-F1 to R2-F6 and the follow-up regeneration commit, issue
RESOLVED, PARTIALLY-RESOLVED, UNRESOLVED, or REGRESSED with your own
evidence, including at minimum: build-graph dependency real (touch a
checker input, make paper regenerates it); probe seed fixed and
commit-stable; fsum determinism on the previously failing metric;
schema documentation present; two-round disclosure verbatim; durable
buffer write log resolving every substitution to exactly one event;
reload audit actually loading persisted lines. Then at least three
falsification probes of your own design, plus the mandatory scans:
hand-entered numbers, ground-truth leakage across all scenario lines,
mutation sampling of 150 HEAD-derived mutants against the committed
kill score with a binomial interval, citation re-fetch of all ten.

## Phase R5: LaTeX package audit (first independent look)

In paper-tex/: rebuild from source with latexmk or tectonic; two builds
produce the same file list and page count. Then verify with YOUR OWN
extraction, stating your normalisations explicitly: number-multiset
parity between the markdown paper and the compiled PDF, where
typesetting-legitimate deltas (reference list, page furniture, date
stamps, superscript flattening such as 2^31-1 extracting as 231-1) are
enumerated and everything else must match; tag counts 21, 26, 7 present
under dehyphenated matching; disclosure and honesty banners verbatim;
refs.bib entries exactly the ten verified records and nothing else;
tarball contents arXiv-appropriate; arxiv-abstract.txt within arXiv's
1920-character limit and a faithful condensation adding no claim absent
from the paper. Adjudicate the committed parity-report.json's internal
G3 inconsistency (totals differ while diffs are empty) and say whether
it indicates artifact damage or reporting sloppiness.

## Phase R6: the report

Write review-out-r3/REVIEW-R3.md and review.json mirror: identity block
with round number, model, date, HEAD sha, protocol filename; the closure
rule statement; response-audit table; fresh verdict table for C1 to C9
and CH1 to CH8; delta table against round two with one-line reasons;
findings ranked by severity; statistics and replay summary with
wall-clock times; the LaTeX audit section; fresh scores under the same
calibration as rounds one and two, with one-paragraph justifications;
and the disclosure paragraph updated to three rounds, verbatim, for the
author's reuse. Attach all evidence under review-out-r3/evidence/. Stop
when the report is written.
