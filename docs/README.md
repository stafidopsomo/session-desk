# Session Desk — Windows preview prerelease

[User-facing GitHub overview](../.github/README.md) · [Migration and optional features](MIGRATION.md). This page contains the development/build details.

A local app for preparing and running independent tabletop adventures. **0.1.0-preview.2 Windows x64 EXE** is the reviewed Windows preview prerelease, not a completed alpha. AI is Off and unavailable.

## Run on Windows

1. Download the Windows x64 application ZIP from [the reviewed preview release](https://github.com/stafidopsomo/session-desk/releases/tag/product-v0.1.0-preview.2). Extract it completely.
2. Double-click **SessionDesk.exe**. Keep its `_internal` folder beside it. Python, Git, Node and an AI login are not needed to run the app.
3. Create a workspace → Add adventure → select your existing local 5e.tools library → import → prepare/review → present.

See [the short instructions](QUICKSTART.txt). No books, official art, characters, personal campaigns or provider accounts are bundled. Local setup can explicitly download a verified 2014 source copy; optional adventure images download during import only for app-installed copies that opted in. Review maps for spoilers before marking them safe to share; source room boundaries are usable directly, and Draw boundary lets you replace an incorrect edge without coordinates or verification controls.

The default workspace location is `%LOCALAPPDATA%/SessionDesk/workspaces`, outside the installation. Export a workspace backup to move it to another computer; Restore creates a separate workspace including its images. Settings groups Display with the unavailable AI control. Open player screen stays separate. Closing the last app window shuts down the local server after a short reload grace; this releases the EXE file lock.

## Current capabilities and limits

Validated local-copy selection/installation, structured adventure import, book-order chapters/sections, original read-aloud boxes/lists/tables, persistent pins above search and room preparation beside the map. One Resources browser opens text in the reader and images/maps in the preview; search has Text/Images/Maps filters. Collapse all returns to closed chapters. Selection keeps sidebar scroll/folds, and tool changes retain map pan/zoom. On player screen lists shared tabs. Reveal/Hide show a radius cursor that follows brush size and zoom. DM navigation omits player variants; supported player assets stay behind their DM map. Freehand boundary correction, explicit shared notes, additive fog, temporary drawing and image-complete backups support the session workflow.

Synthetic source and frozen-app tests run on Windows 11 x64 with a fresh app-data directory and developer tools hidden from PATH. Those automated checks are **not** a clean Windows account/VM test. The owner separately confirmed Gate 1 complete on November 9. All 80 available adventures in the selected local 2014 library passed isolated import/persistence checks, including Sunless Citadel, Forge of Fury and Waterdeep. Visual/geometry acceptance, laptop/friend-PC compatibility and complete alpha acceptance are still pending; [build status](BUILD-STATUS.md) records the distinction. Packages are unsigned. Changed source snapshots require a new workspace to protect existing manual work. PDF/OCR, AI and LAN players remain deferred. Restore now imports supported prepared campaigns with all authored files and optional character/story/shop controls; see MIGRATION.md.

## Development and packaging

From the repository root, use Windows x64 Python 3.12.10. The root `ci.ps1` is the canonical Windows CI job; `.github/workflows/readiness.yml` is its required GitHub wrapper. Markdown stays outside the root, under docs/ plus the user-facing .github/README.md entry. The core uses the standard library; these locked dependencies are build/browser-test tools only.

```text
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes --only-binary=:all: -r requirements-build.lock -r requirements-e2e.lock
.venv\Scripts\python -m playwright install chromium
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python tools/check_product_boundary.py
.venv\Scripts\python tools/e2e_core.py
.venv\Scripts\python tools/e2e_prepared.py
.venv\Scripts\python tools/build_windows.py
.venv\Scripts\python tools/smoke_core.py --archive dist/SessionDesk-0.1.0-preview.2-windows-x64.zip
.venv\Scripts\python tools/e2e_core.py --exe dist/SessionDesk/SessionDesk.exe
.venv\Scripts\python tools/e2e_prepared.py --exe dist/SessionDesk/SessionDesk.exe
```

For source development: `.venv\Scripts\python -m sessiondesk`. All checks use original synthetic data and isolated saves; no provider is launched. Packaging produces an explicit file manifest, SHA-256 checksums, dependency/license notices and a clean development ZIP. See [architecture](ARCHITECTURE.md), [implementation gates](IMPLEMENTATION-GATES.md) and [CI/release pipeline](RELEASE-PIPELINE.md).

## Distribution boundary

Public product source: https://github.com/stafidopsomo/session-desk, selected by the owner on November 11. Its main/release-dev branches descend only from the independent, campaign-free product root. The original campaign repository stays private. Never merge its personal branch or mirror all its refs/objects into the product repository. Workspace backups and case-specific migration reports stay outside both product source and application packages.

Tagged alpha publication fails closed until versioned acceptance evidence covers the exact product tree. The first preview is separately authorized by the owner’s request for automated tests and publication while laptop access is unavailable. Its exact-tree/package checks must pass; laptop and full visual acceptance remain deferred. This scoped decision does not authorize an alpha or future preview tags. [Provider feasibility](PROVIDERS.md) and [Codex preflight](CODEX-PREFLIGHT.md) are historical references for a deferred phase, not setup steps or blockers for this core.

Older imports: re-import the same adventure once to add original book formatting and player-map metadata. The same-snapshot upgrade preserves notes, pins, custom pictures, drawn edges and session/fog.

Gate 2 reliability: backups/restores have progress and cancellation, stream through private temporary files, and publish a restored workspace only after validation. Re-importing the same source repairs missing/damaged source images while keeping prep and session state. No partial workspace is exposed after a failed/cancelled restore.
