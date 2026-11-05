# Session Desk — release development

A proposed local app for preparing and running independent tabletop adventures. **Session Desk is a working title.**

**Current status: architecture review, not a runnable tester release.** No executable, provider connection or automated adventure preparation has been delivered on this branch. Implementation is gated below, following the owner's instruction to resolve architecture/dependency gaps first.

## Intended tester experience

1. Download and extract the Windows release ZIP. Run `SessionDesk.exe`; no Python, Git, Node or coding editor is required to run the core app.
2. Choose an existing local 5e.tools adventure and image library. Select the adventure to import. A fresh install has no campaign or characters preloaded.
3. Connect a supported AI provider in Settings, using the user's own account. The setup flow handles supported provider dependencies; the user completes the provider's sign-in.
4. Choose **Prepare**, review the proposed materials, then **Start session**. The user operates the app through its features; a coding assistant or ongoing developer chat is not part of this workflow.

These steps are the release acceptance target, not installation instructions for a build that already exists. An account, provider allowance and internet access are still needed for online AI work; local play and already-created materials should work offline.

## Decisions and implementation gate

- [Product scope and release-readiness assessment](docs/READINESS.md)
- [Architecture and data boundaries](docs/ARCHITECTURE.md)
- [Provider feasibility and official references](docs/PROVIDERS.md)
- [CI, packaging and release design](docs/RELEASE-PIPELINE.md)
- [Acceptance milestones](docs/IMPLEMENTATION-GATES.md)

First import format: **an existing local 5e.tools adventure plus images**, confirmed by the owner. PDF ingestion is deferred. Windows x64 is the proposed first target; other platforms need separate builds and tests.

## Privacy and distribution

This branch begins with a parentless commit and contains no personal campaign content. Development uses a separate worktree from the live personal app.

The surrounding GitHub repository still contains private campaign history on other refs. **Do not make that repository public or give testers repository access.** Pending a final distribution decision, testers receive only audited release ZIP/EXE assets. A separate clean repository is required before sharing source access without exposing the personal repository.

No books, adventure pictures, character records, user workspaces, credentials, generated campaign notes or personal branding belong in the product build. Users import their own local source library after installation.

The superseded prototype is not the base for this product. No personal-app migration occurs until a stable release exists and the owner chooses to migrate.
