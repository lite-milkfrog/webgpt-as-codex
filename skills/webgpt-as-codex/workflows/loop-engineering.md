# Loop Engineering Workflow

## 目的

用于用户明确要求“一个阶段一个新对话、每一轮自动更新文档并继续下一阶段”的长任务。

Loop Engineering 不是后台监控器，也不是无限自主权限。它是一个阶段接力协议：

`Stage N 接管真实状态 -> 执行 -> 验证 -> 更新 SoT/进度 -> commit -> 生成 Stage N+1 prompt -> Playwright 交棒 -> 验证下一会话接管`

聊天窗口是可替换 worker；仓库/项目文档是长期 Source of Truth。

## 1. 什么时候启用

满足以下任一即可启用：

- 用户明确要求“每一轮自动开新对话继续”；
- 用户要求长项目按阶段连续执行且不想手工复制提示词；
- 当前任务明显超过单会话合理上下文，并且项目已有可持久化 SoT。

普通一次性任务不启用。

## 2. Stage 必须按语义成果拆分

好：

- transaction truth
- rollback
- crash recovery
- binary safety
- release closure

不好：

- Serena 阶段
- Coding Tools 阶段
- Windows-MCP 阶段

每个 stage 必须有：

- 唯一主目标；
- 明确不做什么；
- 输入 SoT；
- 工具 execution map；
- tests/gates；
- exit criteria；
- 下一棒定义。

## 3. Stage 0：Skill + Tool Bootstrap

任何 stage 碰产品代码前先完成：

1. 读取 `.skills/webgpt-as-codex/SKILL.md`；
2. 读取 `.skills/webgpt-as-codex/routing.md`；
3. 读取 `.skills/webgpt-as-codex/workflows/loop-engineering.md`；
4. 代码阶段读取 `.skills/webgpt-as-codex/workflows/coding.md`；
5. 多工具阶段读取 `.skills/webgpt-as-codex/workflows/cross-tool.md`；
6. 交棒前读取 `.skills/webgpt-as-codex/workflows/browser.md`；
7. 生成下一 prompt 前读取 `.skills/webgpt-as-codex/workflows/handoff-template.md`；
8. 权限不明确时读取 `.skills/webgpt-as-codex/permissions.md`；
9. 检查当前会话真正暴露的 MCP/tools。
10. 读取 `.skills/webgpt-as-codex/environment.local.md`，记录本 stage 真正需要的 MCP locator；direct schema 未暴露时先判断 local service 是否在线，禁止把 `NOT_EXPOSED` 直接等同于 `NOT_RUNNING`。
11. 对本 stage 真正有用、且 `environment.local.md` 已登记的本地 MCP 执行自恢复：listener/process 缺失时在既有用户授权范围内启动；随后做标准 MCP `initialize -> tools/list` 与一个最小只读实调。未经过这一步，不得仅因 direct schema 未暴露就宣布 Serena / Desktop Commander / Playwright 不可用。
12. Windows-MCP 仍按需启用：当前 stage 不涉及 native GUI 时可标记 `NOT_NEEDED`，无需为了“全 MCP 健康检查”强行调用。
13. 在 Serena/IDE 类工具激活项目前，先记录 Git status/pre-state；若工具本轮新生成未跟踪 `.serena/`/cache/local metadata，标记 `TOOL_LOCAL_METADATA`，不得进入产品/docs commit，收口前只清理由当前 worker 新建且 pre-state 不存在的那一份。

如果这些 Skill 文件不可见，明确记录 `COMPUTER_AGENT_SKILL_NOT_EXPOSED`，然后使用项目自己声明的 fallback 文档；不得假装读过 Skill。

### 第一条用户可见更新必须给 MCP Execution Map

至少写：

