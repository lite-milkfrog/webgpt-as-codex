# Stage 8 Closure — Desktop Launcher / Runtime Supervisor / Autostart

Result: CLOSED_LOCAL_VERIFIED

## Implemented
- repository-owned runtime supervisor with fixed adapters for the local Manager and MCPJungle;
- machine-local PID/log/runtime-state receipts outside Git;
- PID ownership validation using process birth identity plus executable-image checks before stop/restart;
- stale/dead/reused PID rejection and duplicate-listener/process avoidance;
- discovery-first Start All that preserves healthy unmanaged listeners and process-only system services;
- truthful partial-readiness reporting when an enabled required component is unavailable but not lifecycle-owned;
- bounded shutdown/restart with graceful attempt followed by bounded forced fallback when required;
- Stage 8 Manager executors for Start All and Restart only; Update remains unavailable;
- explicit Manager restart component scope with no arbitrary command/PID/path/argv surface;
- Windows launcher that ensures Manager/runtime state and may exit independently of browser/UI/runtime lifetime;
- reversible Desktop and Startup-folder launcher install/status/uninstall with exact managed-content ownership checks and no embedded credentials;
- CLI routes for status/start/stop/restart/launcher/desktop-launcher/autostart.

## Lifecycle ownership boundary
Discovery is evidence to preserve a healthy service, not authority to terminate it.

Stage 8 lifecycle-owned processes require:
1. a fixed repository adapter;
2. a machine-local PID receipt;
3. a live matching PID;
4. the same process birth token;
5. a compatible executable image.

Serena, Coding Tools, Playwright, Windows-MCP, Tailscale and Remote Desktop Commander remain unmanaged by stop/restart even when discovered healthy. MCPJungle is currently Manager-restartable. The Manager itself is launcher/supervisor-managed but is not self-restarted through its own HTTP request.

The current machine has an mcp-auth-proxy binary plus Stage 5 E2E OAuth data but no separate production/autostart credential contract. Stage 8 therefore does not reuse a test password, OAuth database or private key merely to make Start All appear fully ready.

## Live Windows evidence
- process birth-token/image probe passed after explicitly importing Windows ctypes types;
- first Start All started only missing repository-owned MCPJungle and preserved healthy external MCP services;
- second Start All preserved the same owned MCPJungle without creating a duplicate;
- process evidence preserved Tailscale and Remote Desktop Commander despite no listener contract;
- targeted MCPJungle restart changed the owned PID and restored its listener;
- live MCPJungle ignored the graceful window on this host, so bounded forced shutdown fallback was used and reported truthfully;
- Manager actions showed Start All/Restart/Doctor/Repair available and Update unavailable;
- Manager rejected Restart for Serena with invalid-component-scope;
- Manager accepted targeted MCPJungle Restart only;
- launcher process exited while Manager remained reachable and responsive, proving launcher/browser lifetime independence.

## Validation
- Stage 8 lifecycle/launcher tests cover unmanaged preservation, stale/reused PID handling, duplicate prevention, bounded stop/restart, fixed Manager scope, reversible launcher/autostart and UI/runtime lifetime independence.
- Full repository tests: 56 PASS.
- Ruff: PASS.
- Secret scan: PASS.
- Live Start All: idempotent and discovery-first.
- Live Manager action boundary: PASS.
- Live Windows PID identity probe: PASS.

## Failure / operating lessons
- Serena initial-instructions/config calls timed out at the orchestration layer; this was treated as harness/session evidence rather than proof Serena was unavailable.
- Coding Tools remained bound to coding-tools-mcp-demo, so Stage 8 used a dedicated worktree inside that authorized workspace instead of bypassing policy.
- Coding Tools default Python lacked pytest. The known shared venv was reused with explicit worktree PYTHONPATH to avoid importing the canonical editable tree.
- Mocked tests initially missed that ctypes.wintypes required an explicit import on this host; a real Windows identity probe is now part of the evidence.
- Windows text newline normalization initially caused a project-created .cmd file to look unmanaged; ownership comparison now normalizes line endings while still requiring complete managed content.
- final canonical launcher dogfood exposed that Desktop Commander service context had no USERPROFILE/APPDATA while registry User Shell Folders still contained those tokens; the first install therefore landed in a literal token-relative directory. Only the two Stage 8-created launcher files/tree were removed, shell-folder resolution was hardened, and a real host-context re-probe resolved absolute C:\Users\... Desktop/Startup paths before reinstallation.
- final real installation succeeded at the resolved user Desktop; autostart then passed an install/status/uninstall/absent/reinstall/present round trip and was left installed/managed. The earlier literal-token directory remained absent.
- the first Stage 9 Playwright handoff attempt did not submit any text: ChatGPT's hidden fallback textarea still carried an active/autofocus snapshot marker, so browser_type timed out before fill. This contradictory live evidence reopened only the handoff composer-selection boundary. The helper now focuses a DOM-visible editable composer before accepting a fresh active snapshot ref.
- listener discovery alone was insufficient for Tailscale/system transports; process evidence was factored into shared discovery without promoting it to protocol health.
- final canonical launcher dogfood also observed Serena's external listener down. The supervisor correctly reported it as required/unmanaged missing and did not convert discovery into restart authority.

## Stage sizing evidence
This stage stayed one coherent runtime/launcher concern but required several closure-critical iterations:
- isolated worktree setup because of workspace binding;
- runtime + launcher implementation;
- narrow and full tests;
- two live Windows safety probes/fixes;
- repeated real Start All and targeted Restart;
- live Manager HTTP boundary verification;
- architecture/state/decision/Skill/ledger documentation;
- commit and verified Playwright handoff still remain mandatory post-document steps.

This supports the existing rule that closure/handoff budget must be protected and that host-level lifecycle safety cannot be inferred from mocked unit tests alone.

CURRENT_STAGE = STAGE-9-GENERIC-ADD-MCP
NEXT_STAGE = STAGE-10-LOOP-ENGINEERING-DOGFOOD
AFTER_NEXT_STAGE = STAGE-11-SECURITY-RELIABILITY-HARDENING

## Recursive handoff invariant
After this Stage 8 closure is committed, generate Stage 9 from that exact committed HEAD, validate/hash the prompt, and submit it through the existing authenticated Playwright MCP context. Stage 9 must then repeat the same protocol for Stage 10, and every later stage continues recursively through Final Overall Acceptance.
