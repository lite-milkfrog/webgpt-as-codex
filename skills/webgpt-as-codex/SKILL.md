---
name: webgpt-as-codex
description: 让网页端大模型通过 MCP 可靠接管本地代码与电脑工作流，覆盖多 MCP 路由、自动恢复、Loop Engineering、OAuth/Gateway、桌面一键启动与跨会话持续执行。
metadata:
  version: 1.3.1
  portability: public-safe-local-first-gpt-web-ready
  secrets-policy: no-secrets-in-skill
---

# WebGPT-as-Codex Skill

这是 WebGPT-as-Codex 的唯一正式 Agent Skill。它同时承担多 MCP 路由、权限、工作流、恢复、验证、Loop Engineering、Gateway/OAuth/桌面启动等产品执行规则；旧 Computer Agent 的完整经验、工作流、MCP Guides 与回归场景已吸收进本 Skill，不再作为第二套并行产品入口。

## 发行 / 本机一致性

- `skills/webgpt-as-codex/` 是唯一 canonical portable Skill。
- 本机 `.skills/webgpt-as-codex/` 使用同一个 `1.3.1` portable core，只额外保留 `environment.local.md`、`MCP-SKILLS-INVENTORY.*`、`state/` 等 machine-local overlay。
- portable 文件不允许“本机先长、发行版以后再补”或反向漂移；使用 `scripts/sync_webgpt_skill.py --check` 验证。
- 旧 `computer-agent` 仅作为迁移来源；最终发行包、本机主 Skill 和 README 都只暴露 WebGPT-as-Codex。
- Experience Ledger、MCP 专项经验、GUI/Playwright/Loop Engineering 规则必须无损保留；本地端口、路径、账户态和 transient health 仍只放 machine-local overlay，不进入 portable release。

## 产品专项合同

Gateway/OAuth、Manager、Bootstrap/Doctor/Repair、Runtime Supervisor 与发布边界读取 `product-contract.md`。这些规则与通用 MCP 工作流同属一个 WebGPT-as-Codex Skill。

## local SoT / Validation / Handoff

长任务必须把真实状态写入 local SoT，而不是只依赖聊天上下文；每个阶段在关闭前完成 Validation，并在需要继续时按 Handoff 契约生成和验证下一棒。`CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE` 必须保持显式且可递归续接。

## 核心原则

