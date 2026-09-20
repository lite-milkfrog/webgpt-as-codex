# WebGPT-as-Codex

[**English**](README.md) | [简体中文](README.zh-CN.md)

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

The wheel includes the public component manifests plus English/Chinese Manager HTML and their shared CSS/JavaScript required by installed runtime commands. Stage18 also packages bilingual public release/legal/provenance resources: the English/Chinese README, authoritative Apache-2.0 `LICENSE`, its explicitly non-binding Chinese reading translation, bilingual third-party notices, provenance metadata and the translation coverage manifest. Machine-local state is created outside the installed package.

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
- English/Chinese Manager parity with one shared functional implementation, explicit `/en`/`/zh` routes, public-safe environment/deployment/version/Gateway/OAuth/HTTPS/inventory surfaces, URL copy/open controls, secret-safe recent activity and reduced-motion/accessibility handling;
- discovery-first Bootstrap, deep Doctor and allowlisted Repair;
- PID birth/image ownership checks, idempotent Start All and bounded Restart;
- reversible credential-free desktop launcher/autostart, with a current-deployment Chinese default and safe structural upgrade of the previously managed launcher;
- stale-Manager generation/contract detection so a still-listening old Python process cannot mix a new static tree with an old route table; ambiguous non-WebGPT listeners remain protected from termination;
- desktop Manager opening that reuses the user's normal running Edge profile (or the Windows default URL handler) instead of creating an automation-only blank profile;
- generic Add MCP with capability-evidence states and portable Operating Guides;
- durable Loop Engineering state and exactly-once Playwright handoff semantics;
- atomic machine-local state writes, untrusted custom-manifest validation and bounded rollback;
- repository-approved Manager Update authority.

Manager local credential controls are loopback/confirmation gated. Normal status never returns an OAuth password. Explicit Reveal returns it only to that local response; Set and Regenerate do not echo it, Regenerate creates a new value, and the activity feed never records plaintext credentials. Adding a custom MCP candidate changes local registry visibility only and does not grant Gateway routing or runtime lifecycle authority.

## Public-safe release boundary

Git and release artifacts must not contain OAuth databases, tokens, passwords, private keys, cookies, browser profiles, pairing data, private machine URLs, local state receipts, generated handoff receipts, PID/process state or machine-specific private paths.

The wheel intentionally carries runtime Python code, public component manifests, the Manager static UI, the bounded Stage18 public release/legal/provenance resources, and the unified Agent Skill 1.2.0 portable profiles under `share/webgpt-as-codex/skills`. Stage closures/prompts and machine-local runtime evidence remain outside the installed Skill/runtime surface. The local Computer Agent uses the same portable 1.2.0 core plus machine-only environment/inventory/state overlays.

See `docs/ARCHITECTURE.md`, `docs/CURRENT-PROJECT-STATE.md`, `docs/DECISIONS-AND-RISKS.md` and `skills/webgpt-as-codex/SKILL.md`.
