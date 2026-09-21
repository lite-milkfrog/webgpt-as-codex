# Zero-Guess Stage Handoff Template

> 用于 Loop Engineering 每一棒生成下一棒 prompt。所有标记为 **REQUIRED** 的章节都必须实例化；不得只复制模板标题或使用“相关文件/合适工具/按需处理”等模糊词。

`STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2`

## Stable Core Contract — REQUIRED / DO NOT DRIFT

每个 NEXT-WINDOW prompt 都必须由**本模板当前版本重新实例化**，禁止复制上一棒 prompt 后只替换 Stage 名、HEAD 或文件路径。

Stable Core 必须完整保留：

1. Recursive Handoff Invariant；
2. Program Completion Gate：Batch 完成、B05/B04/B06/B07 完成、单个 MCP 故障、`BLOCKED_ENV` 都不能自动变成 `GLOBAL_LOOP_COMPLETE`；
3. Program state taxonomy：`ACTIVE / PAUSED_EXTERNAL_BLOCKER / USER_STOPPED / GLOBAL_LOOP_COMPLETE`；
4. Single-writer + Git/dirty/tool-local-metadata safety；
5. Known-local MCP Auto-Recovery 与 capability/auth-state 分层；
6. prompt fill/submit/post-state integrity 与 duplicate-send 防护；
7. final hardening + mandatory tests + version/build + Obsidian installable trio + release ZIP 完成后，才允许项目级完成。
8. Active-Recovery：普通 test/build/tool/browser/MCP 故障默认继续自主恢复，不得在仍有可执行路径时停工等待用户；
9. Docs-before-prompt：所有受影响 live SoT/evidence/risk/environment/session/progress 文档必须先更新并完成检查，之后才能生成 next prompt；
10. Prompt-location truth：明确 Skill 根、当前 Stage prompt、next prompt、SoT/source/tests 根；worktree 与 workspace 根不同的项目必须写清实际路径。

Stage-specific 内容只属于 Variable Payload：Stage goal/out-of-scope、真实 repo state、tests、exact source/test scope、BLOCKED_ENV、CURRENT/NEXT/AFTER_NEXT。Stable Core 版本变化时，旧 prompt 视为 stale，必须从当前模板重建。

# <Project> Loop Engineering — <Stage ID + Stage Name>

## 0. 本棒唯一目标 — REQUIRED

- Stage：`<stage-id>`
- 唯一主目标：`<one semantic outcome>`
- 本棒明确不做：`<out-of-scope items>`
- 前一棒状态：`<closed/local verified/handoff>`
- 当前产品版本：`<version>`
- 不得重做：`<closed stages>`

## 1. 真实仓库 / Workspace Map — REQUIRED

明确写出：

- 仓库：`<owner/repo>`
- Coding Tools worktree：`<workspace-relative path>`
- branch：`<branch>`
- `PRODUCT_HEAD`：`<stage product/docs closure commit>`；这是当前产品事实基线
- 当前实际 HEAD：启动时重新 `git rev-parse HEAD`；如果仅比 `PRODUCT_HEAD` 多 handoff-metadata/prompt commit，记录差异即可，不把它误判成产品代码变化
- upstream：`<upstream or none>`
- 产品根：`<path>`
- 源码根：`<path>`
- tests 根：`<path/pattern>`
- docs/SoT 根：`<path>`
- package/config 关键路径：`<paths>`
- 已知 dirty/WIP/noise：逐项列路径
- Tool-local metadata policy：如果下一棒会激活 Serena/IDE 类工具，必须要求它在激活前记录 Git pre-state；本轮新建、此前不存在的未跟踪 `.serena/`/cache/local config 只算 `TOOL_LOCAL_METADATA`，不得提交，收口前清理；已有/已跟踪同名目录不得擅删。
- 禁止 reset/clean/deploy/push 等边界

## 2. WebGPT-as-Codex Skill Bootstrap — REQUIRED

首先说明 Skill 的逻辑/实际入口：

- **Workspace Skill 根**：`<absolute-or-workspace-root>/.skills/webgpt-as-codex/`
- **当前 Stage prompt**：`<exact current prompt path>`
- **下一 Stage prompt**：`<exact next prompt path>`