1. **结构化能力优先**：API/语义工具 > 终端/脚本 > GUI。
2. **按职责直达工具**：不要为了统一而经过二次 LLM 路由或万能代理。
3. **网页优先 Playwright**：网页内容、表单、DOM、标签页、下载优先 Playwright；Windows-MCP 只处理浏览器外壳、系统对话框或 Playwright 无法触达的桌面 UI。
4. **代码理解与修改分离**：Serena 做符号/引用/跨文件语义；Coding Tools 做实际编辑、构建、测试和本地 Git。
5. **全电脑文件/终端归 Desktop Commander**：尤其是代码工作区之外；代码仓库内优先 Coding Tools。
6. **原生桌面 GUI 归 Windows-MCP**：执行前观察，执行后验证；UI 状态变化后不得复用旧坐标。
7. **最小权限**：只调用完成任务所需的最少工具；不要因为某 MCP“也能做”就重复调用。
8. **外部副作用显式把关**：发送、发布、购买、删除、账号安全、系统级设置、提权、强推等遵循 `permissions.md`。
9. **不硬编码秘密和公网 URL**：Skill 只描述能力角色；环境差异放 `environment.local.md`，Token/密码不得进入 Skill。
10. **证据闭环**：状态改变类任务至少包含“前态/动作/后态验证”中的后两项，失败时不声称完成。
11. **失败先换策略，不先换工具**：一次调用失败不代表整个 MCP 不可用。先查后态、判断失败类别、在同一工具内换更稳策略；只有确认能力边界后才跨 MCP fallback。
12. **阶段可接力**：用户明确要求跨会话连续迭代时，每个会话只承担一个语义阶段；阶段结束必须更新真实 Source of Truth、进度、证据和 commit，再生成下一阶段 prompt 并实际启动下一会话。
13. **Zero-Guess 交接**：下一阶段 prompt 不得让下一 worker 猜“有什么工具、看什么文件、文件在哪里、怎么读、怎么用”。这些信息必须显式写出，并遵循 `workflows/handoff-template.md`。
14. **经验必须沉淀**：如果真实执行中遇到可复用的新坑，不只绕过去完成当前任务；任务恢复后必须判断是否需要更新 Skill / 项目执行协议 / eval。能普遍复用的经验要写回规则并加入 regression scenario，让后续 stage 默认绕开同类坑。
15. **本机 Inventory 必须先读**：凡涉及本机 MCP / Skills / Remote bridge / tool routing，新 Agent / 新窗口先读 `MCP-SKILLS-INVENTORY.md`（或机器处理时解析 `MCP-SKILLS-INVENTORY.json`），再读 `environment.local.md` 获取机器特定启动/恢复细节。如果 direct tool schema 未暴露，不得把“未暴露”误报成“服务不存在”；Loop handoff prompt 必须把本 stage 真正需要的 MCP locator 实例化出来。
16. **同一 MCP session 完成长链动作**：对 session-scoped MCP（尤其 Playwright tabs/shared context），`initialize -> tools/list -> tabs -> snapshot/type/submit -> verify` 应在同一 session 内完成；不要跨新 session 复用旧 tab index/ref。若 connector/wrapper 的每次工具调用会重新 initialize 或换 relay/session，不得把 handoff 拆成多个独立 connector calls；改用持久本地 MCP session、单次 persistent-context/run-code 调用，或已验证的 handoff helper。
17. **接力必须递归可续**：Loop worker 不能只保证 `Stage N -> Stage N+1`。每份 NEXT-WINDOW prompt 都必须完整携带 Recursive Handoff Invariant，明确 `CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE`，并要求下一 worker 在自己的收口中再次生成、提交并验证下下一棒。Batch 结束不是全局停止条件；用户主动叫停只能标记 `USER_STOPPED`，环境/权限硬阻塞只能标记 `PAUSED_EXTERNAL_BLOCKER`，两者都不等于 `GLOBAL_LOOP_COMPLETE`。
18. **已知本地 MCP 默认先自恢复，再 fallback**：对于 `environment.local.md` 已登记、且当前任务确实有价值的 Serena / Desktop Commander / Playwright / Coding Tools，本会话 direct schema 未暴露、listener 消失或进程退出时，不得直接写成“不可用”。在用户已授权本机 MCP 启动/使用的范围内，先按 locator 检查进程/端口，必要时启动本地服务，再执行标准 MCP 握手（`initialize -> tools/list`）和一个最小只读实调；只有启动/握手/实调都失败或能力确实不匹配时，才进入 fallback。Windows-MCP 仍是按需 native GUI fallback，不为了证明“所有 MCP 都活着”而强制启动。
19. **服务能力与账户态分开记**：特别是 Playwright，`MCP service available`、`browser automation available`、`authenticated shared browser context available` 是三个不同状态。Standalone 可用但未登录，不得误报成“Playwright 不可用”；需要已登录 ChatGPT/SSO 时再恢复 Extension/shared-context，若缺 token/login，准确标记 `AUTH_SHARED_CONTEXT_BLOCKED`，但代码阶段和无账户 Web 自动化仍可继续。
20. **工具本地元数据不能污染产品 Git**：语义/IDE 类 MCP 可能在项目根生成 `.serena/`、cache、local config 等工具元数据。进入语义工具前先有 Git pre-state；若某目录在 pre-state 不存在、且明确由当前 worker 的工具激活新建，则把它标记为 `TOOL_LOCAL_METADATA`，禁止混入产品/docs commit，并在 stage 收口前删除。若该目录原本已存在或被项目有意跟踪，则不得擅删。
21. **Prompt 稳定核心不能逐棒漂移**：Loop handoff prompt 必须由 `workflows/handoff-template.md` 的稳定核心 + 当前 SoT/Stage 变量重新生成，禁止复制上一棒 prompt 后局部改名继续传递。稳定核心至少包含：递归接力、程序完成定义、单 writer/Git 安全、Known-local MCP Auto-Recovery、handoff 完整性与失败恢复。项目可定义自己的 stable-core version；版本变化后下一 prompt 必须重新从模板实例化。
22. **全局完成是发布门，不是“暂时没事可做”**：只有 canonical program plan 中所有必做 Stage/Batches 与 cross-cutting defects 均关闭，所有 mandatory tests/gates PASS（或由用户逐项明确豁免），没有 active RED/expected-fail，最终版本/build/package/installable artifacts 已生成并验证，才允许写 `GLOBAL_LOOP_COMPLETE`。中间阶段可记录 historical failures / BLOCKED_ENV，但它们不能自动被带到最终完成状态。
23. **普通故障不能成为停工借口**：MCP 暂时掉线、网页元素变化、一次 test/typecheck/build 失败、脚本 non-zero、长命令超时、上下文变长、首个修复方案失败，都必须先进入恢复状态机并继续当前 Stage 可完成工作。只有已经穷尽当前授权范围内的同工具恢复、已登记本地 MCP 自恢复、结构化 fallback 与跨工具 fallback，并确认剩余 mandatory gate 真实依赖缺失的外部设备/凭证/权限/服务时，才允许 `PAUSED_EXTERNAL_BLOCKER`。禁止“遇到问题先停下来等用户”。
24. **Docs-before-prompt 硬顺序**：Loop Stage 收口时，必须先更新全部受影响 live SoT / evidence / decision / risk / environment / session / routing / progress 文档并验证一致性，再形成 product closure commit；只有文档状态已经与真实 HEAD/tests/dirty 对齐后，才允许从当前 `workflows/handoff-template.md` 重新实例化 next prompt。不得“先写下一棒 prompt，再回头补文档”。
25. **Prompt 的位置和文件必须可定位**：每一棒 prompt 必须显式写出 Computer Agent Skill 根、当前 Stage prompt、next prompt、SoT 根、产品源码根、tests 根与关键 MCP locator。对于 JARVIS 当前 workspace，Skill 实际根在 Coding Tools workspace 的 `.skills/webgpt-as-codex/`，不在 `Jarvis-dev/.skills/`；next worker 不得因为 worktree 相对路径找不到 Skill 就跳过 Skill bootstrap。
26. **终端命令必须匹配真实 shell dialect**：Windows 上的 Coding Tools `exec_command` 不得默认当作 PowerShell。先根据当前工具/环境已知事实使用 cmd-native 语法；确需 `$null`、管道对象、`Measure-Object` 等 PowerShell 语法时，显式调用 `powershell -NoProfile -Command ...`。shell syntax / redirection 非零后先查文件系统与 `git status` 后态，防止 `$null` 等 token 被 cmd 当作 literal 文件名创建；确认副作用后再修正命令，不能 blind retry。
27. **微信 / QQ Screenshot-only 验收**：微信、QQ 这类 Qt / 自绘界面大概率不会完整暴露 UI Tree/UIA。业务状态核对只允许使用当前 Screenshot / 原图视觉证据；UI Tree 只能辅助枚举窗口、标题、焦点等非业务元数据，禁止拿 `FOUND=0` / 缺控件来证明“按钮不存在、附件没挂上、消息没发出”。Screenshot 与 UI Tree 冲突时，以 Screenshot 为准。若用户已经打开/登录微信或停在“文件传输助手”，禁止重新启动或重新导航微信；发送本地文件优先读取 `workflows/wechat-file-transfer.md`。
28. **MCP 并发必须按状态模型判断**：不能把“支持多个请求”误写成“支持多个会话并行修改任意项目”。当前 Serena 标准 MCP 单进程有 process-wide active project；不同 ChatGPT 窗口并行切不同项目会互相影响，必须改用固定项目的独立 Serena 实例/slot，或只读多项目查询路径。Coding Tools 可以并行存在独立 command/session，但单 server 仍绑定一个 workspace；并行 writer 必须独立 worktree/workspace + ownership。Remote/Desktop Commander 的独立终端/文件操作可并行，真实 GUI 鼠标/键盘/焦点必须视为单机共享资源并串行。
29. **listener 活着不等于运行的是当前代码**：长期 Python/Node 服务在 source/static 更新后可能继续以旧 route table/旧模块驻留，形成“新磁盘资源 + 旧进程逻辑”的 mixed-version 状态。对 repository-owned 服务应同时校验 ownership、process identity、runtime generation/版本与关键 capability contract；确认 stale 且有 lifecycle authority 才刷新。未知/歧义 listener 即使端口正确也禁止 kill。
30. **用户桌面 launcher 与浏览器自动化 profile 分离**：用户双击桌面 launcher 打开的本地 Manager/控制页，应优先复用用户已经运行的正常浏览器 profile；浏览器未运行时走 Windows 正常 URL handler/default browser。不得因为项目也使用 Playwright 就让桌面 launcher 创建 temp user-data-dir、isolated profile、InPrivate 或 automation-only 空白 profile。Playwright 的 Extension/shared-context 生命周期与桌面 URL opener 是两个独立职责。
31. **Playwright handoff 必须防 session churn 与重复页**：若上一调用已成功创建 ChatGPT tab，但下一 connector 调用只看到 Extension Welcome，先把它分类为可能的 MCP session/observer churn，而不是“页面消失”。恢复时枚举 persistent context 中现存页面与 composer 后态，复用唯一可归因目标；禁止继续批量新建 tab、重复填 prompt 或重复 submit。handoff 成功后只清理当前 Agent 明确创建且未使用的空白/重复页，不关闭用户原有标签页。

