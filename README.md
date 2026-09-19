# WebGPT-as-Codex

WebGPT-as-Codex is a local-first control plane for using a web AI client as a durable coding/computer agent over MCP. Repository state is the public-safe source of truth; machine-local runtime state, credentials and browser/account state stay outside Git.

## Architecture

The verified implementation separates:
- **Agent plane:** project SoT, WebGPT-as-Codex Skill, Loop Engineering and verified recursive handoff.
- **Control plane:** bootstrap, component registry, Doctor/Repair and the loopback Manager.
- **Runtime plane:** Serena, Coding Tools MCP, Playwright MCP and Windows-MCP.
- **Gateway plane:** MCPJungle as the replaceable local aggregator.
- **Edge plane:** compatibility adapter -> mcp-auth-proxy -> MCPJungle, published through Tailscale Funnel.
- **Optional full-machine plane:** Remote Desktop Commander.

The browser UI never owns runtime lifetime. Health is reported in separate layers rather than treating a live process/listener as proof of MCP, OAuth or remote health.

## Install

Python 3.11+ is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\webgpt-codex.exe --version
```

The wheel includes the public component manifests and Manager static UI required by installed runtime commands. Machine-local state is created outside the installed package.

For development:

```powershell
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python scripts\secret_scan.py
```

## CLI

`webgpt-codex --help` exposes the supported command surfaces:

- `paths`: show the machine-local state root.
- `status`, `start`, `stop`, `restart`: bounded runtime-supervisor surfaces.
- `doctor`: prerequisite-aware deep health checks.
- `repair`: fixed allowlisted repair operations with confirmation/backups.
- `bootstrap`: discovery-first state/bootstrap planning.
- `manager`: loopback-only Manager UI/API.
- `launcher`, `desktop-launcher`, `autostart`: Windows launcher integration.
- `add-mcp`: discovery-first generic MCP onboarding; dry-run by default, explicit machine-local apply.
- `loop`: durable Loop Engineering execution/closure evidence.

Manager actions are fixed contracts only. Start/Restart are restricted by repository runtime ownership. Stage 11's Update action is repository-approved and offline-by-default: it can only consume an already-staged artifact whose component/version/source/digest/destination authority is declared by the repository.

## Verified behavior

Stages 0-11 established and regression-tested:
- one Gateway endpoint over the four core MCP backends;
- real public HTTPS OAuth metadata, DCR + PKCE, refresh and authenticated MCP calls;
- unauthorized public MCP access rejected with HTTP 401;
- loopback Manager with shallow polling, sanitized output and Host/Origin/action-schema hardening;
- discovery-first Bootstrap, deep Doctor and allowlisted Repair;
- PID birth/image ownership checks, idempotent Start All and bounded Restart;
- reversible credential-free desktop launcher/autostart;
- generic Add MCP with capability-evidence states and portable Operating Guides;
- durable Loop Engineering state and exactly-once Playwright handoff semantics;
- atomic machine-local state writes, untrusted custom-manifest validation and bounded rollback;
- repository-approved Manager Update authority.

## Public-safe release boundary

Git and release artifacts must not contain OAuth databases, tokens, passwords, private keys, cookies, browser profiles, pairing data, private machine URLs, local state receipts, generated handoff receipts, PID/process state or machine-specific private paths.

The wheel intentionally carries only runtime Python code plus public component manifests and the Manager static UI. Project documentation, stage evidence and Skill sources remain repository artifacts; machine-local runtime evidence remains outside both.

See `docs/ARCHITECTURE.md`, `docs/CURRENT-PROJECT-STATE.md`, `docs/DECISIONS-AND-RISKS.md` and `skills/webgpt-as-codex/SKILL.md`.
