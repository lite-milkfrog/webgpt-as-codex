# Stage 4 Closure — Unified Gateway POC

Result: CLOSED_LOCAL_VERIFIED

## Implemented
- Installed MCPJungle 0.4.5 from the official GitHub release into machine-local state.
- Verified the Windows x86-64 ZIP against the official release SHA-256 checksum before extraction.
- Added reusable MCP JSON-RPC helpers and a bounded MCPJungle lifecycle adapter.
- Built a real integration harness that starts temporary isolated Serena and Playwright instances, registers those plus live Coding Tools and Windows-MCP, validates the unified tool catalog, performs safe calls, then terminates temporary processes.
- Kept the existing production-like Funnel/OAuth stack untouched.

## Real E2E evidence
Unified Gateway tools/list returned 87 tools.
The following calls passed through the same MCPJungle /mcp endpoint:
- serena__get_current_config
- coding__server_info
- windows__DisplayInventory
- playwright__browser_tabs action=list

Final marker: STAGE4_GATEWAY_E2E_PASS

## Corrected upstream truth
Official GitHub Releases currently verify MCPJungle 0.4.5 as latest.
A third-party SourceForge mirror exposed a 0.4.6 artifact, but mirror-only versions do not override official upstream truth.

## Runtime evidence
The existing Serena backend on local port 9121 became unresponsive to fresh local initialize calls during Stage 4 while the connected Serena tool path remained usable.
Stage 4 did not restart that production-like service.
The existing Playwright port 8931 also became unavailable later in the run.
Both were replaced only inside the test harness by bounded temporary instances.

## Protected lessons
- Official upstream release truth outranks third-party mirrors.
- Installed-by-PATH, listener health, protocol health and active tool-session health are separate states.
- A temporary Serena must start with --project instead of changing shared active-project state through a tool call.
- Playwright may bind as localhost even when 127.0.0.1 was requested; use its actual listening host.
- Service contexts may lack Windows path environment variables; discover and pass browser executable paths explicitly.
- Browser snapshot can hang while narrower tab enumeration works; choose the narrowest safe diagnostic call.
- Integration tests should own and clean up temporary subprocesses rather than mutate working services.

## Gates
- repository unit tests: PASS
- Gateway 4-backend real E2E: PASS
- secret scan: PASS
- git diff --check: PASS

CURRENT_STAGE = STAGE-5-OAUTH-AND-TAILSCALE-EDGE
NEXT_STAGE = STAGE-6-MANAGER-CONTROL-PLANE
AFTER_NEXT_STAGE = STAGE-7-BOOTSTRAP-DOCTOR-REPAIR
