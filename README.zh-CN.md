# WebGPT-as-Codex

[English](README.md) | **简体中文**

> **把 ChatGPT 网页版变成一个真正能持续操作你本地代码和电脑的 Agent。**
>
> 一个 OAuth 保护的公网 MCP 入口，聚合 Serena、Coding Tools、Playwright、Windows-MCP；再配上本地 Skill、自动恢复、开机自启和 Loop Engineering。

**一次部署 · 一个 MCP 地址 · 一键启动 · 自动恢复 · 本地优先。**

> **不需要额外 API Token，不需要额外 API 账单。**
>
> WebGPT-as-Codex 的目标不是让你再买一份 API 算力，而是把你现有的 ChatGPT 计划、本地电脑、本地 MCP、浏览器和桌面能力组合起来，获得一定程度上的 **“算力自由”**。尤其适合 **Codex 额度不够、但你还想继续让 Agent 干活** 的时候：代码、测试、Git、浏览器、Windows GUI、自动化任务都可以继续走本地工具链。
>
> 经过本人长期实测，它已经能完成非常非常多的真实任务：仓库开发、测试与修复、Git 工作流、网页自动化、Windows 桌面操作、MCP 部署、OAuth 恢复、跨对话长任务接力等。

ChatGPT 本身仍然遵守你当前套餐和客户端的使用额度；这里的“不消耗 tokens”指的是 **不需要额外购买 OpenAI API Token / API 余额，也不会因为 WAC 本身再产生一份 API 调用账单**。只要你的 ChatGPT 客户端支持 MCP/Plugins，就可以基于你现有的计划使用这套本地能力。

WebGPT-as-Codex 解决的不是“怎么再接一个 MCP”，而是 MCP 多起来以后真正麻烦的部分：谁负责什么、怎么统一暴露给网页大模型、OAuth 怎么稳定、电脑重启后怎么恢复、多个窗口怎么不互相打架，以及长任务怎么跨对话继续而不丢状态。

## 最快的使用方式：把仓库交给 AI

不想手搓环境？直接把 [`prompts/ONE-CLICK-AGENT-DEPLOY.md`](prompts/ONE-CLICK-AGENT-DEPLOY.md) 交给一个能操作目标 Windows 电脑的 Agent。

它会按真实环境自动完成：

- 检测 Python / Git / uv / Node / winget / Tailscale；
- 发现并保留已有健康 MCP，避免重复安装；
- 部署/校验核心 MCP 与 Unified Gateway；
- 配置 OAuth + Tailscale HTTPS Edge；
- 安装桌面“一键启动”和 Windows 登录自启；
- 同步唯一的 `WebGPT-as-Codex` Skill；
- 执行 Doctor、OAuth、Gateway、启动幂等性和发布验收；
- 最后只把必须由人确认的账号登录/OAuth consent 留给你。

## 你最终得到什么

| 能力 | WebGPT-as-Codex 做什么 |
|---|---|
| **统一入口** | ChatGPT 只需要面对一个 OAuth-protected MCP Gateway，而不是分别维护一堆公网 MCP |
| **正确路由** | Serena 看语义，Coding Tools 改代码/跑测试，Playwright 操作网页，Windows-MCP 操作原生 GUI |
| **一键启动** | 桌面脚本和 Windows Autostart 先恢复本机后端，再启动 Gateway/OAuth/Manager，并做真实 READY 判定 |
| **断线自恢复** | 区分 process / listener / MCP / OAuth / public edge，不用“端口活着”冒充健康 |
| **长任务持续执行** | Loop Engineering 把 SoT、验证、commit、next prompt 和跨会话 handoff 变成可重复流程 |
| **并发不互踩** | 对 Serena project state、Git worktree writer、真实 GUI 焦点等共享状态设置明确边界 |
| **独立救援面** | Remote Desktop Commander 不塞进 Gateway，保留为整机 repair/control plane |
| **本地优先** | 密码、OAuth DB、Token、浏览器账号态和机器私有状态留在本机，不进入 Git |

## 30 秒架构

```text
ChatGPT / Web AI
        │
        │ HTTPS + OAuth 2.1 / PKCE
        ▼
 WebGPT-as-Codex Edge
        │
        ▼
  Unified MCP Gateway
   ├─ Coding Tools   → 改代码 / 测试 / Git
   ├─ Serena         → symbols / references / semantic navigation
   ├─ Playwright     → Web / 已登录浏览器
   └─ Windows-MCP    → Windows 原生 GUI

Remote Desktop Commander
   └─ 独立整机恢复与控制，不是 Gateway 的硬依赖
```

网页 Manager 只是控制面，不拥有运行时生命周期；关掉网页不会把 Agent 后端一起关掉。

## 手动安装

需要 Python 3.11+。如果你不使用 Agent-native Prompt，可以手动：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\webgpt-codex.exe --version
```

先看部署计划，再显式执行：

```powershell
webgpt-codex deploy
webgpt-codex deploy --apply
webgpt-codex desktop-launcher install
webgpt-codex autostart install
webgpt-codex launcher --no-open --start-all
webgpt-codex doctor
```

完整契约见 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)。

## 当前已经验证的关键行为

- Unified Gateway 可聚合核心 MCP，并通过 namespaced tool surface 暴露；
- 真实 HTTPS OAuth metadata、动态注册、PKCE、token、refresh 和 authenticated MCP 已做过端到端验收；
- 未授权公网 MCP 请求返回 401，而不是裸暴露工具；
- Start All 幂等，能 preserve 健康外部服务，不重复拉实例；
- OAuth Edge READY 不再只看 9340/9341 本地端口，还校验真实 Funnel 443 target；
- 桌面 launcher 与 Autostart 可安全升级、可逆、无凭据；
- 唯一正式 Skill 为 `skills/webgpt-as-codex/`，保留完整 Experience Ledger、原有 53 个 regression scenarios，并补回 3 个 legacy compatibility aliases（总计 56），以及 MCP Guides；
- Manager 提供中英文 UI、Doctor/Repair、版本/环境/Gateway/OAuth/HTTPS 状态，但普通状态接口不泄露 Secret。

## CLI

`webgpt-codex --help` 提供：

- `deploy`：组件发现、版本/兼容性判断与受控安装；
- `bootstrap`：fresh-machine prerequisite / 本机状态准备；
- `status` / `start` / `stop` / `restart`：受所有权约束的 Runtime Supervisor；
- `doctor`：分层深度诊断；
- `repair`：固定白名单、可回退的修复；
- `manager`：loopback-only Web Manager；
- `launcher` / `desktop-launcher` / `autostart`：启动与 Windows 集成；
- `add-mcp`：discovery-first MCP 扩展；
- `loop`：持久化 Loop Engineering 证据。

## 安全边界

Git / release artifact 不得包含 OAuth DB、Token、password、private key、cookie、browser profile、pairing data、私有机器 URL、PID/process transient state 或 machine-local handoff receipts。

WebGPT-as-Codex 不把“能执行命令”当成无限权限。Manager、Repair、Update、runtime lifecycle 都有固定 authority boundary；未知 listener 和用户自己管理的健康服务默认 preserve。

## 开发与验证

```powershell
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python scripts\secret_scan.py
```

项目状态与设计细节见 [`docs/CURRENT-PROJECT-STATE.md`](docs/CURRENT-PROJECT-STATE.md)、[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)、[`docs/DECISIONS-AND-RISKS.md`](docs/DECISIONS-AND-RISKS.md) 与 [`skills/webgpt-as-codex/SKILL.md`](skills/webgpt-as-codex/SKILL.md)。
