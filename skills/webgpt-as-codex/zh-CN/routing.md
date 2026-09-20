# Routing — 简体中文

[English](../routing.md) | **简体中文**

选择距离数据源最近、权限最窄的 structured capability。

| Intent | Primary | Fallback |
|---|---|---|
| symbols/references/semantic impact | Serena | repo search |
| repo edit/build/test/git | Coding Tools | 仅 binding unavailable 时 local terminal |
| machine files/processes | Desktop Commander | native shell |
| browser DOM/login-state | Playwright | 仅 browser chrome/system UI 时 Windows-MCP |
| Windows native GUI | Windows-MCP | 若本质是 structured task 则 CLI/API |
| hosted platform data/actions | dedicated connector/API | 没有 API 才 browser |

## Routing vs Operating Guide
Routing 决定 **WHICH capability**。MCP Guide 决定 **HOW**：
- real exposed tools/schema；
- goal-oriented call pattern；
- misuse；
- verification；
- performance/context；
- justified fallback。

server/tool name 只是 hint；capability claim 需 initialize/tools/list 或其他真实 schema evidence。Stage9 新 MCP 只有真实 evidence 才产生 routing recommendation；不可达/失败/未尝试则 defer。

当前 portable Guide：
- Serena：`mcp-guides/serena.md`
- Coding Tools：`mcp-guides/coding-tools.md`
- Remote Desktop Commander：`mcp-guides/remote-desktop-commander.md`

规则：
- one file one writer；
- external side effect 尝试一次后查 post-state；
- 不用 broader tool 绕 security gate；
- GUI state change 后重新获取 UI evidence；
- process/listener check != MCP protocol health；
- 可行时用 Tool Group 降低无关 tool exposure；
- 宣称 preferred MCP unavailable 前先诊断 workspace/session/auth/schema/harness；
- Serena config 中 `ready` 不等于 semantic capability proof，必须 exercise intended semantic call；
- RDC control-plane `online` 不等于 execution proof；必须区分 installation / local process / control plane / execution plane，并在把 RDC 选为 recovery executor 前完成真实 read-only execution probe；
- complementary recovery 只允许一个 healthy owner，禁止递归互救：healthy WebGPT 可修 unhealthy RDC，healthy RDC 可修 unhealthy WebGPT，unhealthy plane 不得成为 active repair executor；
- endpoint/binding/availability 属 machine-local inventory，不写 portable routing。
