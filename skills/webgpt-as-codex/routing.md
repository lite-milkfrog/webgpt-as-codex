# Routing

[**English**](routing.md) | [简体中文](zh-CN/routing.md)

Choose the narrowest structured capability closest to the data source.

| Intent | Primary | Fallback |
|---|---|---|
| symbols/references/semantic impact | Serena | repo search |
| repo edit/build/test/git | Coding Tools | local terminal only when binding unavailable |
| machine files/processes | Desktop Commander | native shell |
| browser DOM/login-state | Playwright | Windows-MCP only for browser chrome/system UI |
| Windows native GUI | Windows-MCP | CLI/API if the task is actually structured |
| hosted platform data/actions | dedicated connector/API | browser only when no API exists |

## Routing versus Operating Guide

Routing decides **WHICH capability** owns an intent.

The selected MCP Operating Guide decides **HOW to use it**:
- actual exposed tools/input schemas;
- goal-oriented call patterns;
- common misuse;
- verification signals;
- performance/context trade-offs;
- justified fallback.

A component/server/tool name is only a hint. Capability claims require initialize/tools/list or other real schema evidence.

For newly onboarded MCPs, Stage 9 produces a routing recommendation from actual tools/list evidence. `success` may produce `recommend-review`; unavailable/failed/unattempted evidence is deferred instead of being promoted into Skill routing.

Current portable Guides:
- Serena: `mcp-guides/serena.md`
- Coding Tools: `mcp-guides/coding-tools.md`
- Remote Desktop Commander: `mcp-guides/remote-desktop-commander.md`

Rules:
- one file has one writer at a time;
- one external side effect is attempted once, then post-state is queried;
- do not use a broader tool to bypass a security gate;
- after a GUI state change, reacquire current UI evidence;
- a process/listener check is not an MCP protocol health check;
- use Tool Groups to reduce irrelevant tool exposure where possible;
- diagnose workspace/session/auth/schema/harness state before declaring a preferred MCP unavailable;
- a configuration summary that says `ready` is not semantic-capability proof; exercise the intended semantic call before relying on Serena;
- Remote Desktop Commander control-plane `online` is not execution proof; distinguish installation, local process, control plane and execution plane, and require a real read-only execution probe before selecting RDC as a recovery executor;
- complementary recovery is one-owner and non-recursive: a healthy WebGPT plane may repair unhealthy RDC, or healthy RDC may repair unhealthy WebGPT, but an unhealthy plane is never the active repair executor;
- local availability, bindings and endpoints belong in machine-local inventory/state, not portable routing rules.
