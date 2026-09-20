# STAGE-17 Post-Acceptance Hotfix Closure

Status: CLOSED_LOCAL_VERIFIED

Scope: only the user-reported post-acceptance regressions after the accepted Stage 17 closure. The original `docs/STAGE-17-CLOSURE.md` remains historical evidence and is not rewritten.

## Reproduced failures

1. The real one-click desktop Manager on port 9200 rendered the newer Stage 17 HTML shell, but the long-running Python process still held the pre-Stage-17 route table. `/en`, `/zh`, `/manager.css`, `/manager.js` and `/api/local-config` returned 404.
2. The desktop browser-open path used generic browser dispatch without an explicit normal-user-profile continuity contract. The user observed a new empty Edge experience instead of the expected normal logged-in browser context.

## Root cause

The Manager defect was a mixed-generation runtime: a live listener and shallow health check proved liveness, not that the long-running interpreter had loaded the current Python code. Because the process had no current Runtime Supervisor PID receipt, it was classified as healthy-unmanaged and preserved forever.

On Windows, the venv launcher can also spawn a child base-Python process that becomes the actual listener, so a receipt tied only to the launch wrapper is insufficient service identity.

The browser defect was a responsibility leak: ordinary desktop URL opening and Playwright automation profiles were not explicitly separated.

## Implemented repair

- Manager runtime generation is hashed from the executable Python Manager code plus its required static assets.
- Manager preservation checks the current Stage 17 contract: health, `/en`, `/zh`, `/manager.css`, `/manager.js` and `/api/local-config`.
- A stale repository-owned Manager is refreshed only after PID birth/image ownership proof.
- A stale unmanaged listener may be refreshed only when the listener process strictly matches the WebGPT Manager command identity on 127.0.0.1:9200.
- An unrelated or ambiguous listener on 9200 fails closed and is never killed.
- After startup, the Manager receipt rebinds to the actual listening Python process when a venv wrapper spawned a child listener, while retaining bounded launcher identity for cleanup.
- The desktop opener prefers an already-running Microsoft Edge normal profile, using `Local State.profile.last_used`; if no suitable running Edge session is available, it uses the Windows default URL handler. It never intentionally creates a temp user-data-dir, isolated automation profile or InPrivate session.
- Added `tests/test_stage17_hotfix.py` covering current/stale Manager handling, ambiguous-listener protection, listener-PID receipt rebinding and browser-profile opener behavior.

## Real host acceptance

Before repair:
- port 9200 listener was the old Python Manager process;
- `/` returned the new Stage 17 HTML shell;
- `/en`, `/zh`, `/manager.css` and `/api/local-config` returned 404.

Repair:
- Runtime Supervisor classified the old process as a strictly identified legacy stale WebGPT Manager and replaced it;
- current Manager contract became HTTP 200 for `/`, `/en`, `/zh`, `/manager.css`, `/manager.js`, `/api/local-config`.

Desktop path:
- current Edge user-data `last_used` profile is `Default`;
- the first real Desktop launcher run opened the Manager through the existing normal Edge profile and served Chinese root HTML;
- the second real Desktop launcher run preserved the same listener PIDs for Windows-MCP 8001, Coding Tools 8766, Playwright 8931, Serena 9121, Manager 9200, Gateway 9330 and Edge 9341;
- the existing Edge top-level `Default` process remained the same and no new automation-only profile window was created;
- Windows-MCP live Snapshot observed the foreground `WebGPT-as-Codex Manager` window and the complete Manager control tree.

Serena was not called, restarted or project-switched during this Hotfix.

## Verification

- targeted Hotfix + Stage 8 + Stage 17: `31 passed`;
- full repository: `184 passed`;
- Ruff: PASS;
- repository secret scan: `SECRET_SCAN_PASS`;
- `git diff --check`: PASS;
- Computer Agent Skill: `1.1.17-local-candidate`;
- Computer Agent validator: `VALIDATION_OK`, `files=20 scenarios=51`;
- reusable regressions added: R50 mixed-version long-running service, R51 desktop launcher/browser profile separation.

## Protected invariants

- no broad audit or earlier Stage reopen;
- no unrelated process termination;
- no unsafe `reset`, `clean` or force push;
- no secrets copied into Git;
- healthy core MCPs preserved across launcher idempotence acceptance;
- original `STAGE-17-CLOSURE.md` retained unchanged.

## Next stage

`STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES` remains the next product stage. The Stage 18 worker must inherit the current Computer Agent Skill and this Hotfix closure before touching repository-wide translation/notices work.
