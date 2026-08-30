# Replications

Independent third-party replications of this artifact: reproductions
run by outside parties after release, distinct from the commissioned
adversarial review rounds tracked in the README's
[Review chain](README.md#review-chain). Entries here are attributed
under the replicator's current organisation name; where that name has
since changed, the name in effect at publication time is recorded
alongside it, since this file is a historical record and should not be
silently rewritten as organisations rename themselves.

## Replication 1

**Moona Intelligence** (published 28 August 2026 under the
organisation's then-name, Belay Intelligence, since renamed), 28
August 2026.

Independent clean-clone reproduction: bootstrap, `make all`, and `make
release-check` all passed; 207 tests, formal checkers, and
byte-identical double paper builds confirmed. Eight additional
adversarial authority tests on a separate branch, zero edits to
existing code; results: one positive control confirming
Remediate-Regate correctly reauthorizes a changed order value, four
coverage boundaries of the configured authority policy (resource
identity, actor identity, temporal validity, execution-specific grant
binding), and two documented scope limits confirmed as documented.

Report: <https://moona.ozlunara.com/intelligence/sarc-suite-remediate-regate-authority-coverage-boundary>
(published at: <https://belay.ozlunara.com/intelligence/sarc-suite-remediate-regate-authority-coverage-boundary>)