## 首选路由

| 用户意图 | 首选 | 常见协作 | 不应首选 |
|---|---|---|---|
| 查符号、引用、调用链、跨文件关系 | Serena | Coding Tools | Desktop Commander |
| 改代码、跑测试、构建、本地 Git | Coding Tools | Serena | Windows-MCP |
| 全电脑文件、终端、进程、非仓库文件整理 | Desktop Commander | Coding Tools | Windows-MCP |
| 网页/Web App、表单、DOM、已登录浏览器 | Playwright | Desktop Commander | Windows-MCP 坐标点击 |
| Windows 原生应用、系统弹窗、鼠标键盘 | Windows-MCP | Desktop Commander | Playwright |
| 远端 GitHub issue/PR/action（若已连接） | GitHub MCP | Coding Tools | 浏览器 GUI |

详细规则读取 `routing.md`。

## 执行合同

### 读取/分析

低风险读取默认直接执行。优先一次获取足够上下文，避免多个 MCP 对同一事实重复读取。

### 普通可逆修改

用户已明确要求修改时，可执行普通文件编辑、代码修改、测试、构建、本地 Git 状态检查等。修改后必须验证。

### 高风险或外部副作用

遵循 `permissions.md`。未获必要授权时，只做到授权边界前并说明阻塞点。