- Stage：唯一目标；
- Serena：`DIRECT_AVAILABLE / LOCAL_RECOVERED / LOCAL_AVAILABLE / FAILED / NOT_NEEDED`；本棒用途；
- Coding Tools：`DIRECT_AVAILABLE / LOCAL_RECOVERED / FAILED`；本棒用途；
- Desktop Commander：`DIRECT_AVAILABLE / LOCAL_STDIO_RECOVERED / LOCAL_REMOTE_RUNNING / FAILED / NOT_NEEDED`；是否需要；
- Playwright：`DIRECT_AVAILABLE / LOCAL_RECOVERED / BROWSER_AVAILABLE_AUTH_BLOCKED / FAILED / NOT_NEEDED`；何时使用；
- Windows-MCP：`DIRECT_AVAILABLE / LOCAL_AVAILABLE / FAILED / NOT_NEEDED`；是否需要；
- Fallback：每个不可用工具怎么替代。
- Locator：本棒真正要用的 MCP 的 direct namespace/resource 或 localhost endpoint/path/reconnect 方式。

不要只说“我会开始开发”。

## 4. Stage 开始协议

新会话先：

1. 读取 stage prompt；
2. 读取 prompt 指定的最小 SoT；
3. 检查 cwd/worktree/branch/HEAD/upstream；
4. 检查 dirty/WIP 和前一会话新 commit；
5. 发现实际状态与 prompt 冲突时，以真实状态为准并更新文档；
6. 确认当前会话是该 worktree 的唯一 writer。

### 单 Writer 原则

同一 Git worktree 默认只能有一个 active writer。

其它会话可以：

- 只读调研；
- Web research；
- 在独立 worktree/branch 中工作。

需要并行修改代码时必须：

- 独立 worktree；
- 独立 branch；
- 明确 ownership；
- 后续专门 merge/收束。

## 5. 工具角色

### Serena

用于大型/陌生代码的 symbol、references、call hierarchy、impact map。

不用于：构建、测试、Git commit、运行时正确性证明。

代码阶段存在跨文件语义收益时，Serena 是默认 semantic-map 工具。direct schema 未暴露不算不可用：先按本机 9121 locator 恢复/握手，激活当前 project，再做 symbol/reference 调用。只有本地恢复或语言能力确实失败时，才回退 `Coding Tools search/read`。

### Coding Tools

代码仓库默认 Source of Truth 与唯一写 owner：

- git status/log/diff；
- 精确读取 repo docs/source/tests；
- search/read；
- edit/patch；
- tests/typecheck/build；
- 本地 commit；
- stage docs 和 next prompt 文件。

不要让 Desktop Commander 同时写同一 repo 文件。

### Desktop Commander

只用于：

- 工作区外 Windows 文件；
- 通用命令/进程；
- Obsidian host/log；
- Coding Tools 工作区外主机证据。

如果 direct connector 未暴露但上述 host/process/log 证据对本棒有价值，先按 `environment.local.md` 确认已有 Remote 进程；仍需要结构化本地调用时，从当前 package/runtime 发现入口建立临时 stdio MCP，至少完成 `tools/list` + `get_config`/等价只读实调。不要因为 namespace 未显示就直接跳过。

### Playwright

只用于 Web/ChatGPT/已登录 Edge 和 stage handoff。

Web 不应默认切 Windows-MCP 坐标操作。

若 8931 未监听且用户已授权本机 MCP 启用：无账户态需求可自动启动 standalone；最终 ChatGPT handoff / 已登录后台优先 Extension/shared-context。Standalone 成功但页面未登录时，状态应写为 `BROWSER_AVAILABLE_AUTH_BLOCKED`，而不是 `PLAYWRIGHT_FAILED`。

Loop handoff 是 session-scoped 长链：`initialize -> tools/list -> tabs -> target lease -> prompt fill -> exactly-once submit -> post-state verify -> duplicate-tab cleanup`。如果网页 connector 每次调用都会换 `mcp-session-id`/relay，不能继续逐调用 new/list/type；改用持久本地 MCP session、`scripts/chatgpt-loop-handoff.mjs` 或一次 persistent-context 调用。上一调用已开出 ChatGPT、下一调用只见 Welcome 时，先检查 persistent context 和现有 composer，禁止把 observer/session churn 误判成页面消失并连续多开窗口。

