# Session Desk

A local Windows app for preparing tabletop adventures and showing maps, pictures and notes on a separate player screen.

[![Windows checks](https://github.com/stafidopsomo/session-desk/actions/workflows/readiness.yml/badge.svg?branch=main)](https://github.com/stafidopsomo/session-desk/actions/workflows/readiness.yml)

**0.3.1 — Windows x64 regular release.** AI is Off and unavailable.

[**Download the Windows application ZIP**](https://github.com/stafidopsomo/session-desk/releases/download/product-v0.3.1/SessionDesk-0.3.1-windows-x64.zip) · [Release notes and checksum](https://github.com/stafidopsomo/session-desk/releases/tag/product-v0.3.1)

## Start

1. Download and extract the complete application ZIP.
2. Double-click **SessionDesk.exe**. Keep `_internal` beside it.
3. Create a **Campaign** or **One-shot / standalone session** workspace.
4. Choose **Add source**, connect your local 5e.tools library or explicitly install the supported local 2014 copy, then import.
5. Prepare your resources → **Present** → **Open player screen**.

Have a backup? Choose **Restore backup**. No Python, Git, Node or AI account is needed. Source books, pictures, campaigns, characters and credentials are not bundled.

## At the table

- **Book:** session records, preparation and missions, with separate offered/awarded rewards and retained conflicting drafts.
- **Resources:** imported book readers, maps, pictures, pins and inline preparation; restored maps retain their calibrated geometry and fog.
- **Party:** concepts and private notes, with complete restored sheets available through Open full sheet.
- **Independent tabs:** keep characters, rooms and book entries open separately. Map inspection is private; presentation and reveal are explicit.

Campaign starts at Book. One-shot opens Resources directly without a Book section. Adventure tabs keep imported sources side by side. Settings contains display, updates and Quick tour; Open player screen stays separate.

## Saves and updates

Use **Settings → Check for updates → Download and install → Restart into update**, or extract the new application ZIP. Regular updates retain `%LOCALAPPDATA%\SessionDesk\workspaces`; source files and imported campaigns are not re-imported or replaced. Export a backup before changing installations or computers. Restore creates a separate workspace; reconnect its local source library on another PC.

The earlier local `--preview` profile remains separate. Its edits do not automatically merge into the regular app. Launchers from 0.1.1 onward forward to verified installed updates; earlier launchers need one manual download and shortcut change.

## Limits

The package is unsigned. Actual laptop/friend-PC compatibility and complete source-map geometry review remain pending. Full mechanical-sheet editing uses the compatibility editor; further Party, scene-card and cross-source presentation integration remains planned. Homebrew JSON/PDF/OCR importing, AI generation and remote/LAN players are not implemented. No automatic telemetry or provider activity is enabled.

Use GitHub Issues for feedback with the app/Windows versions and steps to reproduce. Keep private backups and source books out of reports.

## Development

The root [ci.ps1](../ci.ps1) runs the canonical Windows checks; GitHub's wrapper is under .github/workflows/. Tests use original synthetic fixtures. The tag pipeline validates exact-tree acceptance and every file in its own CI-built ZIP before publication.

[Developer guide](../docs/README.md) · [Quick start](../docs/QUICKSTART.txt) · [Build status](../docs/BUILD-STATUS.md) · [Migration](../docs/MIGRATION.md)
