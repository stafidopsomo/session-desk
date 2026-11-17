# Windows desktop build status

Current regular release: **0.2.1**, published as GitHub Latest and installed from its verified public package on November 17 for everyday use. Book / Resources / Party is the default on the normal SessionDesk profile; the separate local preview remains intact. The evidence below distinguishes automated checks, owner reports and deferred hardware/geometry acceptance.


Updated November 14, 2026. Version **0.1.3**, unsigned initial Windows desktop release. No completed alpha is claimed.

## Implemented

- Independent workspaces outside the installation; generic local 5e.tools adventure import, source-ordered Resources/search/pins, original book formatting, inline room preparation and image review.
- Cancellable import/export/restore, atomic workspace publication, same-source image repair, staged interruption recovery and bounded verified backups.
- Separate DM/player capabilities and windows, explicit shared tabs/notes, room/brush fog, corrected boundaries, adjustable brush cursor, pan/zoom and temporary drawing. Selection does not reveal.
- Settings contains Display and AI Off/unavailable. Open player screen stays separate. No provider runtime, account discovery, quota polling, inference or generation routes.
- Prepared-campaign recovery import through the same Restore backup control and EXE. Optional data activates editable characters/sheets/threads/backstories, scene/session guides, shops, calibrated cropped maps/fog, shared room notebooks and temporary tokens/camera/drawing. Fresh workspaces have no empty optional panels.
- All authored campaign files and original recovery archive preserved as data/attachments. Imported scripts/templates are never executed. Explicit local 2014 rules connection stays machine-local. Unknown module versions remain inert and portable.
- Workspace schema 2; schema 1 upgrades with a SQLite recovery copy and existing schema 1 ZIPs remain importable. Older app versions cannot open schema 2.
- Frozen Windows x64 one-folder ZIP, bundled Python/Tk, explicit source/static allowlists, dependency/license notices, checksums, file manifest and provenance. Tests, books, workspaces and personal data are excluded.

## Verification

Host: Windows 11 Pro x64 build 26300, Python 3.12.10. Synthetic automated tests use isolated app data and original fixtures. No owned books/private data run in CI or enter its artifacts.

- 134 offline unit/contract tests cover generic import/storage/HTTP, schema upgrades, prepared-file preservation, unknown-module roundtrip, failed/cancelled imports, DM/player separation, 2014 rules, attachment safety and AI rejection.
- Core browser E2E covers first run/import, preparation, book formatting, pins/folds/scroll, boundaries, reveal radius, Space-pan, player tabs/notes/drawing, cancellation, native backup download and restored state.
- Prepared browser E2E uses Restore, connects a synthetic rules library, edits a sheet, opens guides/shops, shares notes/draws, exports and restores into another data root. It checks that a fresh workspace has no optional panels and blocks/asserts external requests.
- Frozen smoke/E2E use an isolated profile and hide developer tools from PATH. Extracted-ZIP checks verify hashes, Unicode relocation, persistence, last-window shutdown and unchanged install files. This is not a clean VM or another physical computer.
- Local owned-library import/persistence sweep: all 80 available adventures in the selected 2014 library loaded, with zero importer warnings, including Sunless Citadel, Forge of Fury, Waterdeep and Icewind Dale. Private reports stay outside Git. Import success does not certify every source polygon's visual accuracy.
- Private campaign migration checks files, assets, saved fog and specialized controls against the recovery snapshot. Reports/backups stay outside source and builds. See MIGRATION.md for preservation and temporary-state limits.