自动 handoff 默认必须把 `scripts/chatgpt-loop-handoff.mjs` 视为**唯一 mutation owner**，而不是与 direct connector 并行的另一条可选发送路径。事务身份使用完整 prompt 的 whitespace-normalized SHA-256；helper 必须在创建新 tab 前先找 exact-hash 草稿/已提交消息，并在任何 submit primitive 前先写 machine-local `SUBMIT_ATTEMPTED` receipt。exact submit 被证明后升级 `SUBMITTED`，takeover 被证明后升级 `HANDOFF_OK`。只要 receipt 已到 `SUBMIT_ATTEMPTED` 或更后状态，后续 session churn、进程失败或用户手动关闭 tab 都只允许恢复/验证先前尝试；无法证明未提交时 fail closed，不能盲目再次 submit。

### Windows-MCP

只用于 Windows/Obsidian 原生 GUI、浏览器 chrome、系统 dialog/file picker 等 DOM 外 UI。

它是 optional GUI evidence，不是 loop spine。卡住时记录 `WINDOWS_MCP_SKIPPED_UNSTABLE` 并继续可继续工作。

## 6. Stage 执行协议

默认顺序：

`理解 -> semantic/evidence map -> baseline/red contract -> 实现 -> targeted verify -> broader gate`

架构结论不能只靠一个类名、几个 grep 或旧 research。复杂结论至少需要：

- semantic relation（若 Serena 可用）；
- exact source；
- relevant test/runtime evidence；

缺哪层就明确标记 hypothesis/limitation。

## 7. 自适应失败恢复

标准状态机：

`POST_STATE_CHECK -> FAILURE_CLASSIFICATION -> SAME_TOOL_ADAPTATION -> STRUCTURED_FALLBACK -> CROSS_TOOL_FALLBACK -> BLOCKED`

### 7.0 默认继续执行，不默认暂停

普通工程故障的默认状态是 `ACTIVE_RECOVERY`，不是 `PAUSED`。以下情况都必须自主排查并继续：

- MCP direct schema 暂时消失；
- 已登记本地 MCP listener/process 掉线；
- Playwright selector/overlay/tab-group/登录共享上下文异常；
- Coding Tools revision mismatch、command running、单次 command non-zero；
- Serena activation/LSP 短暂失败；
- targeted test / typecheck / build 首轮失败；
- 第一种实现方案不工作；
- 上下文变长或工具返回超时。

只有在以下全部满足时，才允许从 `ACTIVE_RECOVERY` 进入 `PAUSED_EXTERNAL_BLOCKER`：

1. 当前授权范围内的已知本地服务自恢复已尝试；
2. 同工具替代 primitive/selector/command path 已尝试；
3. 结构化 fallback 已尝试；
4. 能力边界允许时的跨工具 fallback 已尝试；
5. 当前 Stage 其余不依赖该 blocker 的工作已经做完；
6. 剩余 mandatory gate 确实依赖用户未提供的设备、凭证、权限或外部服务。

禁止把“需要多排查几步”升级成 blocker，也禁止在尚有可执行恢复路径时停下来等待用户。

### 7.1 先查后态

超时、click error、断线、command running 都不等于动作没有发生。

有副作用的动作重试前必须检查真实后态。

### 7.2 分类失败

至少区分：

- 输入/参数错误；
- stale ref/revision；
- 页面/窗口状态变化；
- interaction primitive 不适合；
- MCP 连接故障；
- MCP 能力边界；
- 权限/安全门；
- 外部环境缺失。

### 7.3 同工具先换策略

例：

- Playwright click 被 overlay 拦截 -> 查后态 -> 新 locator/DOM/keyboard/form path -> 再验证；
- Coding Tools revision mismatch -> reread -> 基于最新 revision edit；
- Windows-MCP UI 变化 -> 新 Snapshot -> UIA/shortcut；
- long command 返回 running -> poll/read_output，不重复启动同命令。

