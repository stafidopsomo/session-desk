# Session Desk 0.1.0-preview.1

First public **Windows x64 preview prerelease**.

Download the application ZIP, extract it completely, then run **SessionDesk.exe**. Keep the _internal folder beside it. Python, Git, Node and an AI account are not required.

## Included

- Independent workspaces; import an adventure from a selected local 5e.tools library, or explicitly install the supported local 2014 copy.
- Source-ordered Resources, Text/Images/Maps search, pins, original book formatting and editable narration/private DM notes.
- Reviewed image/map presentation, separate player window, shared tabs/notes, room/brush fog, boundary correction, zoom and temporary drawing.
- Verified, cancellable backup/restore. Supported prepared-campaign backups activate their character sheets, story guides and shops in the same EXE. Fresh workspaces have no empty optional panels.
- Saves outside the application folder, so replacing the application preserves them.

## Validation and limits

Automated unit, browser and extracted-EXE tests run on the maintainer's Windows 11 x64 PC and in Windows GitHub Actions. Tests cover fresh startup, imports, preparation, DM/player separation, fog/drawing, restart, cancellation, backup/restore, relocation and shutdown. Generic import/roundtrip checks also exercised 80 available local 2014 adventures; owned source data is excluded from source, CI and releases.

**The owner's laptop and a friend's PC have not been tested.** The owner requested this first preview using automated tests while laptop access is unavailable. Hardware compatibility and complete visual review of every source map remain pending; this is not a completed alpha or stable release.

- Unsigned Windows package; no signing certificate is claimed.
- AI remains Off/unavailable. No provider installation, login, quota polling or generation.
- No books, official artwork, campaigns, characters, credentials or personal data are bundled.
- Same-computer/TV presentation only; no remote/LAN players, PDF/OCR or automatic geometry inference.
- Review maps for spoilers and incorrect source boundaries before presenting them. Imported source geometry is not a guarantee of complete room outlines.
- Temporary drawings, token positions and camera/ping are not persisted.
- Restoring a backup creates a separate workspace. Reconnect your local 2014 library on another computer. Workspace schema 1 upgrades with a recovery copy; preview 5 cannot open schema 2.

Before upgrading or moving computers, **Export backup** and keep that ZIP private. Close DM/player windows before replacing the extracted application folder. Report the app version, Windows version and reproducible steps through GitHub Issues; do not upload private campaigns or source books.
