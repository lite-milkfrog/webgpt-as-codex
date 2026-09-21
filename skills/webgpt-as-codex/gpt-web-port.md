# GPT Web Port Plan

## 目标

核心 Skill 与本地 MCP URL 解耦。等各 Remote MCP 的固定 HTTPS/OAuth 接口收尾后，将相同路由/权限逻辑迁移到 GPT 网页端。

## 迁移前置条件

对每个需要注册到 GPT 的 MCP，确认：

- 固定 HTTPS URL
- OAuth/认证可持久化
- 重启后 URL 不变
- 工具列表稳定
- 权限 allowlist 已定
- 不暴露秘密
- 实测 initialize/tools/list 和至少一个真实只读调用

## 预期 GPT 侧角色

- Serena：代码语义
- Coding Tools：代码执行/编辑/Git
- Windows-MCP：原生 Windows GUI（限制工具集）
- Playwright：网页/Web App
- Desktop Commander：使用其官方 Remote/App 链路
- 可选 GitHub MCP：远端 repo/issue/PR/action

## 迁移方式

优先保持“多个独立 MCP + 一个 WebGPT-as-Codex Skill”，而不是先做万能 MCP 聚合器。

Skill 中不硬编码 URL；GPT 端通过已注册 MCP 的名称/工具描述识别能力。

## 迁移验证

用 `evals/scenarios.json` 在 GPT 网页端重复一遍路由测试，重点观察：

- 是否选对 MCP
- 是否因工具数量增加而犹豫/重复调用
- 是否遵循 P2/P3 确认
- 是否网页优先 Playwright
- 是否 Windows-MCP 避免旧坐标

## 何时考虑统一 Ingress/Gateway

只有当固定 Remote MCP 数量和 OAuth/端口维护开始显著复杂时，统一**接入层**（HTTPS/OAuth/path routing/logging），但工具仍保持独立命名空间；不要引入第二个 LLM 做智能路由。