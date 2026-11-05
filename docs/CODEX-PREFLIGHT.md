# Codex connection preflight

Date: November 5, 2026. Selected first route: **ChatGPT through Codex**.

## Result

**Authentication and protocol discovery succeeded. Job isolation failed to execute its check. No model inference ran.** This is a developer-machine diagnostic, not a working product adapter or a release acceptance result.

The installed component was `codex-cli 0.166.0-alpha.6`. Its stdio app-server initialized successfully, `account/read` reported ChatGPT authentication, and `model/list` returned eight catalog entries. No email, account ID, token, raw account response or model transcript is retained here. The provider process uses its own existing authentication; the probe does not open credential files itself.

Generated stable schemas exposed `outputSchema` on turn start, `ephemeral` on thread start, and an interruption request schema. These establish protocol availability only. No thread was started and no output schema or live turn cancellation was exercised. Catalog entries do not establish subscription entitlement or image-generation access.

## Isolation blocker

The diagnostic created original synthetic canary files in a temporary input folder and a sibling folder. It attempted an app-server `command/exec` with `readOnly` sandboxing and network disabled, without starting an agent turn. The first command returned RPC error `-32600`; a separate synthetic diagnostic identified the underlying Windows error:

```text
exec failed: windows sandbox: CreateProcessWithLogonW failed: 267
```

Retrying with a long-form temporary path produced the same RPC failure. Neither inside-input nor outside-input readability was established. The child process was stopped, scratch files were cleaned up, and no raw protocol report was saved. No global sandbox settings, account permissions, installed tools or login were changed. No unrestricted fallback was attempted.

The installed **stable command schema** lacks the restricted-read-root `access` shape shown in the current [app-server documentation](https://learn.chatgpt.com/docs/app-server). Permission-profile discovery schemas are present, but that alone does not establish a selectable restricted-read policy or successful enforcement. This is a version/installation compatibility gap to investigate, not evidence that all Codex configurations lack isolation. Read-only permissions alone must not be equated with confidentiality of other folders.

## Safe diagnostic boundary

`tools/probe_codex.py` is optional developer diagnostics for an already-installed CLI. It does not install tools, initiate login, create threads, call inference or change provider configuration. Its request allowlist rejects thread/turn creation and authentication/configuration mutations; the only command used by the program reads its own temporary synthetic canaries. It denies unexpected server requests and suppresses raw provider errors/account details. It removes API-key fallback variables from the child environment without modifying the parent environment.

To repeat deliberately on a developer machine:

```text
python tools/probe_codex.py
```

This command launches the installed provider app-server and reads authentication status. It returns a nonzero exit code for an incomplete diagnostic. Do not run it in CI or use its output as a full security/capability certification. The ordinary unit suite uses fakes and does not launch the CLI.

## Dependencies before the first live job

1. Select a supported Windows app-server version and enforce a job boundary that cannot read other workspaces or mutate application/live workspace data. Diagnose the sandbox error under a synthetic staging directory; verify in-scope reads, out-of-scope denial, write denial and network policy. Resolve configuration precedence, optional tools/plugins and child-process cleanup. Any OS/global setup change needs a concrete scoped plan first.
2. Confirm the authentication/distribution route for each tester's own account. Existing developer authentication proves neither clean-machine sign-in nor permitted redistribution. Follow official [Sign in with ChatGPT app-server integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server) requirements where that route is used; do not copy login material into the application.
3. With a separately authorized bounded synthetic task, verify structured output validation, observable failures, quota handling and cancellation of an active turn. Set deadlines, retry limits and input limits. Do not invent token-cost guarantees: the [current preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) do not support `max_output_tokens` on that route.
4. Verify installation and capability detection under a fresh Windows standard-user profile. Enable only proven task kinds. Image generation remains unverified and unavailable in the proposed first text slice.

Application implementation and tester publication remain gated by IMPLEMENTATION-GATES.md. This preflight uses no campaign or source-library content and does not advance the personal campaign.
