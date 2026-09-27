# Routing

## 0. Workflow 编排层优先于单工具路由

当任务是多阶段交付、需要多个 Skills 协作、或用户明确要求“按流程做”时，先读取
`workflow-registry.json`，匹配 Workflow，再进入当前 Stage。

顺序是：

`Task -> Workflow -> Stage -> Skill selectors -> MCP/tool routing -> gate -> next Stage`

规则：

- Workflow 决定“这个阶段应该加载哪些 Skills、产出什么、什么条件才允许继续”。
- 本文件继续决定“当前 Skill/Stage 内具体用哪个 MCP/tool 执行”。
- 两层不能互相替代：Workflow 不是 MCP 路由器，MCP 路由也不能替代 Stage/gate。
- 简单单步任务不强制套 Workflow；直接按本文件路由，避免为了编排而编排。
- 一个 Stage 只加载该阶段需要的 Skills；禁止把整个 Skill 库一次性塞入上下文。
- `required=true` 的 Skill 缺失时 Stage 为 `blocked`；仅 optional Skill 缺失时可 `degraded` 继续。
- Manager 中的分类/拖动属于 machine-local 组织视图，不得暗中改写 repository-owned Workflow 执行语义。
- Workflow 的 canonical 定义来自仓库 `workflow-registry.json`；运行态/证据属于 machine-local run state。
- Stage 通过 gate 后再进入下一 Stage；失败先按对应 Skill/本文件恢复规则处理，不因为一个 Skill 失败就重做整个 Workflow。

如果没有匹配 Workflow，回到下面的直接工具路由。

## 1. 决策顺序

先判断任务对象，再判断动作类型：

1. **代码语义对象** → Serena。
2. **代码工作区的变更/执行** → Coding Tools。
3. **网页 DOM/Web App** → Playwright。
4. **Windows 原生 GUI** → Windows-MCP。
5. **全电脑文件/终端/进程** → Desktop Commander。
6. **服务端平台 API MCP**（如 GitHub，若连接）→ 对应官方/专用 MCP。

如果两个工具都能做，选“更结构化、更窄权限、更靠近数据源”的那个。

### 1.1 Availability 不是只有 exposed / unavailable 两档

对 `environment.local.md` 已登记的本机 MCP，按下面顺序判定：

`DIRECT_AVAILABLE -> LOCAL_LISTENER/PROCESS_CHECK -> AUTO_START_IF_AUTHORIZED -> MCP_INITIALIZE/TOOLS_LIST -> MINIMAL_READ_ONLY_PROBE -> USE -> FALLBACK`

规则：

- `NOT_EXPOSED` 只表示当前 ChatGPT tool surface 没直接给 schema，不代表本机 MCP 不可用。
- 用户已经授权本机 MCP 启动/使用时，已知服务进程掉线应主动拉起，不应先停工或直接降级。
- listener/process 只能证明“进程可能在线”；真正可用至少要完成 MCP 握手和一个最小只读 tool call。
- Remote/Desktop Commander 还要额外区分 control plane 与 execution plane：device visible/auth valid/`online` 不等于 live command transport；选作 recovery executor 前必须真实 `ping` / `get_config` / read-only host probe 成功。
- Serena / Desktop Commander / Playwright 只要对当前 stage 有实际收益，应先走本地恢复路径；不要为了省一步直接长期退化到 Coding Tools/Windows-MCP。
- Windows-MCP 是例外：只有任务真的涉及 native GUI / browser chrome / system dialog 才需要启用；代码/Web DOM阶段无需为了健康检查而强制使用。
- 不得为了自动恢复绕过新的权限/安全门，也不得读取、打印或持久化 Token/Cookie/OAuth secret。

## 2. Serena vs Coding Tools

### Serena 首选

- symbol 定义/实现
- references/call hierarchy
- 跨文件语义导航
- 重构前影响面分析
- “这个函数在哪里被调用？”

### Coding Tools 首选

- 修改源码
- 应用 patch
- 运行测试/构建/lint
- 本地 Git diff/status/commit（用户授权范围内）
- 读取明确仓库文件

### 推荐组合

`Serena 找对位置 → Coding Tools 改 → Coding Tools 测 → Serena 必要时复查引用`。

