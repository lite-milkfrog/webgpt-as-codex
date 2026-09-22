# Skill Workflow Control Plane — 单一事实源

STATUS = ACTIVE_IMPLEMENTATION

CURRENT_STAGE = WCP-02-MANAGER-API-AND-HOST-INTEGRATION
NEXT_STAGE = WCP-03-WEB-MANAGER-UX
AFTER_NEXT_STAGE = WCP-04-WEB-MANAGER-BROWSER-ACCEPTANCE

BASE_REPO = lite-milkfrog/webgpt-as-codex
BASE_MAIN = c3884abecbb6644fb33c353f67fc76b895d44454
WORK_BRANCH = feat/skill-workflow-control-plane-clean-20260922
START_DATE = 2026-09-22

## 1. 产品目标

搭建位于单个 Skill 之上的编排层。

系统必须依靠可持久化真值，而不是聊天记忆，回答：

1. 这台机器上有哪些 Skills？
2. 它们属于哪些分类？
3. 它们真实位于文件系统哪里？
4. 当前有哪些 category router 引用了它们？
5. 某个任务应该使用哪个 Workflow？
6. 当前处于哪个 Stage？
7. 当前 Stage 哪些 Skills 是 required / optional？
8. 进入下一 Stage 前需要哪些 evidence / gate？
9. 哪些状态能跨重启或新 ChatGPT 窗口保存？
10. 本地 Manager 怎样查看和控制这些状态，同时不成为新的真值源？

网页 UI 明确放在最后。它只能读取和操作这套系统，不能重新定义系统。

## 2. SoT 模型

必须保留两层真值。

### Repository SoT

由仓库拥有，可版本化、可审查：

- Workflow registry 与 schema；
- Workflow Stage / Skill / gate 定义；
- 路由策略；
- 安全边界；
- control-plane 实现；
- 测试与发布行为。

Canonical 文件：

- `skills/webgpt-as-codex/workflow-registry.json`
- `skills/webgpt-as-codex/workflows/*.md`
- `src/webgpt_as_codex/skill_workflow.py`
- 本文档。

### Machine-local SoT

只属于本机，不进入公开 Git 历史：

- 已发现的 Skill roots 与真实路径；
- 逻辑分类/顺序覆盖；
- Workflow run 状态与 evidence；
- 打开文件夹等 host-specific 操作。

Canonical 状态：

`state_root()/skills/control-plane.json`

Workflow runs：

`state_root()/workflow-runs/*.json`

本机路径只能通过 loopback Manager API 暴露。

## 3. Skill 模型

每条 Skill 记录包含：

- 稳定本地 ID；
- slug / 文件夹名；
- display name 与 description；
- kind：category-router / skill / reference-skill；
- entrypoint：SKILL.md 或 REFERENCE.md；
- 逻辑分类；
- 分类来源；
- 顺序位置；
- 从 router 推导出的分类关系；
- primary path 与 resolved path；
- 所有可见 root 位置/别名；
- link/junction 证据；
- 被哪些 Workflow / Stage 使用。

默认扫描：

- `~/.agents/skills`
- `~/.codex/skills`
- WebGPT 包内 `skills/`

本地部署/测试可用 `WEBGPT_CODEX_SKILL_ROOTS` 覆盖。

## 4. 分类与移动策略

“移动”分成两类，不能混淆。

### Logical move — 已实现

在分类之间拖动/重新分类 Skill，只修改 machine-local overlay 和排序。

它不会移动真实 Skill 文件夹。

原因：当前 category-router 使用指向平铺 shared Skill root 的相对路径。盲目物理移动会破坏 routes 与全局 junction。

### Physical relocation — 已实现，等待真机验收

跨 root 的真实文件移动现在采用两阶段安全事务：

1. 只接受已扫描 Skill ID 与 target root ID；
2. category router、link/junction、alias、多份同 slug 冲突直接拒绝；
3. 计算受影响的 category-router references；
4. 验证目标 root、目标 router 与路径冲突；
5. 先返回只读 relocation plan；
6. 真正写盘前必须 explicit confirmation；
7. 单次 move，并同步 source/target routes；
8. 重新扫描验证 entrypoint 与 route membership；
9. 任一步失败回滚 routes、文件位置与 local overlay。

Manager 仍不允许浏览器传入任意 filesystem path 执行 relocation。

## 5. Workflow 模型

Workflow 属于 Repository SoT，由有序 Stages 组成。

每个 Stage 可以定义：

