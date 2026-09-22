# Browser Workflow

## 首选 Playwright

网页内容、Web App、表单、标签页、已登录 Edge 会话、网页下载均优先 Playwright。

### 不假定固定 Playwright MCP tool 名

每个新会话第一次需要 Playwright 时，先看当前真正暴露的工具/schema。Playwright MCP 版本或包装层可能把同类能力暴露成不同名字。

优先能力顺序，而不是背固定 tool 名：

1. navigate / tabs
2. accessibility snapshot / find
3. type / fill form
4. click / press key
5. element/page evaluate（用于同语义状态检查或已授权 DOM activation）
6. 任意代码执行类/`unsafe` 工具只在结构化能力确实不足时考虑，并且不能因此扩大权限或绕过安全门

如果历史 prompt/脚本引用的某个 Playwright tool 不存在：

- 先读取实际 schema；
- 映射到当前等价结构化能力；
- 保留同一个页面状态和已验证结果；
- 不因为旧 tool 名消失就切 Windows-MCP。

### direct schema 未暴露时先找本地 MCP，不要误判“没有 Playwright”

在本机环境中，先读 `environment.local.md`。如果它声明了 Playwright local endpoint / deployment root：

1. 检查 listener/process/status；
2. 对 local endpoint 做标准 MCP `initialize`；
3. 接受 `notifications/initialized` 成功但 HTTP body 为空；
4. `tools/list` 获取当前真实 schema；
5. 整个 tabs/snapshot/type/submit/verify 链保持在同一个 `mcp-session-id`。

不要在一个 session `tabs list` 后，新开第二个 MCP session 再用旧 `tab index`；tab index/ref 是 session-scoped，必须在当前 session 重新发现。

可复用：

- `.skills/webgpt-as-codex/scripts/mcp-http-client.mjs`
- `.skills/webgpt-as-codex/scripts/chatgpt-loop-handoff.mjs`

## 元素定位优先级

1. accessibility ref / role / label
2. test-id / stable selector
3. DOM text/semantic relation
4. viewport 相对位置（仅最后手段）

不要把 Windows-MCP 的物理屏幕坐标作为网页默认定位方式。

## 登录态

- 需要用户现有登录状态/SSO/2FA：优先 Extension 模式。
- 不需要真实账号：优先隔离浏览器/profile，降低权限。
- **桌面 launcher / 本地控制页例外**：用户双击桌面入口打开 Manager、Dashboard 等普通页面时，它不是 Playwright 自动化会话。若用户正常浏览器已经运行，优先让 URL 进入该浏览器当前正常 profile；浏览器未运行时使用 Windows 默认 URL handler。不得把 Playwright 的 temp/isolated/automation profile 创建逻辑复用给桌面 launcher，也不得默认 InPrivate。桌面 opener 与 Playwright Extension/shared-context 分开验证、分开维护。
- 密码/Token 不写入 Skill 或普通日志；可让用户在浏览器内完成敏感输入。
- 对 Loop handoff 必须把 `Playwright service`、`browser automation`、`authenticated ChatGPT context` 分开判定。前两者正常、只有账户态缺失时，不得把整个 Playwright 写成 FAILED。
- Extension token 已建立连接但当前 session 只看到扩展 `Welcome` 页时，**不要要求用户手动点旧的 `Allow & select`**。先在同一 MCP session 直接 `browser_tabs new` 打开 `https://chatgpt.com/`；若新 tab 能看到账号资料/历史记录/composer，即视为已成功继承同一 Edge 登录态，直接使用这个新 tab 完成 handoff。只有新建 ChatGPT tab 仍未认证时，才进入 shared-context/tab-group/auth 恢复或 handoff-only Windows-MCP fallback。
- 如果 Extension/shared context 因缺 token/未登录而不能复用账户态，先检查是否存在**已运行且已登录的用户浏览器窗口**。用户已经明确授权自动 handoff 时，可把 Windows-MCP 作为**仅限 handoff transport 的最后 fallback**：重新 Snapshot 现有浏览器，确认是 ChatGPT 且已登录，再通过原生键盘/可访问控件打开新对话、粘贴完整 prompt、只提交一次并验证新 user message/assistant generating。不得读取密码/Token、不得修改浏览器账户安全设置、不得用坐标盲点绕过登录。

