# Architecture

## Planes
1. Agent plane: reusable Skill, local SoT, stage/handoff rules.
2. Control plane: bootstrap, component registry, Doctor/Repair, Manager.
3. Runtime plane: Serena, Coding Tools, Playwright MCP, Windows-MCP.
4. Gateway plane: replaceable MCPJungle adapter and curated Tool Groups.
5. Edge plane: OAuth compatibility adapter -> mcp-auth-proxy -> MCPJungle, published by Tailscale Funnel.
6. Optional full-machine plane: Remote Desktop Commander vendor relay.

## Trust boundaries
Repository source is public-safe.
Machine state is outside Git.
Secrets are generated/stored machine-locally and never embedded in manifests.
Existing healthy services are discovered before any install or restart.

## Edge contract
The public path is one HTTPS MCP endpoint.
Tailscale Funnel terminates public HTTPS and forwards to the local OAuth compatibility adapter.
The compatibility adapter preserves forwarded HTTPS host/proto semantics and server-side consent continuity for the current mcp-auth-proxy behavior.
mcp-auth-proxy owns OAuth 2.1, dynamic client registration, PKCE, access/refresh tokens and backend authorization.
MCPJungle owns protocol aggregation only.

## Health model
Process -> listener -> MCP initialize -> tools/list -> safe tool call -> OAuth metadata -> DCR/PKCE -> refresh -> remote endpoint.
Each level is reported separately.

## Performance model
Prefer a curated gateway Tool Group over exposing every tool.
Do not duplicate overlapping MCPs merely because they are installed.
Routing belongs in the Skill; protocol aggregation belongs in the Gateway.
