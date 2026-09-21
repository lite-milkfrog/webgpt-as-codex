# WebGPT-as-Codex Product Contract

This file preserves product-specific rules inside the single canonical WebGPT-as-Codex Skill.

## Startup and truth

1. Read repository SoT before relying on chat memory.
2. Distinguish installed, configured, process-alive, listener-alive, MCP-healthy, OAuth-healthy and remotely reachable states.
3. Preserve unrelated repositories and healthy unmanaged services.
4. Never put credentials, OAuth databases, browser tokens, cookies or private machine identity into Git.

## Gateway and OAuth Edge

- MCPJungle is the replaceable local aggregation layer.
- Production public identity is the canonical HTTPS 443 endpoint.
- Managed readiness requires the full compatibility edge on 9341, OAuth child on 9340, expected issuer, current runtime generation, and real Funnel 443 target pointing at the managed edge.
- A raw 9340 listener is degraded state, not READY.
- Local metadata never substitutes for real public OAuth/401 acceptance.
- Unknown or incompatible listeners fail closed; do not kill them without repository ownership evidence.

## Manager / Doctor / Repair

- Manager is loopback-only and does not own browser lifetime.
- Manager actions are fixed allowlisted contracts, never arbitrary shell execution.
- Doctor reports process, listener, MCP protocol, safe call, OAuth and remote layers separately.
- Repair is bounded, reversible and confirmation-aware.
- Public/status surfaces never expose plaintext secrets, secret paths, executable paths or private network identity.

## Runtime and launcher

- Start All preserves healthy unmanaged services and starts only repository-managed runtimes.
- Required unmanaged backends are reported explicitly; partial startup must not be called fully ready.
- Runtime generation plus capability contract is required before preserving a long-running repository-owned service.
- Desktop and Windows-login launchers are transparent, reversible and credential-free.
- The user-facing Manager opener reuses the normal browser profile/default URL handler; Playwright automation profile lifetime is separate.
- Current-host additions belong in machine-local hooks/overlays, not public release scripts.

## Loop and handoff

- Keep CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE explicit.
- Update SoT/docs before generating the next prompt.
- Generate handoff from verified current state, then verify exactly-once submission and next-run takeover.
- Do not silently discard a defensive rule; keep, relocate or retire it only with evidence.

## Release acceptance

Source tests alone are not release proof. Build and install the artifact in an isolated environment, exercise representative entry points, verify packaged non-code resources, run secret scanning, and confirm the public-safe release boundary.
