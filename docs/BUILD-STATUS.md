# Windows core build status

Updated November 11, 2026. Version **0.1.0-preview.1**, unsigned Windows preview prerelease. No completed alpha is claimed.

## Implemented

- Independent workspaces outside the installation; generic local 5e.tools adventure import, source-ordered Resources/search/pins, original book formatting, inline room preparation and image review.
- Cancellable import/export/restore, atomic workspace publication, same-source image repair, staged interruption recovery and bounded verified backups.
- Separate DM/player capabilities and windows, explicit shared tabs/notes, room/brush fog, corrected boundaries, adjustable brush cursor, pan/zoom and temporary drawing. Selection does not reveal.
- Settings contains Display and AI Off/unavailable. Open player screen stays separate. No provider runtime, account discovery, quota polling, inference or generation routes.
- Prepared-campaign recovery import through the same Restore backup control and EXE. Optional data activates editable characters/sheets/threads/backstories, scene/session guides, shops, calibrated cropped maps/fog, shared room notebooks and temporary tokens/camera/drawing. Fresh workspaces have no empty optional panels.
- All authored campaign files and original recovery archive preserved as data/attachments. Imported scripts/templates are never executed. Explicit local 2014 rules connection stays machine-local. Unknown module versions remain inert and portable.
- Workspace schema 2; schema 1 upgrades with a SQLite recovery copy and existing schema 1 ZIPs remain importable. Older app versions cannot open schema 2.
- Frozen Windows x64 one-folder ZIP, bundled Python/Tk, explicit source/static allowlists, dependency/license notices, checksums, file manifest and provenance. Tests, books, workspaces and personal data are excluded.

## Verification

Host: Windows 11 Pro x64 build 26300, Python 3.12.10. Synthetic automated tests use isolated app data and original fixtures. No owned books/private data run in CI or enter its artifacts.

- 84 offline unit/contract tests cover generic import/storage/HTTP, schema upgrades, prepared-file preservation, unknown-module roundtrip, failed/cancelled imports, DM/player separation, 2014 rules, attachment safety and AI rejection.
- Core browser E2E covers first run/import, preparation, book formatting, pins/folds/scroll, boundaries, reveal radius, Space-pan, player tabs/notes/drawing, cancellation, native backup download and restored state.
- Prepared browser E2E uses Restore, connects a synthetic rules library, edits a sheet, opens guides/shops, shares notes/draws, exports and restores into another data root. It checks that a fresh workspace has no optional panels and blocks/asserts external requests.
- Frozen smoke/E2E use an isolated profile and hide developer tools from PATH. Extracted-ZIP checks verify hashes, Unicode relocation, persistence, last-window shutdown and unchanged install files. This is not a clean VM or another physical computer.
- Local owned-library import/persistence sweep: all 80 available adventures in the selected 2014 library loaded, with zero importer warnings, including Sunless Citadel, Forge of Fury, Waterdeep and Icewind Dale. Private reports stay outside Git. Import success does not certify every source polygon's visual accuracy.
- Private campaign migration checks files, assets, saved fog and specialized controls against the recovery snapshot. Reports/backups stay outside source and builds. See MIGRATION.md for preservation and temporary-state limits.

The product implementation commit passed [GitHub run 43047995272](https://github.com/stafidopsomo/session-desk/actions/runs/43047995272). Its downloaded package independently passed seven real-library import/export/restore cases and a full private campaign roundtrip, including exact fog raster comparison. All 80 available sources completed roundtrips across the local runs; three transient loopback connection timeouts were retained in private reports and passed when checked again. The exact commit's GitHub Actions run is the remote CI record. Local success is not described as remote CI. Packaging fails if developer paths or disallowed content appear in the ZIP.

## Remaining acceptance

Gate 0 is closed; Gate 1 is complete by the owner's explicit November 9 confirmation. Gate 2's non-AI workflow is implemented. Broader visual/geometry acceptance and actual laptop/friend-machine testing remain separate from same-PC automated evidence. Alpha publication stays blocked by release/acceptance.json until exact-tree evidence covers all required checks. Do not turn pending flags true merely to publish.

AI, PDF/OCR importing, automatic geometry inference and remote/LAN player devices are deferred. No universal campaign format, runtime plug-in installation, signed installer or bit-identical reproducible EXE is promised. A compatible prepared module preserves authoring files without installing the tools that originally created them.

## First public preview validation

The owner requested the first GitHub preview with automated tests while laptop access is unavailable. This changes the publication scope for product-v0.1.0-preview.1 only; it does not claim a laptop test or completed alpha. The release gate separately requires exact-tree evidence, a scoped owner decision and verified package provenance/file hashes. Local and GitHub Windows runs cover all 84 Python tests, Node renderer tests, both browser workflows from source/frozen EXE, and extracted-ZIP lifecycle/relocation/backup checks. Owned sources and private backups remain local-only. The final acceptance record identifies the checked tree and evidence; publication is blocked until those runs succeed.
