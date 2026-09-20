# Supplemental Final Acceptance Closure

STATUS = CLOSED_LOCAL_VERIFIED + REAL_HOST_VERIFIED
CURRENT_STAGE = SUPPLEMENTAL-FINAL-ACCEPTANCE
NEXT_STAGE = GLOBAL_LOOP_COMPLETE
AFTER_NEXT_STAGE = TERMINAL
ENTRY_HEAD = 95a4e42004d20f13d09e9d5aec9829e66ec0b2e3
DESKTOP_REBOOT_REPAIR_COMMIT = 369beee9cc782a8f46da8575404ffce52de9ddbf
RDC_RECOVERY_CLOSURE_COMMIT = c3947132c00a0f791cfe0928c1f5eb089d762f21
RDC_INTEGRATED_MAIN_COMMIT = 963efdafb43ab6850fe43aaad91fca96bba01953
STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2

## Scope

This acceptance closes the post-Stage19 supplemental work only. It does not reopen the already accepted Stage 1-19 program.

Owned reconciliation:
- Windows reboot/startup recovery and false-ready prevention;
- one-click Desktop launcher behavior and browser continuity;
- Remote Desktop Commander recovery-plane truth;
- unified release/local Agent Skill 1.2.0;
- final installed-artifact and real-host acceptance;
- final Source of Truth reconciliation.

## Desktop / reboot recovery

The reboot incident exposed a real startup race: Windows login can occur before Tailscale/public-edge prerequisites are ready. The runtime now performs a bounded prerequisite wait before starting the OAuth Edge, remains fail-closed on timeout, and Doctor exposes sanitized prerequisite context when the Edge cannot start.

The Desktop launcher is user-triggered and uses --open; Windows-login autostart and Agent acceptance use --no-open. Manual browser opening uses the user's ordinary Windows browser path and best-effort foreground activation. Focus failure does not convert a healthy WebGPT runtime into failure.

Real host acceptance:
- Start All run 1: ok=true, fully_ready=true, required_unmanaged_missing=[];
- Start All run 2: ok=true, fully_ready=true, required_unmanaged_missing=[];
- Manager PID remained 37400;
- OAuth Edge PID remained 42036;
- Gateway PID remained 34744;
- Doctor status=pass, required_failures=[], warnings=[], component_count=8;
- public protected-resource status=200;
- public unauthenticated MCP status=401 with OAuth challenge;
- Desktop launcher installed=true, managed=true, upgradeable=false;
- autostart installed=true, managed=true, upgradeable=false;
- manual Desktop run recorded browser_open_requested=true and browser_open_dispatched=true via windows-default-url-handler.

No second destructive Windows reboot was forced for this final closure. A real reboot had already occurred and exposed the defect; the repaired recovery path was then verified on the real post-reboot host with repeated idempotent Start All and Doctor. This closure does not manufacture a second cold-reboot claim.

## Machine-local Desktop overlay boundary

The canonical release does not contain current-host-specific integrations.

The manual Desktop launcher exposes one fixed post-READY local extension point:

%LOCALAPPDATA%\WebGPT-as-Codex\local-launcher-overlay.cmd

Rules:
- the file is machine-local and absent from a fresh release;
- the release package does not know the integration-specific content;
- the overlay runs only after WebGPT is already READY;
- overlay failure does not downgrade WebGPT READY;
- Windows-login autostart does not invoke the overlay.

The current host uses that overlay for CloudBase restoration. CloudBase configuration, environment identity and local registration state remain outside Git and outside the release package. This current-host addition was verified locally and is explicitly NOT release content.

## Remote Desktop Commander

RDC remains an independent complementary full-machine repair/control plane.

Final accepted model:
- installation = VERIFIED;
- local process = VERIFIED;
- control plane = VERIFIED;
- transport_broadcast_v1 = VERIFIED;
- execution plane = VERIFIED.

A device record that is visible/authenticated/online is not execution proof. Real connector-side acceptance previously passed list_devices, ping -> pong, get_config and a read-only host probe on the fixed 0.2.51 runtime.

WebGPT and RDC may repair one another only when the selected repair executor is itself healthy and holds the needed lifecycle authority. Recovery is attempt-scoped, one-owner and non-recursive.

Canonical RDC evidence: docs/RDC-FINAL-RECOVERY-PLANE-CLOSURE.md.

## Unified Agent Skill 1.2.0

