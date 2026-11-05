# CI and release pipeline design

**Design only. No workflow or runnable artifact has been published.** The architecture gate must be resolved before implementing a build pipeline for an application that does not yet exist. In particular, do not publish the old personal app or notes prototype as a supposed clean alpha.

## Branch and repository policy

- `release-dev` has a parentless, campaign-free history and a separate worktree. Feature branches should descend from it.
- The personal branch remains private and independent. Never merge its commits into the release history.
- For now, share only vetted release files; access to a branch of a private repository is not isolation from that repository's other refs/history.
- Before exposing source or changing repository visibility, move the clean product history to a separate repository and verify its object/ref contents. No personal repository visibility change is authorized.
- Production/alpha tags must point to commits reachable from the clean product branch. Never build product tags from the personal branch.

## Packaging decision

Start with a Windows x64 **one-folder frozen Python build in a ZIP**, with `SessionDesk.exe` at the top level and a very short README. A batch launcher is an optional convenience; it cannot be the only means of acquiring missing runtimes on a tester's machine.

[PyInstaller's official packaging documentation](https://pyinstaller.org/en/stable/operating-mode.html) explains bundling the Python interpreter/dependencies so users do not need an installed Python. It also requires platform-specific builds. Its recommendation to validate one-folder mode before one-file mode fits an inspectable first alpha.

Do not bundle all AI tools into every core install. Bundle core dependencies, then provide an app-managed setup for the selected official provider component once its installation/redistribution route is verified. Provider login remains a user interaction. If that path cannot be made reliable, the affected provider is not ready for the tester claim.

The application install is read-only. Workspaces live in a user-data directory and survive replacement/upgrades. Support paths with spaces, Unicode names, standard users and no developer repository installed.

## Pull request / release-dev CI

Trigger on pushes to release-dev and pull requests targeting it. Use a clean checkout with no personal library, account or private campaign. [GitHub's workflow event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) distinguishes branch/tag triggers from events that require a workflow on the repository's default branch; avoid assuming a manual-dispatch workflow on a non-default branch is discoverable automatically.

Required jobs:

1. **Boundary audit:** assert the allowlisted product tree, no campaign data or credentials, no source-book fixtures, and the expected clean-history baseline.
2. **Static checks:** Python and UI syntax/lint/type checks, format checks, dependency/license inventory and secret scanning.
3. **Unit and contract tests:** synthetic source adapters, unknown schema errors, IDs/references, jobs, provider fakes, source visibility, coordinate transforms and draft validation.
4. **Storage tests:** workspace isolation, transaction failures, version migrations with rollback/backup, export/import including all assets, and no credential export.
5. **UI/E2E:** empty first run → synthetic adventure import → map/room review → fake-provider preparation → approval → player presentation → restart and persistence.
6. **Windows package build and smoke test:** frozen EXE starts from an extracted ZIP under a clean temporary profile. Hide developer tool paths for the launch test and verify that installed Python/Node/Git are not needed for core runtime. Provider dependency/authentication remains a separate test.

Use original synthetic fixtures, including repeated region keys, one feature polygon that is not a full room, a map with no keyed regions, a missing player-safe image and a deliberately bad generated draft. No real book or real provider inference belongs in CI. Mock tests are not evidence of a working account integration; a bounded live conformance check is a separate release gate.

## Release/tag pipeline

Proposed alpha tags: `product-v0.1.0-alpha.1` and later semver alpha tags, from the clean history only.

1. Verify tag reachability and clean-tree/version consistency.
2. Run the same mandatory checks used for the exact commit.
3. Resolve locked dependencies with hashes and build on Windows. Pin action versions by reviewed commit SHA; pin the runner image/OS target and document the supported-OS floor.
4. Package **only an explicit staging manifest**, never the whole checkout. No `.git`, workspaces, source libraries, model logs, auth material, personal names/data, generated campaign media or developer paths in the archive.
5. Inspect archive entries and content against the privacy boundary, including compiled/bundled assets. Produce dependency notices/SBOM, SHA-256 checksums, build provenance and versioned release notes.
6. Smoke-test the extracted artifact, fresh profile, offline core startup, save/restart, and installation-path independence.
7. Publish a GitHub **prerelease** only if every gate passes. Give release-writing permissions only to this job; ordinary CI should be read-only. Separate signing/publishing secrets from untrusted PR jobs and never run PR code under a privileged `pull_request_target` release job.

Code signing is a distribution decision: do not falsely label an unsigned alpha as signed, and do not instruct testers to disable OS protections. A signing certificate, if chosen, is a protected build secret. No certificate or provider credentials are currently configured here.

## Release is blocked until proved

There is currently no product application, package specification, dependency lock, provider integration, clean-profile build result or pipeline run for this branch. They must not be replaced with placeholder scripts that merely open the old app, install arbitrary tools, or publish a docs-only ZIP as a product.

A source timestamp and dependency lock support reproducible builds, but do not by themselves establish byte-identical EXEs. Claim bit-for-bit reproducibility only after comparing independent builds. Record provenance and hashes from the first real alpha regardless.
