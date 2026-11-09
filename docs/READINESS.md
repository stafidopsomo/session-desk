# Release-readiness assessment

Initial assessment: November 5, 2026. Scope/owner decisions updated November 9, 2026. This work makes no model calls and imports no real adventure content into this branch.

## Decision

**Proceed to Gate 1 implementation of the non-AI core.** The owner accepted ARCHITECTURE.md and Windows x64, with one top-right Settings menu containing Display and the global AI switch, and Open player screen kept separate. All provider/AI features and route-isolation work are deferred, so the earlier Codex preflight gap does not block the core build.

This resolves design approval; it does not establish a built/tested EXE. The first release still needs deterministic import, manual preparation/review, isolated persistent workspaces, maps/fog/notes/player presentation and clean-machine packaging evidence. See IMPLEMENTATION-GATES.md.

## Historical starting-point assessment (November 5)

| Area | Existing behavior | Product requirement |
|---|---|---|
| Content loading | Repository-relative folders and one campaign's imported datasets | User-selected sources; multiple isolated adventures; empty initial profile |
| Identity | Keyed room numbers are reused across data files | Stable workspace/adventure/map/region/source-entry IDs; repeated keys supported |
| Data storage | Live state, notes and edits span JSON files in the checkout | Versioned workspace database, managed asset store, backups and migrations outside the install |
| Import | Adventure-specific import code and hand-authored corrections | A generic source adapter with schema detection, reference resolution and validation |
| Geometry | Known map regions plus campaign-specific collars/layout fixes | Preserve verified regions; distinguish areas/features from whole rooms; review missing/ambiguous boundaries |
| AI work — deferred | Machine-specific CLI execution and manual review/import | Later supported adapters/capabilities; no provider dependency in the first core |
| Packaging | A batch file assumes Python/paths on the owner's machine | Frozen Windows runtime tested without developer tools or personal files |
| Release process | No product CI/build/release workflow | Synthetic tests, clean-profile E2E, artifact privacy gate and reproducible packaging |

The old standalone prototype offers generic entries and brush fog. It does not implement a source-adventure graph, resource provisioning, AI preparation, or a synchronized separate player view. Extending it as the product would repeat the wrong direction.

## Import feasibility check

A read-only inspection of the owner's local Icewind Dale structured source found **42 maps, 38 with region metadata, and 465 keyed regions**. Four maps have no keyed regions. This supports the selected first input format without promising every map is room-keyed.

This is evidence from one local library snapshot, not a universal guarantee about every 5e.tools version or book. No book text or map images are stored in this assessment. The importer must handle wrapper/schema variants, missing images, references across source files and maps without regions.

## Decisions established

- Local, independent workspaces; no automatic migration of the personal campaign.
- Existing local 5e.tools adventure/image library is the first import path. PDF/OCR is outside the first release.
- Small core workflow: Add adventure → manually Prepare/review → Start session. Settings is top-right and groups Display with AI; Open player screen remains a separate header control.
- Code, imported source content and generated/user content have separate storage and distribution boundaries.
- Existing source geometry is imported by code and reviewed/corrected manually. AI notes/translations/art/geometry proposals remain a deferred phase; their draft/review boundaries are accepted design constraints.
- Installation and deterministic imports should be reproducible. Model outputs are not promised to be bit-for-bit identical; their inputs, versions and provenance must be recorded.
- Windows x64 and the architecture are confirmed. The owner/friend machines are target test hardware, not already verified environments.
- The first build has AI Off/unavailable and makes no provider calls. ChatGPT through Codex remains the earlier candidate for later AI work.

## Remaining engineering proofs

1. Build the core architecture spike and establish the supported Windows-version floor through actual package/machine tests.
2. Verify independent workspace storage, transactions, migrations/rollback and asset-complete backup/import outside the installation.
3. Implement generic deterministic source import and manual notes/resource/geometry review, then test with synthetic sources and a separately selected owned-library acceptance run.
4. Verify the Settings layout, separate Open player screen control and the unavailable/Off AI state, including zero provider activity.
5. Implement/audit CI packaging and clean-profile launch before sharing an alpha. Keep this repository private; default to direct sharing of vetted ZIP/EXE files rather than tester repository access.

These are implementation acceptance checks, not more architecture approvals for the owner to read. Provider authentication, installation, isolation and generation are future AI-phase proofs and are not required for the current core.

## Current deliverable

Approved architecture and a scoped non-AI implementation path, clean independent history, offline readiness checks, release design and historical provider/preflight notes. The existing workflow checks readiness only. No product app, installer, provider integration or tester release is claimed as delivered by this scope update.
