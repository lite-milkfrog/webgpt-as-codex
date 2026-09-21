# WebGPT-as-Codex

**English** | [简体中文](README.zh-CN.md)

> **Turn ChatGPT on the web into a durable local coding and computer agent.**
>
> One OAuth-protected public MCP endpoint, multiple local specialist MCPs, one canonical Agent Skill, reboot recovery, and Loop Engineering—a staged execution and automatic handoff system for work that must survive beyond one chat window.

**Deploy once · one MCP URL · one-click start · self-recovery · local-first.**

> **No extra API tokens. No extra API bill.**
>
> WebGPT-as-Codex is designed to use your existing ChatGPT plan instead of asking you to buy a separate API balance. That gives you a practical degree of **local compute freedom**: when Codex quota is tight, you can keep working through your own local tools, browser and computer. It is especially useful for long coding, automation and desktop-control tasks that would otherwise burn through dedicated coding-agent quota.
>
> Personally tested across a very wide range of real tasks: repository development, testing, Git workflows, browser automation, Windows GUI control, MCP deployment, OAuth recovery, long-running handoffs and more.

ChatGPT itself still follows the limits of your current plan and client. In practice, the project does **not** require a separate OpenAI API key or additional API-token spend. If your ChatGPT client supports MCP/Plugins, the same local stack can be used from the plan you already have.

WebGPT-as-Codex is not another MCP server. It is the control, routing, recovery and deployment layer you start needing once several MCPs must work together reliably: who owns code semantics, who writes files, how OAuth stays stable, what happens after reboot, how concurrent sessions avoid shared-state collisions, and how a long task hands itself to the next conversation without losing truth.

One thing became obvious after using it on real work: **giving an agent tools only solves whether it can touch the computer. What decides whether it can keep working is whether it has a durable way to work.**

