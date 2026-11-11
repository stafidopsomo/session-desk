# Approved architecture

Status: approved by the owner on November 9, 2026, with the Settings/AI-switch changes below. Windows x64 is confirmed. The current implementation scope is the non-AI core; every provider/AI feature and its isolation work is deferred. An initial non-AI core and frozen Windows development preview now implement these boundaries; see BUILD-STATUS.md for verified behavior and remaining acceptance. The full architecture is not claimed complete. Working product name: Session Desk.

## Runtime and deployment

Start with one Python application and a local browser UI. Preserve the useful DM/player concepts without adding an Electron rewrite, cloud service, Redis, Docker or a separate database server.

The confirmed first distribution target is Windows x64 on the owner's laptop, main PC and a friend's PC. Bundle the Python runtime and core dependencies in a frozen one-folder application. Double-clicking the EXE starts a loopback server and opens the UI. A batch launcher may be supplied as an alternative, but testers must not install Python/Git/Node merely to run the core app. Establish the supported Windows-version floor through the packaging spike and actual machine tests; hardware confirmation is not a completed compatibility test. A later native window wrapper is optional.

The first build installs no provider components and requires no AI account. Deterministic import, manual preparation/editing, resource review, maps/fog, notes and presentation must work independently. A future AI phase may add supported provider setup/sign-in under the same Settings menu after its own implementation and validation.

## Code, content and personal-app boundary

| Layer | Location | Included in application release? |
|---|---|---|
| Application code, static UI, neutral icons, schemas | Product source/build | Yes, explicit packaging allowlist |
| Original synthetic demo/test fixtures | Product source/tests | Only an explicitly selected demo |
| User-selected source library | User-owned local directory | Never bundled |
| Imported adventure snapshots/assets | Managed workspace directory | Never bundled in the application |
| Characters, notes, sessions, fog and generated drafts | Managed workspace directory | Only in an explicit user backup/export |
| Provider credentials and session material | Provider-owned credential store, or approved OS store for future explicit key mode | Never in workspace exports, logs or releases |

Default mutable storage should be under an OS user-data directory, not beside the EXE or inside a checkout. For example, `%LOCALAPPDATA%/SessionDesk/` on Windows. Source paths are selected explicitly, not discovered by walking the owner's adjacent folders.

Personal development stays on the private personal branch. Product work stays in this separate worktree and parentless history. Do not merge personal commits into release-dev; extract/review reusable code intentionally. The owner migrates the campaign later through a dedicated import/export path.

## Application modules

1. **Workspace service:** create/open/list/export/import workspaces; versioned SQLite state and schema migrations.
2. **Source adapters:** parse supported library versions into an internal adventure graph; resolve source-entry IDs, local image paths, chapter/section links and source geometry.
3. **Resource service:** content-addressed assets, dependency/provenance manifests, safe local file validation and draft/approved states.
4. **Preparation service:** manage imported/manual resources, dependencies and validated review results in the core. Bounded AI preparation jobs are deferred.
5. **Provider adapters — deferred:** future authentication/status/capabilities, submit/cancel jobs, structured progress/results and quota errors. No campaign semantics inside an adapter. Do not load or implement adapters for the first core build.
6. **Review/editor service:** compare source and draft, edit notes/translations, correct region geometry, approve selected results.
7. **Session/presentation service:** DM and player views, shared tabs, notes and fog with explicit visibility state. Provider jobs never control live reveal directly.
8. **Local API/UI:** workspace- and adventure-scoped endpoints, fixed app assets, structured errors and concise workflows.

## Internal data contract

Use opaque, stable IDs. Never use a room number alone as a cross-workspace key.

- `Workspace`: ID, display name, schema version, selected locale/rules profile and active session.
- `Adventure`: ID, workspace ID, source adapter/version, source fingerprint and import status.
- `SourceEntry`: adventure ID, original source ID, chapter/entry locator, normalized structure and references. Location/room/NPC is metadata, not an assumption about all entries.
- `Map`: adventure ID, asset references, coordinate dimensions/transforms, optional grid calibration and source locator.
- `Region`: map ID, stable source-region ID, source-entry relationship, polygon, role (`room`, `feature`, `landing`, `area`, `unknown`) and verification status. One entry may relate to several regions/maps.
- `PreparationResource`: scoped source IDs, kind, language, origin (`imported`, `manual`, later `ai`), draft/approved/superseded state, input fingerprint and asset reference. Prompt/provider provenance is optional future metadata; manual resources do not require a provider.
- `Character` — planned, not implemented in the preview: workspace-scoped record, user-confirmed fields and optional adventure links. No preloaded party, level, gold or backstory. See MIGRATION.md for optional-module and backup requirements; the current document validator rejects this namespace.
- `Session`: workspace/adventure links, presentation tabs, room notes and fog operations. Keep preparation separate from actual-play history.
- `Job`: kind, immutable input manifest/hash, provider/capability requirements, state, attempts, cancellation flag, result reference and safe failure classification.

SQLite transactions own mutable state. Assets live in managed folders using relative references and hashes. Database migrations require a backup and rollback strategy; app upgrades cannot overwrite imported content.

Workspace backup/export must include its database, manifest and required images, not a JSON file whose maps remain stranded on another computer. Test import into a different root path. Explicit exports may contain source material; they are user content, not application release artifacts.

## Current core: deterministic import and manual preparation

`Select library → validate source/schema → preview inventory → choose adventure → import graph/assets/known regions → manually prepare or import missing materials → review → play`

