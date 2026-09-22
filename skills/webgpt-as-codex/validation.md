# Validation

## 任务完成检查

### 路由

- 是否用了最结构化、最窄权限的工具？
- 是否存在不必要的重复 MCP 调用？
- 是否把网页交给 Playwright、原生桌面交给 Windows-MCP？
- 代码理解/修改是否合理区分 Serena 与 Coding Tools？

### 状态改变

- 动作是否真实执行？
- 是否验证后态？
- 超时/报错后是否先查询而非直接重试？
- 是否避免重复提交/发送/下载？

### GUI

- Windows-MCP 操作前是否观察当前状态？
- UI 变化后是否重新 Snapshot？
- 是否优先元素/快捷键而非旧绝对坐标？
- 错点后是否停止盲点？

### 权限

- P2/P3 是否有足够授权？
- 是否意外输出秘密？
- 是否通过另一个 MCP 绕过了安全门？

### 代码

- 是否保护未提交改动？
- 是否运行相关测试/构建？
- 是否检查 diff？

### 自适应恢复

- 第一次调用失败后，是否先查询后态？
- 是否区分了“某个 interaction primitive 失败”和“整个 MCP 不可用”？
- 是否优先在同一 MCP 内换策略，而不是立刻跨 MCP？
- 是否避免原样重复同一个失败动作？
- 是否没有通过更宽权限工具绕过安全门？
- 若出现新的可复用坑，是否在恢复后做了 experience absorption 判断？
- 若新经验进入通用 Skill，是否有对应 regression scenario 并通过 validator？

### Loop Engineering（启用时）

- 当前 stage 是否有唯一主目标和明确 exit criteria？
- 是否先读 `.skills/webgpt-as-codex/SKILL.md`、`routing.md`、`workflows/loop-engineering.md`？
- 是否在第一条执行更新里报告 MCP availability / 用途 / fallback？
- 是否遵守同一 worktree 单 writer？
- 是否更新真实 SoT、阶段进度和总进度？
- 是否读取 `workflows/handoff-template.md` 后再生成下一 prompt？
- 下一 prompt 是否明确：工具、路径、必读文件、读取方式、使用方式、fallback、tests/gates、exit criteria、handoff？
- 是否禁止使用“相关文件”“合适工具”“按需处理”等让下一 worker 猜测的表述？
- next prompt 是否基于最新 HEAD/tests/dirty state/BLOCKED_ENV，而不是提前写死？
- Playwright handoff 是否验证 prompt 完整性？
- Playwright handoff 是否在同一 `mcp-session-id` / persistent context 内完成 target discovery、fill、submit、verify，而不是把 session-scoped 长链拆成会换 relay 的独立 connector calls？
- 自动 handoff 是否只有一个 mutation owner（canonical helper / 等价事务客户端），而没有 helper 与 direct connector 同时开页/填充/提交？
- 恢复是否绑定 exact whitespace-normalized prompt SHA-256，而不是把“任意 `/c/` + 任意 user message”当成目标 handoff？
- submit primitive 前是否先写 machine-local `SUBMIT_ATTEMPTED` write-ahead receipt；如果 receipt 已到 `SUBMIT_ATTEMPTED`/`SUBMITTED`，即使用户关闭 tab/连接断开是否仍禁止 blind resubmit，并优先恢复证明先前尝试后态？
- 如果上一调用已成功创建 ChatGPT、下一调用只见 Welcome，是否先证明/排除 `OBSERVER_SESSION_CHURN`，而不是继续多开页面？
- submit/click 超时后是否先查后态？
- 是否验证下一 conversation 已接管？
- 是否清理本轮 Agent 自己创建且未使用的空白/重复 handoff tabs，同时保留用户原有 tabs 和已接管 conversation？
- 若本 stage 迭代了 Skill，下一 prompt 是否明确新版本、规则路径与新增 scenario，而不是只写“已优化”？

## Skill 本身验收

最低场景集见 `evals/scenarios.json`：

- ≥2 个应触发场景
- ≥1 个不应触发近邻场景
- ≥1 个权限阻塞场景
- ≥1 个跨工具场景
- ≥1 个高 DPI GUI 场景
- ≥1 个网页优先 Playwright 场景
- ≥1 个 Playwright 同工具恢复场景
- ≥1 个 Loop Engineering 自动交接场景
- ≥1 个 Zero-Guess handoff 场景
- ≥1 个单 worktree 写入冲突防护场景

运行 `scripts/validate_skill.py` 做结构检查。该脚本只验证文件结构/链接/场景 schema，不替代真实 MCP 行为测试。