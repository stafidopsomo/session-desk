# Local 0.2.0-preview.1 candidate

Unpublished campaign-book test build. LaunchPreview.bat selects the separate preview profile. Adds a shared Book / Resources / Party surface for fresh and restored workspaces, editable book entries and mission outcomes/rewards, guarded character-note edits, retained conflicting drafts and independent URL-addressed map/room inspection. Existing source import, calibrated fog and backups remain in the app. Full sheet editing uses the compatibility editor; cross-source presentation, scene-card migration and new tours remain pending. No live campaign migration is performed.

# Session Desk 0.1.3

Windows x64 regular correction release. Update through Settings, or extract the whole ZIP and run SessionDesk.exe with _internal beside it.

## Prepared-map correction
Fixed “Cannot set properties of null (setting 'hidden')” when opening a restored prepared campaign. The map renderer referenced an AI control that is absent from this non-AI release. That interrupted map loading and room-list rendering. The obsolete reference is removed; no AI feature is enabled.

Your existing imported workspace is retained. You do not need to restore or import it again. Saved fog, notes, characters and source images stay in the same data folder; no workspace schema/data changes are introduced.

Browser regressions now require a hidden loading/error panel, rendered map pixels and the correct room list on both the initial dungeon and when switching between dungeon and regional maps. The previous heading-only check did not detect a caught renderer exception. These checks run against source and the frozen EXE.

## Updating
Save edits and export a private backup, then use Settings → Check for updates → Download and install → Restart into update. Updates verify the official checksum and packaged files, install side by side and preserve workspaces. Launchers from 0.1.1 onward forward to verified future installs. Preview/0.1.0 users need one manual download and shortcut change.

The home/removal/guided tutorial features from 0.1.2 remain. Prior release files stay immutable for rollback. This is an unsigned Windows x64 build with AI Off. No campaigns, books, artwork or credentials are bundled. Laptop/friend-PC and full source-geometry acceptance remain deferred.
