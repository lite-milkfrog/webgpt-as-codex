# Stage 13 Closure — Supplemental SoT / Deployment Foundation

CURRENT_STAGE = STAGE-13-SUPPLEMENTAL-SOT-DEPLOYMENT-FOUNDATION
NEXT_STAGE = STAGE-14-PRODUCTION-UNIFIED-GATEWAY-EDGE
AFTER_NEXT_STAGE = STAGE-15-COMPONENT-INSTALL-UPGRADE-LIFECYCLE

Status: CLOSED_LOCAL_VERIFIED

## Owned concern

Reopen only the post-TERMINAL product delta needed to make WebGPT-as-Codex a one-repository deployment authority, and establish fresh-machine prerequisite/provision foundations without mutating healthy existing MCP services.

## Implemented

- Added the canonical supplemental product goals, deployment contract, concurrency/fallback contract and supplemental roadmap.
- Added dedicated third-party/upstream notice location outside product-oriented README prose.
- Added Windows/Python/winget/Tailscale environment reporting.
- Tailscale evidence now distinguishes install/version/backend/login/online/DNS/Funnel readiness.
- Added an allowlisted Tailscale winget install path for a missing installation; existing healthy installs are preserved.
- Added WebGPT-owned runtime provisioning for MCPJungle and mcp-auth-proxy from approved official release assets with SHA-256 verification.
- Provisioning preserves existing binaries by default.
- Bootstrap can persist the expanded environment report, optionally install missing Tailscale and optionally provision the WebGPT-owned runtime binaries.
- Added Stage 13 tests for environment-state truth, boolean blocking semantics, preserve behavior and bootstrap orchestration.
- Recorded the observed concurrency facts that drive Stage 16:
  - standard Serena has process-wide active-project state and shuts down the previous project on project switch;
  - Coding Tools can have overlapping server-managed command execution while remaining bound to one configured workspace.

## Boundaries preserved

- Existing healthy Serena, Coding Tools, Playwright, Windows-MCP, Tailscale and Remote Desktop Commander services were not reinstalled or reconfigured by Stage 13.
- No third-party MCP source tree was copied wholesale into the repository.
- No OAuth password, token, private URL, account state or machine secret entered Git.
- Production Edge/Gateway lifecycle promotion remains Stage 14 ownership.
- Generic third-party MCP install/upgrade adapters remain Stage 15 ownership.
- Serena multi-instance/project-slot isolation and complementary recovery remain Stage 16 ownership.
- Final Manager UX/bilingual desktop experience remains Stage 17 ownership.

## Validation

- Stage 13 narrow tests: 7 PASS.
- Affected Stage 7/8/11/12/13 regression: 44 PASS.
- Full repository tests on the current supplemental worktree: 115 PASS.
- Ruff: PASS after removing silent broad Edge cleanup and formatting imports in the adjacent WIP.
- Secret scan: PASS; the scanner was not weakened.
- `git diff --check`: PASS.
- Real local bootstrap probe reported the current host `ready_for_edge=true` with Tailscale online/Funnel evidence and preserved existing WebGPT runtime binaries.

## Contradictory evidence handled

No accepted Stage 1-12 implementation was reopened. The only reopened scope is the new user-requested supplemental roadmap.

## Next owner

Stage 14 promotes the already-started production Edge/Gateway scaffolding into a tested, restart-safe production contract with route synchronization, OAuth secret lifecycle and Tailscale HTTPS publication.
