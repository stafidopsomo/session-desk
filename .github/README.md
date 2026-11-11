# Session Desk

A local Windows app for preparing a tabletop adventure and showing maps, pictures and notes on a separate player screen.

[![Windows checks](https://github.com/stafidopsomo/session-desk/actions/workflows/readiness.yml/badge.svg?branch=main)](https://github.com/stafidopsomo/session-desk/actions/workflows/readiness.yml)

**Status:** Windows x64 development preview, 0.1.0-dev.6. A first tester prerelease is being prepared; no GitHub release has been published yet. AI is Off and unavailable.

## Run a packaged build

1. Download the **SessionDesk Windows x64 ZIP** supplied with the build. Use the application ZIP, not GitHub's automatically generated source-code ZIP.
2. Extract the entire ZIP. Double-click **SessionDesk.exe**, keeping `_internal` beside it.
3. Create a workspace, choose **Add adventure**, and select an existing local 5e.tools library or install the supported local 2014 copy at a location you choose.
4. Import an adventure. Prepare narration and private notes, review map/image safety, then choose **Present to players** and **Open player screen**.

No Python, Git, Node or AI account is required to run the EXE. Current development builds are available as `sessiondesk-windows-x64` artifacts from green [Actions runs](https://github.com/stafidopsomo/session-desk/actions/workflows/readiness.yml); GitHub requires sign-in to download an Actions artifact. A versioned download will appear under [Releases](https://github.com/stafidopsomo/session-desk/releases) after release acceptance is complete. An Actions artifact is not a published release.

## At the table

- **Resources:** browse collapsible book chapters or search Text, Images and Maps. Pin entries and images you use often. Text opens the reader/preparation; media opens its preview.
- **Maps:** inspect rooms without revealing them, draw a corrected boundary, reveal rooms or use the adjustable brush. The brush circle follows size and zoom.
- **On player screen:** select/close shared tabs. Players can zoom and make temporary drawings. Shared notes stay separate from private DM preparation.
- **Workspaces:** keep independent adventures together and move a workspace between computers using Export backup / Restore backup.

Books, official artwork, campaigns, characters, provider accounts and credentials are not bundled. You select your own source files. Restore backup also imports supported prepared campaigns, enabling their character sheets, scene guides and shops in the same EXE. Fresh workspaces have no empty optional panels. AI generation remains deferred.

## Saves and updates

Workspaces live in `%LOCALAPPDATA%\SessionDesk\workspaces`, outside the app folder. Before moving computers or upgrading, **Export backup**. Restore creates a separate workspace with its pictures. Supported prepared-campaign recovery ZIPs convert during Restore. Other applications/formats need a compatible converter; arbitrary saves are not accepted.

Close both DM and player windows, wait about ten seconds for the local server to exit, then replace the extracted app folder. Your workspace data remains in its separate location. Never overwrite workspace data with files from a release ZIP.

This is an unsigned development build, initially checked on Windows 11 x64. Same-computer/TV presentation is supported; remote/LAN player devices are not. No automatic telemetry or AI/provider activity is enabled. Report the app version, Windows version, steps and expected/actual behavior when giving feedback; keep campaign backups and source books private.

## Development

The canonical Windows job is [`ci.ps1`](../ci.ps1) in the repository root. GitHub's workflow wrapper is under `.github/workflows/`. Source tests use original synthetic content; packaging excludes tests, source libraries, workspaces and provider tooling.

[Developer guide](../docs/README.md) · [Short user instructions](../docs/QUICKSTART.txt) · [Build status](../docs/BUILD-STATUS.md) · [Migration and optional features](../docs/MIGRATION.md) · [Release process](../docs/RELEASE-PIPELINE.md)
