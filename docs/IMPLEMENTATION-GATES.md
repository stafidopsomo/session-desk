# Implementation and alpha acceptance gates

Updated November 9, 2026. These are implementation/acceptance milestones, not a request for the owner to approve another document packet. The personal campaign remains separate and is not migrated automatically.

## November 9 implementation status

Gate 0 is complete. The owner explicitly confirmed **Gate 1 complete** in the conversation on November 9; that is the recorded basis for closure. No specific Windows build or new compatibility range was supplied, so none is invented. Do not reopen Gate 1 or ask for its approval packet again.

Development preview 4 completes the defined non-AI Gate 2 slice with cancellable backup/restore, atomic workspace publication, interruption recovery, source-image repair and expanded schema/failure coverage. This remains a development preview. Gate 3 visual/owned-library acceptance and Gate 4 tester/artifact acceptance remain separate; no alpha is published automatically.

## Gate 0 — resolved for the non-AI core

Owner decisions confirmed on November 9:

- ARCHITECTURE.md is accepted, including workspace/source/resource/job boundaries and review of uncertain geometry.
- Windows x64 is the first target: the owner's laptop, main PC and a friend's PC. The supported Windows-version floor is established by the packaging spike and recorded machine tests, not another architecture approval.
- One top-right Settings menu groups Display and the global AI on/off control. Keep Open player screen in its separate existing header position.
- All proposed AI features and route-isolation work are deferred for now. This includes provider adapters, component installation/discovery, sign-in, account/quota polling, generation, image/mask proposals and live diagnostics. They are not prerequisites for the current core.
- Existing local 5e.tools adventure/images remain the first import format. The later November 9 setup request also authorizes an explicit local 2014 source installer at a chosen location, with optional on-import adventure images. PDF/OCR stays deferred.
- Preserve the clean product history and the existing personal instance. No campaign data in source/builds; no automatic personal migration.

The safe distribution default is audited ZIP/EXE files shared directly with testers, without giving them access to this private repository. Public source/repository distribution remains a later decision and does not block the core spike.

**Gate 1 core implementation and core dependency/packaging work may proceed.** No provider tooling or live AI work is authorized by this scope change. Gate 0 is a design approval, not proof that an app, installer or alpha already exists.

## Gate 1 - complete by owner confirmation

Owner confirmation: November 9, 2026, conversation message: "gate 1 is omplete lets continue". This closes the executable core/Windows x64 spike. Automated evidence also covers isolated workspaces, generic source identities/regions, Settings/player workflow, bundled-runtime startup with developer PATH hidden, and AI rejection.

The agent's automated tests are not relabeled as clean-VM tests. Exact additional OS/account details were not supplied with the owner's confirmation; this does not block Gate 2 or create another approval request. Broader version/device compatibility remains part of release acceptance.

## Gate 2 — useful non-AI vertical slice

Status: implemented and covered by synthetic storage/HTTP/browser/frozen-package checks in development preview 4. Scope includes the failure and cancellation paths below. Real-library visual/geometry verification belongs to Gate 3.

`New workspace → select local library → select adventure → import inventory/maps/known regions → manually prepare/edit or import materials → review → present → save/restart/export/import`

Requirements:

- Exact source locators, version/schema detection and useful missing-resource errors.
- No hidden source downloads, account provisioning or paid dependencies in the core setup.
- Imported facts/assets, manual edits and actual session state remain distinguishable. Translations/notes can be entered or imported manually; no automatic generation is promised.
- Locale, names, rules profile and encounter assumptions belong to the workspace, with no preloaded personal party or campaign preferences.
- Room/brush fog, player-safe map selection and direct mouse boundary correction. Source polygons are usable without an approval step; missing geometry requires a drawn edge or brush. Do not invent geometry. The November 9 owner correction removes coordinate fields and verification controls.
- Shared player tabs/notes and explicit visibility actions; preparation never reveals a room automatically.
- Import/export cancellation, failure recovery and asset validation. Backup/import into another root includes all required images and state.
- One top-right Settings menu; Display and AI control together; Open player screen stays separate. AI remains Off with no provider/background activity.

## Gate 3 — Icewind Dale acceptance, local owned-source test

Use the owner's explicitly selected library outside Git/CI. Import its inventory without adventure-specific code changes. Confirm image resolution, chapter/source links, maps with/without keyed regions, repeated physical areas and source-entry references. Compare geometry with actual images; report ambiguity or missing content instead of inventing it. This acceptance path requires no AI.

The earlier local inventory (42 maps,38 region-bearing maps,465 regions) is an assessment datum, not a hard-coded expectation for every library version.

Do not publish source files, the resulting workspace or screenshots containing book/personal content in fixtures or releases.

## Gate 4 — first private tester alpha, AI deferred

- Build/release pipeline is implemented and green for the exact tag/commit.
- Windows x64 ZIP starts on clean standard-user profiles without developer tools/accounts. Test on the named owner/friend machines when available and record the actual results; naming them is not a completed hardware test.
- Fresh profiles contain no campaigns, characters, notes, source books, account state or personal branding.
- Import/manual preparation, review, maps/fog, tabs/notes, backup/restore and persistence pass end to end.
- Settings groups Display and the global AI control; Open player screen stays outside. AI is Off/unavailable, and the artifact contains no provider runtime/dependency or claimed AI capability.
- Artifact manifest, privacy audit, dependency notices, signing status and checksums are verified.
- Tester instructions stay short: extract → run EXE → select local library/adventure → import/review/edit → play. Known limitations explicitly say AI preparation is deferred.
- The owner may download the vetted private build and provide its ZIP directly to testers. Do not assume a private GitHub release link is accessible without repository permissions.
- Feedback exports are opt-in and redact personal content, credentials and local paths by default.

## Later AI phase — separate workstream

ChatGPT through Codex remains the earlier selected first candidate, but no provider route or isolation implementation is required now. When the owner resumes AI work, validate supported installation/authentication, an enforced staging boundary, bounded structured output, cancellation and the global Off policy before enabling any capability. The historical sandbox preflight is neither a successful integration nor a blocker to the current core.

Use capability-specific validation and human review for uncertain geometry. Do not silently revive deferred AI work, add paid fallbacks or claim that text-provider access includes artwork generation.

## Personal migration and later platforms

After product stability, prepare personal-campaign migration with backup, dry run, compatibility report and rollback. Do not rewrite the live personal app or merge its history. PDF/OCR, other operating systems, additional providers, native shells and remote player devices remain later scope.