> **MCP gives it hands. The Skill teaches it how to work. SoT (Source of Truth—the authoritative record of the project's real state) keeps the project from forgetting. Loop Engineering (staged execution + validation + persistence + automatic handoff) keeps it moving across conversation windows.**

That is why `skills/webgpt-as-codex/` is not a thin “use Playwright for websites” prompt. It is an execution system: tool routing, permission boundaries, recovery, single-writer discipline, concurrency isolation, validation, the Experience Ledger, regression evals, cross-conversation handoff and Loop Engineering. Machine-specific ports, paths, live health and handoff receipts stay in the machine-local overlay instead of being pushed into the public repository.

### A few terms in plain English

- **MCP (Model Context Protocol)**: the common “socket” that lets an AI call external tools. With MCP, ChatGPT can use code, browser, filesystem and Windows-control tools instead of only returning text.
- **Skill**: not another tool, but the agent's operating manual + accumulated working rules. It decides which tool to use, how to recover from failure, what must be verified and which actions require stronger authorization.
- **SoT (Source of Truth)**: the project's real ledger. Progress, Git HEAD, validation state and known risks come from durable repository evidence—not from whatever one chat window happens to remember.
- **Loop Engineering**: the system for work that does not fit in one conversation. A large task is split into Stages; each Stage executes, validates, updates SoT, commits, generates the next prompt and hands it to a new ChatGPT conversation.
- **Automatic long-task handoff**: the practical result of Loop Engineering. The current window does not merely say “continue”; it passes verified code state, test results, Git HEAD, next-stage objective, tool locations and recovery rules, then verifies that the next window actually took over.
- **Handoff**: the controlled transfer from one agent/conversation to the next. It passes verified project state and an execution contract instead of relying on copied chat history.
- **Machine-local durable state**: restart/recovery evidence stored only on the local machine, such as CURRENT/NEXT/AFTER_NEXT, prompt hash and handoff receipts. It helps recover from disconnects and context loss, but it never replaces repository SoT.
- **Gateway**: the single entry point that aggregates multiple MCP servers so ChatGPT does not have to manage several public endpoints separately.
- **READY**: not merely “a port is open.” The relevant process, MCP, OAuth and HTTPS layers must pass their checks before the stack is treated as usable.
- **Start All / one-click startup**: the startup path that recovers missing services and preserves already healthy ones instead of blindly launching duplicates.

## Fastest path: give the repository to an AI agent

Repository: **[https://github.com/liusiong/webgpt-as-codex](https://github.com/liusiong/webgpt-as-codex)**

Give the agent both the **repository link** and [`prompts/ONE-CLICK-AGENT-DEPLOY.md`](prompts/ONE-CLICK-AGENT-DEPLOY.md). The repository tells it where the real project is; the deployment prompt tells it how to inspect the machine, install/recover the stack, verify it and close the setup correctly.

The prompt tells it to actually deploy—not just explain how—to:

- discover Python / Git / uv / Node / winget / Tailscale;
- preserve healthy existing MCPs instead of duplicating them;
- install and verify the core MCP stack and Unified Gateway;
- configure OAuth + Tailscale HTTPS Edge;
- install the desktop one-click launcher and Windows autostart;
- synchronize the single `WebGPT-as-Codex` Skill;
- run Doctor, Gateway, OAuth, startup-idempotence and release acceptance;
- stop only for account/login/OAuth consent that genuinely requires a human.

## After the first setup, daily use is one click

The first deployment has real setup work—OAuth, Tailscale, MCPs, the Skill and account consent—but **that is not something you are supposed to rebuild every morning**.

The normal path is:

1. Once, give the agent the repository URL **https://github.com/liusiong/webgpt-as-codex** together with [`prompts/ONE-CLICK-AGENT-DEPLOY.md`](prompts/ONE-CLICK-AGENT-DEPLOY.md), so it works from the real repository instead of from copied instructions;
2. complete the required account login, OAuth consent and ChatGPT MCP connection;
3. on later boots, **double-click the WebGPT-as-Codex desktop one-click launcher**;
4. the launcher runs the **machine-local prestart (a local-only startup hook)** for approved external MCP backends, then starts or recovers the **Gateway (the unified MCP entry point)**, **OAuth Edge (the public authorization/HTTPS edge)**, Manager and the rest of the WebGPT runtime, followed by layered **READY (the whole chain is actually usable)** checks;
5. healthy services are preserved instead of duplicated, so clicking Start All again is safe and idempotent;
6. once READY, open ChatGPT and start asking it to work. Under normal conditions there is no need to re-enter the MCP URL or redeploy the stack.

In other words, the everyday experience should not be “open five terminals and remember which command starts which daemon.” It should look like this:

```text
boot Windows
  ↓
double-click one launcher
  ↓
recover missing services / preserve healthy ones
  ↓
READY
  ↓
open ChatGPT and work
```

If Windows-login autostart is enabled, much of the stack may already be recovering before you click anything. The desktop Start All path is still idempotent, so it can be used as the single visible readiness check.

## The Skill is more than an MCP router

A real long-running task follows a durable chain instead of trusting chat memory. A **Stage** is one bounded piece of work with one objective, explicit validation and an exit condition:

```text
Stage N
  ↓
read real repository SoT / Git HEAD
  ↓
execute + validate
  ↓
update SoT / decisions / risks
  ↓
commit
  ↓
generate + validate the Stage N+1 prompt
  ↓
Playwright submits it into a new ChatGPT conversation
  ↓
verify that the next window actually took over
  ↓
persist a machine-local handoff receipt
```

The state model deliberately keeps two layers separate:

- **Repository SoT (the repository's authoritative project truth)** remains valid after any chat window disappears;
- **machine-local durable state (local restart/recovery evidence)** keeps CURRENT/NEXT/AFTER_NEXT (current / next / after-next Stage), source HEAD (the Git commit this Stage is based on), closure phase, prompt hash, handoff result and recovery evidence without replacing repository truth.

**Loop Engineering (staged long-task execution with automatic cross-conversation handoff)** also turns reusable failure into reusable engineering knowledge:

```text
RECOVER → DISTILL → GENERALIZE → PATCH → EVAL → VALIDATE → PROPAGATE
```

So the agent is not supposed to merely “find a workaround and forget it.” Reusable failure modes are distilled into the Skill, MCP Guides or regression scenarios and propagated forward. This is not model-weight self-training; it is **engineering experience becoming explicit, testable execution rules**.

## WAC × RDC: two independent control planes that can rescue each other

WebGPT-as-Codex (WAC, the primary structured execution plane) and Remote Desktop Commander (RDC, the independent full-machine control/recovery plane) are intentionally not a parent process and a child plugin.

```text
WebGPT-as-Codex
= primary structured execution plane
= code / Git / browser / Windows GUI / Gateway / OAuth

Remote Desktop Commander
= independent full-machine repair / control plane
= files / terminal / processes / logs / host recovery
```

Keeping them independent is what makes mutual recovery useful:

- **WAC healthy, RDC unhealthy**: use WAC-side Coding Tools / Windows-MCP / approved local control to inspect and recover RDC;
- **RDC healthy, WAC unhealthy**: use RDC to inspect Gateway, Coding Tools, OAuth Edge, Tailscale/Funnel, Manager, Playwright/Windows-MCP relays and startup scripts, then recover WAC;
- **both healthy**: route normal structured work through WAC and keep RDC outside it as a full-machine recovery plane;
- **both unhealthy**: fall back to local desktop bootstrap, startup/reboot recovery or human-local repair.

An unhealthy plane is never chosen to repair itself, and recovery is not allowed to recurse into a WAC → RDC → WAC loop. RDC is still not a Gateway child or a WAC READY prerequisite; on a configured machine, the desktop bootstrap can use the machine-local prestart hook to bring up approved external backends such as RDC alongside the rest of the one-click startup.
## What you get

| Capability | What WebGPT-as-Codex does |
|---|---|
| **One endpoint** | Your web AI talks to one OAuth-protected MCP Gateway instead of several public MCP registrations |
| **Correct routing** | Serena for semantics, Coding Tools for edits/tests/Git, Playwright for the web, Windows-MCP for native GUI |
| **One-click startup** | Desktop and Windows-login launchers recover local backends, then start Gateway/OAuth/Manager and verify real READY state instead of trusting a live port |
| **Recovery with evidence** | Process, listener, MCP, OAuth and public-edge health are separate states; a live port is never called “healthy” by itself |
| **Durable long tasks** | Loop Engineering (staged execution + automatic handoff) persists SoT (project truth), validation, commits and verified next-conversation handoff |
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
