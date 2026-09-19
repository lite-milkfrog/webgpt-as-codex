---
name: webgpt-as-codex
description: Local-first MCP computer/coding agent workflow with durable SoT, Loop Engineering, verified handoff, Doctor/Repair, gateway routing and multi-window continuation.
metadata:
  version: 0.1.0
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

## Generic MCP extension
New MCPs are added through manifests + discovery + health checks + gateway registration + optional Tool Group + Skill routing.
See `add-mcp.md`.

## Manager boundary
The Manager is a loopback-only local control surface backed by the component registry and durable Doctor evidence.
Its browser UI never owns agent runtimes, polling stays bounded/shallow, and health levels remain distinct.
Manager actions are a fixed allowlist whose real executors are supplied only by the stage that owns their safety contract.

## Completion
A stage is complete only when owned behavior is implemented, relevant tests are green, post-state is verified, affected docs are updated, and remaining work is represented in CURRENT/NEXT/AFTER_NEXT.
