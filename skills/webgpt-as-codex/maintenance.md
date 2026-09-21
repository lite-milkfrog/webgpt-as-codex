## 从真实失败沉淀通用规则

优先把“真实发生并且具有复用价值”的失败模式沉淀成通用规则，而不是给每次事故新增专用 workaround。

记录模板：

- 失败表象；
- 实际根因类别；
- 原策略为什么不稳；
- 更稳的同工具策略；
- 什么时候才应该跨工具 fallback；
- 是否需要新增 eval scenario；
- 后续模型升级后是否仍需要该规则。

例如：网页 `click()` 被 overlay 拦截，不应增加“改用 Windows-MCP 坐标点击”的规则；应增加“查后态 -> Playwright 内 DOM/keyboard/form 恢复 -> DOM 外才 Windows-MCP”的通用规则。

## Experience Absorption Loop

已验证的通用失败类别包括“表面健康但代次错误”：端口/listener/healthz 可以保持绿色，但长期运行的解释器仍加载旧模块/旧 route table，而磁盘静态资源已经更新。通用修复不是“看到端口就杀”，而是先证明 ownership/process identity，再比较 runtime generation 与 capability/resource contract；只有确定属于当前产品且 stale 才 bounded refresh。浏览器侧同理，用户桌面入口的正常 profile 与自动化 isolated/shared context 不应混成一套启动逻辑。

WebGPT-as-Codex 在真实任务中遇到新坑时，优先完成当前用户目标，但**恢复成功后必须做一次经验吸收判断**：

`RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE`

### RECOVER

先按现有恢复阶梯把当前任务救回来，不要为了写 Skill 中断主要任务。

### DISTILL

记录最小事实：

- 失败表象；
- 真正根因；
- 哪个原规则不够；
- 哪个替代策略实际成功；
- 成功证据是什么。

### GENERALIZE

判断它是否值得进入长期规则：

- 未来同类任务高概率再遇到；
- 不依赖当前项目一次性细节；
- 新规则能减少盲重试、错误工具路由或安全风险；
- 不会把一个偶发现象过拟合成全局约束。

若只是一次性项目细节，只写入项目 Decision/Session/Risk，不强行污染通用 Skill。

### PATCH

根据问题落到正确层：

- 工具职责/路由问题 -> `routing.md`；
- 网页恢复 -> `workflows/browser.md`；
- 代码流程 -> `workflows/coding.md`；
- 跨工具恢复 -> `workflows/cross-tool.md`；
- Loop/handoff -> `workflows/loop-engineering.md` / `workflows/handoff-template.md`；
- 权限边界 -> `permissions.md`；
- Skill 维护原则 -> `maintenance.md`。

### EVAL

每个进入长期规则的新坑至少增加一个 `evals/scenarios.json` regression scenario，覆盖“旧错误策略”和“新期望行为”。

### VALIDATE

运行 `scripts/validate_skill.py`。结构校验不通过时，Skill 迭代不算完成。

### PROPAGATE

如果当前任务属于 Loop Engineering：

- 更新当前项目里受影响的 routing/decision/risk/session 文档；
- 下一 stage prompt 写入新 Skill 版本和新增规则；
- 下一 worker 开始前重新加载 Skill；
- 不让新经验只停留在上一窗口聊天里。

## 自我迭代边界

允许在用户已授权的本地开发/自动接力范围内迭代 Skill 本地文件和项目执行规范，但：

- 不自动发布 Skill 到外部平台；
- 不自动安装到未授权环境；
- 不为了“学习”扩大用户原任务范围；
- 不记录密码/Token/Cookie 等秘密；
- 不把未经验证的猜测直接固化成规则；
- 如果新规则会扩大外部副作用权限，必须重新按权限模型判断，不得自行放宽。

## Handoff 漂移防护

Loop Engineering 的下一 prompt 必须始终从 `workflows/handoff-template.md` 实例化。若连续几棒后出现工具、路径、读取顺序、fallback 或 exit criteria 被省略，应视为 Skill regression，并新增/强化 eval，而不是只修当前 prompt。

# Maintenance and Skill Pruning

## 目标

Skill 应随模型能力进步而**变薄**，而不是只增不减。

## 何时增加规则

仅当满足至少一项：

- 真实失败重复出现
- 不同 MCP 能力重叠导致稳定误路由
- 存在设备特有约束（如高 DPI、特定登录态）
- 安全/权限边界需要明确
- 跨工具顺序对成功率有明显影响

不要把模型已经稳定掌握的通识写成冗长教程。

## 定期盲测

每次大模型或 MCP 重大升级后，对同一批任务做 A/B：

- A：不加载 WebGPT-as-Codex Skill
- B：加载 Skill

比较：

- 成功率
- 工具选择错误数
- MCP 调用次数
- 重复读取/重复动作
- 总耗时
- Token 消耗
- 风险动作/越权次数
- 用户纠正次数

如果某条规则在多轮测试中不再带来收益，删除或压缩。

## 变更纪律

- 新增规则必须注明来源：真实失败 / 新工具 / 新权限 / 环境变化。
- 不在核心 SKILL.md 堆供应商手册；细节进对应 workflow/reference。
- 环境特性放 `environment.local.md`，迁移时可替换。
- 秘密永不进入版本控制。

## MCP 变化

新增 MCP 时先回答：

1. 它是否提供现有工具没有的结构化能力？
2. 与谁重叠？
3. 应该成为 primary、fallback 还是 optional？
4. 权限比现有方案更宽还是更窄？
5. 是否值得增加路由规则？

只有答案明确后才扩展 Skill。