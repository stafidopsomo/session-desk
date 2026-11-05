# Release development instructions

- This is a campaign-free product worktree. Read README.md and docs/IMPLEMENTATION-GATES.md first.
- The current phase is architecture assessment. Do not begin application implementation, dependency installation or executable publication until the recorded architecture gates are explicitly resolved with the owner.
- Read-only developer diagnostics and their synthetic/offline readiness checks are permitted in this phase. They are not the product adapter, a live conformance test or a release build. The live diagnostic must never run in CI.
- Do not merge the personal branch, copy its data directories, scan adjacent campaign folders for defaults, or add campaign-bearing commits as parents. Keep this history independent.
- Synthetic, original test fixtures only. No source-book text, official maps, real characters, local workspace state, authentication material or real provider transcripts in source, fixtures, CI artifacts or releases.
- Build code and user content must be separate. All user-editable content lives outside the installation and repository.
- Use supported provider interfaces. No browser automation for ChatGPT, Claude or Gemini; no borrowed logins, hidden API billing, paid fallback or unbounded model calls.
- No real inference or personal source library in CI. Provider tests use fakes; live conformance requires a separately authorized, bounded user-account test.
- Providers may propose typed drafts. They do not edit the app, production database or active fog directly.
- Keep the surface small: Add adventure, Prepare/review, Start session; provider setup in Settings and contextual room actions.
- Never claim a CLI, quota percentage or model name establishes image-generation access. Test capabilities independently and show unavailable states honestly.
- Keep docs clear about implemented behavior versus planned behavior. A documentation-only branch is not a release candidate.
