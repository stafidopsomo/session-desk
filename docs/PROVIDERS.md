# AI provider feasibility

Checked against official documentation on November 5, 2026. This is a capability/integration assessment, not a completed integration or entitlement test. No inference, login change or provider installation was performed.

## Product boundary

The app runs locally. The named providers normally process AI jobs online under each user's own account. Installing the core app does not provide an AI subscription or imply unlimited capacity.

Support provider **capabilities**, not interchangeable brand labels: structured text, vision input, illustration generation, geometry proposals, streaming/cancellation and authentication modes. A text provider need not be an image provider. The UI offers only verified operations for the connected configuration. Manual prompt export/result import remains a supported fallback.

## OpenAI / ChatGPT

Official [Codex App Server documentation](https://learn.chatgpt.com/docs/app-server) describes the interface for rich product clients. It distinguishes local/open-source app-server authentication from commercial/hosted services, and recommends the explicit Sign in with ChatGPT route. [Sign in with ChatGPT's app-server integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server) documents passing a user-authorized ChatGPT-plan OAuth token to app-server over a configured provider. A model catalog is not an entitlement check.

**Proposed adapter:** local app-server over its documented structured protocol. Select and validate the proper authentication route for distribution before implementation; do not silently reuse the developer's login or assume ChatGPT web sessions are an API. Sign in with ChatGPT registration/client configuration is an outstanding integration dependency. No browser automation or scraped cookies.

Text/structured generation is a plausible first vertical slice. Vision and image generation require their own documented and tested capability; do not advertise illustration support solely from a model name. No live capability or clean-Windows install was verified in this assessment.

## Anthropic / Claude Code

The [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) describes Python/TypeScript embedding through the published Claude Code binary. The current [product integration conditions](https://code.claude.com/docs/en/legal-and-compliance) address unmodified binaries, available authentication methods, and each end user's own credentials/billing agreement. The [subscription guidance](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) currently describes plan-authenticated SDK/print-mode use and separately explains linked API credits.

**Proposed adapter:** official Agent SDK or documented structured CLI mode, subject to those product/redistribution conditions. Confirm its supported Windows installation, permission boundary, cancellation and intended authentication before shipping it. Do not package a modified binary, intermediate usage using the owner's account, or assume that a detected API key is permission to incur separate API billing.

Structured text and vision tasks are candidates. Native illustration generation through this route has not been established; another verified image capability or manual import may be needed. The developer machine does not currently have the Claude CLI available on PATH, so no local conformance result is claimed.

## Google / Gemini

The official [consumer-account deprecation notice](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals) says personal Google/AI Pro/Ultra login in the old Gemini CLI ended June 18, 2026 and points consumers to Antigravity. Older/general Gemini CLI authentication instructions still found online must not be used as proof that this consumer route works.

**Proposed adapter:** the current official Antigravity headless/SDK route for supported consumer accounts, with an explicitly detected version and verified capabilities. [Headless mode documentation](https://antigravity.google/docs/cli/headless) is the starting protocol reference. A separately configured Gemini API adapter is a different billing/authentication mode, not an automatic fallback.

Do not equate Gemini Apps web allowance with CLI image capacity. Browser automation of the web app is outside the architecture. Image-tool availability, artifact return format and model-specific restrictions need product conformance tests. Manual prompt export/import can still work when automated image access is unavailable.

## Required adapter contract

Each adapter must provide:

- `discover`: supported installed component and version, without searching for secrets or starting inference.
- `auth_status` / `connect` / `disconnect`: provider-owned sign-in, actionable errors and an explicit billing/authentication mode.
- `capabilities`: declared versus actually verified task kinds for the current configuration; no fabricated quota counts.
- `submit(job_manifest)` / `cancel(job_id)`: typed progress, bounded execution, structured result or classified failure.
- Output validation: source-reference integrity, result schema, relative artifact paths, supported formats/sizes and actual file existence.
- An isolated staging/permission boundary. No unrestricted agent access to the app source, developer repository, other workspaces or provider credential stores.
- No silent paid fallback, provider switching, recursive retries or publishing to the player screen.

Credentials remain in the provider/approved OS store. Do not place token snapshots, login sessions or personal accounts in a build, workspace export or support report. A future explicit API-key mode must be user-selected and clearly identified; it is not part of the approved default.

## Implementation recommendation

Validate **one supported text-provider route end to end** before claiming the preparation workflow works. Add the other adapters against the same job/resource contract, then enable each capability after its own conformance proof. Unsupported image generation must remain unavailable rather than routed through a guessed subscription loophole.

The source importer, maps, notes editor, workspace backup and session UI must not depend on any provider. A quota or sign-in problem should pause only the dependent preparation jobs, not prevent play with existing material.
