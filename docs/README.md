# Session Desk — Windows development preview

A local app for preparing and running independent tabletop adventures. The first **0.1.0-dev.2 Windows x64 EXE** is implemented; this is a development preview, not a completed tester alpha. AI is Off and unavailable.

## Run on Windows

1. Download the `sessiondesk-windows-x64` artifact from a green release-dev Actions run. Extract the artifact ZIP, then extract the enclosed SessionDesk ZIP completely.
2. Double-click **SessionDesk.exe**. Keep its `_internal` folder beside it. Python, Git, Node and an AI login are not needed to run the app.
3. Create a workspace → Add adventure → select your existing local 5e.tools library → import → prepare/review → present.

See [the short instructions](QUICKSTART.txt). No books, official art, characters, personal campaigns or provider accounts are bundled. Local setup can explicitly download a verified 2014 source copy; optional adventure images download during import only for app-installed copies that opted in. Review maps for spoilers before marking them safe to share; imported region geometry requires review before region reveal.

The default workspace location is `%LOCALAPPDATA%/SessionDesk/workspaces`, outside the installation. Export a workspace backup to move it to another computer; Restore creates a separate workspace including its images. Settings groups Display with the unavailable AI control. Open player screen stays separate. Closing the last app window shuts down the local server after a short reload grace; this releases the EXE file lock.

## Current capabilities and limits

Validated existing-copy selection, optional verified 2014 local installation, local structured adventure/image import, exact source locators in the source reader, manual narration/translations and private DM notes, image library folders, image/geometry review, shared player tabs/notes, additive region and brush fog, pan/zoom, temporary player drawing, SQLite persistence and checksummed workspace backups.

Synthetic source and frozen-app tests run on Windows 11 x64 with a fresh app-data directory and developer tools hidden from PATH. This is **not** a clean Windows account/VM test. Owned 2014 Icewind Dale import now succeeds in an isolated workspace. Visual/geometry acceptance, laptop/friend-PC compatibility and complete alpha acceptance are still pending; [build status](BUILD-STATUS.md) records the distinction. Packages are unsigned. Changed source snapshots require a new workspace to protect existing manual work. PDF/OCR, AI, LAN players and personal-campaign migration remain deferred.

## Development and packaging

From the repository root, use Windows x64 Python 3.12.10. The root `ci.ps1` is the canonical Windows CI job; `.github/workflows/readiness.yml` is its required GitHub wrapper. All Markdown lives in docs/. The core uses the standard library; these locked dependencies are build/browser-test tools only.

```text
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes --only-binary=:all: -r requirements-build.lock -r requirements-e2e.lock
.venv\Scripts\python -m playwright install chromium
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python tools/check_product_boundary.py
.venv\Scripts\python tools/e2e_core.py
.venv\Scripts\python tools/build_windows.py
.venv\Scripts\python tools/smoke_core.py --archive dist/SessionDesk-0.1.0-dev.2-windows-x64.zip
.venv\Scripts\python tools/e2e_core.py --exe dist/SessionDesk/SessionDesk.exe
```

For source development: `.venv\Scripts\python -m sessiondesk`. All checks use original synthetic data and isolated saves; no provider is launched. Packaging produces an explicit file manifest, SHA-256 checksums, dependency/license notices and a clean development ZIP. See [architecture](ARCHITECTURE.md), [implementation gates](IMPLEMENTATION-GATES.md) and [CI/release pipeline](RELEASE-PIPELINE.md).

## Distribution boundary

This branch has independent, campaign-free history. Never merge the personal branch into it. The surrounding private repository has personal content on other refs: share only vetted ZIP/EXE artifacts directly, without granting testers repository access. Private release links require repository permissions. Public source sharing needs a separate clean repository.

Tagged alpha publication fails closed until versioned acceptance evidence covers the exact product tree. The current record deliberately does not authorize an alpha. [Provider feasibility](PROVIDERS.md) and [Codex preflight](CODEX-PREFLIGHT.md) are historical references for a deferred phase, not setup steps or blockers for this core.
