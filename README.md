# WebGPT-as-Codex

WebGPT-as-Codex is a local-first control plane for using a web AI client as a durable coding/computer agent over MCP.

The project deliberately separates:
- upstream MCP servers;
- one replaceable local gateway;
- OAuth and remote transport;
- machine-local state/secrets;
- a local Manager/Doctor;
- the reusable Computer Agent + Loop Engineering Skill.

## Current implementation baseline
Core backends: Serena, Coding Tools MCP, Playwright MCP, Windows-MCP.
Default gateway: MCPJungle.
OAuth edge: WebGPT-as-Codex compatibility adapter + mcp-auth-proxy.
Remote ingress: Tailscale Funnel.
Remote Desktop Commander remains an optional direct vendor relay.

The repository-owned Manager is available as `webgpt-codex manager --open` and binds to loopback only by default. It shows registry-backed component/version status, distinct health levels, Gateway/OAuth/Tailscale state, an optional configured public MCP URL, the last Doctor result, and fixed Start All / Restart / Doctor / Repair / Update contracts. Closing the browser UI does not own or stop runtimes. Stage 7 and Stage 8 wire the actual Doctor/Repair and bounded runtime executors; Update remains a later-stage contract.

Stage 8 also provides `webgpt-codex launcher`, `desktop-launcher install|status|uninstall` and `autostart install|status|uninstall`. The Windows launcher starts/opens the local Manager workflow without making the browser its process owner. Start All preserves healthy external MCP/system services and starts only repository-owned missing runtimes.

Validated so far:
- four core MCP backends through one Gateway endpoint;
- real public HTTPS OAuth metadata, dynamic registration and PKCE;
- authenticated MCP calls through Tailscale Funnel;
- refresh-token reuse after OAuth proxy restart;
- unauthorized public MCP access rejected with HTTP 401;
- loopback Manager status/actions API and web UI;
- Manager output suppresses sensitive state and private/loopback service addresses;
- bounded Manager polling does not perform deep MCP safe-calls.
- repository-owned PID/birth-image lifecycle receipts reject stale/reused PID ownership;
- discovery-first Start All is idempotent and avoids duplicate healthy services;
- targeted Manager Restart refuses unmanaged component scope;
- desktop launcher/autostart contracts are reversible and do not embed credentials.

## Development
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
webgpt-codex manager --open
webgpt-codex doctor
pytest
```

No private recovery archive, OAuth database, token, password, private key, cookie, or machine identity belongs in this repository.

See `docs/ARCHITECTURE.md`, `docs/CURRENT-PROJECT-STATE.md`, and `skills/webgpt-as-codex/SKILL.md`.
