# Release development instructions

- This is a campaign-free product worktree. Read README.md and docs/IMPLEMENTATION-GATES.md first.
- November 9 owner decision: ARCHITECTURE.md is approved and Windows x64 is confirmed for the owner's main PC/laptop and a friend's PC. Gate 0 is resolved for the non-AI core; Gate 1 implementation and core packaging/dependency work may proceed. Do not claim a runnable build exists until it is actually built/tested, or publish a tester release before its acceptance checks pass.
- All AI implementation is deferred: no provider adapters, isolation experiments, provider installation/discovery/sign-in, account/quota polling or live inference in the current workstream. Keep the future interfaces/design documented without treating them as core-build dependencies.
- Existing diagnostic tools are historical developer material. Their offline fake tests may run; do not rerun live provider diagnostics for the non-AI core. They are not a product adapter or a release build. The live diagnostic must never run in CI.
- Do not merge the personal branch, copy its data directories, scan adjacent campaign folders for defaults, or add campaign-bearing commits as parents. Keep this history independent.
- Synthetic, original test fixtures only. No source-book text, official maps, real characters, local workspace state, authentication material or real provider transcripts in source, fixtures, CI artifacts or releases.
- Build code and user content must be separate. All user-editable content lives outside the installation and repository.
- Use supported provider interfaces. No browser automation for ChatGPT, Claude or Gemini; no borrowed logins, hidden API billing, paid fallback or unbounded model calls.
- No real inference or personal source library in CI. Provider tests use fakes; live conformance requires a separately authorized, bounded user-account test.
- Providers may propose typed drafts. They do not edit the app, production database or active fog directly.
- Keep the surface small: Add adventure, manual Prepare/review, Start session. One top-right Settings menu contains Display and the global AI on/off control. Keep Open player screen in its separate existing header position, outside Settings. In the first non-AI build, AI is Off and cannot be enabled; hide unavailable AI generation actions instead of scattering placeholders around the app.
- When AI is implemented later, Off must be enforced centrally: no new AI requests, background/provider activity or queued AI resumption; stop/cancel active AI work while preserving manual/imported/approved resources. Manual import/edit/review/play remains usable. Read the full approved toggle behavior in ARCHITECTURE.md.
- Never claim a CLI, quota percentage or model name establishes image-generation access. Test capabilities independently and show unavailable states honestly.
- Keep docs clear about implemented behavior versus planned behavior. A documentation-only branch is not a release candidate.
