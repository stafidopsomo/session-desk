# Session Desk

A local Windows app for preparing a tabletop adventure and showing maps, pictures and notes on a separate player screen.

[![Windows checks](https://github.com/stafidopsomo/session-desk/actions/workflows/readiness.yml/badge.svg?branch=main)](https://github.com/stafidopsomo/session-desk/actions/workflows/readiness.yml)

**0.1.0-preview.1 — Windows x64 preview prerelease.** Laptop/friend-PC testing is pending. AI is Off and unavailable.

[**Download the Windows application ZIP**](https://github.com/stafidopsomo/session-desk/releases/download/product-v0.1.0-preview.1/SessionDesk-0.1.0-preview.1-windows-x64.zip) · [Release notes and SHA-256 checksum](https://github.com/stafidopsomo/session-desk/releases/tag/product-v0.1.0-preview.1)

## Start

1. Download the application ZIP above; GitHub's Source code ZIP is not the application.
2. Extract the entire ZIP. Double-click **SessionDesk.exe**, keeping _internal beside it.
3. Choose **New workspace → Add adventure** and select an existing local 5e.tools library, or explicitly install the supported local 2014 copy.
4. Import, prepare/review the resources, then **Present to players → Open player screen**.

Have a compatible Session Desk or prepared-campaign backup? Choose **Restore backup** instead. Imported content enables its character sheets, scene guides and shops. New workspaces have no empty optional panels.

No Python, Git, Node or AI account is required to run the EXE. Books, official artwork, campaigns, characters and credentials are not bundled. Choose your own source files.

## At the table

- **Resources:** collapsible chapters, Text/Images/Maps search and persistent pins. Text opens the reader/preparation; media opens its preview.
- **Maps:** inspect rooms without revealing, draw a corrected boundary, reveal rooms or use the adjustable brush.
- **On player screen:** select/close shared tabs, zoom and make temporary drawings. Shared notes stay separate from private DM notes.
- **Workspaces:** keep independent adventures together and move them between computers using Export backup / Restore backup.

## Saves and updates

Workspaces live in %LOCALAPPDATA%\\SessionDesk\\workspaces, outside the app folder. **Export backup before upgrading or moving computers.** Restore creates a separate workspace with its images; reconnect the local 2014 library on a different PC. Keep backups private.

Close DM/player windows, wait about ten seconds, then replace the extracted app folder. Do not replace your workspace data with release files. Older schema-1 workspaces upgrade with a recovery copy; older preview 5 cannot open schema 2.

## Preview limits

This package is unsigned. Automated checks run on Windows 11 x64 and Windows CI; a fresh app profile/PATH test is not a physical laptop or clean-VM test. Laptop/friend-PC compatibility and full visual review of every source map remain pending. Review maps before sharing. AI generation, PDF/OCR and remote/LAN players are deferred. No automatic telemetry or provider activity is enabled.

Use GitHub Issues for feedback with the app/Windows versions and reproducible steps. Do not attach private workspaces or source books.

## Development

The root [ci.ps1](../ci.ps1) is the canonical Windows job; GitHub's wrapper is under .github/workflows/. Tests use original synthetic fixtures. Packages exclude tests, source libraries, workspaces and provider tooling. The tag pipeline checks exact-tree acceptance, clean provenance and every package file hash before publishing.

[Developer guide](../docs/README.md) · [Short instructions](../docs/QUICKSTART.txt) · [Build status](../docs/BUILD-STATUS.md) · [Migration](../docs/MIGRATION.md) · [Release process](../docs/RELEASE-PIPELINE.md)