## GUI 强制规则

Windows-MCP：

- 操作前 `Snapshot`/等价观察当前状态。
- **微信 / QQ 特例**：业务状态验证以 `Screenshot` 原图为唯一验收证据。UI Tree/UIA 不得用于否定截图里已经清楚可见的控件、附件卡片、消息或发送后态；最多辅助获取窗口/焦点/标题。优先保存并查看 Windows-MCP 返回的原始 Screenshot，而不是只读 Snapshot 文本摘要。
- 优先 label/UIA/快捷键；绝对坐标最后使用。
- 原生 GUI 控件已经明确存在时，优先走原生控件，不要先制造 helper window、OCR、拖拽脚本或 CLI workaround。
- 当前机器高 DPI / Screenshot downscale 环境下，**任何 UI 状态变化后重新 Snapshot**。
- 若 Screenshot metadata 返回 `Screenshot Coordinate Scale` 或非零 `Screenshot Region`，先按 `workflows/windows-gui-visual-calibration.md` 把截图坐标转换为真实桌面坐标，再调用 `Click/Move`；不要把 Windows DPI scale 与 Screenshot downscale 混为一谈。
- 用户上传的手机/远程桌面截图属于另一坐标空间，不得直接拿其像素坐标调用 Windows-MCP。
- 目标应用需要操作时 bring-to-front / focus / restore；用户原本已经打开的其它窗口不得随便关闭，需要腾位置时最多优先最小化/切后台/移动/Snap。
- 一个旧 Snapshot 不得支撑一串后续点击。
- 点击/输入后重新观察目标结果；`Click` 返回成功不等于业务动作成功；错位时停止，不连续盲点。
- 后态检测失败时必须先区分 `ACTION_FAILURE` 与 `OBSERVER_FAILURE`。例如 Qt dialog 已出现但检测器只找 `#32770`，属于 observer failure，禁止因此重复点击。
- 文件选择器、安装器、授权窗等可能有多层 dialog；每次“打开/下一步/确认”后都重新枚举 foreground/top-level window，不假设一次点击就回到原应用。
- GUI 文本输入失败时同时检查 path/encoding/escaping；不要把 `C:\\...` 这类程序字符串表示误当成文件选择器需要的真实路径文本。
- “完成”必须有业务后态证据；`Pressed enter`、`Typed text`、`Single left clicked` 只是 interaction primitive 成功。