### 7.4 再跨工具 fallback

只有确认当前工具能力边界才跨 MCP。对于已登记的本地 MCP，“当前会话没有 direct schema”本身不构成能力边界；先完成 local auto-recovery + handshake + minimal probe。

不得因为一次 interaction primitive 失败就声明整个 MCP 不可用。

### 7.5 恢复后吸收经验

如果本 stage 出现了 Skill/路由中尚未覆盖、但具有复用价值的新失败模式：

1. 先完成当前 stage 的恢复，不中断主线；
2. 读取 `.skills/webgpt-as-codex/maintenance.md`；
3. 判断该经验应进入通用 Skill 还是仅进入当前项目文档；
4. 若进入 Skill，修改最小相关规则文件；
5. 在 `evals/scenarios.json` 增加 regression scenario；
6. 运行 `scripts/validate_skill.py`；
7. 在当前项目 Decision/Risk/Session 中记录规则变化；
8. 下一 stage prompt 明确新的 Skill 版本/规则入口。

这一步叫 `EXPERIENCE_ABSORPTION`。它的目标不是让 Agent 随意改规则，而是让已验证的恢复经验跨 stage 持久化。

## 8. Stage 收口协议

达到当前 stage 产品 gate 后，离开当前会话前必须：

1. 更新受影响 Source of Truth；
2. 更新 stage 进度；
3. 更新总项目进度；
4. 记录 tests/gates/evidence；
5. 记录 BLOCKED_ENV；
6. 更新 decision/risk（判断变化时）；
7. 检查 git diff/status；
7.5. 清理本 stage 自己新建、且 pre-state 明确不存在的 `TOOL_LOCAL_METADATA`（例如 Serena 新建的未跟踪 `.serena/`）；不得删除用户原有或项目已跟踪的同名目录；
8. 对照项目文档清单确认**所有受影响 live docs 已经先更新完成**；不得先生成 next prompt 再补文档；
9. path-scoped product closure commit；
10. 再次读取最新 `workflows/handoff-template.md`、当前 live SoT、Stage evidence、Git HEAD/tests/dirty；
11. 只有此时才基于真实最终状态生成 next-stage prompt；
12. next prompt 生成后做 Zero-Guess / Recursive Handoff / locator / docs-before-prompt 自检，再形成 handoff artifact commit；
13. 若本 stage 发生了新的可复用工具/流程失败，完成 `EXPERIENCE_ABSORPTION` 并把新规则传给下一 stage。

不要为了“所有文档都动一下”机械改历史封板证据。

### Live-doc completion barrier

项目若定义 live-doc 清单，则在生成 next prompt 前必须逐项检查。每一项必须属于以下之一：

- `UPDATED_WITH_NEW_EVIDENCE`
- `CHECKED_NO_CHANGE_REQUIRED`
- `NOT_APPLICABLE_THIS_STAGE`

不能因为某文件“通常不需要改”就完全跳过检查。next prompt 必须只基于这个检查完成后的 SoT。

## 9. Zero-Guess Next Prompt

下一棒 prompt 必须完整实例化 `workflows/handoff-template.md`。

### Stable Core + Variable Payload

每一棒都必须从模板重新生成，禁止复制上一棒 prompt 再改 Stage 名称。

- `STABLE_CORE_VERSION`：由 `workflows/handoff-template.md` 定义；只有协议本身变化才升级。
- Stable Core：递归接力、Program Completion Gate、单 writer/Git safety、Known-local MCP Auto-Recovery、handoff transport integrity、failure recovery。
- Variable Payload：CURRENT/NEXT/AFTER_NEXT、真实 repo/HEAD/dirty、当前 tests、exact source/test scope、stage-specific steps、BLOCKED_ENV。

如果上一 prompt 的 stable-core version 与当前模板不同，必须按当前模板重建；不得继续复制旧块。

