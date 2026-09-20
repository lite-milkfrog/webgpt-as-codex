# Coding Workflow

## 适用

代码审查、调试、实现、重构、测试、构建、本地 Git。

## 默认流程

1. **确认仓库/工作区与目标**：不要在错误副本上修改。
2. **语义定位**：涉及未知代码结构时先 Serena 查 symbol/references/call chain。
3. **最小变更计划**：明确要改哪些文件、验证什么。
4. **Coding Tools 修改**：使用原子 edit/patch；避免 Desktop Commander 同时写同一仓库文件。
5. **验证**：先相关测试，再更广泛测试；必要时 build/lint/typecheck。
6. **检查 diff**：确认没有意外文件、秘密或生成垃圾。
7. **Git 动作**：只有用户要求或当前开发流程明确授权时 commit/push。

## 快速任务

若用户给出明确文件/行和简单修改，不强制先 Serena；直接 Coding Tools 更高效。

## 调试

- 先复现或读取真实错误。
- 不把旧文档“已完成”当成当前代码事实。
- 找根因时 Serena 负责关系，Coding Tools 负责运行证据。

## Coding Tools 行编辑稳定性

- `apply_changes` 同一文件里的多条 line edit 都必须按**同一次 `read_file` 返回的原始行号**理解；前一条 insert/replace 不会让后续行号自动重算。
- 如果同一文件的多个修改彼此会改变结构或行数，优先改用 context-anchored `apply_patch`，或拆成“修改 -> 回读最新 revision/行号 -> 下一次修改”，不要把递增后的想象行号塞进同一个 line-edit 请求。
- 任何涉及函数/类边界、括号或大段替换的 line edit，写后立即回读受影响边界，再进入测试；发现结构异常时先修编辑结果，不把 parser/test failure误判成产品行为回归。

## Windows shell dialect 与命令副作用

- Coding Tools 的 `exec_command` 在 Windows 环境下必须按当前实际 shell 工作，不能因为机器安装了 PowerShell 就把每条命令默认写成 PowerShell。
- 当前命令若使用 cmd 语义，错误重定向使用 `2>nul` 等 cmd-native 写法；`$null`、`Measure-Object`、PowerShell object pipeline 等语法只能放进显式 `powershell -NoProfile -Command "..."` 调用。
- shell syntax、redirection 或管道命令 non-zero 后，固定先查后态：命令是否部分执行、目标文件是否改变、`git status --short` 是否出现新的 literal 文件/工具噪声。特别警惕 cmd 把 PowerShell token（例如 `$null`）解释为普通文件名。
- 如果失败命令新建了开工 pre-state 不存在、且可精确归因于该命令的工具噪声，只删除该精确噪声；不得用 `git clean`/广泛删除作为恢复手段。
- 修正 shell dialect 后仍留在同一 Coding Tools route，不把 shell 写法错误升级成跨 MCP fallback 理由。

## 版本控制保护

- 修改前读 `git status`。
- 不覆盖用户未提交改动。
- 不 reset/clean/force push 除非 P3 明确确认。
- 多 worktree/多分支环境优先确认 cwd、branch、HEAD。

## 完成证据

至少报告：改了什么、验证命令/测试结果、仍未验证的部分。

## Loop Engineering 下的代码阶段

若当前代码任务属于自动接力 loop：

### 开始

- 先读 `SKILL.md`、`routing.md`、`workflows/loop-engineering.md`、当前 stage prompt；
- `git status` / worktree / branch / HEAD / upstream；
- 检查前一会话新 commit/WIP；
- 确认当前会话是该 worktree 唯一 writer；
- 多窗口并行前先区分 MCP transport 并发与工作区状态并发：Coding Tools 可有多个 command/session，但同一 configured workspace/worktree 仍是一份共享写状态；并行 writer 必须拆独立 worktree/workspace。Serena 标准单进程也只有一个 active project，不允许不同窗口同时切不同项目。
- 第一条用户可见更新给出本棒 MCP Execution Map。

### 中间

- 大型/陌生代码关系优先 Serena semantic map（若可用）；
- Coding Tools 负责 exact source/tests/runtime evidence、修改、测试；
- 不把 research/grep/类名直接升级为架构事实；
- 工具失败遵循“查后态 -> 同工具适配 -> fallback”。

### 结束

- 完成当前 stage 验收，不越界吞掉下一 stage；
- 更新 live SoT、证据、进度；
- path-scoped diff/status；
- 形成必要 commit；
- 读取 `workflows/handoff-template.md`；
- 生成下一 stage Zero-Guess prompt，写入真实 HEAD/tests/dirty state/BLOCKED_ENV；
- 用 Playwright 完成下一会话 handoff。

如果产品工作完成但 handoff 失败，保留 commit 和 prompt，状态写 `STAGE_COMPLETE_HANDOFF_PENDING`，不得伪称完整 loop success。