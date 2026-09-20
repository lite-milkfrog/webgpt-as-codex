# Concurrency and Complementary Fallback

[**English**](CONCURRENCY-AND-FALLBACK.md) | [简体中文](zh-CN/CONCURRENCY-AND-FALLBACK.md)

## Why Serena collides across ChatGPT windows

The currently installed Serena implementation uses one `SerenaAgent` per standard MCP server process and that agent stores a single process-wide `_active_project`.

Observed installed-source behavior:
- activating a different project shuts down the previously active project before switching;
- `active_project_context` temporarily overwrites the same agent field;
- Serena's separate read-only ProjectServer explicitly documents that active project is process-wide state and uses `_active_project_lock` around project-scoped tool execution.

Therefore two ChatGPT conversations that share the same standard Serena MCP process can race project activation. One window can move the active project out from under the other. This is a backend state-sharing issue, not a ChatGPT-window limitation.

### Required WebGPT solution

Do not make one mutable Serena MCP process the universal parallel backend.

Support a Serena pool:
- one fixed-project Serena instance per active project slot, each on its own loopback port/state identity; or
- a read-only multi-project ProjectServer path for operations that it supports.

Gateway routing must bind a request/task/project to a stable Serena slot. A slot may be reused after its owner task releases it. Project switching inside a shared slot is not a safe concurrency primitive.

## Coding Tools concurrency

Coding Tools has a different model.

A server process is configured with one workspace. Multiple commands/processes can be active at the same time; current live testing launched two server-managed commands whose execution windows overlapped, proving at least bounded concurrent execution rather than a strict one-command global mutex.

That does not make concurrent writes to the same working tree safe.

Policy:
- independent reads/processes may run concurrently;
- one file has one writer at a time;
- parallel coding writers use separate Git worktrees/workspaces;
- destructive/shared Git operations are serialized;
- a single Coding Tools instance does not magically provide per-conversation workspace isolation.

For unrelated projects, prefer one Coding Tools instance per workspace/project binding or a future workspace-pool adapter.

## Remote Desktop Commander concurrency

Remote Desktop Commander supports independent terminal sessions and filesystem/process operations, so multiple logical tasks are possible.

However the physical GUI is a shared singleton resource:
- mouse;
- keyboard;
- foreground window;
- clipboard-sensitive workflows;
- native modal dialogs.

Therefore:
- filesystem/process/terminal work may overlap when targets are independent;
- GUI side effects are serialized by a machine-level GUI lease;
- after any GUI state mutation, reacquire visual/UI evidence.

## Windows-MCP and Playwright

Windows-MCP follows the same shared-native-GUI rule.

Playwright may parallelize across independent pages/contexts, but actions against one page/profile/login state must have one writer/owner at a time.

## Complementary fallback

The two top-level ChatGPT control paths are deliberately independent:

```text
A. ChatGPT -> WebGPT Unified Gateway -> structured MCP backends
B. ChatGPT -> Remote Desktop Commander -> host filesystem/process/terminal/GUI
```

### Gateway/backend failure -> Remote Desktop Commander rescue

When A is unavailable or a routed backend is unhealthy while B remains healthy:
1. classify public-edge vs Gateway vs backend failure;
2. use Remote Desktop Commander to inspect the local WebGPT/backend process, logs, ports and state;
3. perform only an allowlisted recovery action or invoke the repository CLI;
4. verify listener/protocol health;
5. retry the structured Gateway path.

### Remote Desktop Commander failure -> Gateway rescue

When B is unavailable while A remains healthy:
1. use Gateway-routed Windows-MCP/Coding Tools/WebGPT control capability as appropriate;
2. inspect the Remote Desktop Commander runtime/process;
3. recover only where lifecycle authority and safety policy permit;
4. verify Remote Desktop Commander reconnects before depending on it.

### Hard limitation

If the entire public WebGPT endpoint is unreachable, that same endpoint cannot rescue itself. The Agent must choose the independent Remote Desktop Commander path or a local human action.

Likewise, Remote Desktop Commander cannot be assumed to rescue a machine that is offline/unpaired at the vendor relay layer.

## Recovery rules

- preferred structured capability first;
- diagnose before fallback;
- fallback does not weaken auth/security;
- one external side effect is attempted once, then post-state is queried;
- recovery actions require evidence and bounded ownership;
- never let two recovery paths restart the same component simultaneously.

## Stage 16 implementation

### Serena fixed-project slots

