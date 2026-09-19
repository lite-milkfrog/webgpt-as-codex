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
OAuth edge: mcp-auth-proxy.
Remote ingress: Tailscale Funnel.
Remote Desktop Commander remains an optional direct vendor relay.

## Development
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
webgpt-codex doctor
pytest
```

No private recovery archive, OAuth database, token, password, private key, cookie, or machine identity belongs in this repository.

See `docs/ARCHITECTURE.md`, `docs/CURRENT-PROJECT-STATE.md`, and `skills/webgpt-as-codex/SKILL.md`.
