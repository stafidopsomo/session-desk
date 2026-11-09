# CI and release pipeline design

**Application build/release pipeline: design only.** A small readiness workflow now checks the campaign-free history/file boundary and offline diagnostic tests. It does not build, run a provider, upload artifacts or publish a release. Gate 0 was resolved on November 9 for the non-AI core; application/package implementation may proceed, and its build/release jobs must be added as real code and evidence exist. In particular, do not publish the old personal app or notes prototype as a supposed clean alpha.

The implemented readiness workflow uses read-only repository permissions, SHA-pinned checkout/setup-python actions, Windows 2025 and Python 3.12. It fetches only the tested commit's history, not other branch histories. Its exact file allowlist, text-only checks and independent-root check help catch accidental leakage; they do not replace review, secret scanning or a future packaged-artifact privacy audit. The runner image and Python patch version are not locked for reproducible application builds at this stage.

## Branch and repository policy

- `release-dev` has a parentless, campaign-free history and a separate worktree. Feature branches should descend from it.
- The personal branch remains private and independent. Never merge its commits into the release history.
- Share audited ZIP/EXE files directly with testers. The owner can download a private build and forward its vetted ZIP. A private GitHub release URL is not accessible without repository permissions; giving access to a branch does not isolate other refs/history.
- Before exposing source or changing repository visibility, move the clean product history to a separate repository and verify its object/ref contents. No personal repository visibility change is authorized.
- Production/alpha tags must point to commits reachable from the clean product branch. Never build product tags from the personal branch.

## Packaging decision

The owner confirmed Windows x64 on November 9, targeting the laptop, main PC and a friend's PC. Establish the supported Windows-version floor with packaging/machine tests. Start with a **one-folder frozen Python build in a ZIP**, with `SessionDesk.exe` at the top level and a very short README. A batch launcher is an optional convenience; it cannot be the only means of acquiring missing runtimes on a tester's machine.

[PyInstaller's official packaging documentation](https://pyinstaller.org/en/stable/operating-mode.html) explains bundling the Python interpreter/dependencies so users do not need an installed Python. It also requires platform-specific builds. Its recommendation to validate one-folder mode before one-file mode fits an inspectable first alpha.

The first core build contains no AI provider components or dependencies. AI is Off/unavailable in the unified top-right Settings menu, alongside Display. Open player screen remains its own header control. Provider installation/authentication/isolation and generation belong to a later phase, with separate validation before any capability is enabled.

The application install is read-only. Workspaces live in a user-data directory and survive replacement/upgrades. Support paths with spaces, Unicode names, standard users and no developer repository installed.

## Pull request / release-dev CI

Trigger on pushes to release-dev and pull requests targeting it. Use a clean checkout with no personal library, account or private campaign. [GitHub's workflow event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) distinguishes branch/tag triggers from events that require a workflow on the repository's default branch; avoid assuming a manual-dispatch workflow on a non-default branch is discoverable automatically.

Required jobs:

1. **Boundary audit:** assert the allowlisted product tree, no campaign data or credentials, no source-book fixtures, and the expected clean-history baseline.
2. **Static checks:** Python and UI syntax/lint/type checks, format checks, dependency/license inventory and secret scanning.
3. **Unit and contract tests:** synthetic source adapters, unknown schema errors, IDs/references, import/export jobs, source visibility, coordinate transforms, resource validation and enforcement of the unavailable/Off AI state.
4. **Storage tests:** workspace isolation, transaction failures, version migrations with rollback/backup, export/import including all assets, and no credential export.
5. **UI/E2E:** empty first run → synthetic adventure import → manual notes/resource/geometry preparation and review → player presentation → restart and persistence. Check Display/AI in one Settings menu, Open player screen outside it, and zero provider activity.
6. **Windows package build and smoke test:** frozen EXE starts from an extracted ZIP under a clean temporary profile. Hide developer tool paths for the launch test and verify that installed Python/Node/Git are not needed for core runtime. Provider dependencies/authentication are absent from this first artifact; they are future AI-phase tests.

Use original synthetic fixtures, including repeated region keys, one feature polygon that is not a full room, a map with no keyed regions, a missing player-safe image and a deliberately invalid manual draft. No real book or real provider inference belongs in CI. No account integration is claimed in the core. Bounded live provider conformance belongs to the deferred AI phase, not the first core release gate.

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

There is currently no product application, package specification, dependency lock or clean-profile product build result for this branch. Provider integration is intentionally deferred and does not block the scoped core release. The missing application and build work must not be replaced with placeholder scripts that merely open the old app, install arbitrary tools, or publish a docs-only ZIP as a product.

A source timestamp and dependency lock support reproducible builds, but do not by themselves establish byte-identical EXEs. Claim bit-for-bit reproducibility only after comparing independent builds. Record provenance and hashes from the first real alpha regardless.
