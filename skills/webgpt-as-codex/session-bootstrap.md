# WAC Session Bootstrap

本文件定义每个 WebGPT-as-Codex Agent session 的强制启动门。

## 何时触发

只要当前会话准备通过 WAC / WAC Unified Gateway / 已连接的 WAC MCP 能力对本机进行实质性读取、修改、自动化、测试、浏览器操作或 GUI 操作，就触发本门。

纯概念问答、不使用 WAC 本机能力时不触发。

## 必须执行的最小序列

1. 找到 canonical `webgpt-as-codex` Skill。
2. 读取 `SKILL.md`。
3. 读取 `routing.md`。
4. 如果任务涉及本机 MCP、路径、端口、连接恢复或运行态，读取 machine-local：
   - `MCP-SKILLS-INVENTORY.md` 或 JSON；
   - `environment.local.md`。
5. 如果任务是多阶段交付、开发工作流、设计/实现/QA 链路，读取 `workflow-registry.json` 并选择 Workflow。
6. 只加载当前 Stage 所需 leaf Skills / `mcp-guides/` / `workflows/`。禁止把整个 Skills 库一次性塞进上下文。
7. 如果当前 portable Skill 与 repository canonical core 漂移：
   - 先运行 `scripts/sync_webgpt_skill.py --check`；
   - 必要时同步；
   - 运行 `scripts/validate_skill.py`；
   - 验证后才能继续 substantive mutation。

## Bootstrap 前允许

只允许为完成 bootstrap 本身进行：

- WAC / MCP liveness probe；
- Skill / Inventory / environment 文件定位；
- 只读 Git/source identity 检查；
- 读取必要配置。

## Bootstrap 前禁止

- 修改代码或文档；
- 写入工作区；
- 浏览器提交/发送；
- GUI 点击/键盘副作用；
- 发布、push、删除、安装/升级外部组件；
- 用“上一窗口已经读过”或模型记忆代替当前 session 读取。

## 完成条件

当前 session 至少明确掌握：

- canonical Skill 版本；
- 当前 routing contract；
- 当前任务的 primary MCP / fallback；
- 若为复杂任务，当前 Workflow / Stage / required Skills；
- 本机相关任务所需的 machine-local locator。

完成后才进入实际执行。
