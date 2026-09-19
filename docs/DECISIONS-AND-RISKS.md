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

## Cross-stage decision — recursive verified handoff

Automatic continuation is a project invariant, not a one-time permission.
Every stage closure must:
- commit first;
- generate the next prompt from that committed HEAD;
- carry CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE;
- include the recursive continuation invariant;
- validate + hash the prompt;
- Playwright-submit the exact prompt in one MCP session;
- verify sent-message SOURCE_HEAD + assistant run + /c/ conversation URL;
- require the receiving window to repeat the same protocol.

The chain terminates only after the planned final stage and Final Overall Acceptance are both closed.

## Stage 6 — Manager control plane

### Decision: reference Manager is evidence, not source
The existing service on `127.0.0.1:9199` was inspected read-only. Its machine-specific service inventory, external addresses, local authentication state and recovery implementation were not copied into the repository.

### Decision: shallow polling, deep Doctor evidence
Manager polling is cached and limited to inexpensive discovery/listener evidence. Protocol initialize, tools/list, safe-call, OAuth and remote checks remain distinct and are supplied by the durable last-Doctor result. This preserves diagnostic fidelity without creating a continuous performance tax.

### Decision: action contracts precede action executors
Stage 6 exposes a fixed allowlist for Start All, Restart, Doctor, Repair and Update but ships with no real executor wired. Later owner stages inject the bounded implementations. This prevents Stage 6 from acquiring arbitrary shell authority or restarting healthy production-like services.

### Risk: stale Doctor evidence
Protocol/OAuth/remote fields may be unknown or stale until Stage 7 writes a fresh Doctor result. The UI must display unknown separately from failed and must never infer protocol health from a listener.

### Risk: workspace binding drift
The shared Coding Tools service was bound to a different repository during Stage 6. Repository writes were therefore moved into a dedicated Git worktree inside the Coding Tools workspace rather than bypassing its path boundary. Future windows must verify workspace binding before writes.