## 外部副作用

填写表单可以先做到提交按钮前；真正发送/发布/购买/授权按 `permissions.md`。

提交后不要只相信点击成功：读取成功页、状态、记录 ID 或其它后态。

## 下载

1. Playwright 发起下载并确认完成。
2. Desktop Commander 处理工作区外下载文件；代码资产需要修改时转 Coding Tools。
3. 不重复下载同一文件以“确认”。

## Playwright → Windows-MCP 回退

仅当：

- 系统文件选择器
- 浏览器扩展 chrome
- OS 权限对话框
- 页面之外的原生窗口
- Playwright 明确无法访问的 UI
- Loop handoff 所需的 authenticated browser context 无法通过 Playwright Extension/shared context恢复，但用户现有已登录浏览器窗口可由 Windows-MCP安全观察和操作

切换前重新观察 Windows UI，不复用 Playwright 的 CSS 坐标。

对上面的 handoff-only fallback 额外要求：

- 先用 Desktop Commander / process evidence 确认目标浏览器实例存在；
- Windows-MCP 每个状态变化后重新 Snapshot；
- 优先快捷键、可访问控件和粘贴，不用历史坐标；
- prompt 完整性至少做首/中/尾 spot-check；若无法做 DOM hash，则以 repo prompt + clipboard/可访问文本后态为证据，不声称完成强 hash；
- 提交动作只做一次，超时后先查消息是否已出现；
- 只用于恢复自动接力，不把 Windows-MCP升级为常规网页执行工具。

## Playwright 自适应恢复阶梯

一次 Playwright 调用失败时，不要直接把整个网页任务切给 Windows-MCP。

按顺序：

1. **查后态**：URL、composer/form 值、按钮状态、成功/错误提示、请求是否已经发生。
2. **分类失败**：selector/ref 过期、overlay/intercept、元素未 stable/editable、页面状态变化、Extension/连接、真正 DOM 外 UI。
3. **同工具内适配**：重新 snapshot/find；role/label/test-id；DOM relation；keyboard/Enter；合法 form path；同语义 programmatic DOM activation。
4. **再次验证后态**。
5. 只有确认目标位于 browser chrome、系统 dialog、file picker、OS permission 等 DOM 外区域时才切 Windows-MCP。

Programmatic DOM activation 只能替代已经授权、正常可执行但被页面布局/overlay 阻挡的**同一动作**。不得用来绕过 disabled、permission gate、安全确认或其它权限边界。

### 真实案例：click 被 overlay 拦截

若 `locator.click()` 报 `intercepts pointer events`：

- 不原样重复 click；
- 先确认动作是否已经发生；
- 若未发生，检查目标按钮是否 enabled 以及遮挡层；
- 可使用同语义的 keyboard/form/DOM activation；
- 提交后验证 URL、composer/form、用户消息/成功状态；
- 不因为一个 overlay 就升级到 Windows-MCP 坐标点击。

### 真实案例：ChatGPT 长 prompt fill 超时

`browser_type` / `fill` 对超长 ProseMirror composer 可能在 MCP 的固定调用超时内返回 timeout，但页面已经把完整内容写入。

因此：

1. timeout 后禁止立即重填；
2. 查 `userMessages / composer / send-button / URL` 后态；
3. 对本地 prompt 与 composer 做首/中/尾校验；需要强校验时，对双方做相同 whitespace normalization 后计算 SHA-256；
4. hash 一致即可把 fill 视为成功，不要重复输入；
5. ProseMirror 的 `textContent` 与 `innerText` 对换行/块结构计数不同，不能只拿字符数差异判断“被截断”。