- `.skills/webgpt-as-codex/SKILL.md`
- `.skills/webgpt-as-codex/routing.md`
- `.skills/webgpt-as-codex/workflows/loop-engineering.md`
- `.skills/webgpt-as-codex/workflows/coding.md`
- `.skills/webgpt-as-codex/workflows/cross-tool.md`
- `.skills/webgpt-as-codex/environment.local.md`
- `.skills/webgpt-as-codex/workflows/handoff-template.md`
- 交棒前 `.skills/webgpt-as-codex/workflows/browser.md`
- 权限不明时 `.skills/webgpt-as-codex/permissions.md`
- 完成前 `.skills/webgpt-as-codex/validation.md`

### 怎么读

默认用 Coding Tools `read_file` 精确读取这些 workspace 文件；不要用 Windows-MCP 打开文件管理器读 Skill。

如果当前会话无法访问 `.skills/webgpt-as-codex/`：

1. 明确记录 `COMPUTER_AGENT_SKILL_NOT_EXPOSED`；
2. 读取项目 prompt 指定的 Skill fallback 文档；
3. 不得声称已经读过 Skill。

## 3. 当前 MCP / Tool Execution Map — REQUIRED

下一 worker 必须先探测实际暴露工具，并在第一条用户可见更新中报告。

对每个工具写清楚以下五项：**是否可用 / 本机 locator（direct namespace 或 local endpoint/path）/ 本棒哪里用 / 哪里不用 / fallback**。

对于 `environment.local.md` 已登记且本棒有实际收益的 MCP，还必须写第六项：**direct 未暴露或进程掉线时的自动启动/本地恢复方法**。不能把“当前 ChatGPT 没显示 schema”当作跳过 Serena / Desktop Commander / Playwright 的充分理由。

### MCP Locator Table — REQUIRED

必须把本 stage 真正需要的 MCP 写成可执行定位表，禁止只写“本地 MCP”或“如果可用”：

| MCP | direct tool/resource 名（若当前已知） | 本机 endpoint/path（非秘密） | 如何确认在线/schema | down 时怎么启动 | direct 未暴露时怎么 reconnect |
|---|---|---|---|---|---|
| `<name>` | `<namespace/resource or unknown>` | `<localhost endpoint / launcher / state root>` | `<tools/list/status/process/listener + minimal probe>` | `<exact launcher or discovery rule>` | `<exact structured fallback>` |

规则：

- endpoint/path 必须来自 `environment.local.md` 或当前实测，不得猜；
- 不写 Token/Cookie/OAuth secret；
- direct schema 未暴露 ≠ local service 不存在；
- 用户已授权本机 MCP 启动/使用时，已知 MCP 进程掉线应先自动拉起，再握手/实调；只有失败后才 fallback；
- “进程存在”不是 AVAILABLE 的充分证据；至少需要 `initialize -> tools/list` 和一个最小只读 tool call；
- session-scoped MCP 必须注明“同一 session 完成长链动作”；
- 如果某 MCP 没有稳定 localhost endpoint（例如某 remote connector），要明确写“无稳定本地 HTTP，优先 direct connector namespace”，不能编造端口。

### Serena

- Availability：`AVAILABLE / NOT_EXPOSED / FAILED`
- 用于：`<symbols/references/call chain/impact map>`
- 不用于：tests/build/Git/runtime correctness
- Fallback：Coding Tools search/read
- Local recovery：direct 未暴露时先检查 9121；必要时启动本地 Serena；标准 MCP 握手后 `activate_project(<current worktree>)`，再做 symbol/reference 最小实调。代码 stage 有语义收益时不得无故跳过。
- Git hygiene：`activate_project` 前后比较 Git status；如果当前 worker 新建了此前不存在的未跟踪 `.serena/`，只作为本地工具元数据，禁止进入 commit，并在收口前删除。

### Coding Tools

- Availability：`...`
- 用于：repo truth、read/search、edit、tests、typecheck/build、Git、docs、next prompt
- 写入 ownership：同 repo 文件唯一默认 writer
- Fallback：只在能力边界明确时使用 Desktop Commander；不得双写同一文件

### Desktop Commander

- Availability：`...`
- 用于：工作区外 Windows 文件/命令/进程/host/log
- 不用于：与 Coding Tools 同时编辑 repo
- Fallback：Coding Tools exec（工作区内可覆盖时）/ Windows-MCP（只有 GUI 时）
- Local recovery：若 direct connector 未暴露但本棒需要 host/process/log，先确认现有 Remote 进程；需要本地结构化调用时，从当前 `@wonderwhy-er/desktop-commander` package/runtime 动态发现入口并建立临时 stdio MCP，`tools/list + get_config`/等价只读实调后使用；不得硬编码一次性 cache hash。

