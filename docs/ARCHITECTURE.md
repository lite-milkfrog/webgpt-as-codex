# Architecture

## Planes
1. Agent plane: reusable Skill, local SoT, stage/handoff rules.
2. Control plane: bootstrap, component registry, Doctor/Repair, Manager.
3. Runtime plane: Serena, Coding Tools, Playwright MCP, Windows-MCP.
4. Gateway plane: replaceable MCPJungle adapter and curated Tool Groups.
5. Edge plane: mcp-auth-proxy OAuth then Tailscale Funnel.
6. Optional full-machine plane: Remote Desktop Commander vendor relay.

## Trust boundaries
Repository source is public-safe.
Machine state is outside Git.
Secrets are encrypted or referenced; never embedded in manifests.
Existing healthy services are discovered before any install or restart.

## Health model
Process -> listener -> MCP initialize -> tools/list -> safe tool call -> OAuth -> remote endpoint.
Each level is reported separately.

## Performance model
Prefer a curated gateway Tool Group over exposing every tool.
Do not duplicate overlapping MCPs merely because they are installed.
Routing belongs in the Skill; protocol aggregation belongs in the Gateway.
