# WebGPT-as-Codex Skill（简体中文）

当前唯一正式 Skill 为上一级 `../SKILL.md`，版本 `1.4.0`。

本目录只保留中文辅助文档，不再存在独立的 Computer Agent sibling core。原 Computer Agent 的路由、权限、MCP Guides、GUI/Playwright 工作流、Loop Engineering、Experience Ledger 与回归场景已经无损并入 `skills/webgpt-as-codex/`。

## 读取顺序

1. `../SKILL.md`
2. `../product-contract.md`
3. `../routing.md`
4. 当前任务需要的 `../workflows/` 或 `../mcp-guides/`
5. 本机执行时再读取 machine-local `.skills/webgpt-as-codex/environment.local.md` 与 Inventory

每个新的 WAC Agent session 都必须重新完成 `../session-bootstrap.md`；不能因为上一窗口读过 Skill 就跳过。复杂任务按 Workflow/Stage 只加载需要的 leaf Skills，不一次性加载整个 Skills 库。

机器特定端口、路径、OAuth/Token、账号态和 transient health 不进入公开 Skill。
