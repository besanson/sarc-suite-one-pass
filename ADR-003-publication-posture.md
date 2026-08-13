# ADR-003: Publication Posture — Publish for Audience, No Patent Claims on the Composition Layer

**Status**: Accepted (publication posture) / **Open** (employment-ownership confirmation — see below)
**Date**: 2026-08-13

## Context

Items 1-6 of this artifact's V6 human release checklist (`sarcsuite95upgrade.md`) gate actual publication. Item 1 reads:

> ADR-003 (publish for audience, no patent claims on the composition layer) is committed to the repo; publication proceeds under it. One surviving check, about ownership not monetisation: a one-time confirmation that the founder's employment contract gives the employer no claim over the work.

This record commits the first half of that item — the publication posture — and states, explicitly and separately, what remains open.

## Decision: publish for audience, no patent claims on the composition layer

This artifact and its accompanying paper (`paper4-composition-draft-v0.1.md` through `v0.3-populated.md`) are published for an audience: researchers, engineers, and reviewers evaluating the composition semantics of pre-action gates for agentic AI systems. Specifically:

1. **No patent claims are made or reserved on the composition layer** described here — the restrictiveness lattice and join rule (Definitions 1-2), the remediate-regate protocol (Section 5), the second remediation operator and its non-commutativity result (CH7), the buffer-poisoning mitigations (CH6), or any other mechanism this repository documents. Nothing in this artifact is filed, pending, or intended to be filed as a patent application, and this ADR records that intent as of its date above.
2. Publication is under the repository's existing Apache License 2.0 (`LICENSE`), which already grants an express patent license from contributors to users for any patents they hold that would otherwise be infringed by the licensed work (Apache-2.0 §3). This ADR does not change the license; it records the additional, narrower commitment not to seek new patent protection on the composition-layer contributions themselves.
3. This posture applies to the composition-layer work in *this* repository. It says nothing about the three composed engines (SARC, Green SARC, SARC-DQ), which are separate, independently published works with their own licensing and any IP posture of their own.

This decision does not retroactively apply to or restate anything about prior, unrelated work; it is scoped to what this repository publishes.

## Open: the employment-ownership confirmation

The task's release checklist separates a second check from the ADR itself: "a one-time confirmation that the founder's employment contract gives the employer no claim over the work." That confirmation is a factual attestation about a specific person's specific employment terms. It is not something this repository's automated pipeline can make on anyone's behalf — doing so would fabricate a legal attestation with no basis to verify it, which this artifact's own "no fabricated citations" / "zero source writes" discipline forbids by the same logic applied to any other unverifiable claim.

This section is left explicitly unfilled rather than silently marked done:

> **Employment-ownership confirmation**: PENDING. To be completed by the founder (Gaston Besanson) directly, as a statement in their own words confirming their employment contract gives their employer no claim over this work, then recorded here by amending this file (a new commit, not a rewrite of this one — consistent with this repository's no-squash discipline).

Until that statement is added, checklist item 1 remains open. Committing this ADR does not close it.

## Consequences

- The publication-posture half of checklist item 1 is satisfied by this commit.
- The employment-ownership half is explicitly tracked as open, here and in any future release-checklist reporting, until the founder adds their own confirmation.
- Nothing in this ADR authorizes DOI minting, OSF registration, arXiv submission, or naming a co-author/independent validator (checklist items 2 and 6) — those remain separate, also-open items.
