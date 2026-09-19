# Stage 16 Closure — Concurrency / Session Isolation / Complementary Fallback

CURRENT_STAGE = STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK
NEXT_STAGE = STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP
AFTER_NEXT_STAGE = STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES

Status: CLOSED_LOCAL_VERIFIED

## Owned concern

Make multi-window execution safe without pretending that request concurrency implies shared-state isolation:

- isolate Serena project state by fixed-project process/port slots;
- make Coding Tools workspace/worktree writer boundaries executable;
- serialize native GUI side effects across Remote Desktop Commander and Windows-MCP;
- model Unified Gateway and Remote Desktop Commander as complementary recovery paths;
- prevent recovery loops, duplicate restarts and blind retry after ambiguous mutations.

Stages 1-15 were not reopened. Stage 14's public Gateway/OAuth/Tailscale contract remains unchanged.

## Baseline and preserved WIP

Stage 16 started from:

- Stage 15 product closure: `c8588b9d73e25bb72c01c73656b9df9e993cfaf2`;
- actual opening HEAD: `b7c270451ea0d9a9a23a053d8ac61e505810343d`, one handoff-artifact commit after the product closure;
- branch: `main`;
- upstream state at opening: local main ahead 10 / behind 0;
- package version re-read from `pyproject.toml`: `0.1.0`.

The five pre-existing Stage 17/18 WIP files were preserved and are excluded from Stage 16 ownership/commit:

- `pyproject.toml`;
- `src/webgpt_as_codex/launcher.py`;
- `src/webgpt_as_codex/manager.py`;
- `src/webgpt_as_codex/registry.py`;
- `tests/test_stage12.py`.

No reset, clean, stash, drop, force-push or automatic push was used.

## Implemented

### Serena fixed-project slot isolation

Added `src/webgpt_as_codex/concurrency.py` with `SerenaSlotPool`.

The pool:

- hard-excludes shared port 9121;
- launches one Serena process with an explicit `--project` and isolated loopback port;
- stores machine-local slot receipts outside Git;
- binds project id, owner id, port/endpoint, PID, birth token, image name and launch fingerprint;
- supports idempotent same-owner acquisition;
- reuses a released compatible slot for the same project;
- allocates a separate live slot for another concurrent owner rather than sharing mutable active-project state;
- removes stale receipts only after process-identity evidence shows the recorded worker is gone/mismatched;
- fails closed when no pool port is available;
- releases idempotently;
- destroys only a process whose live identity still matches the slot receipt.

The current CLI flags were verified from the installed Serena executable rather than guessed. The Coding Tools service context initially lacked HOME/USERPROFILE, which made Serena help fail inside `Path.home()`; injecting the resolved user home recovered the same-tool probe.

### Serena current-version/source evidence

Two Serena deployments are currently observable on this machine and were kept distinct:

- the user's already-running shared direct Serena reports version 1.7.0, active project `Jarvis-dev`, language server ready;
- the current CLI-installed executable used for isolated Stage 16 workers self-reported Serena 1.28.1.

The installed 1.28.1 source still contains one `SerenaAgent._active_project`; project switching shuts down the prior active project, while ProjectServer guards temporary active-project context with a lock. Fixed-project process isolation therefore remains required; the premise was not merely inherited from the older 1.7.0 source.

Stage 16 never called shared Serena `activate_project`, never switched its project and never restarted its 9121 process.

### Coding Tools concurrency boundary

Added `CodingWorkspacePolicy`.

- requested paths must be inside the configured workspace;
- read/bounded independent process work does not acquire a writer lease;
- one worktree has one machine-local writer owner at a time;
- another writer for the same worktree is rejected;
- a distinct worktree can hold an independent writer lease;
- no automatic repository copy/worktree creation is performed merely to claim concurrency.

This turns the existing single-writer rule into an executable boundary without redesigning the Coding Tools server.

### Machine GUI lease

Added `MachineGuiLease`, backed by a machine-local JSON lease plus atomic guard.

The lease records:

- owner;
- action;
- acquired time;
- heartbeat time;
- expiry.

