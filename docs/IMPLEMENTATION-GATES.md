# Implementation and alpha acceptance gates

This is the development handoff for future work in this chat/worktree. The personal campaign remains on its own branch and is not migrated automatically.

## Gate 0 — architecture, before application implementation

Confirmed by owner:

- Import an existing local 5e.tools adventure/image library first.
- No personal campaign material in the shared product.
- Create a clean release-dev line and retire the superseded prototype branch.
- Keep the normal product UI small; users do not need an ongoing coding chat.
- Preserve the personal instance and migrate it manually only after product stability.

Awaiting resolution:

- Accept the workspace, source graph, job/resource and provider boundaries in ARCHITECTURE.md.
- Confirm the proposed Windows x64 first target and define the supported OS floor in the packaging spike.
- Select the first supported provider/auth route. OpenAI Sign in with ChatGPT configuration/registration and the intended distribution context must be resolved if that route is selected. Verify the equivalent SDK/installation conditions before choosing another adapter.
- Accept capability-specific support and review of uncertain geometry. No promise that all text providers automatically generate artwork or precise masks.
- Distribution question is still pending. The provisional path keeps this repository private and shares clean build assets only. A separate clean product repository remains an option.

**Do not start application implementation before these are resolved.** Do not install provider tooling, make paid/inference calls or publish a tester build as part of this preflight.

## Gate 1 — executable architecture spike

Prove, with original synthetic data:

1. Frozen Windows app starts under a fresh standard-user profile with no Python/Git/Node dependency for the core runtime.
2. One workspace stores its state/assets outside the installation; a second workspace does not see its records.
3. Source adapter imports a small synthetic adventure with map regions, including repeated keys and a region representing only a feature.
4. A selected provider's supported sign-in and one bounded structured-text task works through the app, without a developer chat, browser automation or developer credentials. Permission/staging boundaries prevent direct production writes.
5. App-managed provider component installation/detection is verified on a clean machine. If it requires undocumented manual steps, the claimed one-click setup is not ready.

This spike is not a tester release. Its outcomes determine the locked toolchain and final schema/API contracts before more UI is built.

## Gate 2 — first useful vertical slice

`New workspace → select library → select adventure → import inventory/known maps and regions → prepare one selected resource → review/edit → present on player screen → save/restart/export/import`

Requirements:

- Exact source locators and useful missing-resource errors.
- No source download or paid account provisioning hidden inside installation.
- All input facts, generated drafts, user edits and active session state remain distinguishable.
- Notes/translations use the selected locale and preserve configured proper names; no personal party assumptions.
- Room/brush fog, player-safe map selection and reviewed geometry; incomplete geometry is visibly incomplete.
- Queued/cancelled/failed AI jobs resume safely without duplicate generation or automatic billing/provider fallback.
- Workspace backup restores required images and state into a different location.

## Gate 3 — Icewind Dale acceptance, local owned-source test

Use the owner's selected library outside Git and outside CI. Import its inventory without adventure-specific code changes. Confirm image resolution, chapters/source links, maps with and without keyed regions, repeated physical areas and source-entry references. Compare imported geometry to actual images. Missing or ambiguous content is reported rather than fabricated.

The observed local inventory (42 maps, 38 region-bearing maps, 465 regions) is an assessment datum, not a hard-coded expected value for all users/versions.

Do not publish the source files, resulting adventure workspace, model context or screenshots containing book/personal content in test fixtures or product releases.

## Gate 4 — private tester alpha

- Build/release pipeline implemented and green for the exact tag/commit.
- Installation tested on a clean Windows machine; no developer folders or saved accounts are required.
- Fresh profile starts with no campaigns, notes, characters, usage/account snapshots or source books.
- Only implemented and verified provider capabilities are offered.
- No image automation is claimed without an actual image-provider artifact test; manual import is clearly available instead.
- Session workflow, backups/migrations, cancellation and provider-failure paths pass end-to-end tests.
- Artifact manifest, privacy audit, dependency notices, signing status and checksums verified.
- Tester instructions are genuinely short: extract → run EXE → choose source → connect provider if desired → prepare/review/play. An honest Known limitations section accompanies the alpha.
- Feedback/support exports are opt-in and redact personal content, credentials and paths by default.

## After stability

Plan personal-campaign migration as a separate export/import feature with a backup, dry run, compatibility report and rollback. Do not rewrite the live personal app or attach its history to the product branch. PDF/OCR imports, additional operating systems, more providers, native window shells and remote player devices are later milestones, not silent additions to the first alpha.