### Playwright

- Availability：`...`
- 用于：Web/ChatGPT/Edge、最终 handoff
- 不用于：源码分析/编辑/Git
- Fallback：先在 Playwright 内恢复/换策略；只有 DOM 外 UI 才 Windows-MCP
- Local reconnect：必须引用 `environment.local.md` 中的实际 endpoint/deployment path；若使用 HTTP reconnect，必须先 `initialize + tools/list`，并在同一 `mcp-session-id` 完成 tabs/submit/verify。
- Auto-start：8931 down 且已获本机启动授权时，按任务选择 standalone 或 Extension/shared-context。必须分别记录 `MCP service`、`browser automation`、`authenticated shared context` 状态；standalone 未登录只算 `AUTH_SHARED_CONTEXT_BLOCKED`，不算 Playwright 整体失败。

### Windows-MCP

- Availability：`...`
- 用于：Windows/Obsidian 原生 GUI、browser chrome/system dialog
- 不用于：网页 DOM、代码阅读、Git
- Fallback：Desktop Commander/logs/source evidence
- 不稳定策略：`WINDOWS_MCP_SKIPPED_UNSTABLE`

## 4. 必读文件清单 — REQUIRED

必须用表格/清单逐个写：

| 顺序 | 精确路径 | 分类 | 为什么读 | 用什么工具读 | 怎么读 |
|---|---|---|---|---|---|
| 1 | `<exact repo/workspace path>` | SoT / Evidence / Research / Historical | `<reason>` | Coding Tools / Serena / etc. | 全文 / 最新 handoff / 指定章节 / 定向搜索 |

规则：

- SoT 与 research/hypothesis 必须标类；
- 不能只写文件名而不写路径；
- 不能只写“必要时读取相关文件”；
- 如果一个文件只需指定章节，写出章节/关键词。

## 5. 当前已确认事实 / 假设 / 限制 — REQUIRED

分别列：

### CONFIRMED

只写有 exact source/test/runtime 证据的事实。

### WORKING_HYPOTHESIS

写待验证假设；明确不能直接继承成事实。

### BLOCKED_ENV / LIMITATION

真实环境限制逐项列出。

## 6. 本棒精确执行步骤 — REQUIRED

每个 Step 都必须写：

- Goal
- Primary tool
- Exact input/path/symbol/command area
- 怎么使用这个工具
- Fallback
- Expected evidence/output
- 何时进入下一 Step

示例：

### Step A — Semantic map

- Goal：找到 transaction owner/call chain
- Primary：Serena
- Path/symbol scope：`<...>`
- Usage：symbol/references/call hierarchy，不修改代码
- Fallback：Coding Tools `search_text + read_file`
- Expected evidence：owner/call-chain map
- Exit：关键入口/引用已定位

### Step B — Exact source/test verification

- Primary：Coding Tools
- Usage：读取 Serena 命中实现与 tests；建立 evidence table
- Expected evidence：CONFIRMED_SOURCE / CONFIRMED_TEST / HYPOTHESIS 分类

后续 Step 按当前 stage 实例化。

## 7. 失败恢复策略 — REQUIRED

写入本 stage 的具体 fallback，而不是只引用通用原则。

固定总序：

`查后态 -> 分类失败 -> 同工具换策略 -> 结构化 fallback -> 跨工具 fallback -> BLOCKED`

必须再明确：普通故障状态为 `ACTIVE_RECOVERY`，不是 `PAUSED`。只有已完成已知本地 MCP 自恢复、同工具替代、结构化 fallback、允许的跨工具 fallback，并且当前 Stage 其余可做工作均完成后，剩余 mandatory gate 仍真实依赖缺失外部条件，才可 `PAUSED_EXTERNAL_BLOCKER`。禁止“遇到问题先停下来问用户怎么办”。

至少说明：

- Serena 不可用怎么办；
- Coding Tools revision mismatch/long command 怎么办；
- Playwright click/submit 超时怎么办；
- Windows-MCP 卡住怎么办；
- 安全门/权限拒绝不能怎么绕过。
- direct schema 未暴露/本地 listener 消失时，哪些 MCP 要自动启动并完成 `initialize -> tools/list -> minimal probe`，哪些（如 Windows-MCP）因本棒不需要而可 `NOT_NEEDED`。

