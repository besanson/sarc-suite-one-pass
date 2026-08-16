# INDEPENDENT AGENT REVIEW PROTOCOL, ROUND 4 (TERMINAL DISPOSITION): sarc-suite-one-pass

You are an independent reviewer agent issuing the FINAL disposition on
this artifact, the analogue of a journal's post-revision acceptance
decision. Round three found two severity-2 release defects and scored
8.5 and 8.0; the author's closure response claims both are fixed by
design. Your job: verify the closure fixes, re-run the core battery on
the release candidate, reissue scores under the identical calibration of
rounds one to three, and account for every withheld point explicitly.
You review, you never fix, you never edit the repo. Evidence beats
prose; anything unverifiable is UNVERIFIED, never passed.

## Terminal rule (binding, print it in your report header)

This is the terminal reviewer round. The scores you issue stand as the
released official scores, except through one mechanism: your own
conditional disposition, whose required changes are verified by the
external adjudicator, never by a further reviewer round. Only a
severity-1 finding blocks release. Severity-2 and below become recorded
known issues and block nothing. There is no round five under any
outcome, and you must not recommend one.

## Ground rules

Fresh empty directory; clone only from
https://github.com/besanson/sarc-suite-one-pass. Bootstrap via the
repository's own bootstrap.sh, which pins engines and provisions the
canonical Tectonic; deviations you need are findings. Outputs only to
sibling ./review-out-r4. All randomness derived from HEAD sha,
derivations recorded. Network only for cloning, pinned installs,
Tectonic's bundle fetch, and re-fetching verified-citations.json URLs.
Treat all committed review folders as prior findings to audit, not as
facts about this commit. Your report states it is an automated review,
round 4, terminal.

## Phase R0: provenance and chain integrity

Record HEAD sha, tags, commit order. Verify prereg-v1 tree contains no
results. Verify the committed round-three package is unedited:
sha256(review-r3/REVIEW-R3.md) equals
8a3da7bf580b6d3560065dd60089b7974b3dbad3c6a4a66cf8a0281e2acda927 and
sha256(review-r3/review.json) equals
4d6dd5672cd5fdc653efe3837877c45c0b0fcc4f1e53e5dab12ab17be6857ddd.
Mismatch is severity 1.

## Phase R1: closure-fix audit (R3-F1, R3-F2, R3-F3, known issues)

With your own probes, issue RESOLVED, PARTIALLY-RESOLVED, UNRESOLVED, or
REGRESSED for each: inputs-hash provenance, recompute every committed
formal artifact's inputs_hash from the current tree and assert equality,
then touch a checker input and confirm make paper regenerates;
release-check, run `make release-check` end to end and record every
stage; compiler-aware gates, run make arxiv under Tectonic, twice, and
under latexmk if present, and confirm the parity report emits raw
totals, enumerated exceptions, and post-exception totals with the
compiler named per build; KNOWN-ISSUES.md present and accurate,
including your adjudication of the author-disclosed informational
head-stamp that references an amended-away sha while inputs_hash
remains the authoritative freshness.

## Phase R2: core battery at the release candidate

Full test suite including slow tests, with counts and reasons for any
skip; three committed-artifact seed replays, 26313, 1028331701, and one
HEAD-derived from the registered list, byte-compared with wall-clock
evidence; recomputation of every mean and interval in sweep_summary at
1e-6; checker reruns including the CH7 counterexample and fixed-seed
probe replayed through composition code, plus one adversarial
weight-family probe of your own against the corrected Proposition 1;
mutation sampling of 150 HEAD-derived mutants against the committed
kill score with a binomial interval; ground-truth leakage scan across
all scenario lines; citation re-fetch of all ten; PDF content
extraction with your stated normalisations verifying the three-round
disclosure verbatim, wrap-tolerant tag counts 21, 26, 7, and
number-multiset parity under the enumerated typesetting exceptions.

## Phase R3: final disposition

1. Refreshed verdict table for C1 to C9 and CH1 to CH8, same verdict
   vocabulary, with delta-from-round-three reasons.
2. Findings by severity, if any, under the terminal rule.
3. Scores under the identical calibration of rounds one to three, one
   paragraph of justification each.
4. REMAINING DEDUCTIONS AND REQUIRED CHANGES, mandatory section: every
   point withheld from 10 in each lens must be accounted for as exactly
   one of
   (a) a named finding from this round, with severity, AND a concrete,
   mechanically verifiable remedy: the exact files, behaviours, or
   tests whose change would close it, the peer-review sense of
   required changes; or
   (b) a named permanent caveat that the paper itself already states,
   labelled PERMANENT-BY-DESIGN, for example honest mechanism-not-
   prevalence scoping or pending-human-review proof tags, for which no
   remedy exists short of changing what the paper honestly claims.
   No unattributed deductions are permitted: if you cannot name the
   reason and, for closable reasons, the remedy, you may not withhold
   the point.
5. CONDITIONAL DISPOSITION, mandatory: sum the closable deductions.
   If implementing every required change from item 4(a) would bring a
   lens to 9.0 or above under this calibration, state conditional
   scores explicitly: "Upon exact implementation of required changes
   R1..Rk, verified mechanically by the external adjudicator, the
   released official scores become X and Y. No further reviewer round
   occurs; adjudicator compliance verification suffices." If the
   PERMANENT-BY-DESIGN caveats alone hold a lens below 9.0, state
   plainly: "9.0 is not reachable under this calibration; the binding
   permanent caveats are the following", and list them. One of these
   two statements must appear for each lens.
6. Disposition line: RELEASE, RELEASE-WITH-REQUIRED-CHANGES (conditional
   scores pending adjudicator verification), or BLOCKED (severity-1
   only), stated plainly.
7. The disclosure paragraph updated to four rounds, verbatim, for the
   author's reuse.

Write review-out-r4/REVIEW-R4.md and the review.json mirror, attach all
evidence under review-out-r4/evidence/, and stop.