不得省略：

- 工具清单；
- 本 stage MCP locator table：direct namespace/resource、localhost endpoint/path、online/schema check、direct 未暴露时 reconnect 方法；
- 每个工具什么时候用/不该用；
- Skill 文件路径与读取顺序；
- repo/worktree/source/test/docs 精确路径；
- 每个必读文件的路径、用途、读取方式；
- 每个执行 step 的 primary tool、fallback、expected evidence；
- known WIP/noise；
- tests/gates；
- exit criteria；
- 下一次 handoff 方法。

禁止模糊写法：

- “看相关文件”；
- “用合适的 MCP”；
- “按需检查”；
- “继续之前流程”。

如果下一 worker 仍需要猜关键路径/工具/读取方式，则 prompt 不合格，不得自动提交。

## 10. Playwright 自动交棒

用户明确授权自动跨会话接力时：

1. docs/commit/next prompt 全部完成；
2. 读取 `workflows/browser.md` 和 `environment.local.md`；
3. direct Playwright schema 未暴露时，按 local locator 连接本机 MCP 并 `initialize -> tools/list`；
4. 如果 8931 未监听，在既有授权范围内自动启动：需要 ChatGPT 登录态则优先 Extension/shared-context；只需验证浏览器能力可用 standalone。Extension token/login 缺失时记录 `BROWSER_AVAILABLE_AUTH_BLOCKED`，不能写成 Playwright 整体不可用；
5. 使用 Playwright 复用已登录 Edge；整个 tabs/type/submit/verify 保持同一 MCP session；
6. 选择空白新 ChatGPT conversation；没有就新建；
7. 从 SoT 读取完整 prompt；
8. 填入 composer；长文本 fill timeout 先查后态，不立即重填；
9. 校验长度 + 首段 + 中段 + 尾段；必要时 whitespace-normalized SHA-256；
10. 只提交一次；
11. 提交报错/超时时先检查 URL、composer、用户消息、send/stop/generating 状态；
12. 只有确认未提交才允许换策略重试；可依次使用 keyboard/Enter 或已启用 send-button 的同语义 DOM activation；
13. 验证下一会话已经响应/接管；
14. 当前会话停止，不继续吞下一 stage。

### 提交 click 被 overlay 拦截

不要直接切 Windows-MCP。

先：

- 查 URL/composer/user message/stop state；
- 确认未提交；
- Playwright 内重新定位；
- 用 keyboard/form path 或同语义 DOM activation；
- 再验证。

只有浏览器 chrome/系统 UI/DOM 外区域才用 Windows-MCP。

## 11. 权限

用户明确要求“自动更新、自动生成下一 prompt、自动提交下一 ChatGPT 对话并继续”时，该请求可覆盖**同一 loop 内 handoff prompt 提交**这一 P2 动作。

不扩展到：发布产品、发邮件/评论、购买、安装软件、账号安全、force push、其它不属于 handoff 的外部副作用。

P3 永远需要单独明确确认。

## 12. Handoff 成功定义

只有全部满足才算 `STAGE_N_TO_N+1_HANDOFF_OK`：

- Stage N gate 达标；
- SoT 更新；
- 进度更新；
- commit 完成；
- next prompt 已按固定模板生成；
- prompt 完整填入；
- 只提交一次；
- conversation URL/用户消息后态确认；
- Stage N+1 已开始响应/接管；
- 本轮 Agent 自己创建的未使用空白/重复 handoff tab 已清理，用户原有 tabs 未受影响。

如果产品工作完成但交棒失败：

`STAGE_COMPLETE_HANDOFF_PENDING`

不得伪称完整 loop success。

## 13. Recursive Handoff Invariant

Loop handoff 是递归合同，不是一次性的 `Stage N -> Stage N+1` 动作。每个 worker 在生成 NEXT-WINDOW prompt 时，必须保证下一 worker 仍拥有继续 `Stage N+1 -> Stage N+2` 的完整规则。

