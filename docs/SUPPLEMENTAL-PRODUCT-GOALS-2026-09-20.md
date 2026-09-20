# Supplemental Product Goals — 2026-09-20

[**English**](SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md) | [简体中文](zh-CN/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md)

This document is the canonical product delta that reopens implementation after the previously accepted TERMINAL state. Stages 1-12 remain closed; this document owns only the new requirements added afterwards.

## Product outcome

WebGPT-as-Codex becomes the single repository entry point for installing, detecting, validating, operating and gradually routing a local MCP toolchain into one public ChatGPT-facing gateway.

The desired external shape is:

```text
ChatGPT
├─ Remote Desktop Commander (independent rescue/control plane)
└─ WebGPT-as-Codex Unified Gateway
   ├─ Serena
   ├─ Coding Tools MCP
   ├─ Playwright MCP
   ├─ Windows-MCP
   ├─ future MCPs
   └─ WebGPT control/recovery capabilities
```

The two ChatGPT connections are complementary rather than mutually exclusive.

## Deployment experience

A new Agent starts from this repository, selects English or Chinese, reads the deployment entrypoint and executes the deployment contract.

The installer must:
1. detect the host and already-installed tools before mutation;
2. preserve healthy existing services;
3. install missing system prerequisites from approved official sources;
4. install missing MCP components through repository-owned adapters;
5. resolve the latest stable upstream version at deployment time, validate provenance and compatibility, and avoid duplicate installations;
6. keep already-newer compatible installations rather than downgrading them;
7. provision WebGPT-owned Gateway/OAuth runtime dependencies;
8. verify process/listener/MCP protocol/tools/safe-call separately;
9. configure the unified local Gateway;
10. configure OAuth and Tailscale HTTPS;
11. expose a loopback Web Manager and a one-click desktop launcher;
12. leave only genuinely interactive account/authorization steps to the user.

## Human-intervention boundary

The intended final manual steps are limited to:

### Remote Desktop Commander
Install/connect the ChatGPT-side official integration, sign in and pair the machine when required.

### WebGPT-as-Codex Unified Gateway
Add the one public HTTPS MCP endpoint to ChatGPT and complete the real browser OAuth authorization flow. Acceptance requires the ChatGPT web flow to return successfully, not merely a local curl/token test.

Tailscale account login may require a browser/account confirmation on a fresh machine, but all deterministic configuration around it belongs to the deployment system.

## Existing-machine migration rule

Current services are not disposable migration fixtures.

For every component:
- discover before install;
- healthy existing instance -> preserve;
- absent -> install;
- older compatible instance -> controlled upgrade;
- newer compatible instance -> preserve and test;
- unhealthy instance -> diagnose before replace;
- lifecycle authority is granted only after WebGPT has explicit ownership evidence.

Routing ownership and lifecycle ownership are separate. A currently external MCP may be routed through the WebGPT Gateway before WebGPT owns its start/stop lifecycle.

## Gateway contract

The production route is:

```text
local MCPs
  -> MCPJungle
  -> mcp-auth-proxy
  -> OAuth compatibility adapter
  -> Tailscale Funnel HTTPS
  -> one public /mcp endpoint
  -> ChatGPT
```

The Gateway route must not require each backend MCP to expose its own public tunnel.

Coding Tools MCP therefore may run only on localhost under this design; its optional Cloudflare remote client is not a required WebGPT dependency.

## Complementary fallback contract

WebGPT Unified Gateway and Remote Desktop Commander form independent rescue paths.

- When a structured Gateway MCP/backend fails but Remote Desktop Commander remains available, the Agent may use Remote Desktop Commander to inspect/recover the local WebGPT/backend service, then retry the structured MCP.
- When Remote Desktop Commander fails but the Unified Gateway remains available, the Agent may use Gateway-routed Windows-MCP/Coding Tools/WebGPT recovery capabilities to inspect/recover the Remote Desktop Commander runtime where safe.
- Neither path may silently bypass authentication/security policy.
- Transport failure, backend failure and tool-call failure remain distinct.
- Recovery is evidence-driven and exactly-once for external side effects.

A failure of the entire WebGPT public endpoint cannot be internally handled by that same dead endpoint; rescue selection therefore belongs partly to the Agent/Skill routing layer.

## Concurrency contract

Parallel ChatGPT windows are a supported deployment target, but concurrency differs by backend:

- Serena: a single standard MCP server process has process-wide active-project state. Different conversations switching different projects can interfere. WebGPT must support isolated Serena instances/project slots for concurrent project work rather than sharing one mutable active-project instance.
- Coding Tools: multiple tool requests/processes can overlap, but one server instance has one configured workspace. Parallel writers must use separate worktrees/workspaces or explicit write serialization. Read/process tasks on independent resources may run concurrently.
- Remote Desktop Commander: independent filesystem/process sessions can overlap, but GUI/mouse/keyboard/focus operations share one physical desktop and must be serialized at the GUI side-effect boundary.
- Playwright: independent browser pages/contexts may run concurrently when their state is isolated; actions against the same page/profile must respect shared-state ownership.
- Windows-MCP: GUI actions share native UI/focus and are not assumed safely parallel.

## Repository/source model

The repository is the single deployment authority. It stores:
- component manifests;
- official upstream/source metadata;
- installer/provision adapters;
- version detection and compatibility rules;
- configuration templates;
- health tests;
- routing/lifecycle contracts;
- WebGPT-owned code and UI.

Third-party source trees do not need to be copied wholesale into this repository. Attribution/license/provenance belongs in dedicated repository metadata/notices rather than product-oriented README prose.

## Bilingual product

The project must ship:
- an English source/release experience;
- a complete Chinese mirror with equivalent functionality;
- Chinese as the default desktop Manager experience for the current user;
- a language switch in the Manager without functional divergence.

Identifiers, commands, URLs, schema keys, hashes and protocol constants remain exact across languages.

Stage 17 verified the Manager/desktop portion of this goal: English and Chinese Manager shells now share one functional JS/CSS contract, the real managed Desktop/Startup launchers default to Chinese, explicit `/en` and `/zh` remain available, and both languages passed DOM-level parity checks. Stage 18 still owns the repository-wide Chinese documentation/release mirror and third-party notices.

The Stage 17 post-acceptance hotfix additionally verifies that a long-running stale Manager cannot be accepted merely because port 9200 is listening: WebGPT now proves process identity plus runtime/resource contract before refreshing an owned/legacy stale Manager, and refuses to kill ambiguous listeners. The user-facing Desktop launcher also keeps browser automation separate from ordinary URL opening by reusing the normal running Edge profile when present, with the Windows default URL handler as fallback.

## Stage 19 product-goal reconciliation

The production Gateway contract is now verified on canonical HTTPS 443 with the compatibility edge on 9341, OAuth proxy on 9340 and Gateway on 9330. Readiness is end-to-end: a surviving 9340 child alone is insufficient.

The real recovery path preserves a compatible OAuth child only when its canonical issuer matches, then reconstructs the managed 9341 Edge without changing public identity or credentials. Runtime receipts follow the real listener PID rather than a Windows venv launcher wrapper.

Real production acceptance passed public OAuth metadata, 401 protection, DCR/PKCE, authenticated 87-tool MCP, controlled Edge restart, refresh continuity and authenticated MCP after restart. The user then confirmed the ChatGPT connector was configured successfully. From that point, disruptive production acceptance is frozen and remaining final acceptance is reconciliation/release-readiness work rather than more connector churn.