- id/title；
- optional context condition；
- required/optional Skill selectors；
- outputs；
- supporting WAC workflow docs；
- gate requirements。

Condition 只能是声明式布尔条件，禁止任意代码、eval、JavaScript 或 shell expression。

Planner 状态：

- `ready`：required 和已选择 optional Skills 都存在；
- `degraded`：required Skills 存在，但至少一个已选择 optional Skill 缺失；
- `blocked`：至少一个 required Skill 缺失；
- `skipped`：Stage condition 未激活。

首批 canonical workflows：

- `web-product-build`
- `screenshot-to-frontend`
- `existing-ui-redesign`
- `long-running-engineering`

Registry 后续可扩展到 research、writing、PPT、image/video、Obsidian、CAD 等能力域。

## 6. Run state

Workflow run 是 machine-local 的持久执行证据。

每个 run 保存：

- run ID；
- workflow ID；
- context；
- created/updated timestamps；
- current Stage；
- run status；
- 各 Stage planner result；
- selected Skills；
- gate；
- evidence list。

Stage 状态：

`pending / in_progress / passed / failed / blocked / skipped`

Run state 必须能跨 Manager/浏览器关闭和 ChatGPT 会话切换继续使用。

未来 Stage 即使 planner-`blocked`，也不能提前阻塞当前 Run；只有推进到该 Stage 时才变成 runtime `blocked`。依赖恢复后允许原 Run refresh 并继续。

## 7. Manager 集成合同

现有 WAC Manager 继续保持 loopback-only。

API：

- `GET /api/skills`
- `POST /api/skills`
- `GET /api/workflows`
- `GET /api/workflow-runs`
- `POST /api/workflow-runs`

Manager mutation 必须沿用现有安全合同：

- loopback host/origin gate；
- `X-WebGPT-Control: 1`；
- bounded JSON body；
- 固定 allowlist fields；
- 本地变更要求 explicit confirmation；
- mutation lock；
- activity record。

打开 Explorer 时只能把已知 Skill ID 解析到扫描得到的路径。浏览器不能直接提供任意路径。

## 8. Frontend 顺序

不能先做新 UI。

固定顺序：

1. control-plane schema 与 SoT；
2. Skill discovery/classification；
3. Workflow registry/planner；
4. durable run state；
5. Manager API；
6. automated tests；
7. 在用户真实 shared Skills 上做 host verification；
8. 之后才开始 UI 设计；
9. 实现 Skill browser + 分类 + 拖动/reclassify + location/open；
10. 实现 Workflow graph/run UI；
11. browser acceptance。

Stage 1–7 稳定前，不开始新的管理端视觉层。

## 9. 当前证据

Clean integration branch 已实现：

- core：
  `src/webgpt_as_codex/skill_workflow.py`
- canonical Workflow registry：
  `skills/webgpt-as-codex/workflow-registry.json`
- headless CLI：
  `webgpt-codex skill-workflow ...`
- loopback Manager Skills / Workflows / Runs API；
- Workflow schema 与 WAC canonical routing 接线；
- targeted tests 与专用 control-plane CI；
- relocation plan + confirmed physical relocation transaction，并带 route patch 与 rollback。

并发恢复事实：

- 原 feature branch 被其它并发流程回拨到 `main`，PR #1 被关闭；
- 已保留原提交对象，没有 force-push 覆盖别人的工作；
- 当前从最新 `main` (`c3884ab...`) 重建 clean branch，并保留 WAC 1.3.1 / Playwright handoff 的最新规则。

仍不得宣称完成：

- 当前聊天无法直连本机 WAC developer MCP；
- RDC execution plane 当前离线；
- clean integration branch 还需要新的 PR CI 结果；
- Windows 真实 Skill root 尚未通过新 scanner 做 host verification；
- Explorer 打开动作与 physical relocation 尚未在用户 Windows 主机实测；
- 新管理端前端尚未开始。

## 10. Exit criteria

WCP-01 的关闭条件：

- Skill scanner 覆盖平铺 Skills、category routes、duplicate/junction aliases；
- logical move/category state 可持久化；
- Workflow registry 可验证并解析 required/optional/conditional Skills；
- run state 可 start / refresh / transition / persist / reload；
- targeted unit tests PASS；
- full suite 中不存在由本次变更引入的回归。

WCP-02 只有在 clean branch CI 全绿，并且 Manager API、真实 Windows Skill scan、Explorer open-folder 与 relocation 安全路径都完成真机验证且不打断 WAC 后关闭。

WCP-03 只能在 WCP-02 真机验收完成后开始。