A second live owner is rejected. Release is idempotent. An expired lease can be reclaimed. Filesystem/process/terminal work is outside the GUI lease; only native GUI side-effect ownership is serialized.

### Complementary recovery and loop prevention

Added `src/webgpt_as_codex/recovery.py`.

`RecoveryRequest` carries:

- attempt/correlation id;
- component id;
- origin path;
- visited path sequence;
- hop budget.

`RecoveryCoordinator` provides:

- Gateway/public-Gateway/backend failure -> independent RDC selection when available;
- RDC failure -> Gateway selection when available;
- visited-path and hop-budget loop prevention;
- one mutation owner for one component in one recovery attempt;
- diagnose-only behavior when lifecycle authority is absent;
- post-state observation when another path already owns mutation;
- exactly-once mutation behavior after timeout/non-zero ambiguity.

Route ownership, install ownership and runtime lifecycle authority remain separate.

## Real shutdown-race finding and correction

The real isolated Serena probes exposed a Windows process-exit timing issue.

An isolated Serena worker could accept shutdown and disappear shortly afterwards while the existing bounded-stop confirmation still returned a timeout. Treating that timeout as permission to kill again would create a duplicate destructive side effect.

Stage 16 therefore added `_stop_verified_process`:

1. attempt the authorized bounded stop once;
2. if confirmation raises a timeout/error, enter a bounded post-state observation window;
3. repeatedly inspect current process identity;
4. if the original process has exited, accept `post-state-exited`;
5. only if the same live identity remains after the observation window is the stop considered unresolved.

This behavior is covered by unit regression and was generalized into Computer Agent 1.1.16 / R49.

## Test coverage

`tests/test_stage16.py` covers:

- two projects -> distinct fixed Serena slots;
- same project with concurrent owners -> no shared mutable slot;
- released same-project slot -> safe stable reuse;
- stale Serena receipt;
- occupied Serena port;
- hard exclusion of shared 9121;
- shutdown timeout followed by process exit;
- delayed process exit inside bounded post-state observation;
- Coding Tools configured-workspace binding;
- same-worktree writer conflict;
- distinct-worktree writers allowed;
- reads do not acquire a writer lease;
- two GUI owners -> one winner;
- stale GUI lease reclaim;
- idempotent GUI release;
- Gateway -> RDC recovery;
- RDC -> Gateway recovery;
- one component/attempt -> one mutation owner;
- A -> B -> A cycle prevention;
- hop-budget exhaustion;
- ambiguous mutation -> post-state success without retry;
- no lifecycle authority -> diagnose-only.

## Safe real-host evidence

### Shared/production services

Opening listener evidence:

- Gateway 9330 -> PID 77084;
- Windows-MCP 8001 -> PID 50508;
- Playwright 8931 -> PID 53880;
- shared Serena 9121 -> PID 38924.

Final listener evidence kept the same PIDs.

The shared Serena direct connector was `Jarvis-dev` before isolated probing and remained version 1.7.0 / active project `Jarvis-dev` afterwards. This, together with the unchanged 9121 listener PID, is the shared-instance before/after identity evidence for this stage.

No production Gateway/Edge, Coding Tools, Playwright, Windows-MCP or Remote Desktop Commander process was restarted or killed by Stage 16.

### Isolated Serena

Real isolated probe evidence:

- non-9121 loopback worker started from the current Serena CLI with fixed `--project`;
- MCP initialize returned HTTP 200;
- MCP session was established;
- `tools/list` returned 29 tools;
- server info reported Serena 1.28.1;
- temporary ports 9477/9478 were absent at final post-state;
- only Stage 16-created isolated workers/receipts were eligible for cleanup.

The first two cleanup probes intentionally generated the shutdown-race evidence described above. No blind second kill was issued.

A later compound third probe was blocked by the tool safety surface before execution; it was not treated as a product failure and was not bypassed with a broader tool because the existing real-host evidence was already sufficient.

### Remote Desktop Commander / Windows-MCP

Remote Desktop Commander direct connector remained online and a read-only `get_config` probe returned version 0.2.50 and current Windows host evidence.