不要用 Serena 代替构建测试，也不要为了找一个符号让 Coding Tools 全仓库 grep 一遍，除非 Serena 不可用。

### 多窗口并发边界

- **Serena**：标准单 MCP server 的 `SerenaAgent` 有 process-wide active project。不同 ChatGPT 窗口如果共用同一进程并分别 `activate_project` 到不同项目，会互相切换/关闭前一个项目 language server。并行多项目任务必须使用“一个固定项目一个 Serena instance/port/slot”，或使用 Serena 的只读多项目 ProjectServer 路径；禁止把共享 `activate_project` 当会话隔离。
- **Coding Tools**：可同时存在多个独立 command/process session，但一个 server instance 只有一个 configured workspace。独立 read/process 可以重叠；同一 worktree 仍只允许一个 writer。不同项目并行写入优先不同 Coding Tools workspace/instance + 独立 Git worktree/branch。
- **Remote/Desktop Commander**：独立 terminal/filesystem/process session 可以重叠；真实 mouse/keyboard/foreground focus/clipboard-sensitive GUI 动作共享一台物理桌面，必须用 machine-level GUI lease 串行，不能让两个窗口同时抢焦点。
- **Windows-MCP**：native GUI 与 Remote/Desktop Commander 的 GUI side effects 使用同一共享桌面资源模型。
- **Playwright**：不同 page/context 可并行；同一 page/profile/login state 仍遵循 one-writer ownership。

## 3. Playwright vs Windows-MCP

### Playwright 首选

- 网站/Web App
- 表单填写
- DOM/accessibility 元素定位
- 标签页管理
- 已登录 Edge/Chrome 页面
- 浏览器内下载
- 页面截图/网络/控制台（能力可用时）

### Windows-MCP 首选

- Windows 设置
- 原生桌面软件
- 浏览器 chrome/UI（地址栏、扩展 UI 等 Playwright 无法触达区域）
- 文件选择器、系统权限框、系统 toast/dialog
- 纯鼠标/键盘桌面动作

### 禁止模式

网页里能通过 Playwright 元素 ref 完成的操作，不应改用 Windows-MCP 绝对坐标。

### 微信 / QQ Screenshot-only 例外

微信、QQ 大量使用 Qt / 自绘界面，UI Tree/UIA 可能严重不完整。对这两类应用：

- 业务状态验收只用当前 Screenshot / 原图；
- UI Tree/UIA 只能辅助窗口、焦点、标题等非业务元数据；
- `FOUND=0` / 缺节点不得触发重试、重发或“控件不存在”结论；
- Screenshot 与 UI Tree 冲突时 Screenshot 胜出；
- 优先读取 Windows-MCP 返回的原始/最高分辨率 Screenshot；
- 用户已打开/登录并定位到目标聊天时直接接管现有会话，不重新启动/搜索应用。


## 4. Desktop Commander vs Coding Tools

### Desktop Commander

- 工作区外文件
- 全盘搜索/整理
- 通用 PowerShell/cmd/Python/Node
- 长进程/进程管理
- 通用本机操作
- current-session direct connector 未暴露但 host/process/log 能力确实有价值时，可建立临时本地 stdio MCP session；package 入口按当前运行进程/安装发现，禁止硬编码一次性 runtime hash。

### Coding Tools

- 配置的代码工作区
- repo-aware 编辑
- 测试/构建/Git
- 原子 patch

代码仓库任务尽量不要用 Desktop Commander 和 Coding Tools 同时写同一个文件。

## 5. 失败恢复与路由回退

### 5.1 先查后态，再判断是否真的要 fallback

任何可能有副作用的操作报错/超时后，先查真实后态。失败响应不等于动作没有发生。

标准顺序：

`POST_STATE_CHECK -> FAILURE_CLASSIFICATION -> SAME_TOOL_ADAPTATION -> STRUCTURED_FALLBACK -> CROSS_TOOL_FALLBACK`

### 5.2 同工具内恢复优先

