# Skills Manager MCP

Skills Manager 是 WAC 的本地 Skills + Workflow canonical backend。

## 职责边界

- Skills Manager：Skill 扫描、权威版本、Router/Composite 递归解析、Workflow、Run、Gate、Evidence、Manager UI。
- WAC：进程监管、Gateway 注册、工具路由，以及浏览器 / 桌面 / Coding Tools 的真实执行。
- 不要在 WAC 内再造第二套 Workflow executor。

## 运行端点

- MCP：`http://127.0.0.1:8943/mcp`
- Manager UI：`http://127.0.0.1:8955/`
- 为兼容现有部署，component ID 保持 `skills-control-plane`。
- Agent 执行不依赖打开 Manager 前端。

## Agent 调用顺序

1. 用 `skills_search` 做能力发现。
2. Router / Composite Skill 用 `skills_resolve`，递归读取必要 routes/resources。
3. 用 `workflow_list/search/get` 找当前 Workflow。
4. 用 `workflow_plan` / `workflow_prompt` 编译执行上下文。
5. 用 Run 工具持久化阶段、证据、阻塞、恢复与完成状态。

禁止只读取顶层 `SKILL.md` 后把 Composite Skill 拍扁。

## 当前生产 Workflow

独立仓库版本化维护：

- Frontend Product Builder v4
- Creator Studio v4

Workflow JSON 真源位于独立 `skills-manager/workflows/`，不复制进 WAC。

## 安装 / 更新

在 WAC 仓库执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_skills_manager.ps1 -Update
```

若 Skills Manager worktree 有未提交改动，安装器会拒绝自动更新，避免覆盖本地工作。