The import is idempotent by source fingerprint. Missing files and unsupported structures produce actionable reports; they do not create fabricated resources or trigger unapproved downloads. Keep source/adventure identifiers generic, including non-numeric keys and shared keys across physical regions.

Text extraction, source lookup, image copying, reference resolution and known map polygons are code tasks. The core supports manual notes/translations and user-supplied pictures without promising automatic generation. Locale, encounter assumptions and desired preparation are user choices, not hard-coded campaign preferences. In the deferred AI phase, a provider would receive only selected relevant source excerpts and a typed task.

Do not infer walls or doors from a keyed region alone. It may mark a throne, landing or subsection. Imported geometry and image dimensions must agree after scaling/cropping. Preserve originals; unclear geometry remains unverified. The November 9 owner correction uses source-provided boundaries immediately, with no coordinate editor or verification step. To correct a boundary, drag its complete edge on the map and save it; backend shape/dimension validation still applies. Missing boundaries require drawing or the fog brush. Future AI proposals remain deferred.

## Global AI switch and Settings

- One **Settings** menu in the top-right header contains **Display** (text size, layout/density and related presentation preferences) and **AI**. Keep **Open player screen** as its own header button in its existing position, outside Settings.
- The global **AI on/off** control governs all AI features. Default is Off. In the first non-AI build it is fixed Off/unavailable with a short explanation; do not offer a working-looking On state, sign-in or generation action without an implementation.
- When AI support is implemented later, enforce Off in the backend as well as the UI. Reject new AI submissions, stop/cancel active AI operations through the adapter, leave queued AI jobs stopped and prevent automatic resumption. A result racing with disable cannot be auto-approved or presented.
- Off also stops AI-related provider discovery/install/auth requests, account/quota polling, model calls, background preparation and retry/provider fallback. Existing saved provider credentials are not deleted merely by switching Off.
- Preserve source imports, manual edits, approved notes/art, session state and fog. Turning AI Off does not disable the rest of the application or remove already-created materials. Turning it back On later does not automatically spend allowance or resume pending jobs; the user chooses the preparation action.
- Future provider options live in this same Settings menu. Avoid a separate provider toolbar and repeated disabled AI buttons on room cards.

## Future phase only: durable, bounded AI jobs

The following accepted boundaries remain design constraints for later AI work. Provider routes, isolation, authentication and generation are not implemented or required for the current core gates.

- Persist jobs before submission. Resume by input hash and completed resources, not by guessing from filenames.
- Separate text, vision/region proposals and image generation. Each requires its own capability.
- Validate structured results and generated files before adding drafts. A success message without a verified artifact is a failure.
- Cancellation terminates the active operation through the adapter; bounded retries do not silently switch providers or billing modes.
- Quota, missing capability and authentication failures leave a resumable blocked job. Never convert a general allowance percentage into a promise of image capacity.
- Changes to prompts/source inputs produce a new resource version; preserve old approved work unless the user explicitly replaces it.
- One job's staging area contains only its selected inputs. Provider tools cannot modify the application or production workspace directly. Validate output paths, types, dimensions, sizes and schema before a transaction imports results.
- Imported book text is untrusted task data, not instructions granting shell, credential or network access. Provider permissions must enforce the job boundary; prose alone is not a sandbox.
- Record the source locator, adapter/prompt/schema versions and artifact hash. Do not log credentials or whole private books.

## UI surface

The home screen lists workspaces and **Add adventure**. An adventure has one **Resources** browser, with collapsible book chapters, pins and Text/Images/Maps search filters. Text opens its book reader and preparation form; media opens the image/map preview and contextual preparation. The persistent **On player screen** strip controls shared tabs, so separate Library, Book/resources and Session modes are unnecessary. Browsing and preparation do not present resources automatically. One top-right Settings menu groups Display and AI, with Open player screen kept separate. Automatic preparation and provider setup enter this surface only in the later AI phase.

Room actions are contextual: read/edit preparation, review available scene, reveal/hide and shared notes. The radius cursor matches the reveal/hide brush at the current zoom. Sidebar selection and tool changes keep existing navigation/viewport DOM rather than rebuilding the whole page. Future generation controls belong beside the selected resource's preparation; unavailable generation actions are hidden. No button claims a provider can generate images merely because it can generate text.

Local HTTP access is loopback-only with instance/session protection, same-origin write checks and tightly bounded asset routes. A separate device/LAN player mode, hosted accounts and remote access are deferred; a local TV window is not a security boundary against an adversarial user on the same computer.

## Book navigation and room workflow (November 9 correction)

Preserve the imported chapter/section hierarchy and structured source nodes for heading, read-aloud box, list, table and illustration rendering. Keep nameless source IDs out of headings/navigation; contextual notes retain their parent breadcrumb. Linked areas resolve to their source entry. This reader preserves book structure rather than flattening it into one text dump; cross-source statblock references currently retain their citation, without the complete 5e.tools hover/reference engine.

The left sidebar contains DM maps in book order. Player variants stay behind their DM map; exact-size and explicit autoScale parent links share the DM coordinate space for fog. Unsupported transforms are not guessed. Pins are workspace/adventure-scoped user data, independent of search/preparation/session and included in backups. A room's source and manual preparation open in the same map page. Whole-book reading remains available separately.

An older snapshot can be enriched by re-importing the identical source fingerprint. Preserve preparation, pins, manual pictures, shared notes, session tabs/fog and saved room boundaries. Changed source snapshots still require a new workspace; the enrichment path is not a general destructive refresh.
