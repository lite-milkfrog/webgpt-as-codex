# Deployment Contract

## Entry point

An Agent or user starts from this repository only. The repository decides the deployment path from discovered machine state.

Deployment is discovery-first, idempotent and version-aware.

## Phase 0 — language and repository truth

1. Select English or Chinese instructions.
2. Read `AGENTS.md`, this document, `docs/CURRENT-PROJECT-STATE.md`, `docs/ARCHITECTURE.md` and the WebGPT Skill.
3. Never treat a prior machine's installed state as a fresh-machine prerequisite.

## Phase 1 — environment gate

Detect at minimum:
- Windows support level;
- Python >= repository minimum;
- Git;
- Node/npm when required by selected MCPs;
- uv when required by selected MCPs;
- winget;
- Tailscale installation/version/login/online/MagicDNS/Funnel capability;
- WebGPT state-root writability;
- reserved ports/conflicts;
- WebGPT-owned MCPJungle and mcp-auth-proxy binaries.

Do not claim Edge readiness until the environment report says it is ready.

## Phase 2 — system dependency bootstrap

For an absent prerequisite, use an allowlisted official source. Existing healthy prerequisites are preserved.

Tailscale:
- absent + winget available -> approved `Tailscale.Tailscale` install path;
- installed but old -> controlled upgrade path;
- installed but logged out/offline -> request the account login step;
- online -> preserve;
- Funnel/HTTPS unavailable -> block public-edge success and surface the exact next action.

## Phase 3 — WebGPT private runtime provisioning

WebGPT owns the Gateway/Edge runtime dependency installation.

Missing approved artifacts are downloaded from official upstream releases, SHA-256 verified and placed under the machine-local WebGPT state root.

Current approved bootstrap baselines are repository metadata, not claims that they remain the latest forever. Deployment resolves current stable upstream metadata, compares it with the verified compatibility policy, and tests before promotion.

Existing binaries are preserved by default.

## Phase 4 — MCP inventory and deployment

For each declared MCP:
1. detect installation;
2. detect running process/listener;
3. detect installed version when safe;
4. query upstream latest stable version through the component adapter;
5. run MCP initialize + tools/list when reachable;
6. run only the manifest-declared safe call;
7. classify as preserve / install / upgrade / diagnose / incompatible;
8. mutate only after component-specific authority is established.

Never deploy a duplicate healthy instance merely because a package executable is absent from PATH.

## Phase 5 — unified local Gateway

Start/preserve MCPJungle.
Register healthy enabled Streamable HTTP MCPs as upstream routes in WebGPT's private Gateway database.

Route registration must not rewrite an upstream MCP's own configuration.

The initial migration may use:
- routing ownership = WebGPT;
- lifecycle ownership = external/preserved.

Later WebGPT-installed components may acquire WebGPT lifecycle ownership after validation.

## Phase 6 — OAuth and HTTPS Edge

Start the WebGPT production Edge:
- private Gateway;
- OAuth proxy;
- compatibility adapter;
- Tailscale Funnel HTTPS.

OAuth credentials live only under the machine-local WebGPT state/secrets area.

The Web Manager exposes status and explicit local credential controls without embedding secrets in static assets or repository files.

## Phase 7 — deep verification

Required health layers:
1. process;
2. listener;
3. MCP initialize;
4. tools/list;
5. safe tool call;
6. OAuth metadata;
7. DCR + PKCE;
8. token exchange;
9. protected unauthenticated 401 gate;
10. refresh token;
11. authenticated MCP call;
12. public HTTPS reachability.

A green lower layer does not imply a green higher layer.

## Phase 8 — desktop/control plane

Install a transparent one-click `WebGPT-as-Codex.cmd` launcher.
Open the loopback Web Manager.
The Manager must show:
- environment readiness;
- MCP inventory/version state;
- Gateway routes;
- local/public MCP addresses;
- OAuth state and local credential controls;
- Tailscale/HTTPS state;
- backend health;
- migration/lifecycle ownership;
- logs/recovery actions.

The browser UI never owns runtime lifetime.

## Phase 9 — final manual actions

Only interactive account/browser authorization remains:

1. Remote Desktop Commander: install/sign in/pair through the ChatGPT-side integration.
2. WebGPT Unified Gateway: add the single public MCP URL to ChatGPT and complete the real OAuth browser flow.
3. If a fresh Tailscale account requires sign-in/permission approval, complete that account action when prompted.

## Phase 10 — acceptance

A deployment is not complete until:
- no duplicate managed MCP instance was created;
- existing healthy external services were preserved;
- required versions are current/compatible;
- local Gateway routing is proven;
- public HTTPS/OAuth is proven;
- the ChatGPT OAuth flow is proven;
- desktop launcher and Manager work;
- fallback paths are exercised;
- concurrency policy is documented and tested.
