# AGENTS.md

This repository is the public-safe source of truth for WebGPT-as-Codex.

## Invariants
- Read docs/CURRENT-PROJECT-STATE.md before substantial work.
- One stage owns one coherent concern; do not reopen closed stages without contradictory evidence.
- Local machine state and secrets never enter Git.
- Validate before closure; update documents before handoff.
- Preserve CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE.
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
