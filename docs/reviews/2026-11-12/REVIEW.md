# Review and correction report — November 12, 2026

Baseline: public product commit 6846ba0 (preview.1). Scope: runtime/storage, import/source setup, presentation, packaging and integration structure. Three independent reviewer passes plus the implementation review used original synthetic fixtures. Private campaigns, sources and running sessions were not used as editable test fixtures.

## Architecture verdict

Keep one local application: a **modular monolith** is appropriate for this Windows desktop tool. SQLite, local files and a browser UI avoid extra services and installations. It has real module boundaries, but the server and two browser entry points accumulated mixed responsibilities. A framework, Electron shell, microservices or database-server rewrite would slow tomorrow's validation without solving the observed failures.

This correction extracts background work and private transfer ownership into `sessiondesk/jobs.py`. HTTP dispatch now delegates job status/cancellation/downloads and shutdown acceptance to that service. Separate lifecycle, job and native-dialog locks prevent a long operation/dialog from owning unrelated state. Existing API paths and workspace formats remain compatible.

Existing integration seams are sufficient for the next phase: source adapters produce the normalized adventure graph; the store validates/persists it; background operations accept progress/cancellation and an explicit commit; optional prepared data activates its trusted renderer. AI/provider work remains deferred. These are internal boundaries, not a claimed working provider integration.

## Verified findings corrected

| Priority | Failure at baseline | Correction / regression coverage |
| --- | --- | --- |
| P1 | A Windows staging-file lock strands failed jobs as running, or reports an already-published restore as failed. | Composed job service keeps terminal outcomes authoritative. Cleanup is retried separately; marked locked staging does not block startup. Synthetic failure/commit/cleanup tests. |
| P1 | A slow player picture decode overwrites a newer selected map. | Revision-guarded asynchronous presentation. Deterministic delayed-image/tab-switch browser test. |
| P2 | Interrupted prepared-file materialization leaves an incomplete root which retry treats as finished. | Stage the complete editable tree privately, then atomically rename it. Injected second-file copy failure, successful retry and recovery tests. |
| P2 | Cancelling a prepared backup waits until every file has been captured. | Propagate cancellation into file capture/chunk copying; rollback manifest changes. Mid-snapshot cancellation test. |
| P2 | Successive edits add obsolete hashes to every export and can exhaust backup limits. | Export currently referenced assets only. Preserve originals, unknown-module attachments and historical local objects needed by concurrent snapshots. No unsafe disk garbage collection. |
| P2 | Character HP/resources cannot be edited without the external rules library. | Existing rules references/labels survive offline tracking. New/changed references still require the classic rules database. Five synthetic sheet/rules tests. |
| P2 | Player token controls remain active behind pictures/references. | Context-aware toolbar visibility. Picture/reference/return-to-map browser tests. |
| P2 | Choosing a valid data directory without optional package metadata reports a false rules connection. | Normalize the conventional selected data root. Metadata-free library selection test. |
| P2 | Setup preference failure reports a completed source installation as failed, leaving retry unusable. | Return the usable copy with a visible warning. Durable consent blocker keeps automatic image downloads Off after preference failure/restart. Write/rename/activation/cleanup fault tests. |
| P2 | Prepared fog/tabs can exceed their own restore validator limits, breaking later backups. | Reject additions before changing saved state/camera. Undo/reset/close remain available. Boundary/compound-action tests. |
| P2 | Prepared guide book sharing is hardcoded to one source. | Validate generic local book locators and use authored titles. Reject external/nonbook links. |

## Deliberate follow-ups after user testing

- Split the large core UI script into resource navigation, presentation/canvas and client-state modules. Keep the API and visual behavior stable. Do this incrementally after tomorrow's feedback.
- Core and prepared renderers remain separate compatibility adapters. Share small transport/lifecycle/render-order helpers first; do not combine their fog representations through an untested rewrite.
- Prepared snapshotting still hashes files under the storage lock. Large backups can briefly pause player updates. Cancellation is now prompt; shortening this critical section requires a consistent snapshot/lease design.
- Browser display preferences use localStorage and the loopback origin changes ports. Move these preferences to app settings so they survive launches reliably. This does not affect saved campaign/session data.
- Historical immutable local assets are retained for concurrent readers; coordinated disk garbage collection remains later work. Portable backups now omit obsolete versions.

## Validation and tomorrow's handoff

The root Windows job runs Python unit/contracts, Node renderer/syntax checks, both browser workflows from source and frozen EXE, and extracted-ZIP relocation/import/restart/backup/shutdown checks. The tagged workflow repeats them and verifies exact-tree/commit/file-hash provenance before publication. Reports contain synthetic/aggregate evidence only; private recovery reports/backups stay outside Git and release assets.

Deliver preview.2 as a new version; never replace preview.1 assets. Laptop/friend-PC compatibility and complete visual review of every imported map remain unverified. AI remains Off; the package is unsigned. Record completed CI/package checks in BUILD-STATUS and the versioned acceptance record, not as invented hardware results.

No architecture decisions, dependency installation or document approval are required from the owner. Tomorrow: extract the complete reviewed ZIP, run SessionDesk.exe, try Add adventure or Restore backup, check one map/player-tab/notes/fog workflow, close/reopen, and report any unexpected result with the app version and steps. Export a workspace backup before replacing an older installation.
