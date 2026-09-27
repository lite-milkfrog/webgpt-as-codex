# AGENTS.md

[**English**](AGENTS.md) | [简体中文](AGENTS.zh-CN.md)

This repository is the public-safe source of truth for WebGPT-as-Codex.

## Mandatory WAC session bootstrap
- Any agent session that will actually use WAC / the WAC Unified Gateway / WAC-managed MCP capabilities must load the canonical `skills/webgpt-as-codex/SKILL.md` in that same session before substantive work.
- Then follow `skills/webgpt-as-codex/session-bootstrap.md`: read routing, machine-local inventory/environment when applicable, select a Workflow for multi-stage work, and load only the current Stage's required leaf Skills/guides.
- Prior-chat memory or "the previous agent already read the Skill" is never a substitute for the current session bootstrap.
- Before bootstrap completes, only liveness/source/Skill-location discovery is allowed; no workspace mutation, browser submission, GUI side effect, deployment/update, publish, or push.

## Deployment dispatch
- If the user gives only this repository URL plus a request such as "deploy this project", treat that as a deployment task, not a request for a tutorial.
- Before changing the target machine, read `prompts/ONE-CLICK-AGENT-DEPLOY.md` and `docs/DEPLOYMENT.md`, then follow their full discovery -> deploy -> verify -> handoff contract.
- Fresh deployment must preserve WebGPT's bundled derivative sources when declared by component metadata. In particular, Coding Tools and Serena are installed from this repository's `vendor/` snapshots rather than silently falling back to unmodified upstream packages.
- Deploy the current default-branch HEAD of the repository URL the user supplied. A stale local checkout, old release, old tag, copied prompt, or prior-chat HEAD is not "latest".
- For an existing checkout, verify its remote, fetch the repository default branch, and only fast-forward when the worktree is clean and the update is safe. Never `reset --hard`, `clean`, or discard unknown local work merely to reach latest.
- If an existing checkout is dirty/diverged and cannot be safely fast-forwarded, preserve it and use a fresh clone of the current default branch in a separate safe directory when possible.
- Record the repository URL, resolved default branch, and deployed source HEAD in the final deployment result.
- Continue through real acceptance. Stop only for a genuine human account/login/OAuth consent boundary or a concrete safety conflict.

## Invariants
- Read docs/CURRENT-PROJECT-STATE.md before substantial work.
- One stage owns one coherent concern; do not reopen closed stages without contradictory evidence.
- Local machine state and secrets never enter Git.
- Validate before closure; update documents before handoff.
- Preserve CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE.
- Automatic handoff is recursive: each window must Playwright-submit the following window after its own verified closure; only Final Overall Acceptance may terminate the chain.
- Diagnose a failed preferred tool before falling back.
- One file has one writer at a time.
- Use worktrees for parallel writers.
- Do not mutate unrelated repositories or existing healthy services.
- Prefer component manifests and adapters over machine-specific hardcoding.
- Process alive, listener alive, MCP protocol healthy, OAuth healthy, and remote reachable are distinct states.
- A test harness failure is not automatically a target component failure.
- Windows-facing CLI output must be UTF-8 safe.

## Safety
- Never commit OAuth databases, passwords, private keys, browser tokens, cookies, pairing data, or public URLs tied to a private machine.
- External publication and destructive operations require explicit stage ownership.
- Existing production-like MCP/Funnel endpoints are evidence and fallback, not disposable test fixtures.