### Experience absorbed in previous stage — REQUIRED when applicable

如果上一 stage 新增/修改了 WebGPT-as-Codex 规则，必须写清：

- 新 Skill 版本；
- 触发该迭代的真实失败；
- 新规则所在精确路径；
- 新增 regression scenario ID；
- 下一 worker 开始前必须重新读取哪些 Skill 文件。
- 如果经验涉及 MCP “在哪里/怎么连”，还必须写明新的 locator、reconnect 脚本/路径和 session 规则。

不要只写“Skill 已优化”。

## 8. Tests / Gates — REQUIRED

列出：

- 开工 baseline；
- 每个 slice targeted tests；
- typecheck/build/lint 规则；
- full suite 是否本棒要求；
- historical failure identity；
- PASS / RED ownership / BLOCKED_ENV 口径。

## 9. 文档与进度更新 — REQUIRED

逐项列出本棒必须检查/更新的 live SoT 路径，以及何时更新。

**硬顺序：文档检查/更新完成 -> product closure commit -> 重新读取最新模板/SoT -> 生成 next prompt -> handoff artifact commit -> Playwright handoff。**

对项目定义的每个 live doc 必须给出 `UPDATED_WITH_NEW_EVIDENCE / CHECKED_NO_CHANGE_REQUIRED / NOT_APPLICABLE_THIS_STAGE` 三态之一。禁止 next prompt 先于 live-doc barrier 生成。

必须更新：

- stage %；
- overall product %；
- 口径：LOCAL_IMPLEMENTATION / LOCAL_VERIFIED / REAL_HOST_OR_DEVICE_VERIFIED。

历史封板文档不能为了统一格式被重写。

如果本 stage 出现了新的可复用坑，还必须检查：

- `.skills/webgpt-as-codex/maintenance.md`；
- 对应 routing/workflow；
- `evals/scenarios.json`；
- `scripts/validate_skill.py` 结果；
- 当前项目 Decision/Risk/Session 是否需要同步。

## 10. Git / Commit 纪律 — REQUIRED

写清：

- write owner；
- path-scoped diff/status；
- 哪些 noise 不得混入；
- commit 要求；
- stage 产品代码/docs closure commit 与 handoff artifact 可以分成两个 path-scoped commit；prompt 内的 `PRODUCT_HEAD` 指向产品 closure commit，避免“为了提交 prompt 又改变 HEAD”形成自引用漂移；
- 是否 push；
- reset/clean/force push/deploy 边界。

## 11. 本棒 Exit Criteria — REQUIRED

用可验证 checklist 列出当前 stage 什么时候可以结束。

不能写模糊的“完成主要工作”。

## 12. 下一棒定义 — REQUIRED

- `CURRENT_STAGE`：`<current stage>`
- `NEXT_STAGE`：`<next stage>`
- `AFTER_NEXT_STAGE`：`<stage after next; derive from latest canonical SoT>`
- 下一 Stage ID/name；
- 唯一目标；
- next prompt 精确保存路径；
- 该 prompt 必须基于当前 stage 真实最终 HEAD/tests/dirty state 生成；
- 不允许提前写死结果。

如果当前 stage 是一个 Batch 的最后一棒，不得因此停止整个 Loop。必须重新读取最新 canonical ordering，解析 NEXT_STAGE / AFTER_NEXT_STAGE，并继续生成跨 Batch prompt，除非 SoT 明确标记 `GLOBAL_LOOP_COMPLETE` 或用户明确停止。

项目级完成只能由 canonical Program Completion Gate 决定。`USER_STOPPED` 与 `PAUSED_EXTERNAL_BLOCKER` 都是未完成状态；最终 mandatory test/host/device/provider gate 如仍 `BLOCKED_ENV`，除非用户逐项明确豁免，否则不得生成 `GLOBAL_LOOP_COMPLETE` prompt。

## 13. Playwright 自动交棒手册 — REQUIRED when loop continues

明确：

