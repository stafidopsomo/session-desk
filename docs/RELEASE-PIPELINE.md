# CI and release pipeline design

**Development build pipeline implemented November 9.** The root ci.ps1 job, called by the GitHub-required .github/workflows/readiness.yml wrapper, now checks the independent product tree, runs offline unit tests and source-browser E2E, builds/audits a frozen development ZIP, tests extracted-package launch/restart/restore with developer tools hidden, runs frozen-browser E2E and uploads only the ZIP/checksum artifact for 14 days. No provider or real source library is used. Local evidence and CI status are distinguished in BUILD-STATUS.md.

Actions are pinned by SHA; build Python is 3.12.10 x64, build/browser dependencies have SHA-256 locks, and UI syntax is checked with Node 22. The Windows 2025 runner image and Node patch are not immutable, so byte-identical reproducibility is not claimed. The workflow fetches only the tested commit history, checks the clean root and uses read-only repository permissions for builds.

A separate tag-only publishing job has release-write permission. It first runs tools/release_gate.py; the current release/acceptance.json fails closed. The gate requires an alpha version/tag, evidence for the mandatory checks and a digest matching the exact product tree. Development preview artifacts do not satisfy tester-alpha acceptance and are never published as alpha automatically. Private prerelease links still require repository access; forward vetted ZIPs directly until a separate download destination is established.

## November 11 GitHub distribution preparation

- `.github/README.md` is the user-facing landing page, with installation/update/save guidance and honest implemented-feature limits. GitHub [gives this location priority over root/docs READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes), so the root can retain its short README.txt and all Markdown stays outside it. docs/README.md remains the developer guide.
- The feedback issue form requests version, Windows version and reproducible steps without asking for private workspaces or source books.
- docs/MIGRATION.md separates full recovery snapshots from supported workspace backups, and optional UI from exclusion of unreleased code in a build. No personal report or backup is added to product source.
- A separate public downloads-only repository is the smallest sharing option when the product source should remain private. Its contents can be limited to the landing README, release notes, feedback instructions and audited application ZIP/checksum assets. A clean product-source repository is another explicit distribution choice. Neither requires changing the personal repository's visibility or granting a tester access to personal history.
- The destination/name/visibility has not yet been selected; no repository/tag/release is created by these preparation changes. The existing publishing job targets its own repository only; cross-repository publication is not implemented or falsely assumed to have credentials. Configure that only after selecting the destination and a least-privilege publishing identity, or create the first draft release through the chosen repository's supported release interface.
- A genuine release uses a versioned tag and vetted assets; a CI Actions artifact is not called a GitHub release. Check the public download from outside the maintainer's signed-in session before handing the link to a friend. GitHub [requires repository read access to view releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases); a private repository cannot provide an anonymous public release link.
- Keep the current alpha gate and remaining evidence truthful. Do not mark laptop, owned-source visual/geometry or artifact acceptance passed merely to publish. Personal migration/Characters support is not bundled as a prerequisite of the first simple release.

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

## Alpha release remains blocked until proved

Core source, a package specification, hash locks, explicit manifest/privacy checks and synthetic source/frozen-app evidence now exist. The owner confirmed Gate 1 complete. Complete owned-source visual/geometry and final tester/artifact acceptance are still pending; no unreported OS/device result is inferred from that confirmation. The selected 2014 library now has parsing/import/persistence evidence; see BUILD-STATUS.md. Update acceptance evidence only after running those checks; do not change flags merely to bypass publication. The code-tree digest prevents stale acceptance from authorizing changed product code. This record is an engineering validation gate, not another architecture packet for the owner.

Provider integration is intentionally deferred and does not block the non-AI core. No provider installation, authentication, quota polling, live diagnostic or inference is included in CI or the artifact.

A source timestamp and dependency lock support reproducible builds, but do not by themselves establish byte-identical EXEs. Claim bit-for-bit reproducibility only after comparing independent builds. Record provenance and hashes from the first real alpha regardless.
