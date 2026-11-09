# Session Desk — release development

A local app for preparing and running independent tabletop adventures. Session Desk is a working title.

**Gate 0 is approved for the non-AI core (November 9, 2026).** The owner accepted the architecture and Windows x64 target. Core implementation/packaging can proceed; all AI/provider/isolation work is deferred. This checkout still contains design and offline readiness tools, not a runnable tester EXE.

## First tester workflow

1. Download/extract the vetted Windows x64 ZIP and run SessionDesk.exe. The core runtime must not require installed Python/Git/Node or a coding editor.
2. Select an existing local 5e.tools adventure/image library and import an adventure. A fresh profile has no campaign or characters preloaded.
3. Review maps/regions, enter notes/translations manually and add/import pictures as needed.
4. Start a session using the DM/player views, explicit fog controls, shared tabs and notes. Save and back up the workspace independently of app upgrades.

One top-right **Settings** menu contains **Display** and the global **AI on/off** control. **Open player screen** stays in its separate existing header position. In the first build AI is Off/unavailable; there is no provider setup, account/allowance polling or generation. The non-AI workflow does not depend on a provider login or an ongoing developer chat.

These are acceptance targets, not instructions for an EXE that already exists. Windows x64 is confirmed for the owner's laptop/main PC and a friend's PC; supported Windows versions and compatibility are established by packaging/machine tests.

## Approved design and implementation milestones

- [Architecture and Settings/AI switch behavior](docs/ARCHITECTURE.md)
- [Current gates and first non-AI release scope](docs/IMPLEMENTATION-GATES.md)
- [Readiness assessment and remaining engineering proofs](docs/READINESS.md)
- [CI, packaging and distribution design](docs/RELEASE-PIPELINE.md)

[Provider feasibility](docs/PROVIDERS.md) and [Codex preflight](docs/CODEX-PREFLIGHT.md) are historical references for the deferred AI phase. They are not blockers or setup steps for the core build. ChatGPT through Codex remains the earlier first AI candidate, with no capability or distribution authentication claimed as implemented.

## Existing developer checks

With Python 3.12 and Git already installed:

```text
python tools/check_product_boundary.py
python -m unittest discover -s tests -v
```

The readiness workflow runs these offline checks using synthetic data. It does not run a provider, build an application or publish an artifact. Product build/E2E jobs must be added as the core is implemented.

## Privacy and distribution

This branch has parentless, campaign-free history and a separate worktree. Do not copy personal content or merge personal commits into it. All editable user content belongs in external workspaces.

The surrounding private GitHub repository contains campaign history on other refs. Testers receive only audited ZIP/EXE files shared directly, without repository access. The owner can download a private build and forward its vetted ZIP; a private release URL is not public distribution. Source sharing requires a separate clean repository.

No source books, official adventure art, character records, workspaces, credentials or personal branding belong in the product build. The owner may migrate the personal campaign later after stability using a separately verified backup/import path.
