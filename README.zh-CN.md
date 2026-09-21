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

我后来越来越确定一件事：**给 Agent 接上工具，只解决“它能不能碰到电脑”；真正决定它能不能长期干活的，是它有没有一套稳定的工作方法。**

> **MCP 给它手，Skill 告诉它怎么干，SoT 让项目不失忆，Loop Engineering 让它跨过一个又一个聊天窗口继续干。**

所以这里的 `skills/webgpt-as-codex/` 不是几条“遇到网页就用 Playwright”式的提示词。它是一套真正参与执行的 Agent 工作系统：工具路由、权限边界、失败恢复、单 writer、并发隔离、验证、Experience Ledger、regression eval、跨会话 handoff，以及长任务的 Loop Engineering 都在里面。机器自己的端口、路径、当前健康状态和 handoff receipt 则留在 machine-local overlay，不往公开仓库里塞私有状态。

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

## 配好一次以后，平时到底怎么用？

第一次部署需要把环境、OAuth、Tailscale、MCP 和 Skill 配好，但**这不是每天都要重来一遍的安装仪式**。

正常的日常用法应该很简单：

1. 第一次，把这个仓库和 [`prompts/ONE-CLICK-AGENT-DEPLOY.md`](prompts/ONE-CLICK-AGENT-DEPLOY.md) 交给能操作 Windows 的 Agent，让它把环境和服务配好；
2. 完成一次必要的账号登录、OAuth consent 和 ChatGPT MCP 连接；
3. 以后电脑开机，**双击桌面的 WebGPT-as-Codex 一键启动器**；
4. 启动器先通过 machine-local prestart 恢复已经批准的外部 MCP 后端，再启动/恢复 Gateway、OAuth Edge、Manager 等 WebGPT 服务，并做分层 READY 检查；
5. 已经健康的服务会被保留，不会因为你又点了一次 Start All 就重复拉一套；
6. READY 后直接打开 ChatGPT 开始干活。正常情况下，不需要重新填一遍 MCP 地址，也不需要每天重新部署。

换句话说，日常体验不应该是“开机以后先打开五六个终端窗口，挨个输命令”。应该是：

```text
开机
  ↓
双击一键启动
  ↓
自动恢复 / 保留健康服务
  ↓
READY
  ↓
打开 ChatGPT，直接说要做什么
```

如果你启用了 Windows 登录自启，很多服务甚至会先自己恢复；桌面 Start All 仍然是幂等的，可以安全地再点一次做统一收口和 READY 验证。

## Skill 不只负责“选哪个 MCP”

真正的长任务会按下面这条链跑，而不是靠聊天窗口记忆：

```text
Stage N
  ↓
读取真实 Repo SoT / Git HEAD
  ↓
执行 + 验证
  ↓
更新 SoT / decisions / risks
  ↓
commit
  ↓
生成并校验 Stage N+1 prompt
  ↓
Playwright 提交到新的 ChatGPT 对话
  ↓
确认下一窗口已经接管
  ↓
写入 machine-local handoff receipt
```

这里故意把两类状态分开：

- **Repository SoT** 是项目的长期事实和最终权威。聊天窗口关了，它还在；
- **machine-local durable state** 记录 CURRENT/NEXT/AFTER_NEXT、source HEAD、closure phase、prompt hash、handoff 结果和恢复证据，用来抗重启、抗断线、抗上下文丢失，但它不会取代仓库真相。

Loop Engineering 还要求把真正有复用价值的失败继续沉淀：

```text
RECOVER → DISTILL → GENERALIZE → PATCH → EVAL → VALIDATE → PROPAGATE
```

也就是说，Agent 不只是“这次绕过去就算了”。可复用的坑会进入 Skill / MCP Guide / regression scenario，下一棒默认继承。这不是模型参数意义上的自我训练，而是**工程经验被持续写进可验证的执行规则**。

## WAC × RDC：两条独立控制面，互相救援

WebGPT-as-Codex 和 Remote Desktop Commander 不是“主程序 + 一个附属插件”的关系。

```text
WebGPT-as-Codex
= 主结构化执行面
= 代码 / Git / 浏览器 / Windows GUI / Gateway / OAuth

Remote Desktop Commander
= 独立整机 repair / control plane
= 文件 / 终端 / 进程 / 日志 / 主机级恢复
```

刻意保持独立，反而是为了**互相救得起来**：

- **WAC 正常、RDC 挂了**：用 WAC 里的 Coding Tools / Windows-MCP / 已授权本地控制能力检查并恢复 RDC；
- **RDC 正常、WAC 挂了**：用 RDC 去看 Gateway、Coding Tools、OAuth Edge、Tailscale/Funnel、Manager、Playwright/Windows-MCP relay 和启动脚本，把 WAC 拉回来；
- **两边都正常**：日常结构化任务优先走 WAC，RDC 留在外面做整机级救援和补位；
- **两边都挂了**：回到本地桌面的一键启动、系统启动恢复或人工本机恢复。

一个已经不健康的控制面不会被拿来“修自己”，也不会形成 WAC → RDC → WAC 的死循环。RDC 仍然不是 Gateway 子进程，也不是 WAC READY 的硬前提；但在配置好的机器上，桌面 bootstrap 可以通过 machine-local prestart 把 RDC 等已批准的外部后端一起拉起。
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
- 唯一正式 Skill 为 `skills/webgpt-as-codex/`，保留完整 Experience Ledger、原有 53 个 regression scenarios、3 个 legacy compatibility aliases，并加入 R54 destructive-action authorization regression（当前总计 57），以及 MCP Guides；
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