每一棒收口必须显式记录三层游标：

- `CURRENT_STAGE`
- `NEXT_STAGE`
- `AFTER_NEXT_STAGE`

每份 NEXT-WINDOW prompt 必须完整包含项目当前声明的《Recursive Handoff Invariant》正文，而不是只引用本 Skill 或上一棒 prompt。下一 worker 必须再次被要求：完成当前 stage、更新 SoT/进度、运行 gates、path-scoped commit、基于真实最终状态生成下一 prompt、完整继承 invariant、Playwright 提交、验证下一 conversation 接管，然后停止当前窗口。

跨 Batch 也继续自动接力。Batch 完成不是 global stop。当前项目大顺序由最新 canonical SoT 决定；如果 prompt/SoT 已指定 `B05 -> B04 -> B06 -> B07 -> FINAL_HARDENING -> RELEASE_PACKAGE`，那么 B05-E 完成后必须重新读取 next-round ordering 并生成 B04 第一实施 stage，而不是停止；B07 完成后也必须进入全局收尾，而不是直接宣布完成。

产品阶段与交棒状态必须拆开：

- `PRODUCT_STAGE_COMPLETE`：code/tests/docs/commit/next prompt 完成；
- `HANDOFF_COMPLETE`：prompt 已提交、完整性已验证、下一 conversation 已出现对应 user message 且下一 worker generating/已响应；
- 前者完成但后者失败：`STAGE_COMPLETE_HANDOFF_PENDING`，恢复时只继续 handoff 层，不重做产品代码。

Program state 与完成状态必须分开：

- `ACTIVE`：继续按 canonical ordering 开发；
- `PAUSED_EXTERNAL_BLOCKER`：当前环境/权限/凭证/真实设备挡住 mandatory gate，但项目未完成；
- `USER_STOPPED`：用户明确叫停，项目未完成；
- `GLOBAL_LOOP_COMPLETE`：只有 Program Completion Gate 全部通过后才能写。

Program Completion Gate 至少要求：

1. canonical ordering 中所有必做 Stage/Batch 与 cross-cutting defects 全部关闭；
2. 没有 active RED、临时 expected-fail、release-blocking TODO；
3. targeted/typecheck/build/full suite 与项目规定的 mandatory tests 全部 PASS；中途历史失败在最终阶段必须修复或由用户逐项明确豁免；
4. real host/device/provider 等 mandatory acceptance 不能只用 `BLOCKED_ENV` 代替 PASS；若环境仍缺失，状态只能是 `PAUSED_EXTERNAL_BLOCKER`，除非用户明确豁免该 gate；
5. 最终版本号/manifest/package metadata 一致；
6. 最终 build 产物、Obsidian 可安装三件套（`main.js` / `manifest.json` / `styles.css`）与 release ZIP 已生成并做静态/安装前校验；
7. 最终 SoT、release evidence、Git state 完整，无未解释产品 WIP。

普通 stage 完成、Batch 完成、单个 MCP 暂时不可用都不是全局停止条件。

若 NEXT-WINDOW prompt 缺少完整 Recursive Handoff Invariant，则 Zero-Guess gate 失败，不得执行自动提交。

## 14. Loop 停止 / 暂停 / 完成条件

Stage worker 只能按上面的 Recursive Handoff Invariant 判断整个 loop 的状态。普通“当前 stage 已完成”只允许停止当前窗口，不允许终止递归开发链。

如果出现需要新 P2/P3 且原请求没有覆盖，或 Source of Truth 冲突到无法安全确定唯一 writer，应先持久化当前安全状态与 blocker；只能标记 `PAUSED_EXTERNAL_BLOCKER`。用户主动叫停只能标记 `USER_STOPPED`。二者都不得伪称 `GLOBAL_LOOP_COMPLETE`。

普通 test/typecheck/build 失败、MCP 一次调用失败、上下文变长，不是自动停止理由。
