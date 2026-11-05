# Release-readiness assessment

Assessment date: November 5, 2026. This assessment makes no model calls and imports no real adventure content into this branch.

## Decision

**Proceed with architecture and isolation. Do not start the application build yet.**

The destination is technically plausible, but the current personal app and the superseded notes/map prototype do not already satisfy its architecture. The owner explicitly asked not to start another partial implementation when architectural dependencies are missing. A new executable or placeholder installer would hide these gaps rather than close them.

## Evidence from the current code

| Area | Existing behavior | Product requirement |
|---|---|---|
| Content loading | Repository-relative folders and one campaign's imported datasets | User-selected sources; multiple isolated adventures; empty initial profile |
| Identity | Keyed room numbers are reused across data files | Stable workspace/adventure/map/region/source-entry IDs; repeated keys supported |
| Data storage | Live state, notes and edits span JSON files in the checkout | Versioned workspace database, managed asset store, backups and migrations outside the install |
| Import | Adventure-specific import code and hand-authored corrections | A generic source adapter with schema detection, reference resolution and validation |
| Geometry | Known map regions plus campaign-specific collars/layout fixes | Preserve verified regions; distinguish areas/features from whole rooms; review missing/ambiguous boundaries |
| AI work | Machine-specific CLI execution and manual review/import | Supported provider adapters, capability checks, durable jobs, typed drafts and app-managed review |
| Packaging | A batch file assumes Python/paths on the owner's machine | Frozen Windows runtime tested without developer tools or personal files |
| Release process | No product CI/build/release workflow | Synthetic tests, clean-profile E2E, artifact privacy gate and reproducible packaging |

The old standalone prototype offers generic entries and brush fog. It does not implement a source-adventure graph, resource provisioning, AI preparation, or a synchronized separate player view. Extending it as the product would repeat the wrong direction.

## Import feasibility check

A read-only inspection of the owner's local Icewind Dale structured source found **42 maps, 38 with region metadata, and 465 keyed regions**. Four maps have no keyed regions. This supports the selected first input format without promising every map is room-keyed.

This is evidence from one local library snapshot, not a universal guarantee about every 5e.tools version or book. No book text or map images are stored in this assessment. The importer must handle wrapper/schema variants, missing images, references across source files and maps without regions.

## Decisions established

- Local, independent workspaces; no automatic migration of the personal campaign.
- Existing local 5e.tools adventure/image library is the first import path. PDF/OCR is outside the first release.
- Small user workflow: Add adventure → Prepare and review → Start session. Provider configuration belongs in Settings.
- Code, imported source content and generated/user content have separate storage and distribution boundaries.
- AI-generated notes, translations, illustrations and region proposals are drafts until validated/reviewed. Existing source geometry should be imported by code, not recreated by a model.
- Installation and deterministic imports should be reproducible. Model outputs are not promised to be bit-for-bit identical; their inputs, versions and provenance must be recorded.

## Outstanding architecture dependencies

1. Accept the workspace/resource/job schemas and migration/backup contract described in ARCHITECTURE.md.
2. Confirm Windows x64 as the first release target; define the supported Windows versions during packaging validation.
3. Choose the first supported provider/authentication route and verify it in the intended product context. Do not promise all three providers or illustration generation at parity.
4. Agree that uncertain AI-generated map regions require review/correction rather than being automatically considered precise fog.
5. Confirm distribution. Provisional default: keep this repository private and share only audited build files. Separate clean repository before any source-sharing or public-repository decision.

Those are gates to application implementation, not terminal commands for testers. See IMPLEMENTATION-GATES.md for concrete proofs required before a build is called an alpha.

## Current deliverable

A clean release branch, architecture assessment, provider findings, release design and measurable milestones. No new product app, CI execution, provider inference, installer or tester release is claimed.