The product implementation commit passed [GitHub run 43047995272](https://github.com/stafidopsomo/session-desk/actions/runs/43047995272). Its downloaded package independently passed seven real-library import/export/restore cases and a full private campaign roundtrip, including exact fog raster comparison. All 80 available sources completed roundtrips across the local runs; three transient loopback connection timeouts were retained in private reports and passed when checked again. The exact commit's GitHub Actions run is the remote CI record. Local success is not described as remote CI. Packaging fails if developer paths or disallowed content appear in the ZIP.

## Remaining acceptance

Gate 0 is closed; Gate 1 is complete by the owner's explicit November 9 confirmation. Gate 2's non-AI workflow is implemented. Broader visual/geometry acceptance and actual laptop/friend-machine testing remain separate from same-PC automated evidence. Alpha publication stays blocked by release/acceptance.json until exact-tree evidence covers all required checks. Do not turn pending flags true merely to publish.

AI, PDF/OCR importing, automatic geometry inference and remote/LAN player devices are deferred. No universal campaign format, runtime plug-in installation, signed installer or bit-identical reproducible EXE is promised. A compatible prepared module preserves authoring files without installing the tools that originally created them.

## First public preview validation

The owner requested the first GitHub preview with automated tests while laptop access is unavailable. This changes the publication scope for product-v0.1.0-preview.1 only; it does not claim a laptop test or completed alpha. The release gate separately requires exact-tree evidence, a scoped owner decision and verified package provenance/file hashes. Local and GitHub Windows runs cover all 84 Python tests, Node renderer tests, both browser workflows from source/frozen EXE, and extracted-ZIP lifecycle/relocation/backup checks. Owned sources and private backups remain local-only. The final acceptance record identifies the checked tree and evidence; publication is blocked until those runs succeed.


First-preview candidate 93d17de passed [Windows CI run 43102202769](https://github.com/stafidopsomo/session-desk/actions/runs/43102202769) and the same local root job. Its frozen EXE passed seven representative owned-adventure import/export/restore checks with zero warnings, plus the private full-file campaign and pixel-identical fog roundtrip. Only aggregate evidence is committed. The tag pipeline repeats the build checks and verifies its own same-run artifact before publishing; laptop/full visual acceptance remains deferred.


## Reviewed preview.2

November 12 owner request: independent structure/code review, fix verified defects and rebuild for tomorrow's testing. Three reviewers plus root review produced [the report](reviews/2026-11-12/REVIEW.md). Job/transfer ownership is now a composed service. Regression checks cover Windows cleanup locks, incomplete materialization, mid-snapshot cancellation, compact asset-complete exports, offline sheets, safe limits, generic book links, installer preference failure and ordered player presentation.

All checks must pass for the exact reviewed tree before preview.2 publication. Laptop/full visual results remain deferred. This is a correction prerelease with preview.1 retained as rollback, not a completed alpha or proof of compatibility on unseen hardware.


Reviewed candidate b952549 passed [GitHub Windows run 43119376138](https://github.com/stafidopsomo/session-desk/actions/runs/43119376138) and the full local root job: 109 Python tests, Node checks, source/frozen browser regressions and extracted-package lifecycle/relocation. Seven owned adventures completed frozen import/export/restore without warnings; the private full-file campaign roundtrip and rendered-fog comparison passed. Only aggregate evidence is committed. The tag pipeline repeats the exact build checks and verifies its same-run archive before publication.


## Initial desktop release 0.1.0

November 13: owner main-PC installation/testing report is positive. The requested ordinary GitHub release is separately scoped in acceptance; untested laptop/full source-map geometry remains deferred. New browser regressions exercise the offline animated home, actual first-run tour, remembered source prefill, direct fully-covered presentation, live brush pixels before release, inspector resize, central-reader scaling, settings dismissal and real player heartbeat LED. Entity links have seven Node checks. Eleven fake-transport updater tests cover trusted URLs, content hashes, traversal, cancellation, failure, existing-install protection and verified retry. Native process-wait/restart-failure tests preserve current app availability. No startup update network polling occurs.


Candidate 48184d6 passed [Windows CI 43338252359](https://github.com/stafidopsomo/session-desk/actions/runs/43338252359) and the local root job:130 Python tests,7 Node tests,all three source/frozen browser workflows and extracted-ZIP smoke. Six owned adventures including Tomb of Annihilation completed frozen portable roundtrips with zero warnings; the private full-file/fog roundtrip and actual local 2014 statblock viewer passed. Only aggregate evidence is committed. The regular release tag repeats all checks, verifies its same-run package, then publishes as Latest. The public download and real updater transport are checked after publication.


## Persistent desktop update handoff 0.1.1

Candidate 2c3b83b passed [Windows CI 43341009359](https://github.com/stafidopsomo/session-desk/actions/runs/43341009359) and the full local root job: 132 Python tests, 7 Node tests, all three source/frozen browser workflows and extracted-ZIP smoke. A verified activation pointer keeps explicit installed updates active through shortcuts pointing to 0.1.1-or-newer launchers on subsequent cold starts. Preview/0.1.0 executable code cannot forward; those users need one manual download and shortcut change. Newer builds verify the exact managed target, manifest and file hashes before forwarding; damaged pointers fall back to the current build. Equal-version launches do not loop. Source code and user workspace files remain separate.

The preceding public 0.1.0 ZIP and real GitHub updater download/install were independently verified, including installed-EXE startup and preservation of synthetic workspace/settings sentinels. Its six real-adventure roundtrips and private full-file/fog migration evidence remain applicable to the unchanged import/session data code. The 0.1.1 tag pipeline repeats the exact package checks before regular publication. No laptop/full geometry result is claimed.


Final documentation/package candidate 26beffc passed [Windows CI 43341919290](https://github.com/stafidopsomo/session-desk/actions/runs/43341919290) and the repeated full local root job with the same 132 Python / 7 Node / three source-and-frozen browser suites. Independent updater review found no remaining blocker after the one-time older-launcher limitation was documented. The final 0.1.1 tag repeats CI and verifies its own artifact before publication.


## Guided adventure management 0.1.2

November 14 owner request: remove adventures and workspaces, simplify the home copy with larger labels, align workspace/import styling and replace general tutorial dialogs with control-anchored spotlight guidance. Removal is DM-only, requires explicit confirmation and waits for active transfers. Adventure removal deletes only its own documents while retaining shared assets; workspace removal moves its exact folder to local recovery outside the visible registry. Tests cover cancellation in the UI, scope/privacy, preserved shared images, recovery, active-job blocking and rejected stale player requests.

Guided tours point at rendered controls, adapt to available text/maps and restore the initial DM selection. Synthetic browser checks walk every step, check card placement and contrast, and assert that the player session is unchanged. Local screenshots use original synthetic material only. Exact-tree local/frozen/CI checks must complete before publication; no new hardware/alpha acceptance is claimed.


Candidate 5278c22 passed [Windows CI 43523309838](https://github.com/stafidopsomo/session-desk/actions/runs/43523309838) and the full local root job: 134 Python tests, 7 Node tests, all three source/frozen browser workflows and extracted-ZIP lifecycle/relocation/restore smoke. Synthetic screenshots verified home, mobile layout, import labels and guided control visibility. Only aggregate evidence is committed. The regular release tag rebuilds and verifies its own same-run archive before publishing; the public download and actual released-EXE updater are checked afterward.


## Prepared map-rendering correction 0.1.3

The owner reported a restored Grove map error. An obsolete lookup for the removed prepareGemini button aborted rendering. The earlier browser check saw the map heading but missed the caught exception shown in the loading panel. A new check reproduced the exact failure before the fix. The obsolete lookup is removed; tests now require actual rendered canvas pixels, a hidden loading/error panel and expected room counts on initial load and dungeon/regional switching. Existing workspaces, files and saved fog require no migration or repeat restore. Source/frozen/ZIP checks must pass before publication.


Candidate 4c01854 passed [Windows CI 43525828312](https://github.com/stafidopsomo/session-desk/actions/runs/43525828312) and the full local root job (134 Python tests, 7 Node tests, all source/frozen browser workflows and ZIP smoke). The exact null.hidden loading error was reproduced by the new browser check before the correction. All 875 actual restored campaign files were verified present read-only. All 15 owned campaign maps rendered in isolated source and frozen checks, with unchanged saved fog and zero script errors. Only aggregate evidence is committed; private reports and screenshots remain outside Git/CI. The regular tag rebuilds and verifies its own archive before publication.


## November 17 local campaign-book preview

Branch codex/unified-campaign-workspace adds an opt-in 0.2.0-preview.1 surface to the same app: native Book/mission editing, shared Book / Resources / Party navigation, revision-guarded drafts, independent map inspection and URL-addressed entries/maps/rooms. LaunchPreview.bat uses --preview and a separate SessionDesk-CampaignPreview profile. This is a local test build, not a published release or completed unification milestone.

Restored authored book data seeds an inert, versioned campaign-journal module once. The original data remains intact; later journal edits live in that module and are included in normal backups. Known journal modules are validated; older readers preserve unknown module data without executing it. Fresh workspaces use the same book/mission/Party surface. Basic character notes are editable with conflict guards; restored mechanical sheets still open the compatibility editor. Generic source resources retain the existing renderer and prepared maps reuse the calibrated Atlas renderer inside the shared shell. Complete presentation unification across imported sources, advanced Party editing, scene-card migration and revised tours remain pending.

The local preview must pass offline unit, source/frozen browser, package/privacy and recovery checks before delivery. A private copied profile may be used for owner testing; never migrate or test against the live campaign. A regular release remains gated separately. Preview edits are isolated and do not synchronise back into the owner's live campaign automatically.

November 17 follow-up: workspace creation offers Campaign or One-shot / standalone session. Mode is portable metadata; one-shots start at Resources with a smaller notebook, while Campaign starts at Book. Both expose the same tools. This does not add PDF or community-JSON importing; source adapters remain independent of play style.


Local preview verification completed November 17: 143 offline Python tests, 7 Node renderer checks, all four source and frozen browser workflows, extracted-ZIP checksum/relocation/lifecycle smoke and the public source boundary passed. The shared-preview browser workflow exercises fresh/restored navigation, Campaign/One-shot creation, independent tabs, retained edit conflicts, mission rewards, Party notes, fog/presentation and a real player-window presence indicator. The frozen app also rendered every map and character in an isolated private campaign copy; native backup/restore preserved all authored files, saved fog and journal records. Private evidence and content remain outside Git/builds. The package is unsigned, local-only and built from the working branch; no GitHub release, remote CI or completed unification milestone is claimed. Stable 0.1.3 and its live profile remain unchanged.

The initial preview plan listed advanced Party/scene-card integration, full cross-source presentation, native Book context projections and onboarding parity as follow-up work. The subsequent explicit owner request scopes the regular release to the tested basic surface; it does not certify those unfinished integrations. Isolated preview edits remain separate until deliberate adoption.


## Regular 0.2.0 acceptance

Candidate 0e632a0 passed [GitHub Windows run 44001763447](https://github.com/stafidopsomo/session-desk/actions/runs/44001763447) and the full local root Windows job: 144 Python tests, 7 Node checks, all four source/frozen browser workflows and extracted-ZIP smoke. The downloaded GitHub artifact independently passed clean commit/digest/provenance and every-file checksum verification. Seven representative owned sources completed frozen portable roundtrips without warnings. A fresh 0.1.3 campaign backup and isolated regular-EXE upgrade preserved every authored file, character record, all rendered maps, saved fog and native Book/mission records. Private evidence/content remains outside source and CI.

The owner's explicit November 17 request authorises this regular campaign_book_workspaces release. The acceptance file covers the exact product digest; the tag pipeline rebuilds and validates its own clean same-run package before Latest publication. Laptop/friend-PC and full geometry review stay deferred, alpha_ready remains false, and advanced Party/scene-card/context/cross-source integration and AI/PDF/homebrew importing remain unfinished as documented. The release changes the default application surface, preserving the normal data profile without automatically merging preview edits.


## Regular 0.2.1 publication candidate

The 0.2.0 tag remained unpublished when its mission-creation browser check raced its own asynchronous navigation. Main carried the deterministic wait fix without moving the tag. The approved regular feature set is packaged as 0.2.1, with full candidate/tag checks repeated, immutable earlier tags, and all hardware/unfinished-feature deferrals retained. Acceptance remains pending until the new version passes.


Candidate 6e66224 passed [GitHub Windows run 44005031100](https://github.com/stafidopsomo/session-desk/actions/runs/44005031100) and the full local root job: 144 Python tests, seven Node checks, all four source/frozen browser suites and extracted-ZIP smoke. The downloaded clean GitHub artifact independently passed exact commit/digest/provenance, archive and every-file checksum verification. Seven representative owned adventures completed regular frozen import/export/restore without warnings. The isolated normal-workspace upgrade rendered all 15 maps and five characters, preserved all 883 authored files and saved fog, and retained 26 native Book entries and 10 missions through backup/restore. Only aggregate evidence is committed; private reports/content remain outside source and CI. The regular tag repeats the complete checks before publishing Latest. Hardware/geometry and unfinished integration deferrals remain explicit.


## Official 0.2.1 publication and installation

Tag product-v0.2.1 at 2352621 passed [the final Windows build and publication run 44006486445](https://github.com/stafidopsomo/session-desk/actions/runs/44006486445). GitHub reports [0.2.1](https://github.com/stafidopsomo/session-desk/releases/tag/product-v0.2.1) as the regular Latest release, with draft/prerelease both false. The anonymously downloaded public ZIP passed checksum, exact tag commit/product digest and every-file manifest verification. Its SHA-256 is 063fec66c9d0cf4ef1dab6e7bca3d580f225a8484121d5c49d62f82256d0a86f.

The installed 0.1.3 EXE successfully checked, downloaded and installed the official update through the normal updater. Installed files match the public manifest; managed activation and the normal desktop shortcut select 0.2.1. The existing normal profile opened with all original authored files and pre-existing workspace documents unchanged; native Book/mission records were added without a repeat import or preview merge. A verified pre-upgrade backup and old shortcut remain available. Private content, paths and detailed reports stay outside public source/artifacts. This is same-PC adoption evidence, not a new laptop/clean-VM/geometry result.


## Resource navigation corrections 0.2.2 candidate

November 17 owner correction: one-shots hide Book without deleting existing data; Add adventure filters titles; resource search matches visible titles only. Resources opens directly with adjacent source tabs, remembers its selected source, retains explicit presentation/removal, and fills wide-screen viewports. Synthetic regressions cover multiple imported sources, restored resources, no extra source chooser, old one-shot Book links, no-match imports, selected-source return/reload, title/body distinction and unchanged player state. Exact-tree source/frozen/package and owned recovery evidence remains pending before regular publication.
