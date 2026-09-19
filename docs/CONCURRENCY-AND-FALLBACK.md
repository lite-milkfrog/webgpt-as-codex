# Concurrency and Complementary Fallback

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
