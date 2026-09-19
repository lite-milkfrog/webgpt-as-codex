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

## Manager control plane
The repository-owned Manager is a loopback-only local control surface. Its default bind is `127.0.0.1:9200`; the existing private/reference Manager on port 9199 is evidence only and is neither copied nor mutated.

Manager status is registry-backed. Each component is rendered without its loopback endpoint or raw manifest and keeps these health levels separate: process, listener, protocol, safe-call, OAuth and remote. The Manager performs only bounded cached listener probes itself; deeper protocol/safe-call/OAuth/remote evidence is read from the last Doctor result. This prevents UI polling from becoming an MCP performance tax.

Machine-local Manager configuration lives outside Git under the normal state root. `config/manager.json` may contain a `public_mcp_url`; only credential-free public HTTPS URLs are renderable. Secret-like keys, bearer material and private/loopback URLs are recursively redacted before API/UI output.

The UI lifecycle does not own runtime lifecycle. Closing a tab only removes the browser view. Manager and later runtime supervisors are independent processes, and agent runtimes are not children of the browser UI.

Stage 6 defines fixed action contracts only: Start All, Restart, Doctor, Repair and Update. There is no arbitrary-command endpoint. Mutating contracts require confirmation, POST requests require the same-origin control header, and real executors are injected only by their owner stages: Doctor/Repair in Stage 7, Start/Restart in Stage 8, and Update hardening later.
