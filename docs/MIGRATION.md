# Campaign migration and optional features

Updated November 11, 2026. This page distinguishes the implemented core from planned migration/module work. It contains no personal campaign data.

## What Restore backup accepts today

Restore accepts a Session Desk workspace ZIP with a supported `workspace.json` manifest and hash-addressed images. It validates typed adventure/preparation/session/pin documents, identity references, geometry and assets, then publishes a new workspace atomically. It does not accept a folder archive, a different app's JSON save, an executable add-on or a raw Git repository.

Add adventure imports the selected source adventure. It does not discover campaign authoring folders, backstories, generated illustrations, custom map crops, house maps, encounter adjustments or live fog from a different app.

There is no legacy campaign converter or Characters module in preview 5. Do not describe a full-file recovery ZIP as an importable workspace or turn character records into generic notes while claiming sheet/thread support has migrated.

## Migration requirements

Before adopting a converted campaign:

1. Make a complete private recovery backup, including the matching old app, local edits, assets and live saved state. Keep external source-library requirements explicit. This recovery backup stays outside product source and release artifacts.
2. Inventory from the snapshot. Classify each item as preserved directly, converted with equivalent behavior, retained as read-only material, or unsupported. Report every unsupported field/module before writing a new workspace.
3. Use stable scoped IDs. Preserve custom/cropped DM/player image dimensions, multi-section room references, chronology of fog changes, initial visibility, reviewed/held image flags, narration, private notes and source provenance. Re-importing a source book alone is not campaign migration.
4. Compare rendered fog/room boundaries against the old runtime. A calibrated wall collar or neighboring-room exclusion is not equivalent to a plain source polygon. Reject mismatched coordinates instead of silently rescaling or revealing nearby secrets.
5. Restore only into a new isolated workspace. Verify source/player payload separation, persistence, packaged-runtime behavior and backup/restore into another root. Leave the original playable instance untouched until the owner adopts the copy.

Characters, ordered scene guides, point-location maps, shops, per-room player notes, token/camera/undo controls and generation tools need explicit preservation decisions where the target core lacks their behavior. Source texts can often be retained as private reference entries, but that does not reproduce specialized controls or calculations. Managed assets are currently validated raster images; retaining original PDFs, Markdown documents, ZIP prompt packs and authoring files requires an explicit non-executable attachment/authoring-data contract, not a claim that image import already covers arbitrary files.

## Optional workspace features: planned contract

The existing code/content boundary supports this direction, but a general module registry, module storage/API and module-aware backup format are **not implemented**. Storage currently rejects unknown document types rather than silently dropping them. No executable plug-in loading is authorized by restoring a workspace.

For a future Characters module, navigation requires all three conditions:

`module present in this build/install AND enabled for this workspace AND usable content exists`

Fresh workspaces remain a simple adventure/resources/session workflow, with no blank Characters, shop or scene-guide panels. Character data belongs to its workspace and DM-only routes; it never enters a player response, a default demo or a public release artifact. Rules references remain tied to the workspace's selected rules edition; do not substitute newer rules silently.

Distinguish optional UI from code distribution:

- A finished public module can be included in the common app while disabled/absent from navigation in a workspace that does not use it.
- An unreleased private module must be excluded from the public package by the explicit source/static/dependency allowlist. Hiding a button does not remove its implementation from an EXE or public source tree. A separately packaged owner module/build should share the core contract rather than fork campaign-specific application code.

Define module/schema versions, backup coverage and supported core versions before enabling it. A build without a module must preserve its stored data with clear read-only/unavailable behavior, or reject the workspace before changing it. Never save a reduced backup that silently discards an unknown module. Unsupported executable files are not imported or launched from backups.

The first simple release can omit these modules entirely. Personal migration is a separate compatibility exercise, not a reason to bundle the owner's data or unfinished features for testers.

## GitHub distribution boundary

The original private campaign repository also has an independent product branch. Publishing a release there does not make downloads available without repository read access; giving that access exposes other branches/history. A clean product branch is not a per-branch permission boundary.

The owner selected a separate public product-source repository on November 11: https://github.com/stafidopsomo/session-desk. Publish only the audited independent product history there. The original campaign repository remains private; do not change its visibility or mirror all its refs. A downloads-only repository was considered but was not the owner's choice.

These choices do not change workspace privacy: no personal campaign, source library, migration report or recovery backup belongs in either distribution repository. See [release process](RELEASE-PIPELINE.md) for actual publication gates and [build status](BUILD-STATUS.md) for remaining acceptance.
