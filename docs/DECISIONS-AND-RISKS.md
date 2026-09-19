# Decisions and Risks

## Stage 5 — OAuth/Tailscale edge

### Decision: one public MCP endpoint
Only the unified Gateway path is published for the self-hosted stack.
Individual core MCP backends remain loopback/private.

### Decision: preserve an OAuth compatibility adapter
The current verified mcp-auth-proxy flow needs correct forwarded HTTPS host/proto semantics and consent-session continuity.
The adapter is generic project code; no machine secret or public hostname is embedded.

### Decision: final OAuth acceptance must use real HTTPS
Local HTTP localization can distort Secure-cookie behavior.
The authoritative Stage 5 gate runs DCR, PKCE, login/consent, token, refresh and MCP calls through a temporary real Tailscale Funnel HTTPS endpoint.

### Risk: upstream OAuth behavior may change
The compatibility adapter is isolated behind a small boundary and must be revalidated when mcp-auth-proxy changes.
Doctor must report OAuth metadata/DCR/PKCE/refresh separately so a future upstream change is diagnosable.

### Risk: hosted Tailscale availability
Tailscale Funnel is an edge adapter, not a repository security boundary.
The core local stack remains useful without public Funnel availability.
