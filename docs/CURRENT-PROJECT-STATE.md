# Current Project State

PROJECT = WebGPT-as-Codex
CURRENT_STAGE = STAGE-8-DESKTOP-LAUNCHER-AND-AUTOSTART
NEXT_STAGE = STAGE-9-GENERIC-ADD-MCP
AFTER_NEXT_STAGE = STAGE-10-LOOP-ENGINEERING-DOGFOOD

Stage 1: CLOSED_LOCAL_VERIFIED
Stage 2: CLOSED_LOCAL_VERIFIED
Stage 3: CLOSED_LOCAL_VERIFIED
Stage 4: CLOSED_LOCAL_VERIFIED
Stage 5: CLOSED_LOCAL_VERIFIED
Stage 6: CLOSED_LOCAL_VERIFIED
Stage 7: CLOSED_LOCAL_VERIFIED

Repository: D:\AgentData\10_Workspaces\webgpt-as-codex
Stage 4 proof: unified Gateway, 4 core MCP backends, 87 tools, safe calls PASS.
Stage 5 proof: real Tailscale HTTPS edge, DCR + PKCE + token + 401 gate + restart + refresh + authenticated MCP call PASS.
Stage 6 proof: repository-owned loopback Manager, registry-backed component status, six-level health schema, Gateway/OAuth/Tailscale/Public-MCP/Doctor surfaces, fixed action contracts, secret/private-URL redaction, 30 tests PASS and Ruff/secret scan PASS.
Stage 7 proof: idempotent discovery-first bootstrap, deep prerequisite-aware Doctor with sanitized machine-local persistence, bounded/confirmable Repair with backups and no arbitrary-command surface, Manager Doctor/Repair executors only, 37 tests PASS, Ruff PASS and secret scan PASS.
Stage 7 live evidence: healthy Serena/Coding Tools/Playwright/Windows-MCP listeners passed MCP initialize + tools/list + declared safe call. Current MCPJungle and default OAuth listeners were truthfully reported down and were not started because runtime lifecycle belongs to Stage 8.

Remaining planned roadmap:
- Stage 8: STAGE-8-DESKTOP-LAUNCHER-AND-AUTOSTART
- Stage 9: STAGE-9-GENERIC-ADD-MCP
- Stage 10: STAGE-10-LOOP-ENGINEERING-DOGFOOD
- Stage 11: STAGE-11-SECURITY-RELIABILITY-HARDENING
- Stage 12: STAGE-12-README-RELEASE-FINAL-ACCEPTANCE
- Final Overall Acceptance

Automatic continuation remains authorized.
The Stage 8 handoff must be generated from the committed Stage 7 HEAD and verified through Playwright MCP.

Recursive handoff invariant:
Every stage window must, after its own verified closure and commit, regenerate a prompt from its new HEAD and use Playwright MCP to submit the following stage. The obligation propagates NEXT -> AFTER_NEXT -> subsequent stages until Final Overall Acceptance is CLOSED_LOCAL_VERIFIED.
