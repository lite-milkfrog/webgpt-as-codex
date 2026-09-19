# Current Project State

PROJECT = WebGPT-as-Codex
CURRENT_STAGE = STAGE-9-GENERIC-ADD-MCP
NEXT_STAGE = STAGE-10-LOOP-ENGINEERING-DOGFOOD
AFTER_NEXT_STAGE = STAGE-11-SECURITY-RELIABILITY-HARDENING

Stage 1: CLOSED_LOCAL_VERIFIED
Stage 2: CLOSED_LOCAL_VERIFIED
Stage 3: CLOSED_LOCAL_VERIFIED
Stage 4: CLOSED_LOCAL_VERIFIED
Stage 5: CLOSED_LOCAL_VERIFIED
Stage 6: CLOSED_LOCAL_VERIFIED
Stage 7: CLOSED_LOCAL_VERIFIED
Stage 8: CLOSED_LOCAL_VERIFIED

Repository: D:\AgentData\10_Workspaces\webgpt-as-codex
Stage 4 proof: unified Gateway, 4 core MCP backends, 87 tools, safe calls PASS.
Stage 5 proof: real Tailscale HTTPS edge, DCR + PKCE + token + 401 gate + restart + refresh + authenticated MCP call PASS.
Stage 6 proof: repository-owned loopback Manager, registry-backed component status, six-level health schema, Gateway/OAuth/Tailscale/Public-MCP/Doctor surfaces, fixed action contracts, secret/private-URL redaction, 30 tests PASS and Ruff/secret scan PASS.
Stage 7 proof: idempotent discovery-first bootstrap, deep prerequisite-aware Doctor with sanitized machine-local persistence, bounded/confirmable Repair with backups and no arbitrary-command surface, Manager Doctor/Repair executors only, handoff explicit-tab selection + active-composer hydration hardening, 41 tests PASS, Ruff PASS and secret scan PASS.
Stage 7 live evidence: healthy Serena/Coding Tools/Playwright/Windows-MCP listeners passed MCP initialize + tools/list + declared safe call. Current MCPJungle and default OAuth listeners were truthfully reported down and were not started because runtime lifecycle belongs to Stage 8.
Stage 8 proof: repository-owned runtime supervisor with PID birth/image ownership checks, stale/reused-PID rejection, discovery-first idempotent Start All, targeted Manager Restart, independent Manager/browser lifetime, reversible credential-free desktop launcher/autostart, 55 tests PASS, Ruff PASS and secret scan PASS.
Stage 8 live evidence: first Start All started only MCPJungle while preserving healthy Serena/Coding Tools/Playwright/Windows-MCP; the second run preserved the same owned MCPJungle without duplication. Process-only evidence preserved Tailscale and Remote Desktop Commander. Targeted MCPJungle restart changed PID after bounded shutdown; Manager rejected restart scope for Serena. Launcher exited while the Manager remained reachable. `mcp-auth-proxy` remains explicitly unmanaged/not started because the machine has Stage 5 E2E credential state but no separate production/autostart credential contract.
Final canonical-launcher dogfood later observed Serena's external listener down. Start All reported it as required/unmanaged missing and did not restart it; this is current external-service health drift, not repository lifecycle ownership. The same dogfood exposed a service-context shell-folder expansion defect, which was corrected and re-probed to resolve the real user Desktop/Startup paths even when `USERPROFILE`/`APPDATA` are absent.

Cross-stage supplemental contract is active immediately:
- the Computer Agent / WebGPT-as-Codex Skill self-evolves from real execution evidence across the whole chain, not only MCP usage;
- repeated friction follows Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse;
- routing decides WHICH capability to use, while MCP Operating Guides teach HOW to use the selected capability correctly from actual exposed tools/schema and verification evidence;
- one preferred-tool failure is not proof that the tool is unavailable; diagnose misuse, binding, session, auth, schema and harness state before justified fallback;
- user guidance that reveals a reusable operating principle is experience input and is classified into Skill, MCP Guide, machine-local inventory/config or one-off evidence;
- Stage sizing currently uses an approximately 20-minute soft execution budget including closure/handoff, not a claimed platform timeout. Shorter fully closed stages are preferred over unfinished closure, and bounded sub-stages are allowed when closure is at risk;
- the next 5-10 stages collect stage-cost baseline evidence (implementation/closure effort, retries, tool switches, tests/docs, handoff first-pass success and almost-done incidents) so the heuristic can self-correct.

Remaining planned roadmap:
- Stage 9: STAGE-9-GENERIC-ADD-MCP
- Stage 10: STAGE-10-LOOP-ENGINEERING-DOGFOOD
- Stage 11: STAGE-11-SECURITY-RELIABILITY-HARDENING
- Stage 12: STAGE-12-README-RELEASE-FINAL-ACCEPTANCE
- Final Overall Acceptance

Automatic continuation remains authorized.
The Stage 9 handoff must be generated from the committed Stage 8 HEAD and verified through Playwright MCP.

Supplemental ownership:
- Stage 9 productizes MCP Guide template/onboarding, capability discovery, inventory/routing attachment and guide validation/feedback.
- Stage 10 productizes self-evolving Loop Engineering, stage sizing/closure budget, context/execution-window resilience, recursive Playwright continuation and handoff failure recovery. Bounded follow-up stages are allowed if evidence justifies them.

Recursive handoff invariant:
Every stage window must, after its own verified closure and commit, regenerate a prompt from its new HEAD and use Playwright MCP to submit the following stage. The obligation propagates NEXT -> AFTER_NEXT -> subsequent stages until Final Overall Acceptance is CLOSED_LOCAL_VERIFIED.
