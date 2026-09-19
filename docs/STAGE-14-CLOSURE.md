# Stage 14 Closure — Production Unified Gateway / Edge

CURRENT_STAGE = STAGE-14-PRODUCTION-UNIFIED-GATEWAY-EDGE
NEXT_STAGE = STAGE-15-COMPONENT-INSTALL-UPGRADE-LIFECYCLE
AFTER_NEXT_STAGE = STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK

Status: CLOSED_LOCAL_VERIFIED

## Owned concern

Promote the previously verified integration Edge into a production runtime contract without taking lifecycle ownership of existing external MCP backends.

## Implemented

- Added the production `edge-runtime` CLI/runtime wrapper.
- Runtime Supervisor now owns the WebGPT OAuth Edge as a fixed runtime target.
- Manager/runtime restart scope expands only to the fixed WebGPT Edge id; Serena, Coding Tools, Playwright and Windows-MCP remain outside restart authority.
- Production OAuth credential is generated/reused under machine-local `secrets/`.
- Production OAuth database lives under the machine-local WebGPT state root.
- Edge startup waits for the local Gateway, synchronizes backend routes, starts mcp-auth-proxy, starts the compatibility adapter and publishes through the dedicated Tailscale Funnel port.
- Edge shutdown tears down only its owned Funnel/child process chain.
- Gateway route synchronization now queries existing MCPJungle registry state:
  - same transport + URL -> preserve;
  - missing -> register;
  - same name but changed URL -> force-replace inside WebGPT's private Gateway only;
  - unhealthy backend -> skip.
- Added a production Edge E2E harness that never prints OAuth passwords or tokens.

## Live evidence

Current WebGPT private Gateway:
- Coding Tools route: preserved as identical;
- Playwright route: registered;
- Serena route: registered;
- Windows-MCP route: registered;
- upstream service configuration remained unchanged;
- MCP `initialize`: HTTP 200;
- MCP session established;
- `tools/list`: 87 tools.

Current production Tailscale Edge on the dedicated WebGPT port:
- public OAuth protected-resource metadata: PASS;
- unauthenticated public `/mcp`: HTTP 401 PASS;
- DCR + PKCE + authorization-code token: PASS;
- authenticated public MCP: PASS, 87 tools;
- safe routed `coding-tools__server_info`: PASS;
- Runtime Supervisor controlled Edge restart: PASS;
- refresh token after restart: PASS;
- authenticated public MCP after restart: PASS, still 87 tools.

Existing Tailscale routes on the machine were not replaced. The WebGPT port was free before publication.

## Validation

- Stage 14 narrow tests: 5 PASS.
- Full repository tests: 120 PASS.
- Ruff: PASS.
- Secret scan: PASS.
- `git diff --check`: PASS.
- Real production Edge E2E: `STAGE14_PRODUCTION_EDGE_E2E_PASS`.

## Boundaries preserved

- No existing backend MCP was reinstalled, restarted or reconfigured.
- Route ownership remains separate from lifecycle ownership.
- OAuth secrets/tokens/database remain machine-local and are absent from Git/static UI.
- Backend-specific public tunnels remain optional; the unified WebGPT path uses localhost upstreams.
- Generic component installation/upgrades remain Stage 15.
- Serena multi-session isolation and complementary rescue remain Stage 16.
- Manager UX/bilingual control surface remains Stage 17.

## Next owner

Stage 15 makes the repository capable of detecting, installing and upgrading declared MCP/system dependencies on a fresh or existing machine while preventing duplicate deployment and preserving compatible existing services.