`src/webgpt_as_codex/concurrency.py` implements a machine-local `SerenaSlotPool`.

- port 9121 is a hard exclusion and can never be placed in the managed pool;
- each managed slot has a fixed project, isolated loopback port, owner id, PID, birth token, image name and launch fingerprint;
- a live slot cannot be stolen from another owner;
- a released compatible slot may be reused for the same project;
- concurrent owners of the same project receive distinct live slots rather than sharing mutable active-project state;
- stale process receipts are removed only after process-identity mismatch/death evidence;
- an occupied candidate port is skipped/fails closed rather than being taken over;
- release is idempotent and destroy only targets a process whose receipt still matches live process identity.

The current CLI-installed Serena used by the real isolated Stage 16 probe self-reported version 1.28.1. Its installed source still stores one `SerenaAgent._active_project`, shuts down the prior active project when switching, and serializes ProjectServer active-project context with a lock. The already-running shared direct Serena is a separate 1.7.0 instance and remained on active project `Jarvis-dev`. The isolation requirement is therefore current across both the observed shared deployment and the newer CLI source.

### Coding Tools writer boundary

`CodingWorkspacePolicy` represents the configured workspace explicitly. Read/bounded independent process work does not take a writer lease. A writer must acquire a machine-local lease keyed by worktree identity; a second owner is rejected until release/expiry, while a distinct worktree can have an independent writer. Paths outside the configured workspace fail with a binding mismatch rather than mutating an unintended tree.

### Machine GUI lease

`MachineGuiLease` serializes native GUI side effects shared by Remote Desktop Commander and Windows-MCP. The lease records owner, action, acquisition/heartbeat time and expiry, supports idempotent release, rejects a second active owner and reclaims only an expired stale lease. Filesystem/process/terminal work does not need this GUI lease.

### Complementary recovery coordinator

`src/webgpt_as_codex/recovery.py` implements attempt-scoped routing and mutation ownership:

- Gateway/public-Gateway/backend failure may select independent Remote Desktop Commander when available;
- Remote Desktop Commander failure may select the healthy Gateway path;
- visited-path tracking and hop budget block A -> B -> A loops;
- one component/attempt has one mutation owner even if both paths observe the same failure;
- no lifecycle authority returns diagnose-only;
- mutation timeout/non-zero is followed by bounded post-state inspection and never authorizes a blind duplicate restart;
- a second path that did not win mutation authority may observe that the first path already recovered the component and return recovered-by-other-path without mutating.

## Stage 16 verification evidence

- Stage 14-16 regression: 52 PASS.
- Full repository: 167 PASS.
- Ruff, repository secret scan and `git diff --check`: PASS.
- Real isolated Serena MCP: initialize 200 and `tools/list=29` on non-9121 loopback slots; temporary probe listeners were absent at final post-state.
- Shared/production listeners stayed on their baseline PIDs after the probe: Serena 9121 = 38924, Playwright 8931 = 53880, Windows-MCP 8001 = 50508, Gateway 9330 = 77084. Shared Serena's direct configuration also remained 1.7.0 / active project `Jarvis-dev`.
- Remote Desktop Commander direct connector remained available and returned read-only host/config evidence; no GUI business mutation was required.
- Computer Agent Skill 1.1.16-local-candidate: `VALIDATION_OK`, 49 scenarios.

The real Serena cleanup probe also produced the Stage 16 shutdown-race lesson: the first bounded stop confirmation can time out even though the isolated process exits shortly afterwards. The final implementation therefore observes post-state for a bounded window before deciding that a new mutation could be necessary.

## Stage 19 — self-restart control-plane recovery

A runtime-plane connector must not be the only repair path for its own restart. If WebGPT/OAuth is being restarted, use the independent repair plane (local Agent shell/filesystem/process access or Remote Desktop Commander) for the mutation and post-state verification.

Do not reuse stale MCP session or browser references across a WebGPT/OAuth restart. Reacquire readiness and fresh tool/page state after the runtime returns.

Stage 19 also separates child liveness from wrapper readiness: 9340 OAuth child up + 9341 Edge down is degraded, not healthy. Start All/Doctor-style readiness must not false-green that state.

Recovery may reuse an already-running 9340 child only when canonical issuer identity matches. This is preserve/reconciliation, not a second mutation. Ambiguous child identity remains fail-closed.

After a real ChatGPT connector has been successfully established, acceptance work should prefer read-only verification. Repeated restart/re-register cycles are not a valid way to gain confidence when they put the known-good external integration at risk.
