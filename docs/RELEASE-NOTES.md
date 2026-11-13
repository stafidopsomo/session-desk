# Session Desk 0.1.2

Windows x64 regular desktop release. Extract the whole ZIP and run SessionDesk.exe; keep _internal beside it. Existing 0.1.1 users can update through Settings.

## Changes
- Remove workspaces from My adventures, or remove individual imported adventures from a workspace, with confirmation and Cancel.
- Workspace removal keeps a local recovery copy under the app data folder. Adventure removal clears its preparation, pins and saved session; export a backup first. Other adventures, shared images and original source libraries stay intact. Removal waits for active imports/backups/downloads to finish.
- Minimal home text with larger labels. Workspace, new-adventure and import windows share the warm glass style.
- A guided tutorial highlights the actual control and points to it with an arrow. Steps adapt to available text/maps, move through the reading and map views, and restore the initial DM selection afterward. Back, Next, Skip and Escape work; replay from Settings. The tutorial never presents media or changes saved fog. The new guide is offered once even if an older tour was completed.

## Updates and data
Use Settings → Check for updates → Download and install → Restart into update. The verified release installs side by side and uses the same workspace data. No re-import replaces authored work. Save edits and export a private backup before updating.

Launchers from 0.1.1 onward forward to verified installed updates on future starts. Preview/0.1.0 users need one manual download and shortcut change. Prior releases remain available for rollback. No workspace schema change is introduced.

## Validation and limits
Synthetic Python/Node tests, source and frozen browser workflows, checksum/provenance audits and extracted-EXE smoke checks run locally and in Windows CI. Private/source-library checks stay outside the public repository and releases. The owner reported successful main-PC use of the preceding release. Physical laptop/friend-PC coverage and complete source-map geometry acceptance remain deferred.

Unsigned Windows x64 package. AI stays Off. No books, source artwork, campaigns, characters or credentials are bundled. PDF/OCR, remote/LAN play and AI generation remain deferred. Temporary drawings, token positions and camera state retain their temporary behavior.