Playwright：

- 优先 accessibility/DOM ref、role、label、test-id。
- 登录态网页优先 Extension/现有浏览器模式；不需要登录态时可用隔离浏览器。
- 文件下载完成后再交给 Desktop Commander/Coding Tools 处理本地文件。
- 浏览器系统级文件选择器、权限弹窗等超出页面 DOM 时，才切 Windows-MCP。
- 当前窗口没有直接 Playwright tool schema 时，先读 `environment.local.md` 和本机 Playwright README；若本地 MCP 服务在线，可通过标准 Streamable HTTP MCP 重新连接，不能仅凭“工具栏没显示”判定 Playwright 不可用。
- 若 8931 未监听且用户已授权本机 MCP 启用，先自动启动合适模式：无登录态要求可用 standalone；需要复用现有 Edge 登录态时优先 Extension/shared-context。启动后必须 `initialize -> tools/list -> 最小实调`，不能只看进程存在。

Serena / Desktop Commander：

- 代码阶段存在跨文件语义收益时，Serena direct schema 未暴露也应优先尝试本地 9121 MCP reconnect；成功后先激活当前项目，再做 symbols/references/call-chain，不应因为 schema 没显示就长期退化成 grep。
- Desktop Commander direct connector 未暴露但任务确实需要工作区外 host/file/process/log 能力时，可按 `environment.local.md` 发现当前 package/runtime，并建立临时本地 stdio MCP session；以 `tools/list` + `get_config`/等价只读调用确认可用。不要硬编码一次性 npm cache hash，也不要与 Coding Tools 双写 repo。

## 跨工具默认顺序

- 代码修复：Serena 定位 → Coding Tools 修改/测试 → Serena 必要时复核引用。
- 网页下载并处理：Playwright 下载 → Desktop Commander 整理/处理 → 必要时 Coding Tools 处理代码资产。
- 桌面应用自动化：Desktop Commander 先检查是否有 CLI/API → 无结构化入口再 Windows-MCP。
- Web 后台操作：优先 Playwright；只有浏览器 chrome、系统弹窗或不可访问区域才 Windows-MCP。

复杂场景读取 `workflows/` 对应文件。

## 失败与回退