Windows-MCP direct schema was not exposed in this ChatGPT tool surface, but its registered listener remained live on 8001/PID 50508. No real GUI mutation was needed to validate the shared lease implementation, so Stage 16 did not manufacture mouse/keyboard side effects merely for a demo.

## Validation

Opening baseline:

- Stage 14+15 regression: 31 PASS;
- full repository: 146 PASS;
- Ruff: PASS.

Final gates:

- Stage 14-16 targeted: 52 PASS;
- full repository: 167 PASS;
- Ruff: PASS;
- repository secret scan: `SECRET_SCAN_PASS`;
- `git diff --check`: PASS;
- Computer Agent validator: `VALIDATION_OK`, 49 scenarios;
- path-scoped implementation/docs review: PASS before selective staging;
- no active expected-fail / mandatory RED.

## Computer Agent experience absorption

Machine-local shared Skill advanced:

- version: `1.1.16-local-candidate`;
- updated `.skills/computer-agent/SKILL.md`;
- updated `.skills/computer-agent/workflows/cross-tool.md`;
- updated `.skills/computer-agent/manifest.json`;
- updated `.skills/computer-agent/CHANGELOG.md`;
- added regression R49 in `.skills/computer-agent/evals/scenarios.json`;
- validator: 49 scenarios PASS.

R48 was re-read directly and confirmed present. An earlier `search_text` query returned a false negative; the direct file read plus validator are authoritative here.

Generalized rule: timeout/non-zero after stop/restart/kill is an ambiguous side-effect result. Use bounded listener + PID birth/image post-state observation before considering any additional mutation.

These Computer Agent files live in the shared workspace Skill root and are not part of the WebGPT-as-Codex product Git commit.

## Live document barrier

Before generating the Stage 17 prompt:

- `docs/CURRENT-PROJECT-STATE.md`: UPDATED_WITH_NEW_EVIDENCE;
- `docs/ARCHITECTURE.md`: UPDATED_WITH_NEW_EVIDENCE;
- `docs/DECISIONS-AND-RISKS.md`: UPDATED_WITH_NEW_EVIDENCE;
- `docs/CONCURRENCY-AND-FALLBACK.md`: UPDATED_WITH_NEW_EVIDENCE;
- `docs/ROADMAP-2026-09-20.md`: UPDATED_WITH_NEW_EVIDENCE;
- `skills/webgpt-as-codex/experience-ledger.md`: UPDATED_WITH_NEW_EVIDENCE;
- `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`: CHECKED_NO_CHANGE_REQUIRED — Stage 16 implements the already-canonical concurrency/fallback requirements without changing product intent;
- `docs/DEPLOYMENT.md`: CHECKED_NO_CHANGE_REQUIRED — public deployment/Gateway/OAuth/Tailscale contract did not change;
- `skills/webgpt-as-codex/SKILL.md`: CHECKED_NO_CHANGE_REQUIRED — portable project execution contract already points to the canonical concurrency/fallback SoT;
- Stage 1-15 closures: NOT_APPLICABLE_THIS_STAGE / unchanged.

## Progress

- Stage 16: 100% — LOCAL_IMPLEMENTATION + LOCAL_VERIFIED + REAL_HOST_VERIFIED for isolated Serena and non-mutation host evidence.
- Supplemental roadmap: Stage 13, 14, 15 and 16 closed = 4 of 8 completion/final-acceptance gates, 50% by stage-count, not an effort estimate.
- Stage 17 remains the next owner; Stage 18 and Stage 19 remain planned.
- Global program state remains ACTIVE. The Program Completion Gate is not satisfied.

## Next owner

Stage 17 owns Manager/desktop UX only:

- English + Chinese Manager functional parity;
- default Chinese desktop launcher/current deployment UX;
- environment/deployment/version/Gateway/OAuth/HTTPS/inventory surfaces;
- MCP URL copy/open;
- local OAuth password set/reveal/regenerate;
- add/remove migration-candidate flows;
- action feedback/activity log;
- requested motion tied to functional state;
- accessibility/reduced-motion;
- careful absorption of the five pre-existing Stage 17/18 WIP files without losing user work.

Stage 17 must preserve the Stage 16 concurrency/recovery contracts and continue recursively to Stage 18 after its own verified closure.
