# WebGPT-as-Codex

[English](README.md) | **简体中文**

WebGPT-as-Codex 是一个本地优先的控制平面，用于让网页 AI 客户端通过 MCP 成为可持续工作的代码/电脑 Agent。仓库状态是公开安全的事实源；机器本地运行状态、凭据以及浏览器/账号状态始终留在 Git 之外。

## 架构

已验证的实现分为：
- **Agent 平面：** 项目 SoT、WebGPT-as-Codex Skill、Loop Engineering 和已验证的递归交接。
- **控制平面：** bootstrap、组件注册表、Doctor/Repair 与 loopback Manager。
- **运行平面：** Serena、Coding Tools MCP、Playwright MCP、Windows-MCP。
- **Gateway 平面：** 以 MCPJungle 作为可替换的本地聚合器。
- **Edge 平面：** compatibility adapter -> mcp-auth-proxy -> MCPJungle，并通过 Tailscale Funnel 发布。
- **可选整机平面：** Remote Desktop Commander。

浏览器 UI 不拥有运行时生命周期。健康状态按层报告，不能把“进程/监听器存活”误当成 MCP、OAuth 或远程链路健康。

## 安装

需要 Python 3.11+。

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\webgpt-codex.exe --version
```

wheel 包含公共组件清单、英文/中文 Manager HTML 及其共享 CSS/JavaScript，以及 Stage18 定义的双语公开发布/法律/provenance 资源。机器本地状态在安装包之外创建。

开发环境：

```powershell
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python scripts\secret_scan.py
```

## CLI

`webgpt-codex --help` 暴露以下受支持的命令面：

- `paths`：显示机器本地状态根目录。
- `status`、`start`、`stop`、`restart`：有界 Runtime Supervisor 操作。
- `doctor`：具备先决条件意识的深度健康检查。
- `repair`：带确认/备份的固定白名单修复操作。
- `bootstrap`：发现优先的状态/bootstrap 规划。
- `manager`：仅 loopback 的 Manager UI/API。
- `launcher`、`desktop-launcher`、`autostart`：Windows 启动器集成。
- `add-mcp`：发现优先的通用 MCP 接入；默认 dry-run，显式执行机器本地 apply。
- `loop`：持久化的 Loop Engineering 执行/收口证据。

Manager 操作只能使用固定契约。Start/Restart 受仓库运行时所有权约束。Stage 11 的 Update 是仓库批准、默认离线的能力：只能消费仓库已声明组件/版本/来源/digest/目标权限且已预先暂存的 artifact。

## 已验证行为

Stages 0-11 及后续补充链已经建立并回归验证了：
- 通过四个核心 MCP 后端提供一个 Gateway endpoint；
- 真实公网 HTTPS OAuth metadata、DCR + PKCE、refresh 与 authenticated MCP calls；
- 未授权的公网 MCP 请求以 HTTP 401 拒绝；
- loopback Manager 的浅轮询、输出净化与 Host/Origin/action-schema 加固；
- 英文/中文 Manager 功能等价：共享功能实现，显式 `/en` / `/zh`，公开安全的环境/部署/版本/Gateway/OAuth/HTTPS/库存信息，URL 复制/打开，以及 reduced-motion/accessibility；
- discovery-first Bootstrap、deep Doctor 和 allowlisted Repair；
- PID birth/image 所有权检查、幂等 Start All 与有界 Restart；
- 可逆、无凭据的桌面启动器/autostart，当前部署默认中文；
- stale-Manager generation/contract 检测，避免“旧 Python 路由表 + 新静态资源”的混合版本；不相关或身份不明的监听器不被终止；
- 桌面 Manager 打开复用用户正常运行的 Edge profile（或 Windows 默认 URL handler），不会创建 automation-only 空白 profile；
- 通用 Add MCP 的 capability-evidence 状态与可移植 Operating Guides；
- 持久化 Loop Engineering 与 exactly-once Playwright handoff；
- 原子机器本地状态写入、不可信自定义 manifest 校验与有界 rollback；
- 仓库批准的 Manager Update 权限。

Manager 的本地凭据控制受 loopback/confirmation 约束。普通 status 从不返回 OAuth password；显式 Reveal 只在当前本地响应返回明文；Set/Regenerate 不回显，Regenerate 生成新值，activity feed 从不记录明文凭据。添加自定义 MCP candidate 只改变本地 registry 可见性，不自动获得 Gateway route 或 runtime lifecycle authority。

## 公开安全发布边界

Git 与发布 artifact 不得包含 OAuth 数据库、token、password、private key、cookie、browser profile、pairing data、私有机器 URL、本地状态 receipt、handoff receipt、PID/process state 或机器特定私有路径。

wheel 有意携带运行时 Python 代码、公共 component manifests、Manager 静态 UI、Stage18 的双语/legal/provenance release resources，以及安装到 `share/webgpt-as-codex/skills` 的统一 Agent Skill 1.2.0 portable profiles。Stage closure/prompt 与机器本地运行证据不进入 installed Skill/runtime surface。本机 Computer Agent 与发行版共享同一 portable 1.2.0 core，只额外叠加 environment/inventory/state 等 machine-local overlay。

参见 [中文架构](docs/zh-CN/ARCHITECTURE.md)、[中文当前状态](docs/zh-CN/CURRENT-PROJECT-STATE.md)、[中文决策与风险](docs/zh-CN/DECISIONS-AND-RISKS.md) 和 [中文 Skill](skills/webgpt-as-codex/zh-CN/SKILL.md)。
