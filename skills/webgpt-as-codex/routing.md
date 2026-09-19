# Routing

Choose the narrowest structured capability closest to the data source.

| Intent | Primary | Fallback |
|---|---|---|
| symbols/references/semantic impact | Serena | repo search |
| repo edit/build/test/git | Coding Tools | local terminal only when binding unavailable |
| machine files/processes | Desktop Commander | native shell |
| browser DOM/login-state | Playwright | Windows-MCP only for browser chrome/system UI |
| Windows native GUI | Windows-MCP | CLI/API if the task is actually structured |
| hosted platform data/actions | dedicated connector/API | browser only when no API exists |

Rules:
- one file has one writer at a time;
- one external side effect is attempted once, then post-state is queried;
- do not use a broader tool to bypass a security gate;
- after a GUI state change, reacquire current UI evidence;
- a process/listener check is not an MCP protocol health check;
- use Tool Groups to reduce irrelevant tool exposure where possible.