- Playwright MCP schema 可能随版本变化：先发现当前实际暴露的 `tools/list`/tool schema；不要把历史窗口里的固定 tool 名当长期 API。优先当前暴露的结构化 `navigate/snapshot/type/fill/click/evaluate/tabs/wait` 类工具；某个旧 tool 名消失不等于 Playwright 不可用。
- Playwright click 失败：重新 snapshot/find、换 role/label/test-id、keyboard/form path、同语义 DOM activation；只有 DOM 外 UI 才 Windows-MCP。
- Coding Tools revision mismatch：重新 read 最新 revision，再 edit；不要 force overwrite。
- Coding Tools 长命令返回 running：poll/read_output；不要另起一份重复命令。
- Windows-MCP UI 状态变化：重新观察；通用应用可优先 UIA/shortcut。微信/QQ 业务验收必须 Screenshot-only，不得让残缺 UI Tree 推翻视觉事实。
- Serena 单个 symbol 查询失败：先校对 symbol/project/context；确认服务/语言能力不可用后再 Coding Tools fallback。
- Serena direct schema 未暴露或 9121 listener 掉线：读取 `environment.local.md`，必要时启动本地 Serena，再 `initialize -> tools/list -> activate_project -> 最小 semantic probe`；这些步骤失败后才 Coding Tools fallback。
- Serena `activate_project` 前先记录 Git pre-state。若它在本轮新建未跟踪 `.serena/`，视为 `TOOL_LOCAL_METADATA`：不提交，semantic pass/阶段收口后删除；若 pre-state 已存在或已跟踪则保留并按项目规则处理。
- Desktop Commander direct namespace 未暴露：若任务需要工作区外 host/process/log，先确认 remote/local process；必要时从当前 package/runtime 发现入口建立临时 stdio MCP session，`tools/list + get_config` 验证后继续。只有确实无法建立结构化连接时才 fallback。
- Desktop Commander 显示 online 但 command 报 no-live-connection：标记 `CONTROL_PLANE_ONLINE / EXECUTION_PLANE_DOWN`，先查 broadcast capability/session persistence；不要把 online 当 usable，也不要未经证据 delete/re-pair。healthy WebGPT 可成为本轮唯一 repair owner；反向亦然，禁止 broken plane 递归互救。
- Playwright 8931 掉线：若任务不要求账户态可自动启动 standalone；需要现有登录态则优先 Extension/shared-context。必须把 `MCP service available` 与 `AUTH_SHARED_CONTEXT_BLOCKED` 分开记录。

### 5.3 路由回退表

| 首选失败 | 先做 | 可回退 | 前提 |
|---|---|---|---|
| Serena | 校对 project/symbol；判断服务/语言能力 | Coding Tools 搜索/读取 | 语义服务不可用或目标语言不支持 |
| Coding Tools | 校对 cwd/path/revision/权限；查命令后态 | Desktop Commander | 操作超出工作区或工具缺失；不要绕过安全策略 |
| Playwright | 查 URL/form/composer/request 后态；Playwright 内换策略 | Windows-MCP | 确认目标属于 DOM 外/browser chrome/系统级 UI |
| Windows-MCP | 新 Snapshot；判断是否可 CLI/API | Desktop Commander | 任务本质可由 CLI/API/日志完成 |
| Desktop Commander | 校对路径/进程/命令后态 | Windows-MCP | 只有 GUI、没有 CLI/API |

## 6. 工具去重

- 同一事实由一个权威工具读取后，不再用第二工具“确认”除非存在冲突风险。
- 同一文件一次修改只能由一个写入工具负责。
- 同一外部动作（发送、提交、点击确认）只执行一次；超时后先查后态再重试。
- 不为了展示能力而调用不必要 MCP。

## 7. 长任务路由

若 `workflow-registry.json` 已有匹配项，优先使用其 Stage 顺序与 Skill selectors；
没有匹配项时，再按下面的通用语义阶段生成临时计划。

将任务拆成语义阶段，而不是按 MCP 拆：

`理解 → 计划 → 执行 → 验证 → 收口/交付`

每个阶段选择最合适 MCP。不要先“把每个 MCP 都跑一遍”。

当用户明确要求跨会话连续迭代时，进入 Loop Engineering：

`Stage N 接管真实状态 -> 执行 -> 验证 -> 更新 SoT/进度 -> commit -> 生成 Stage N+1 prompt -> Playwright 交棒 -> 验证下一会话接管`

详见：

- `workflows/loop-engineering.md`
- `workflows/handoff-template.md`

同一 Git worktree 默认只有一个 active writer。多个 ChatGPT 窗口可以并行只读调研；要并行修改必须独立 worktree/branch + ownership。