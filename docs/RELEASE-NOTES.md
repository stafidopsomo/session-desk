# Session Desk 0.1.0-preview.2

Reviewed Windows x64 preview prerelease. Download the application ZIP, extract it completely and run **SessionDesk.exe** with _internal beside it. No Python, Git, Node or AI account is required.

## Corrections since preview.1

- File cleanup locks no longer strand operations or report a successfully restored workspace as failed.
- Interrupted prepared-file copying publishes no incomplete workspace; cancelling large prepared snapshots stops promptly.
- Portable backups omit obsolete asset versions while preserving originals, unknown modules and current edits.
- HP/resources remain editable without the local rules library; existing character choices are retained.
- Slow image loading cannot replace a newer player view. Token controls hide over pictures/reference pages.
- Metadata-free local data-folder selection resolves correctly. Completed source installations remain usable if preferences cannot be saved, with an explicit warning and automatic downloads kept Off.
- Fog/tab limits are checked before changing state, so ordinary actions cannot create a save that later fails its own backup validation.
- Guide sharing supports validated local book sources beyond a single hardcoded book.

Background work and transfer lifecycle are now separated from HTTP routing. Existing workspace formats and API paths remain compatible. The full [review report](https://github.com/stafidopsomo/session-desk/blob/product-v0.1.0-preview.2/docs/reviews/2026-11-12/REVIEW.md) lists findings, corrections and follow-ups.

## Testing and limits

Automated unit, browser and extracted-EXE checks cover imports, storage/cancellation/fault recovery, DM/player separation, sheets, fog/drawing, tabs, restart, backup/restore, relocation, shutdown and package provenance. CI uses original synthetic content; private campaign/source tests remain local and are never release assets.

**Physical laptop/friend-PC compatibility and complete visual review of every source map remain pending.** This is an unsigned preview, not a completed alpha or stable release. AI is Off/unavailable. PDF/OCR, remote/LAN players and automatic geometry inference remain deferred.

No books, official artwork, campaign data, characters, credentials or provider tools are bundled. Temporary drawings/token positions/camera are not saved. Browser display preferences may reset between launches; campaign/session data stays persistent.

Before upgrading, Export backup and keep it private. Close DM/player windows, then extract this version into a separate application folder. Existing workspace data lives outside the application. Restore creates a new workspace; reconnect your local 2014 library on a different PC. Preview.1 remains available as rollback.