1. 先读 `.skills/webgpt-as-codex/workflows/browser.md` 与 `.skills/webgpt-as-codex/environment.local.md`；
2. 确认 docs/commit/next prompt 完成；
3. 明确 Playwright direct namespace 或 local endpoint + deployment root；若 direct schema 未暴露，先 local MCP `initialize -> tools/list`；
4. local MCP 多步调用必须保持同一 `mcp-session-id`，不得跨 session 复用 tab index/ref；
5. 找/建空白 ChatGPT 对话；
6. 从 repo 读取完整 prompt；
7. 填入；长 prompt `type/fill` timeout 后先查 composer 后态，不盲重填；
8. 校验长度 + 首/中/尾；必要时 whitespace-normalized SHA-256；
9. 只提交一次；
10. click/submit 失败先查 URL/composer/user message/send/stop/generating 后态；
11. 确认未提交才换 Playwright 内策略；优先 keyboard/Enter，随后可对已启用 send button 做同语义 DOM activation；
12. 只有 DOM 外 UI 才 Windows-MCP；**例外仅限已授权 Loop handoff transport**：若 Playwright service/browser automation 正常但 authenticated shared context 无法恢复，且存在已登录用户浏览器，可按 `workflows/browser.md` 让 Windows-MCP 作为最后 transport fallback，必须 Snapshot、优先快捷键/可访问控件、只提交一次并验证后态；
13. 验证 conversation URL、composer 清空、用户消息出现、下一会话 generating/已响应；
14. 所有 transport 路径失败时写 `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`，不得重做已完成产品 stage；
15. 当前会话停止。

## 14. 第一条用户可见执行更新 — REQUIRED

要求下一 worker 第一条更新直接报告：

- Stage；
- 实际 MCP availability；
- 每个 MCP 本棒用途；
- fallback；
- 接下来第一批动作。

不要让用户从工具调用猜执行策略。

## 15. 现在开始 — REQUIRED

最后明确写出完整顺序，例如：

`Skill bootstrap -> MCP map -> Git/SoT -> semantic map -> exact source/tests -> baseline -> implementation -> gates -> ALL live-doc checks/updates -> product closure commit -> reload Stable Core + final SoT -> next prompt -> handoff artifact commit -> Playwright handoff`

并明确：不要停在规划阶段；不要越过证据下结论；不要吞掉下一 stage。

## 16. Recursive Handoff Invariant — REQUIRED / MUST COPY IN FULL

每一份 NEXT-WINDOW prompt 都必须包含一份**完整、自包含的 Recursive Handoff Invariant 正文**，不能只写“遵循 loop-engineering.md”或引用上一棒 prompt。

该正文至少必须明确：

1. handoff 是递归链：当前 worker 不只保证 `CURRENT_STAGE -> NEXT_STAGE`，还要让 NEXT_STAGE worker 被明确要求继续 `NEXT_STAGE -> AFTER_NEXT_STAGE`；
2. 每棒都写 `CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE`；
3. 跨 Batch 继续自动接力；Batch 结束不是 Global Loop Stop Condition；
4. next prompt 必须自包含 repo/worktree/branch/HEAD/upstream/source/tests/SoT/Skill/MCP locator/gates/dirty/BLOCKED_ENV/failure recovery；
5. `PRODUCT_STAGE_COMPLETE` 与 `HANDOFF_COMPLETE` 独立；handoff失败写 `STAGE_COMPLETE_HANDOFF_PENDING`，恢复只做 handoff 层；
6. timeout/non-zero exit 后必须查后态，禁止重复发送；
7. 长 prompt 强校验使用双方相同 whitespace normalization + SHA-256，UTF-8 bytes 不等于 JS characters；
8. 每棒重新发现 MCP；Playwright local reconnect 保持同一 `mcp-session-id`；
9. Experience Absorption 按 `RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE` 继续向后传播；
10. Program state 必须区分 `ACTIVE / PAUSED_EXTERNAL_BLOCKER / USER_STOPPED / GLOBAL_LOOP_COMPLETE`；用户停止与不可恢复安全门都是未完成状态，只有 canonical Program Completion Gate 全部通过才允许 `GLOBAL_LOOP_COMPLETE`；
11. 下一 worker 在生成下下一棒 prompt 时必须再次完整复制该 invariant；
12. prompt 缺失该完整 invariant 时，Zero-Guess / Recursive Handoff gate 失败，不得自动提交。

项目若提供了更完整的 canonical invariant 文本，必须**逐字完整复制项目版本**，不得用上面 12 点摘要替代。
