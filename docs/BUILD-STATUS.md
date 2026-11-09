# Windows core build status

Updated November 9, 2026. Version: **0.1.0-dev.1**. This is an unsigned development preview; no alpha tag/release has been published.

## Implemented

- Empty, named workspaces stored outside the installation in schema-versioned SQLite; workspace/adventure-scoped routes, transactions, stable source/map/region IDs and independently managed hashed assets.
- Explicit local 5e.tools index/adventure/image import, inventory and warnings, chapter/path/entry locators, deterministic fingerprints and safe repeated imports. Imports run as cancellable background tasks; cancellation ends before the atomic commit. Changed snapshots require a new workspace, preserving manual preparation.
- Manual narration/translations, draft/approved review and private DM notes. Imported names remain unchanged. Media folders, manual picture import, image-sharing review and manual source-region boundary correction/verification. Unverified/uncertain geometry never enables precise region reveal.
- Separate DM/player windows, explicit presentation, shared tabs selectable/closable from either window, shared notes, persistent room/brush fog, pan/zoom, adjustable fog brush, and temporary player drawing/color/clear. Region selection never reveals; reveal operations add to prior cleared fog.
- Top-right Settings groups Display and global AI. AI is fixed Off/unavailable; backend AI routes reject submissions/enabling. No provider runtime, install, discovery, sign-in or calls. Open player screen remains a separate header control.
- Complete image-inclusive backup/restore with hashes, size/path/type/identity validation, new workspace identity on restore, and unsupported-schema refusal without resetting data. Initial schema is version 1; no previous product schema needs migration yet.
- Loopback-only server, per-instance DM/player capabilities, same-origin/Host validation, bounded routes/uploads, escaped source text and a strict player-response allowlist. Same-computer presentation is not a security boundary against an adversarial local user.
- Frozen one-folder Windows build with bundled Python/Tk runtime, explicit static-asset allowlist, dependency/license notices, file manifest, checksums and source/version provenance. Synthetic fixtures, diagnostics, source libraries and saves are excluded.
- Windows CI builds/test artifacts and a separate tag publication job fails closed until matching alpha acceptance evidence exists.

## Verification evidence

Host: **Windows 11 Pro x64, build 26300**, Python **3.12.10**. All content in these checks is original synthetic data, generated outside the repository. No personal campaign/save or owned source book is used.

- 29 offline unit/contract tests: importer identities/locators, ambiguous dimensions, workspace isolation, additive reveal, private/player separation, player tabs, backup relocation/corruption/path/identity rejection, unsupported schema, same-origin/auth checks, AI rejection, ephemeral drawing and publication gating; historical diagnostics use only fakes.
- Real Chromium source and frozen-browser E2E: create workspace, inspect/import, save Greek preparation, verify boundary, explicit presentation, player reload, brush reveal, Space-pan after outside focus, shared notes, player drawing/zoom/tab activation/close-all, Settings layout and disabled AI. External browser requests are blocked and asserted absent.
- Frozen lifecycle smoke: fresh application-data directory with Python/Git/Node hidden from PATH; import, manual preparation, player-safe serialization, restart persistence, asset-complete backup and restore. Extracted-ZIP verification also checks entry/ZIP hashes, Unicode relocation and unchanged install files.
- Product source boundary and JavaScript syntax checks. Explicit package content audit scans developer path/name markers and excludes tests, personal data, provider tools and arbitrary source-tree directories.

Local test results are recorded here; the GitHub Actions run for the exact commit is the CI result. A green local run is not represented as remote CI evidence.

## Remaining acceptance and limits

- **Gate 1:** executable spike works with synthetic data. A fresh app profile and hidden PATH are not a fresh standard-user Windows account/clean VM. That OS-profile test remains pending; minimum supported Windows version is not yet established. Only the named host is validated.
- **Gate 2:** initial manual vertical slice works. Broader source-version fixtures and failure/recovery coverage remain to expand. Export/restore currently operate as bounded, in-memory transactions rather than resumable/cancellable jobs; imports can be cancelled before commit. Source schema/asset size limits produce errors, not fabricated geometry.
- **Gate 3:** real, explicitly selected Icewind Dale/owned-library acceptance remains pending. Parent-map transforms are not inferred; mismatched geometry remains unverified. Unsupported/external assets are reported and skipped; nothing is downloaded. Valid image formats: PNG, JPEG, WebP, GIF, up to 48 MB/image and 100 million pixels.
- **Gate 4:** laptop/friend-machine and clean-account tests, full artifact/dependency/privacy acceptance and alpha evidence remain pending. The automated audit is an accidental-leakage check, not a proof that every binary is free of secrets. Packages are unsigned. There is no code-signing certificate or published alpha.
- AI/provider integration and isolation, PDF/OCR, remote/LAN players, character tooling and personal-campaign migration are deferred. No personal branch was merged or campaign content copied.

The default data folder is `%LOCALAPPDATA%/SessionDesk/`. Use Settings > Quit app to stop the background loopback server. Re-running the launcher for the same data folder opens the existing instance. Testers receive audited ZIP files rather than repository access. See QUICKSTART.txt.
