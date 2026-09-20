# Supplemental 产品目标 — 2026-09-20

[English](../SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md) | **简体中文**

本文件是已接受 TERMINAL 状态之后重新开启实现的 canonical product delta。Stage 1-12 保持关闭；这里只拥有后来新增的需求。

## 产品结果

WebGPT-as-Codex 成为安装、发现、验证、操作并逐步把本地 MCP toolchain 路由到一个公开 ChatGPT-facing Gateway 的**单仓库入口**。

```text
ChatGPT
├─ Remote Desktop Commander（独立 rescue/control plane）
└─ WebGPT-as-Codex Unified Gateway
   ├─ Serena
   ├─ Coding Tools MCP
   ├─ Playwright MCP
   ├─ Windows-MCP
   ├─ future MCPs
   └─ WebGPT control/recovery capabilities
```

两条 ChatGPT 连接是互补关系，不互相替代。

## 部署体验

新 Agent 从本仓库开始，选择 English/Chinese，读取 deployment entrypoint 并执行契约。

Installer 必须：
1. mutation 前发现 host 与已有工具；
2. 保留健康服务；
3. 从 approved official source 安装缺失 system prerequisite；
4. 用仓库 adapter 安装缺失 MCP；
5. 部署时解析 latest stable，校验 provenance/compatibility，避免重复安装；
6. 不降级已经更新且兼容的安装；
7. provision WebGPT-owned Gateway/OAuth runtime dependency；
8. 分别验证 process/listener/MCP protocol/tools/safe-call；
9. 配置 unified local Gateway；
10. 配置 OAuth + Tailscale HTTPS；
11. 提供 loopback Web Manager + one-click desktop launcher；
12. 只把真正 interactive 的账号/授权步骤留给用户。

## 人工介入边界

### Remote Desktop Commander
在 ChatGPT 侧安装/连接官方 integration，必要时登录并 pair machine。

### Unified Gateway
把唯一 public HTTPS MCP endpoint 添加到 ChatGPT，并完成真实 browser OAuth。成功标准是 ChatGPT web flow 正常返回，而不是只有本地 curl/token 通过。

fresh Tailscale account 可能要求浏览器登录/授权，但其前后的确定性配置仍由 deployment system 负责。

## Existing-machine migration

每个 component：
- discover before install；
- healthy existing -> preserve；
- absent -> install；
- older compatible -> controlled upgrade；
- newer compatible -> preserve + test；
- unhealthy -> diagnose before replace；
- 只有 WebGPT 明确 ownership evidence 后才授予 lifecycle authority。

Routing ownership 与 lifecycle ownership 分离。已有 external MCP 可以先路由进 WebGPT Gateway，而不改变其 start/stop 所有权。

## Gateway contract

```text
local MCPs
  -> MCPJungle
  -> mcp-auth-proxy
  -> OAuth compatibility adapter
  -> Tailscale Funnel HTTPS
  -> one public /mcp endpoint
  -> ChatGPT
```

不要求每个 backend MCP 自己开 public tunnel。Coding Tools 可只在 localhost 运行；其可选 Cloudflare client 不是 WebGPT 必需依赖。

## Complementary fallback

Unified Gateway 与 Remote Desktop Commander 是独立 rescue path：
- Gateway/backend 出错但 RDC 可用：RDC 检查/恢复本地服务，再重试 structured MCP；
- RDC 出错但 Gateway 可用：通过 Gateway-routed Windows-MCP/Coding Tools/WebGPT 能力在权限允许时恢复 RDC；
- 两边都不能绕过 authentication/security policy；
- transport/backend/tool-call failure 分开判断；
- 外部 side effect exactly-once，先证据后 mutation；
- public WebGPT endpoint 整体失效时不能自救，因此独立 rescue selection 由 Agent/Skill 层承担一部分。

## Concurrency contract

- Serena：标准 server process 只有一个 process-wide active project；不同项目的并发窗口必须使用 isolated fixed-project instance/slot。
- Coding Tools：请求/process 可重叠，但一个 server 绑定一个 workspace；并行 writer 必须 worktree/workspace 隔离或写串行。
- Remote Desktop Commander：terminal/filesystem/process 可并行；mouse/keyboard/focus 等实体 GUI 是共享 singleton，需要 GUI side-effect serialization。
- Playwright：独立 page/context 可并行；同一 page/profile/login state 遵循 one-writer。
- Windows-MCP：原生 GUI 共享焦点，不默认安全并行。

## Repository/source model

仓库是唯一 deployment authority，保存 component manifests、官方 upstream/source metadata、installer/provision adapter、version/compatibility rule、config template、health tests、routing/lifecycle contract、WebGPT-owned code/UI。

无需 vendoring 整个第三方 source tree。第三方 attribution/license/provenance 放在 dedicated metadata/notices，不挤入产品 README。

## Bilingual product

项目必须发布：
- English source/release experience；
- 完整中文镜像且功能等价；
- 当前用户的 desktop Manager 默认中文；
- Manager 可切换语言且功能不分叉。

identifier、command、URL、schema key、hash、protocol constant 在语言间保持精确不变。

Stage17 已完成 Manager/desktop 部分。Stage18 负责仓库级 documentation/release mirror 与 third-party notices。Stage17 Hotfix 进一步保证“9200 listening”不能单独证明当前 runtime generation，并把普通 desktop URL opening 与 Playwright automation profile 分离。

## Stage 19 产品目标对齐

生产 Gateway contract 已在 canonical HTTPS 443 上真实验证：9341 compatibility edge、9340 OAuth proxy、9330 Gateway。readiness 是端到端的；只有 9340 child 存活不能算完整 ready。

真实 recovery path 只有在 canonical issuer 匹配时才复用兼容 OAuth child，然后恢复 managed 9341 Edge，不改变 public identity 或 credential。runtime receipt 跟随真实 listener PID，不把 Windows venv launcher wrapper 当最终 identity。

生产验收通过 public OAuth metadata、401 protection、DCR/PKCE、authenticated 87-tool MCP、controlled Edge restart、refresh continuity、restart 后 authenticated MCP。随后用户确认 ChatGPT connector 配置成功；从该时点开始冻结扰动性 production acceptance，后续只做 reconciliation/release-readiness，不再反复 churn connector。
