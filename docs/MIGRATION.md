# Campaign migration and optional features

Updated November 11, 2026. Implemented in development preview 6. No personal campaign data is distributed.

## One application, two starting points

New users create a workspace and use Add adventure. They see Resources, preparation and presentation, with no empty Characters, shops or story panels.

Existing users choose Restore backup. It accepts native Session Desk workspace ZIPs (schema 1 and 2) and prepared-campaign data ZIPs with a supported campaign.json. A complete campaign-desk-full-snapshot recovery ZIP is also accepted when it contains exactly one campaign. Restore creates a new workspace; it never changes the original campaign or replaces an existing workspace.

A supported, enabled campaign-desk-v1 module with content adds **Open prepared campaign** to that workspace. The same application contains its trusted renderer: editable characters/sheets/backstories/threads, ordered scene and session guides, shops, point-location maps, exact calibrated map/fog behavior, shared room notes, temporary tokens/camera controls and player drawing. Optional navigation depends on usable imported content.

Connect the explicitly selected local 2014 source library once for rules and book links. This machine-local folder setting is excluded from portable backups; reconnect it on another computer. The library itself is never bundled or downloaded implicitly during restoration. A different edition is not silently substituted.

## Preservation contract

The supported prepared format preserves every authored file, custom/cropped DM/player map and its original dimensions, section polygons, wall padding, initial visibility, fog chronology, narration, encounter notes, image review flags, character records, PDFs, Markdown and authoring files. Download individual files through Browse campaign files. The complete original recovery ZIP is retained as an opaque attachment when importing a file-based recovery archive.

Original scripts, HTML and JavaScript carried by a backup are **attachments only**. They are never executed, imported as Python or served as application templates. AI/provider tools are absent from the active renderer. AI stays Off. Generation/quota/provider workflows are deferred; their authoring files can be retained without enabling those tools.

Temporary drawing, token positions, camera/ping and browser display preferences retain their temporary behavior. Restore cannot recover ephemeral state which the original app never saved. Export captures persisted edits, not unsaved typing. Retaining an authoring script does not promise that its old developer environment is installed.

Export backup snapshots edited module files and includes their immutable hashed attachments, generic adventure documents and the original recovery archive. Restore validates paths, hashes, image dimensions, typed references and saved fog before atomic publication. Failed/cancelled imports expose no partial workspace. Backups are private content, not release assets. Total content remains bounded to 1 GB plus metadata; one attachment is limited to 512 MB, one image to 48 MB.

Native workspace schema 1 upgrades to schema 2 with a local workspace-schema-1.sqlite3.bak recovery copy. Schema 1 ZIP backups remain importable. Preview 5 cannot open schema 2; keep the original ZIP for rollback. Unsupported module kinds/versions remain unavailable and roundtrip unchanged instead of being discarded or executed. Unsupported future core formats fail before publication.

## Adoption checks

Make a complete private recovery snapshot first, including local edits and the matching old app. Import into an isolated workspace, compare all file hashes, map coordinates and rendered fog with the previous renderer, then export/restore into a different data root. Check source/player separation and the frozen Windows build. Only then adopt the imported workspace. The original app remains a rollback path.

The generic adventure importer is separate from prepared-campaign conversion: Add adventure loads the chosen source book, while Restore carries authored campaign work. Importing a book alone does not recreate a previous campaign's notes, art, characters or saved session.

## Distribution boundary

Public product source: https://github.com/stafidopsomo/session-desk. It contains only the independent product history, generic renderer and original synthetic tests. The original campaign repository stays private. No personal backup, source library, migration report, private characters or campaign artwork belongs in source/CI/releases. See [build status](BUILD-STATUS.md) for evidence and [release process](RELEASE-PIPELINE.md) for the unchanged alpha gate.
