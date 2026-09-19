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

## Self-evolving operating-knowledge plane
WebGPT-as-Codex treats execution experience as an input to the Skill, not as disposable chat history. The operating loop is:
Execute -> Observe -> detect friction -> Diagnose -> Explore alternatives -> Compare -> Select -> Verify -> Record -> Reuse.

This applies to the entire path from SoT loading and stage sizing through routing, MCP usage, implementation, tests, documentation, commit, prompt generation, Playwright submission and next-run verification. Repeated almost-finished behavior, avoidable retries, premature fallback, incomplete docs or failed handoff closure are process defects to diagnose rather than normal tail work.

Operating knowledge is separated by scope:
- routing.md decides WHICH structured capability should own an intent;
- MCP Operating Guides describe HOW to use an MCP from its actual exposed tools/schema, verification signals, failure modes and performance/cost behavior;
- the inventory records what is installed/configured/available and machine-specific facts without turning them into portable Skill rules;
- the Experience Ledger records evidence-backed lessons and provenance;
- one-off incidents stay out of long-term Skill unless they expose a reusable failure mechanism.

Stage 9 owns formal MCP Guide/onboarding productization. Stage 10 owns formal Loop Engineering self-evolution and sizing/closure productization. The rules are active before those stages; those stages make them systematic.

The current stage-duration target is a soft approximately 20-minute execution budget including closure and verified handoff. It is a heuristic, not a hard platform fact. If implementation expansion threatens validation/docs/commit/handoff, split the owner concern rather than borrowing from closure. Baseline evidence from subsequent stages is used to recalibrate the heuristic.

## Manager control plane
The repository-owned Manager is a loopback-only local control surface. Its default bind is `127.0.0.1:9200`; the existing private/reference Manager on port 9199 is evidence only and is neither copied nor mutated.

Manager status is registry-backed. Each component is rendered without its loopback endpoint or raw manifest and keeps these health levels separate: process, listener, protocol, safe-call, OAuth and remote. The Manager performs only bounded cached listener probes itself; deeper protocol/safe-call/OAuth/remote evidence is read from the last Doctor result. This prevents UI polling from becoming an MCP performance tax.

Machine-local Manager configuration lives outside Git under the normal state root. `config/manager.json` may contain a `public_mcp_url`; only credential-free public HTTPS URLs are renderable. Secret-like keys, bearer material and private/loopback URLs are recursively redacted before API/UI output.

The UI lifecycle does not own runtime lifecycle. Closing a tab only removes the browser view. Manager and later runtime supervisors are independent processes, and agent runtimes are not children of the browser UI.

Stage 6 defines fixed action contracts only: Start All, Restart, Doctor, Repair and Update. There is no arbitrary-command endpoint. Mutating contracts require confirmation, POST requests require the same-origin control header, and real executors are injected only by their owner stages: Doctor/Repair in Stage 7, Start/Restart in Stage 8, and Update hardening later.

## Bootstrap / Doctor / Repair
Bootstrap is discovery-first and idempotent. It evaluates component manifests plus live discovery before proposing work. A component with an already healthy listener is preserved. Installed-but-stopped runtimes are reported as deferred to Stage 8 rather than being started by bootstrap. Bootstrap apply only creates/verifies machine-local state layout and persists a sanitized plan; it does not install, start or restart services.

Doctor owns deep, explicit health evidence. Process, listener, MCP protocol, safe call, OAuth and remote remain separate fields. Deeper checks are prerequisite-aware: a failed listener does not create synthetic protocol/safe-call failures, and a listener never proves protocol health. Safe MCP checks use initialize, tools/list and only the manifest-declared safe tool. Network-capable version commands such as `@latest` are skipped; ambiguous banner output falls back to verified manifest version instead of guessing.

Doctor persists `doctor/last-result.json` under the machine-local state root only after recursive sanitization. Raw process command lines, credentials, private URLs and machine-only paths are not repository evidence. The Manager continues to poll shallowly and consumes this durable Doctor result.

