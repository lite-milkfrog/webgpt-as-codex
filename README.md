# WebGPT-as-Codex

**English** | [简体中文](README.zh-CN.md)

> **Turn ChatGPT on the web into a durable local coding and computer agent.**
>
> One OAuth-protected public MCP endpoint, multiple local specialist MCPs, one canonical Agent Skill, reboot recovery, and Loop Engineering for work that must survive long sessions.

**Deploy once · one MCP URL · one-click start · self-recovery · local-first.**

> **No extra API tokens. No extra API bill.**
>
> WebGPT-as-Codex is designed to use your existing ChatGPT plan instead of asking you to buy a separate API balance. That gives you a practical degree of **local compute freedom**: when Codex quota is tight, you can keep working through your own local tools, browser and computer. It is especially useful for long coding, automation and desktop-control tasks that would otherwise burn through dedicated coding-agent quota.
>
> Personally tested across a very wide range of real tasks: repository development, testing, Git workflows, browser automation, Windows GUI control, MCP deployment, OAuth recovery, long-running handoffs and more.

ChatGPT itself still follows the limits of your current plan and client. In practice, the project does **not** require a separate OpenAI API key or additional API-token spend. If your ChatGPT client supports MCP/Plugins, the same local stack can be used from the plan you already have.

WebGPT-as-Codex is not another MCP server. It is the control, routing, recovery and deployment layer you start needing once several MCPs must work together reliably: who owns code semantics, who writes files, how OAuth stays stable, what happens after reboot, how concurrent sessions avoid shared-state collisions, and how a long task hands itself to the next conversation without losing truth.

## Fastest path: give the repository to an AI agent

Copy [`prompts/ONE-CLICK-AGENT-DEPLOY.md`](prompts/ONE-CLICK-AGENT-DEPLOY.md) to an agent that can operate the target Windows machine.

The prompt tells it to actually deploy—not just explain how—to:

- discover Python / Git / uv / Node / winget / Tailscale;
- preserve healthy existing MCPs instead of duplicating them;
- install and verify the core MCP stack and Unified Gateway;
- configure OAuth + Tailscale HTTPS Edge;
- install the desktop one-click launcher and Windows autostart;
- synchronize the single `WebGPT-as-Codex` Skill;
- run Doctor, Gateway, OAuth, startup-idempotence and release acceptance;
- stop only for account/login/OAuth consent that genuinely requires a human.

## What you get

| Capability | What WebGPT-as-Codex does |
|---|---|
| **One endpoint** | Your web AI talks to one OAuth-protected MCP Gateway instead of several public MCP registrations |
| **Correct routing** | Serena for semantics, Coding Tools for edits/tests/Git, Playwright for the web, Windows-MCP for native GUI |
| **One-click startup** | Desktop and Windows-login launchers recover local backends, then start Gateway/OAuth/Manager and verify real readiness |
| **Recovery with evidence** | Process, listener, MCP, OAuth and public-edge health are separate states; a live port is never called “healthy” by itself |
| **Durable long tasks** | Loop Engineering persists SoT, validation, commits and verified next-conversation handoff |
| **Concurrency boundaries** | Explicit isolation for Serena project state, Git worktree writers and shared physical GUI state |
| **Independent repair plane** | Remote Desktop Commander stays separate from the Gateway as a full-machine recovery/control plane |
| **Local-first security** | Secrets, OAuth databases, browser account state and machine-local runtime evidence stay off Git |

## 30-second architecture

```text
ChatGPT / Web AI
        │ HTTPS + OAuth / PKCE
        ▼
 WebGPT-as-Codex Edge
        ▼
  Unified MCP Gateway
   ├─ Coding Tools   → edit / test / Git
   ├─ Serena         → symbols / references / semantic navigation
   ├─ Playwright     → web apps / authenticated browser
   └─ Windows-MCP    → native Windows GUI

Remote Desktop Commander
   └─ independent full-machine recovery/control plane
```

The browser Manager is a control surface, not the runtime owner. Closing the page does not stop the agent backends.

## Manual install

Python 3.11+ is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\webgpt-codex.exe --version
```

Plan first, then explicitly apply:

```powershell
webgpt-codex deploy
webgpt-codex deploy --apply
webgpt-codex desktop-launcher install
webgpt-codex autostart install
webgpt-codex launcher --no-open --start-all
webgpt-codex doctor
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete deployment contract.

## Verified behavior

- the Unified Gateway aggregates the core MCP backends behind a namespaced tool surface;
- real public HTTPS OAuth metadata, dynamic registration, PKCE, token, refresh and authenticated MCP flows have passed end-to-end acceptance;
- unauthenticated public MCP requests are rejected with HTTP 401;
- Start All is idempotent and preserves healthy unmanaged services instead of duplicating them;
- OAuth Edge readiness verifies the real Funnel 443 target, not only local 9340/9341 listeners;
- desktop launcher and autostart are reversible, credential-free and structurally upgradeable;
- the only canonical Skill is `skills/webgpt-as-codex/`, preserving the full Experience Ledger, 53 original regression scenarios plus 3 legacy compatibility aliases and the R54 destructive-action authorization regression (57 total), and MCP Guides;
- the bilingual Manager exposes Doctor/Repair and environment/Gateway/OAuth/HTTPS state without returning secrets in normal status.

## CLI and safety boundary

`webgpt-codex --help` includes `deploy`, `bootstrap`, runtime `status/start/stop/restart`, `doctor`, allowlisted `repair`, loopback `manager`, launcher/autostart integration, discovery-first `add-mcp`, and durable `loop` evidence.

Git and release artifacts must not contain OAuth databases, tokens, passwords, private keys, cookies, browser profiles, pairing data, private machine URLs, transient PID/process state or machine-local handoff receipts.

WebGPT-as-Codex does not treat “can execute commands” as unlimited authority. Manager, Repair, Update and runtime lifecycle actions use bounded ownership/allowlist contracts; unknown listeners and healthy user-managed services fail closed or are preserved.

## Development

```powershell
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python scripts\secret_scan.py
```

For implementation state and design details, see [`docs/CURRENT-PROJECT-STATE.md`](docs/CURRENT-PROJECT-STATE.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/DECISIONS-AND-RISKS.md`](docs/DECISIONS-AND-RISKS.md), and the canonical [`WebGPT-as-Codex Skill`](skills/webgpt-as-codex/SKILL.md).
