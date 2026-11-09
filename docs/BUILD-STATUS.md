# Windows core build status

Updated November 9, 2026. Version: **0.1.0-dev.2**. This is an unsigned development preview; no alpha tag/release has been published.

## Implemented

- Empty, named workspaces stored outside the installation in schema-versioned SQLite; workspace/adventure-scoped routes, transactions, stable source/map/region IDs and independently managed hashed assets.
- Explicit local 5e.tools index/adventure/image import, inventory and warnings, chapter/path/entry locators, deterministic fingerprints and safe repeated imports. Imports run as cancellable background tasks; cancellation ends before the atomic commit. Changed snapshots require a new workspace, preserving manual preparation.
- Manual narration/translations, draft/approved review and private DM notes. Imported names remain unchanged. Media folders, manual picture import, image-sharing review and manual source-region boundary correction/verification. Unverified/uncertain geometry never enables precise region reveal.
- Separate DM/player windows, explicit presentation, shared tabs selectable/closable from either window, shared notes, persistent room/brush fog, pan/zoom, adjustable fog brush, and temporary player drawing/color/clear. Region selection never reveals; reveal operations add to prior cleared fog.
- Top-right Settings groups Display and global AI. AI is fixed Off/unavailable; backend AI routes reject submissions/enabling. No provider runtime, install, discovery, sign-in or calls. Open player screen remains a separate header control.
- Complete image-inclusive backup/restore with hashes, size/path/type/identity validation, new workspace identity on restore, and unsupported-schema refusal without resetting data. Initial schema is version 1; no previous product schema needs migration yet.
- Loopback-only server, per-instance DM/player capabilities, same-origin/Host validation, bounded routes/uploads, escaped source text and a strict player-response allowlist. Same-computer presentation is not a security boundary against an adversarial local user.
- Frozen one-folder Windows build with bundled Python/Tk runtime, explicit static-asset allowlist, dependency/license notices, file manifest, checksums and source/version provenance. Synthetic fixtures, diagnostics, source libraries and saves are excluded.
- The root ci.ps1 is the main Windows CI job; GitHub calls it from the required .github/workflows wrapper. All Markdown documents, including README and agent instructions, live under docs/. A separate tag publication job fails closed until matching alpha acceptance evidence exists.

## Verification evidence

Host: **Windows 11 Pro x64, build 26300**, Python **3.12.10**. Automated unit/CI content is original synthetic data, generated outside the repository. Unit/CI fixtures never use a personal campaign/save or source book. Separate owned-library and upstream setup checks below run only in temporary folders outside Git; no source content or images are stored in reports/releases.

- 40 offline unit/contract tests: importer identities/locators, ambiguous dimensions, workspace isolation, additive reveal, private/player separation, player tabs, backup relocation/corruption/path/identity rejection, unsupported schema, same-origin/auth checks, AI rejection, ephemeral drawing and publication gating; historical diagnostics use only fakes.
- Real Chromium source and frozen-browser E2E: create workspace, inspect/import, save Greek preparation, verify boundary, explicit presentation, player reload, brush reveal, Space-pan after outside focus, shared notes, player drawing/zoom/tab activation/close-all, Settings layout and disabled AI. External browser requests are blocked and asserted absent.
- Frozen lifecycle smoke: fresh application-data directory with Python/Git/Node hidden from PATH; import, manual preparation, player-safe serialization, restart persistence, asset-complete backup and restore. Extracted-ZIP verification also checks entry/ZIP hashes, Unicode relocation and unchanged install files.
- Product source boundary and JavaScript syntax checks. Explicit package content audit scans developer path/name markers and excludes tests, personal data, provider tools and arbitrary source-tree directories.

Local test results are recorded here; the GitHub Actions run for the exact commit is the CI result. A green local run is not represented as remote CI evidence.

## Remaining acceptance and limits

- **Gate 1:** executable spike works with synthetic data. A fresh app profile and hidden PATH are not a fresh standard-user Windows account/clean VM. That OS-profile test remains pending; minimum supported Windows version is not yet established. Only the named host is validated.
- **Gate 2:** initial manual vertical slice works. Broader source-version fixtures and failure/recovery coverage remain to expand. Export/restore currently operate as bounded, in-memory transactions rather than resumable/cancellable jobs; imports can be cancelled before commit. Source schema/asset size limits produce errors, not fabricated geometry.
- **Gate 3:** The explicitly selected 2014 library now passes list-wrapper parsing and temporary background import/persistence. Icewind Dale: 2108 entries, 81 map images (42 DM + 39 player), 136 pictures, zero warnings. Sunless Citadel: 506 entries, 4 map images, 10 pictures, zero warnings. Full visual/geometry acceptance is still pending. Parent-map transforms are not inferred; mismatched geometry remains unverified. Existing-copy imports remain read-only/offline. App-installed copies may explicitly opt into missing-image downloads during import; external image references remain unsupported. Valid image formats: PNG, JPEG, WebP, GIF, up to 48 MB/image and 100 million pixels.
- **Gate 4:** laptop/friend-machine and clean-account tests, full artifact/dependency/privacy acceptance and alpha evidence remain pending. The automated audit is an accidental-leakage check, not a proof that every binary is free of secrets. Packages are unsigned. There is no code-signing certificate or published alpha.
- AI/provider integration and isolation, PDF/OCR, remote/LAN players, character tooling and personal-campaign migration are deferred. No personal branch was merged or campaign content copied.

The default data folder is `%LOCALAPPDATA%/SessionDesk/`. Closing the last DM/player window now requests automatic shutdown after an 8-second reload grace, cancelling active work and waiting for atomic commits. Lost clients expire after about 100 seconds. Settings > Quit app also stops the server immediately when no job is active. Re-running the launcher for the same data folder opens the existing instance. Testers receive audited ZIP files rather than repository access. See QUICKSTART.txt.

## Development preview 2 fixes and setup validation

- Fixed the real 2014 `adventureData: [{id, source, data}]` wrapper, with deterministic matching and useful unsupported-schema errors. The prior generic AttributeError is eliminated; no private source fixture is committed.
- Import/install errors and cancellation are terminal in the backend and frontend: polling/progress stops, a persistent message remains, and retry/close becomes available. Lost connections attempt cancellation; committing work finishes atomically. Regression tests cover a failed import followed by a successful retry.
- Source setup offers Use existing copy (folder validation, version, available adventure count and image status) and Install local copy (new/empty chosen folder, verified 2014 release, optional adventure images as needed). Folder buttons are type=button and no longer trigger premature required-field validation.
- The upstream 2014 v1.221.6 release archive was downloaded into a temporary folder, checked against its GitHub SHA-256 digest, extracted safely and validated: 80 available adventures. Optional on-import image download was separately validated with all 14 Sunless Citadel images (4 maps + 10 pictures), zero warnings. No downloaded code is executed and Git/Node are not required by the installer. The complete global image archive is not promised/downloaded.
- Installer tests use original synthetic archives and fake transports in CI. Extraction rejects path traversal/links/collisions and size limits; failed/cancelled setup cleans only its own verified staging directory and does not overwrite an existing nonempty destination.
- Last-window close/reload/player-window behavior has deterministic tests. Source and frozen lifecycle smoke tests verify shutdown releases the process/EXE. Existing user data remains outside the application and survives replacement.
- The owner's previously running Desktop test EXE was stopped gracefully to release its file lock; no files/workspaces were deleted.