OAuth Doctor checks are intentionally read-only. Local metadata can establish local metadata health, but the project still treats real public HTTPS as authoritative for OAuth acceptance. Doctor may validate a configured public HTTPS edge with protected-resource metadata plus the unauthenticated 401 challenge; it does not create DCR clients, tokens or mutate the OAuth database merely to refresh a status screen.

Repair is a fixed allowlist, not a shell. Stage 7 permits only state-layout creation and bounded Manager-config repairs. Mutating use requires confirmation and configuration edits create a machine-local backup first. Runtime recovery remains a diagnostic hint until Stage 8 owns start/restart supervision.

## Runtime lifecycle / desktop launch / autostart
Stage 8 adds a repository-owned runtime supervisor without turning component manifests or the Manager into an arbitrary shell. Lifecycle ownership requires a fixed repository adapter plus a machine-local PID receipt whose PID, process birth token and executable image still match the live process. A stale PID file, dead PID, reused PID or image mismatch is discarded rather than trusted.

Start All is discovery-first. A healthy listener is preserved even when the process is external/unmanaged. Components without listener semantics, such as Tailscale, may be preserved from direct process evidence instead. Only fixed repository-managed adapters may start a missing runtime. Installed/required does not imply lifecycle ownership. The current Stage 8 managed set is the local Manager plus MCPJungle; healthy Serena, Coding Tools, Playwright, Windows-MCP, Tailscale and Remote Desktop Commander remain outside supervisor stop/restart authority.

MCPJungle is started with a machine-local database and machine-local log/PID/state receipts. Stop/restart checks ownership again before signaling, attempts bounded graceful shutdown first and uses a bounded forced fallback only when needed. A healthy unmanaged listener is never restarted. Manager Restart additionally accepts only the explicit repository allowlist; Stage 8 does not expose raw command, argv, path or PID parameters through the HTTP API.

Start All distinguishes action success from full-stack readiness. A repository-managed start can succeed while an enabled required but unmanaged component remains unavailable. This is reported as `complete-with-unmanaged-required` with the missing IDs instead of being silently promoted to a healthy full stack. On the current machine, `mcp-auth-proxy` has only Stage 5 E2E credential state, so Stage 8 deliberately does not reuse that test secret as a production launch contract.

The Windows launcher is a control surface, not a process parent contract. It starts/ensures the Manager and repository-managed runtimes, optionally opens the loopback Manager URL, then may exit while those runtimes continue. Desktop and autostart integration use transparent `.cmd` files in the user Desktop/Startup shell folders. Shell-folder resolution prefers Windows' already-expanded `Shell Folders` values and safely expands/falls back from `User Shell Folders` when service contexts omit `USERPROFILE`/`APPDATA`. Installation is reversible and ownership-checked: an existing unmanaged file is neither overwritten nor deleted, and no password/token/cookie/private URL is embedded.


## Generic MCP onboarding / Operating Guide plane

Stage 9 makes Add MCP discovery-first and separates portable operating knowledge from machine state.

The bounded onboarding chain is:
manifest validation -> credential-literal rejection -> initialize -> tools/list -> capability classification -> Operating Guide validation -> routing recommendation -> dry-run -> explicit machine-local apply.

Capability evidence has four states: success, unavailable, failed and unattempted. Names never establish capability. A reached-but-malformed server is different from an unreachable server, and a skipped prerequisite is different from both.

The machine-local apply path stores custom manifests, machine-readable Guides and onboarding/routing receipts under the external state directory. This makes newly onboarded components visible through the existing registry, Manager and Doctor without committing local endpoint/binding/health information.

Portable Guide documents live with the Skill and may be attached to public-safe component manifests by stable component id. Serena and Coding Tools are the first representative Guide attachments validated from real Stage 9 initialize/tools/list evidence.

Onboarding never creates lifecycle ownership. Stage 8 runtime adapters, PID identity rules and the fixed Manager restart allowlist remain unchanged. Discovery is knowledge/visibility evidence, not permission to start, kill or restart an external MCP.
