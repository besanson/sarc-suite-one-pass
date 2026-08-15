# Known Issues

Non-blocking issues recorded per the round-three independent review's
closure rule: severity-3-and-below findings are known issues, not fix
obligations — they do not block release and do not trigger a further
review round. This file exists so each one is documented once, in one
place, rather than only living in a review report.

## R3-F3: G3's parity report showed raw totals without the enumerated exception that explains them

**Severity 3 (round-three independent review). Non-blocking. No further
review round triggered.**

Before the round-three response, `paper-tex/parity-report.json`'s G3
(number parity) gate reported raw numeric-token totals of 689 (Markdown)
and 688 (PDF) alongside an *empty* post-exception diff, with no
intermediate accounting shown. The 689-vs-688 gap has a single, already-
understood cause — math-mode `$2^{31}$` (Appendix C's `[1, 2^31-1]`
range) has its superscript `31` concatenated onto the base `2` with no
separator by `pdftotext`, since PDF's text layer carries no baseline-
shift marker, so it extracts as the token `231` instead of the two
tokens `2` and `31`. This was already allowlisted in code
(`KNOWN_EXTRACTION_ARTIFACTS`) before round three; the gap between the
raw totals and the empty diff was reporting sloppiness, not a content
discrepancy or an unaccounted defect.

**Resolution status: fixed as part of the round-three response.**
`gate_g3_number_parity()` in `paper-tex/gates/run_gates.py` now reports
three explicit tiers instead of only the last one: `raw_totals` and
`raw_diff` (before any exception), `exceptions_applied` (the enumerated
allowlist itself, with a `matched` flag per entry), and
`post_exception_totals` / `post_exception_diff` (what G3 actually gates
on). The raw 689/688 totals and the single superscript-flattening
exception are now both visible in `paper-tex/parity-report.json`
directly, closing the reporting gap the review flagged.
