# Stage 5 Closure — OAuth + Tailscale Public Edge

Result: CLOSED_LOCAL_VERIFIED

## Implemented
- machine-local mcp-auth-proxy binary location;
- reusable OAuth edge lifecycle adapter;
- dynamic Tailscale DNS discovery and bounded Funnel start/stop;
- OAuth 2.1 dynamic client registration + PKCE test client;
- access-token and refresh-token validation;
- generic OAuth compatibility adapter preserving forwarded HTTPS origin and consent continuity;
- real public HTTPS Stage 5 E2E harness;
- stable handoff prompt generator/validator and SHA-256 contract.

## Real E2E evidence
A temporary public Funnel on port 10003 was created without touching the existing 443/8443/10000-10002 mappings.

The authoritative HTTPS flow passed:
- PUBLIC_METADATA_PASS
- DCR_PKCE_TOKEN_PASS
- PUBLIC_INITIAL MCP_PASS
- PUBLIC_UNAUTH_401_PASS
- proxy stop/restart using the same machine-local OAuth data
- REFRESH_AFTER_RESTART_PASS
- PUBLIC_RESTARTED MCP_PASS
- STAGE5_EDGE_E2E_PASS

The MCP safe call behind the authenticated public endpoint was coding__server_info through MCPJungle.

## Root-cause lesson
A local HTTP OAuth probe initially failed because Secure-cookie and external-origin semantics differed from the real HTTPS client path.
The project now treats real HTTPS as the authoritative OAuth acceptance layer.
The compatibility adapter preserves forwarded host/proto and performs consent continuity without weakening OAuth.

## Security
- no passwords, tokens, cookies, OAuth databases or Tailscale private state are tracked;
- test passwords are generated at runtime only;
- OAuth state is machine-local;
- temporary Funnel 10003 is removed in finally paths.

## Handoff stability
Handoff prompts are generated only after stage commit, must contain the committed SOURCE_HEAD and all required protocol sections, and are validated before Playwright submission.
A SHA-256 receipt is recorded locally.

CURRENT_STAGE = STAGE-6-MANAGER-CONTROL-PLANE
NEXT_STAGE = STAGE-7-BOOTSTRAP-DOCTOR-REPAIR
AFTER_NEXT_STAGE = STAGE-8-DESKTOP-LAUNCHER-AND-AUTOSTART