### 真实案例：ChatGPT 发送按钮被 thread overlay 拦截

如果普通 `browser_click` 显示 `intercepts pointer events`：

- 先查后态确认仍未提交；
- composer 仍完整且按钮 enabled 时，优先让 composer focus 后 `browser_press_key Enter`；
- 若 keyboard 路径仍未提交，再对**同一个已启用 send button**做同语义 DOM activation（`element.click()`）；
- DOM activation 之前必须验证按钮不是 disabled / `aria-disabled=true`；
- 每次 submit primitive 后都检查 conversation URL、composer 是否清空、用户消息、stop/generating/assistant 状态；
- 任一步已提交就停止，不再执行下一种 submit primitive。

## ChatGPT / Agent 自动接力

当用户明确授权自动跨会话接力时：

1. 先完成当前 stage 的 docs/commit/next prompt；
2. 读取 `workflows/handoff-template.md` 确认 prompt Zero-Guess 字段完整；
3. 先读 `environment.local.md` 获取本机 Playwright locator；direct schema 未暴露时连接本机 MCP，不得直接判定不可用；
4. 优先复用已登录 Edge Extension/shared context；Extension session 只见 `Welcome` 但显示 connected 时，先直接在**同一 MCP session** `browser_tabs new -> https://chatgpt.com/` 并验证登录态，不要求人工选择旧 tab；如果新 tab仍未登录，才按“登录态”章节继续 auth/shared-context fallback。若 direct connector 的下一次调用换了 MCP session/relay，禁止因此再次开 tab；改用持久本地 8931 session、单次 persistent-context/run-code 调用或 handoff helper；
5. 使用这个已验证登录态的新 ChatGPT tab 作为空白新聊天；
6. 从 Source of Truth 读取完整 handoff prompt；
7. 填入后校验长度 + 首/中/尾片段；超长 prompt 可加 whitespace-normalized SHA-256；
8. 只提交一次；
9. 若 submit/click/type 超时或报错，先查 conversation URL、composer、用户消息、send/stop/generating 后态；
10. 只有确认未提交才允许换 Playwright 内策略；优先 Enter，再考虑已启用 send-button 的同语义 DOM activation；
11. 验证 conversation URL 已形成、composer 清空、用户消息可见且下一会话已响应或开始 generating；
12. handoff 成功后枚举当前 persistent context；只关闭本 Agent 本轮明确创建、且仍为空白/重复/未使用的 ChatGPT tab，保留已接管 conversation 与所有用户原有标签页；
13. Playwright 与 handoff-only Windows-MCP fallback 都不可用时，写 `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`，但不得重做已完成产品 stage；恢复时只恢复 transport 层。

用户对自动 loop 的明确授权只覆盖该 loop 内 handoff prompt 的提交，不扩展到其它外部副作用。

### Shared-browser tab lease

当 Playwright Extension/shared context 与用户真实浏览器共享多个标签页时，handoff 不能把易变化的 tab index 当成长期身份。

- 新建并选中 handoff ChatGPT tab 后，在该 tab 的 sessionStorage 写入随机 lease token；它只用于区分同源标签页，不包含 cookie、账号、OAuth 或其它 secret。
- 在长 prompt 写入前、以及唯一一次 submit 前，重新验证当前 tab 的 lease；如果其它窗口/Agent 抢走 current tab，则在当前 Playwright MCP session 内枚举 ChatGPT tabs 并恢复到匹配 lease 的 tab。
- lease 丢失时 fail closed，不猜测“最后一个 ChatGPT tab”，也不切到 Windows-MCP 盲点提交。
- 不复制 agent-browser 的 daemon/CDP/session-state persistence；真实登录态继续由现有 Edge Extension/shared context 提供，避免新增 cookie/localStorage 持久化副本和服务重启面。

