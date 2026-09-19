# Stage 7 Closure — Bootstrap / Doctor / Repair

Result: CLOSED_LOCAL_VERIFIED

## Implemented
- idempotent discovery-first bootstrap plan that preserves healthy listeners and defers runtime starts to Stage 8;
- machine-local bootstrap plan persistence without service installation/restart;
- deep Doctor with bounded version, process, listener, MCP initialize/tools-list, declared safe-call, OAuth metadata and optional public HTTPS remote checks;
- prerequisite-aware health truth so a listener is never promoted to protocol proof and unattempted deeper checks do not become cascading failures;
- sanitized atomic `doctor/last-result.json` persistence outside Git;
- bounded Repair allowlist with dry-run, explicit confirmation, targeted hints and backup-before-config-edit semantics;
- Manager wiring for Doctor/Repair only; Start All/Restart/Update remain owned by later stages;
- manifest discovery support for machine-local binaries and process markers without embedding machine-private paths.

## Validation
Narrow Stage 7/Manager tests: PASS.
Full repository tests: 37 PASS.
Ruff: PASS.
Secret scan: PASS.

Bootstrap was run twice with apply enabled. Both runs preserved the already healthy Serena, Coding Tools, Playwright and Windows-MCP listeners, made no service mutation, and deferred installed-but-stopped runtimes to Stage 8.

Live Doctor verified MCP initialize + tools/list + declared safe call for Serena, Coding Tools, Playwright and Windows-MCP. Tailscale process/version evidence was healthy. The current machine truthfully reported the default MCPJungle listener/process down and the default OAuth listener down. No runtime was started or restarted because that lifecycle belongs to Stage 8.

Doctor persisted only sanitized machine-local evidence. No public MCP URL was configured, so remote evidence remained unattempted rather than being guessed. Repair dry-run found no safe automatic config repair and returned only targeted runtime hints; no mutation was performed.

## Failure/harness lessons
- Coding Tools was still bound to `coding-tools-mcp-demo`; Stage 7 therefore used an isolated Git worktree under that authorized workspace.
- the shared virtual environment editable install pointed at the canonical tree, so worktree tests used an explicit source path rather than modifying the shared environment.
- a first version parser accepted address-like banner text; the parser was tightened and regression-tested.

## Ownership boundary
Stage 7 does not own service startup, restart, launcher/autostart or browser/runtime lifecycle. Those remain Stage 8 work. It also does not repeat Stage 5 OAuth DCR/PKCE/token database mutation merely to refresh Doctor.

CURRENT_STAGE = STAGE-8-DESKTOP-LAUNCHER-AND-AUTOSTART
NEXT_STAGE = STAGE-9-GENERIC-ADD-MCP
AFTER_NEXT_STAGE = STAGE-10-LOOP-ENGINEERING-DOGFOOD

## Recursive handoff invariant
Stage 8 must close and commit its own work, regenerate Stage 9 from that new HEAD, validate/hash it, and Playwright-submit it with sent-message + assistant-run proof. Every later stage repeats the same protocol through Stage 12 and Final Overall Acceptance.
