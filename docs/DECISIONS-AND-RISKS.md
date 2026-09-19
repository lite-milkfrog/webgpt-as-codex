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

## Cross-stage decision — self-evolving Skill and operating knowledge

Execution is not complete merely because the immediate task worked. Reusable friction must be diagnosed, verified and written back at the narrowest durable layer: general principles to the Skill, MCP-specific behavior to an Operating Guide, machine facts to local inventory/config, and one-off evidence only to the relevant stage/ledger.

Routing and operating knowledge remain distinct. Routing selects the narrowest appropriate capability. An MCP Guide is based on actual exposed schema/capability evidence and teaches correct goal-oriented usage, verification, common misuse and justified fallback. Tool names are never treated as proof of capability.

User guidance is reusable evidence when it exposes a stable operating principle. It does not become a brittle click recipe by default; record the mental model, goal, constraints, verification and failure signals.

### Decision: stage sizing protects closure
The current target is an approximately 20-minute soft stage budget with closure included. This is a planning heuristic derived from observed workflow continuity needs, not a claimed 25-minute platform cutoff. A shorter fully closed stage is preferable to a larger stage that ends before docs/commit/handoff verification.

Collect baseline data over the next 5-10 stages: implementation versus closure effort, files/tests changed, major tool switches/calls, retries/harness failures, docs effort, first-pass handoff success, almost-done incidents and emergency splits. Recalibrate from evidence.

### Risk: self-improvement can bloat or overfit the Skill
Do not append every incident to core rules. Merge duplicates, retire obsolete methods with provenance, move machine details out of portable docs and keep detailed MCP-specific behavior in Guides. Optimize for the fastest known safe/reliable/low-context path without weakening verification.

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

## Stage 7 — Bootstrap / Doctor / Repair

### Decision: bootstrap discovers before it mutates
Bootstrap preserves an already healthy listener and never treats “installed” as permission to restart it. Stage 7 apply is limited to creating/verifying machine-local state directories and persisting the plan. Runtime start/restart remains Stage 8 ownership.

### Decision: health evidence is prerequisite-aware
Process, listener, protocol, safe-call, OAuth and remote are stored independently. Protocol is attempted only after a listener is present; safe-call only after protocol succeeds; OAuth metadata only when its local listener is present; remote only when a valid credential-free public HTTPS endpoint is configured. Unattempted deeper checks remain unknown rather than becoming cascaded failures.

### Decision: Doctor is read-only with respect to OAuth authority
The normal Doctor checks OAuth metadata locally and may probe the configured real HTTPS edge for protected-resource metadata plus the expected unauthenticated 401 challenge. It does not create clients/tokens or mutate OAuth state. Full DCR/PKCE/consent/token/refresh acceptance remains an explicit real-HTTPS integration gate.

### Decision: bounded Repair has no shell surface
Repair accepts only named repository-defined actions. Apply requires explicit confirmation. Manager configuration repairs back up the original machine-local file before replacement/edit. Runtime failures produce targeted hints instead of generic command execution.

### Risk: version probes can lie if arbitrary banner text is parsed
Doctor accepts explicit version-labelled or exact-semver command output and otherwise falls back to verified manifest evidence. This prevents dotted addresses or banner decoration from being reported as versions.

### Risk: live Doctor can correctly be red while the Stage is green
A machine may intentionally have Gateway/OAuth runtime listeners stopped. Stage 7 closure means the diagnostic/bootstrap/repair contracts are verified, not that Stage 7 silently starts later-stage runtimes. Stage 8 owns bringing repository-managed services up.

### Risk: test environment can import the wrong editable worktree
The shared virtual environment points at the canonical repository. Stage 7 tests in the Coding Tools worktree therefore used an explicit worktree `PYTHONPATH`. A missing pytest/module import in the harness is not target-code evidence.

## Stage 8 — Runtime supervisor / launcher / autostart

### Decision: lifecycle ownership requires repository evidence, not process discovery
Finding a matching listener/process is sufficient to preserve a healthy service but not sufficient to stop or restart it. Stage 8 requires a fixed runtime adapter plus a machine-local PID receipt validated against the live process birth token and executable image. PID reuse/stale receipts therefore fail closed.

### Decision: Start All is discovery-first and may be partially ready
Start All preserves healthy listeners and process-only system services before considering starts. It starts only repository-owned missing adapters and reports required-but-unmanaged missing components separately from action success. This prevents a successful MCPJungle start from being mislabeled as proof that the whole OAuth/edge stack is ready.

### Decision: do not promote Stage 5 E2E credentials into autostart authority
The machine contains an mcp-auth-proxy binary and Stage 5 E2E OAuth data, but no separate credential-safe production runtime contract. Stage 8 therefore leaves the stopped proxy unmanaged rather than embedding/reusing a test password, OAuth DB or private key. A later owner may add an explicit credential-reference/config contract with its own security evidence.

### Decision: Manager Restart is narrower than component discovery
The Manager accepts only a named component from a repository-fixed restart allowlist; Stage 8 currently allows MCPJungle. It does not accept arbitrary shell, PID, executable, URL or argv input. Healthy unmanaged components such as Serena cannot be restarted through this action.

### Decision: Windows Startup folder is the bounded autostart mechanism
The project uses a transparent user Startup-folder `.cmd` launcher rather than hidden registry persistence, scheduled tasks or credential-bearing scripts. Install/status/uninstall verify exact managed content (newline-insensitive for Windows text normalization) and refuse to overwrite/delete user-owned files. Windows shell-folder lookup must also work in service/MCP contexts where `USERPROFILE` and `APPDATA` are missing, so it prefers expanded `Shell Folders` registry values and rejects unresolved relative token paths in favor of a known user-home fallback.

### Risk: graceful shutdown is component-dependent
The supervisor first attempts a bounded graceful signal and then applies a bounded forced fallback. Live MCPJungle evidence on Windows required the forced fallback after the graceful window. This is recorded as runtime behavior, not hidden by reporting restart as intrinsically graceful.

### Risk: process evidence is not protocol evidence
Process-only preservation is used only to decide “do not start/kill this unmanaged system service.” It does not promote Tailscale or any MCP to protocol/OAuth/remote health; Doctor continues to own those deeper evidence levels.