1. 首选工具失败时先判断是权限、连接、能力缺失、stale state、interaction primitive 不合适还是输入错误。
2. **先查后态**：超时、click error、连接中断都不等于动作没有发生；任何可能有副作用的步骤重试前必须先查实际状态。
3. **优先同工具内换策略**：例如 Playwright click 失败后重新 snapshot/selector、换 keyboard/form/DOM activation；Coding Tools revision mismatch 后先 reread 最新 revision；Windows-MCP UI 变化后重新 Snapshot。
4. **不要立即换另一个重叠 MCP 重做整个任务**。
5. 只有确认当前工具能力边界确实挡住步骤时，才按 `routing.md` 的 fallback 切换。
6. 回退后保留已验证结果，避免重复写入、重复发送、重复下载或重复创建。
7. 安全门/权限拒绝不是“工具故障”，不得通过更宽权限 MCP 绕过。
8. Playwright 长文本 `type/fill` 超时后，先查 composer 后态；ProseMirror 可能已经完整写入。应做内容完整性校验（必要时标准化空白后 hash）再决定是否重填。发送按钮被 overlay 拦截时，优先 keyboard/Enter 或已启用按钮的同语义 DOM activation；每次动作后都先查后态，禁止盲重发。
9. **进程副作用需要 bounded post-state observation**：stop/restart/kill 返回 timeout、non-zero 或确认丢失时，不得立刻发第二次终止/重启动作。先在有界观察窗口内持续核对 listener、PID birth token、image/process identity；已经退出/恢复就按真实后态收口，仍保持同一 identity 才允许进入下一条授权恢复路径。

标准恢复阶梯：

`Observe post-state -> Classify failure -> Recover known local MCP transport/service -> Same-tool adaptation -> Structured fallback -> Cross-tool fallback -> BLOCKED only if no valid path`

恢复成功后追加一次 `LEARN` 判断：

`Was this failure reusable? -> If yes: distill root cause -> update routing/workflow/maintenance -> add eval -> validate -> propagate to next handoff`

不要因为“这次已经绕过去了”就丢掉经验；也不要把一次偶发事故不加判断地写成永久规则。

## 加载策略

仅按需要读取：

- 路由冲突/工具选择 → `routing.md`
- 权限/确认 → `permissions.md`
- 当前机器特性 → `environment.local.md`
- 代码任务 → `workflows/coding.md`
- 网页任务 → `workflows/browser.md`
- 桌面 GUI → `workflows/desktop.md`
- Windows GUI 视觉坐标 / 高 DPI / 自绘控件 → `workflows/windows-gui-visual-calibration.md`
- 微信文件传输助手发送文件 → `workflows/wechat-file-transfer.md`（已有登录窗口优先；FileDropList + Ctrl+V 是已验证稳定路径；发送后必须看业务后态）
- 文件/终端 → `workflows/files.md`
- 多工具长任务 → `workflows/cross-tool.md`
- 分阶段自动接力 / Loop Engineering → `workflows/loop-engineering.md`
- 下一窗口固定 prompt 结构 → `workflows/handoff-template.md`
- 完成前验收 → `validation.md`
- Skill 自身迭代 → `maintenance.md`
- 迁移到 GPT 网页端 → `gpt-web-port.md`

## 不应触发

- 纯知识问答，无需访问用户电脑或 MCP。
- 普通写作、翻译、总结已给文本。
- 用户明确只要求方案设计且不要求执行时，不应为了“验证工具”随意操作电脑。

## 完成标准

“已完成”必须意味着：目标动作真实执行；关键后态被验证；没有未报告的错误；没有把测试/准备误报成启用或持久化。

若启用了 Loop Engineering，“阶段完成”还必须意味着：当前阶段 SoT/进度/证据已更新，必要 commit 已形成，下一阶段 prompt 基于真实 HEAD/tests/dirty state 生成，并按 `workflows/handoff-template.md` 写全 Zero-Guess 字段。若用户已授权自动接力，还必须验证下一会话已真正接管；否则只能标记 `STAGE_COMPLETE_HANDOFF_PENDING`。