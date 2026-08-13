# ADR-003: Publication Posture — Publish for Audience, No Patent Claims on the Composition Layer

**Status**: Accepted
**Date**: 2026-08-13

## Context

This artifact's V6 human release checklist (`sarcsuite95upgrade.md`) gates actual publication on, among other things, a publication-posture decision: publish for audience, no patent claims on the composition layer. This record commits that decision.

## Decision: publish for audience, no patent claims on the composition layer

This artifact and its accompanying paper (`paper4-composition-draft-v0.1.md` through `v0.3-populated.md`) are published for an audience: researchers, engineers, and reviewers evaluating the composition semantics of pre-action gates for agentic AI systems. Specifically:

1. **No patent claims are made or reserved on the composition layer** described here — the restrictiveness lattice and join rule (Definitions 1-2), the remediate-regate protocol (Section 5), the second remediation operator and its non-commutativity result (CH7), the buffer-poisoning mitigations (CH6), or any other mechanism this repository documents. Nothing in this artifact is filed, pending, or intended to be filed as a patent application, and this ADR records that intent as of its date above.
2. Publication is under the repository's existing Apache License 2.0 (`LICENSE`), which already grants an express patent license from contributors to users for any patents they hold that would otherwise be infringed by the licensed work (Apache-2.0 §3). This ADR does not change the license; it records the additional, narrower commitment not to seek new patent protection on the composition-layer contributions themselves.
3. This posture applies to the composition-layer work in *this* repository. It says nothing about the three composed engines (SARC, Green SARC, SARC-DQ), which are separate, independently published works with their own licensing and any IP posture of their own.

This decision does not retroactively apply to or restate anything about prior, unrelated work; it is scoped to what this repository publishes.

## Consequences

- The publication-posture item on the release checklist is satisfied by this commit.
- Nothing in this ADR authorizes DOI minting, OSF registration, arXiv submission, or naming a co-author/independent validator — those remain separate, still-open items.
