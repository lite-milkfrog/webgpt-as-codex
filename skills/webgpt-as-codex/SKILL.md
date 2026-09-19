---
name: webgpt-as-codex
description: Local-first MCP computer/coding agent workflow with durable SoT, Loop Engineering, verified handoff, Doctor/Repair, gateway routing and multi-window continuation.
metadata:
  version: 0.4.0
  portability: public-safe-local-first
  secrets-policy: no-secrets-in-skill
---

# WebGPT-as-Codex Skill

Use this Skill when a web AI session is expected to operate a real computer or codebase through MCP and continue substantial work reliably.

## Startup contract
1. Locate the project-local source of truth before relying on chat memory.
2. Read `docs/CURRENT-PROJECT-STATE.md`, owner-stage closure and `AGENTS.md`.
3. Discover actual available tools/services; distinguish installed, configured, listening, protocol-healthy and remote-reachable.
4. Keep unrelated repositories and healthy services unchanged.

## Tool routing
- semantic code navigation: Serena;
- repository writes/tests/local Git: Coding Tools when bound to the repo;
- full-machine files/processes: Desktop Commander;
- browser/Web App DOM: Playwright;
- native Windows UI: Windows-MCP;
- platform API: dedicated connector/API when available.
Prefer structured tools over GUI and diagnose before fallback.
See `routing.md`.

## Loop Engineering
Every stage has one owner concern and three explicit pointers:
`CURRENT_STAGE`, `NEXT_STAGE`, `AFTER_NEXT_STAGE`.
Closed stages are not re-audited without contradictory evidence.
Validation and documentation updates happen before closure/handoff.
See `loop-engineering.md`.

## Self-evolving execution
Do not merely execute. Execute, observe, learn and improve.
Any repeated friction across SoT loading, planning, stage sizing, routing, MCP use, implementation, validation, docs, Git or handoff should trigger:
Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse.

Explore reasonable tool/schema/environment/log/history evidence before asking the user. One failed call is not proof an MCP is unavailable. Diagnose binding, session, authentication, capability mismatch and harness state before fallback; when fallback is justified, record why.

Classify lessons narrowly:
- general reusable rule -> Skill;
- MCP-specific operating behavior -> MCP Guide;
- machine-specific state -> machine-local inventory/config;
- one-off incident -> stage evidence only.
User guidance that reveals a reusable principle is valid experience input and should be classified the same way.

## Local memory
For long tasks, durable facts go to local SoT files during the run.
Chat context is a transport cache, not the authoritative project state.
Never place secrets in local SoT committed to Git.

## Handoff
Generate a next-window prompt from current verified state, not by renaming an old prompt.
If automatic continuation is authorized, verify submit + new run start before marking handoff successful.
The handoff contract is recursive: every next window must close its own stage and Playwright-submit a newly generated prompt to the following window, preserving CURRENT/NEXT/AFTER_NEXT, until Final Overall Acceptance is closed.
See `handoff.md`.

## Experience Ledger
Do not silently delete an old defensive rule.
Trace its origin, test whether the failure remains possible, then keep, relocate or retire it with evidence.
See `experience-ledger.md`.

## MCP operating knowledge
Routing decides WHICH tool. Operating knowledge decides HOW to use it. Real evidence decides whether it worked. Experience decides how to do it better next time.
Do not invent capability from an MCP name; inspect actual tool/schema evidence. Formal per-MCP Operating Guide onboarding is Stage 9 ownership, with the Guide template covering mental model, best/poor use cases, exposed capability, goal-oriented patterns, mistakes, failure diagnosis, verification, performance/cost, lessons and better alternatives.

## Generic MCP extension
New MCPs are added through manifests + discovery + health checks + gateway registration + optional Tool Group + Skill routing.
See `add-mcp.md`.

## Manager boundary
The Manager is a loopback-only local control surface backed by the component registry and durable Doctor evidence.
Its browser UI never owns agent runtimes, polling stays bounded/shallow, and health levels remain distinct.
Manager actions are a fixed allowlist whose real executors are supplied only by the stage that owns their safety contract.

## Bootstrap / Doctor / Repair discipline
- bootstrap must discover first and preserve a healthy service; installed-but-stopped does not authorize an automatic restart;
- Doctor records process, listener, protocol, safe-call, OAuth and remote independently and respects prerequisites between deeper checks;
- a listener is never protocol proof, and an unattempted deeper check is unknown rather than failed;
- skip version probes that can fetch/update packages (for example an `@latest` command) and reject ambiguous dotted banner text as version evidence;
- persist Doctor results only in sanitized machine-local state; never persist raw process command lines, credentials or private endpoints into Git;
- local OAuth metadata is useful diagnosis, while real HTTPS remains authoritative for final OAuth acceptance;
- Repair is a fixed action allowlist with dry-run/confirmation/backups; never turn Repair into a generic shell;
- runtime start/restart belongs to the runtime-owner stage, not to Bootstrap or Doctor.

## Runtime supervisor / launcher discipline
- discovery is permission to preserve, not permission to kill: stop/restart requires repository-owned PID identity evidence;
- stale PID files and PID reuse are rejected using process birth identity plus executable-image checks;
- Start All preserves healthy unmanaged listeners and process-only system services, then starts only fixed repository-managed missing runtimes;
- report required-but-unmanaged missing services separately from managed action success; never turn partial startup into a full-health claim;
- Manager runtime actions keep a fixed component allowlist and never accept arbitrary commands, argv, paths or PIDs from the browser;
- browser/Manager UI/desktop launcher lifetime never owns agent-runtime lifetime;
- Windows desktop/autostart launchers must be transparent, reversible, credential-free and refuse to overwrite/delete unmanaged files;
- do not reuse integration-test OAuth credentials as a production/autostart launch contract merely because the files exist.

## Completion
A stage is complete only when owned behavior is implemented, validation is green, post-state is verified, affected docs/ledger are updated, closure is written, the stage is committed, the next prompt is generated from that committed HEAD, validated/hashed, Playwright-submitted, the sent user message is verified and the next assistant run is verified.

Use an approximately 20-minute soft stage budget including closure/handoff; it is a heuristic, not a hard timeout. Split a stage when continuing implementation would endanger true closure. Short fully closed stages are preferable to repeated almost-complete windows.