### Connector session churn / duplicate-tab recovery

某些网页端 connector/wrapper 会让**每一次 Playwright 工具调用重新建立 MCP session 或 Extension relay**。这时上一调用成功创建的 ChatGPT 页可能仍真实存在，但下一次 `browser_tabs list` 只显示新的 Welcome 页。

- 把“上一调用 new 成功、下一调用只剩 Welcome”优先分类为 `OBSERVER_SESSION_CHURN`，不是 `PAGE_GONE`。
- 在创建第二个 tab 之前，用同一个本地 Streamable HTTP MCP session 做 `initialize -> tools/list -> tabs/new -> tabs/list`，或用一次 persistent-context/run-code 调用检查 `context.pages()`；若旧 ChatGPT 页仍在，继续复用它。
- connector 无法保留 `mcp-session-id` 时，不要把 `new -> snapshot -> type -> submit -> verify` 拆成多次独立 connector calls；使用 `scripts/chatgpt-loop-handoff.mjs`、持久 local MCP client 或单次 persistent-context 调用。
- 恢复前先检查所有可归因 ChatGPT 页：URL、是否空白、composer 是否已含完整 prompt、是否已形成 `/c/...`。composer 已经完整填入但未提交时，禁止再开页/再填一份；只在同一目标页执行 exactly-once submit。
- 如果故障恢复过程已经多开空白页，成功交棒后只关闭本 Agent 明确创建且未使用的重复页；不关闭用户原有标签页，也不把“清理”变成 broad tab close。

### Prompt-hash transaction / durable receipt

Loop handoff 不能再靠“当前看见哪个 tab”推断事务状态。canonical `scripts/chatgpt-loop-handoff.mjs` 是默认唯一 mutation owner：

- 每次 handoff 以完整 prompt 的 whitespace-normalized SHA-256 作为事务身份。已有 `/c/...` 页面只有在**最后一条 user message 的 normalized SHA-256 精确相同**时才算同一 handoff；“有 user message + composer 为空 + URL 是 `/c/`”不够。
- helper 在新建页面前先枚举当前 Playwright context：若发现唯一 exact-hash 已提交消息，只做 takeover 验证；若发现唯一 exact-hash 未提交草稿，复用草稿；只有两者都不存在才允许创建一个新 tab。多个 exact-hash 候选属于歧义，fail closed。
- 选中目标后写入 sessionStorage lease，并在 fill/submit 前重新验证；current tab 被其它窗口/Agent 抢走时，只能按 lease 在同一 MCP session 内恢复，lease 丢失则 fail closed。
- 真正触发 Enter/click submit **之前**先写 machine-local `SUBMIT_ATTEMPTED` write-ahead receipt（默认 `%LOCALAPPDATA%\\WebGPT-as-Codex\\handoff-receipts\\<prompt-sha256>.json`）；exact submitted message 被证明后升级为 `SUBMITTED`，takeover 验证后升级为 `HANDOFF_OK`。这样可以覆盖“提交动作已经跨过副作用边界，但 helper 在确认后态/写 `SUBMITTED` 前崩溃”的窗口。
- `SUBMIT_ATTEMPTED`/`SUBMITTED` receipt 都是 blind-resubmit barrier：即使用户手动关掉目标 tab、网页连接断开、helper 进程退出或下一 worker 暂时没有可见响应，也不得把“现场消失”解释为“没发”。`SUBMITTED` 可按 receipt conversation URL 做只读 exact-hash/takeover 复核；`SUBMIT_ATTEMPTED` 必须先恢复并证明上一尝试未产生副作用，无法证明时 fail closed，而不是再发一次。
- 当 canonical helper 已开始该 handoff transaction 后，direct connector / Windows-MCP 不得成为第二个 mutation owner。它们可以做只读诊断；只有在 helper **尚未发生任何 submit side effect** 且明确不可执行时，才允许按既有授权选择单一 fallback transport。