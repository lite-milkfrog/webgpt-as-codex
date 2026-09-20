# Cross-tool Workflows

## A. 修复一个大型代码问题

1. Serena：定位入口、依赖、references。
2. Coding Tools：读取必要文件并修改。
3. Coding Tools：测试/build/lint。
4. Serena：仅在重构/影响面有疑问时复核 references。
5. Coding Tools：diff/status。

不要让 Desktop Commander 参与 repo 写入，除非 Coding Tools 无法访问所需路径。

## B. 从网页下载资料并纳入项目

1. Playwright：找到并下载。
2. Desktop Commander：确认落盘、整理位置。
3. Coding Tools：若进入代码仓库，复制/修改/测试。
4. 验证最终文件而不是重复下载。

## C. Web 后台 + 本地代码发布流程

1. Coding Tools：构建/测试本地代码。
2. GitHub MCP（若有）或 Coding Tools：处理远端代码动作。
3. Playwright：仅处理没有 API/MCP 的 Web 后台。
4. Windows-MCP：仅处理系统/浏览器原生弹窗。
5. 发布/提交前按权限等级把关。

## D. 操作一个桌面应用并处理生成文件

1. Desktop Commander：先找 CLI/API/文件路径。
2. 无结构化入口时 Windows-MCP 操作 UI。
3. Desktop Commander 验证生成文件。
4. 文件进入 repo 后切 Coding Tools。

## E. 工具不可用

- Serena 不可用：Coding Tools 搜索，明确这是 fallback。
- Playwright 不可用：只对必要页面使用 Windows-MCP；复杂网页自动化可暂停而不是盲点。
- Windows-MCP 不可用：寻找 CLI/API；不存在则报告 GUI 阻塞。
- Desktop Commander 不可用：先区分 installation/local process/control plane/execution plane；`online` 但真实 command 失败仍属于 execution-plane unavailable。WebGPT healthy 时可由 Coding Tools/Windows-MCP/approved shell 做 bounded RDC recovery；仓库内任务继续 Coding Tools；不要用 Windows-MCP 模拟文件管理器做大规模文件任务。
- WebGPT 不可用而 RDC execution plane healthy：RDC 可检查 Gateway/OAuth/Manager/Tailscale/startup/logs 并执行 allowlisted repair；恢复后重新获取 fresh connector/tool refs。
- WebGPT 与 RDC 都不可用：转 local startup/reboot/human-local recovery，不构造递归 repair loop。

## F. 长任务状态管理

每完成一个阶段记录：

- 已验证事实
- 已执行动作
- 当前状态
- 下一步
- 未验证/阻塞

不要因为换 MCP 丢掉前一阶段证据。

## G. 自适应失败恢复

失败不是“换 MCP”的同义词。按以下状态机处理：

`POST_STATE_CHECK -> FAILURE_CLASSIFICATION -> SAME_TOOL_RETRY_WITH_DIFFERENT_STRATEGY -> STRUCTURED_FALLBACK -> CROSS_TOOL_FALLBACK -> BLOCKED`

### POST_STATE_CHECK

先确认副作用是否已经发生。超时、断线、click error 都可能发生在动作之后。

### FAILURE_CLASSIFICATION

至少区分：输入/参数错误、stale ref/revision、页面/窗口状态变化、interaction primitive 不适合、MCP 连接故障、MCP 能力边界、权限/安全门、外部环境缺失。

### SAME_TOOL_RETRY_WITH_DIFFERENT_STRATEGY

不要原样重试同一个失败动作。必须改变策略，例如：

- Playwright click -> 新 snapshot/selector -> keyboard/form/DOM activation；
- Windows-MCP 坐标 -> 新 Snapshot -> UIA/shortcut；
- Coding Tools revision mismatch -> reread -> 基于最新 revision 编辑；
- command timeout/running -> 查进程/输出 -> 再决定继续/终止/重跑。
- process stop/restart timeout/non-zero -> 在 bounded observation window 内持续检查 listener + PID birth/image identity；确认动作未发生且 authority 仍成立后，才允许新的 mutation attempt，禁止瞬时一次检查后 blind retry。
- source/static 已更新但长期服务 listener 仍在 -> 不得把 listener/healthz 直接当“当前版本”证据。检查 ownership + process identity + runtime generation/启动代次 + 关键 capability/resource contract；若确定是当前项目旧进程才做 bounded refresh。端口被 unrelated/ambiguous 进程占用时 fail closed，不得为了“加载新代码”直接 kill。

### CROSS_TOOL_FALLBACK

只有确认当前工具不能完成该步骤时才切换；保留已经验证的事实，不从头重做。

## H. 自动交接型长任务

用户明确要求连续跨会话迭代时：

- 读取 `workflows/loop-engineering.md`；
- 生成下一阶段 prompt 前读取 `workflows/handoff-template.md`；
- 每个会话只承担一个明确语义阶段；
- repo/项目文档是真实状态载体，聊天上下文不是长期 SoT；
- 同一 worktree 默认单 writer；
- 当前阶段负责把下一阶段真正启动，而不是只写“下一步建议”。