The release/local Skill split is now explicit:

- skills/computer-agent/ = canonical portable Computer Agent core;
- skills/webgpt-as-codex/ = WebGPT-as-Codex product specialization;
- local .skills/computer-agent/ = the same portable core plus machine-local environment/inventory/state overlays.

Both release profiles are version 1.2.0.

Portable release content preserves:
- the complete Computer Agent routing/permission/workflow model;
- 53 regression scenarios;
- Loop Engineering / Zero-Guess / recursive handoff rules;
- Windows GUI and WeChat/QQ field experience;
- MCP Guides;
- RDC four-layer health rules;
- the complete WebGPT-as-Codex Experience Ledger.

The Computer Agent and WAC product Experience Ledger are byte-identical at acceptance.

Machine-local environment, MCP inventory, state, secrets, credentials, transient health and current-host launcher overlays remain outside the portable release core.

Local validation:
- PORTABLE_SKILL_SYNC_OK;
- VALIDATION_OK;
- required files=26;
- scenarios=53;
- local Skill version=1.2.0.

A new drift regression protects this boundary: portable release/local rules, workflows, evals and reusable experience must be synchronized in the same closure rather than allowed to diverge.

## Installed artifact acceptance

A fresh wheel built from the final source is installed into an external venv and must retain the same public portable knowledge as the source release.

Verified installed artifact contract before the final closure rebuild:
- package version 0.1.0;
- Computer Agent Skill version 1.2.0;
- WAC Skill version 1.2.0;
- 53 Computer Agent scenarios;
- Experience Ledger byte match=true;
- RDC Operating Guide present;
- Chinese WAC Skill profile present.

The final closure rebuild re-runs this installed-artifact check after all live documentation/coverage updates.

## Validation

Pre-closure final code gate:
- targeted Desktop/Reboot/RDC/Skill regression: 52 PASS;
- full repository: 225 PASS;
- Ruff: PASS;
- SECRET_SCAN_PASS;
- git diff --check: PASS;
- portable Skill sync: PASS;
- local Skill validator: PASS.

Final post-documentation repository gate: 225 PASS; Ruff PASS; SECRET_SCAN_PASS; git diff --check PASS; PORTABLE_SKILL_SYNC_OK.

FINAL_WHEEL_SHA256 = 3082f5e1d8db3a5e3dc1565ee4574917b7c5806fb146e840a9e2add6c2b5cd17
FINAL_WHEEL_SIZE = 339894 bytes

## Documentation reconciliation

UPDATED_WITH_NEW_EVIDENCE:
- README.md / README.zh-CN.md;
- docs/ARCHITECTURE.md / docs/zh-CN/ARCHITECTURE.md;
- docs/DEPLOYMENT.md / docs/zh-CN/DEPLOYMENT.md;
- docs/DECISIONS-AND-RISKS.md / docs/zh-CN/DECISIONS-AND-RISKS.md;
- docs/CURRENT-PROJECT-STATE.md / docs/zh-CN/CURRENT-PROJECT-STATE.md;
- docs/TRANSLATION-COVERAGE.json / docs/TRANSLATION-COVERAGE.md;
- skills/computer-agent/*;
- skills/webgpt-as-codex/SKILL.md and manifest;
- skills/webgpt-as-codex/experience-ledger.md;
- relevant tests and packaging declarations.

CHECKED_NO_CHANGE_REQUIRED:
- canonical public HTTPS/OAuth identity from Stage19;
- Stage1-19 historical closure evidence;
- external MCP lifecycle ownership rules;
- Apache-2.0 authoritative LICENSE bytes.

NOT_APPLICABLE_THIS_STAGE:
- new product feature stages;
- destructive production OAuth migration;
- second forced cold reboot;
- Git push/deployment beyond the user's local acceptance scope.

## Program completion gate

All mandatory Stage 1-19 work and the authorized Supplemental Final Acceptance ownership are closed. No active RED/expected-fail remains. The product has a verified one-click Desktop path, reboot recovery contract, production Gateway/OAuth evidence, complementary RDC repair plane, synchronized Agent Skill release/local model, clean repository gates and a fresh installed-artifact acceptance.

PROGRAM_STATE = GLOBAL_LOOP_COMPLETE
NEXT_STAGE = TERMINAL
AFTER_NEXT_STAGE = TERMINAL

No further development handoff is required unless new contradictory evidence or a new user requirement appears.
