# Proposed architecture

Status: design awaiting the implementation gate. Working product name: Session Desk.

## Runtime and deployment

Start with one Python application and a local browser UI. Preserve the useful DM/player concepts without adding an Electron rewrite, cloud service, Redis, Docker or a separate database server.

The Windows distribution should bundle its Python runtime and core dependencies in a frozen one-folder application. Double-clicking the EXE starts a loopback server and opens the UI. A batch launcher may be supplied as an alternative, but testers must not install Python/Git/Node merely to run the core app. A later native window wrapper is optional, not an architectural prerequisite.

Only the selected AI integration may need an additional official provider component. Settings offers detection, a supported installation/update flow and provider-owned sign-in. Authentication cannot be completed silently on behalf of a new user. Core play must remain usable without an AI login.

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
4. **Preparation service:** create bounded jobs from selected resources, track dependencies and accept validated results.
5. **Provider adapters:** authentication/status/capabilities, submit/cancel jobs, structured progress/results and quota errors. No campaign semantics inside an adapter.
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
- `PreparationResource`: scoped source IDs, kind, language, draft/approved/superseded state, input fingerprint, prompt/schema version, provider provenance and result/asset reference.
- `Character`: workspace-scoped record, user-confirmed fields and optional adventure links. No preloaded party, level, gold or backstory.
- `Session`: workspace/adventure links, presentation tabs, room notes and fog operations. Keep preparation separate from actual-play history.
- `Job`: kind, immutable input manifest/hash, provider/capability requirements, state, attempts, cancellation flag, result reference and safe failure classification.

SQLite transactions own mutable state. Assets live in managed folders using relative references and hashes. Database migrations require a backup and rollback strategy; app upgrades cannot overwrite imported content.

Workspace backup/export must include its database, manifest and required images, not a JSON file whose maps remain stranded on another computer. Test import into a different root path. Explicit exports may contain source material; they are user content, not application release artifacts.

## Deterministic import, then optional preparation

`Select library → validate source/schema → preview inventory → choose adventure → import graph/assets/verified regions → prepare selected missing resources → review → play`

The import is idempotent by source fingerprint. Missing files and unsupported structures produce actionable reports; they do not create fabricated resources or trigger unapproved downloads. Keep source/adventure identifiers generic, including non-numeric keys and shared keys across physical regions.

Text extraction, source lookup, image copying, reference resolution and known map polygons are code tasks. AI receives only selected relevant source excerpts and a typed task. Translation language, encounter assumptions and desired preparation are explicit user choices, not hard-coded campaign preferences.

Do not infer walls or doors from a keyed region alone. It may mark a throne, landing or subsection. Imported geometry and image dimensions must agree after scaling/cropping. Preserve originals; unclear geometry remains unverified. AI may propose masks or polygons, but only reviewed geometry becomes the basis of precise room reveal. Manual brush/fog editing remains available.

## Durable, bounded AI jobs

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

The home screen lists workspaces and **Add adventure**. An adventure has Library/Maps, Preparation and Session views. One **Prepare** flow chooses missing resource kinds and shows a resumable queue; **Review** is the resulting inbox. **Start session** opens the DM/player workflow. Provider installation and connection live in Settings, not on every room card.

Room actions are contextual: read/edit preparation, review available scene, reveal/hide and shared notes. Advanced generation controls stay in the preparation view. Unavailable features explain their missing capability; no button claims a provider can generate images merely because it can generate text.

Local HTTP access is loopback-only with instance/session protection, same-origin write checks and tightly bounded asset routes. A separate device/LAN player mode, hosted accounts and remote access are deferred; a local TV window is not a security boundary against an adversarial user on the same computer.
