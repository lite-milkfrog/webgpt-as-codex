# 部署契约

[English](../DEPLOYMENT.md) | **简体中文**

## 入口

Agent/用户只从本仓库开始。部署路径由仓库根据实际发现到的机器状态决定。部署必须 discovery-first、idempotent、version-aware。

Stage15 component lifecycle 规划命令：

```powershell
webgpt-codex deploy
```

默认 dry-run，只报告 preserve/install/upgrade/diagnose/manual，不修改服务。`--apply` 安装缺失 component，并升级已由 WebGPT 安装且停止的 component。停止的旧 external install 仍需显式 `--adopt-external` 才能受控升级/收养；运行中的 external service 不会被静默接管。

## Phase 0 — 语言与仓库事实

1. 选择 English 或 Chinese。
2. 读取 `AGENTS.md`、本文件、`docs/CURRENT-PROJECT-STATE.md`、`docs/ARCHITECTURE.md`、WebGPT Skill。
3. 不把上一台机器的 installed state 当作 fresh-machine prerequisite。

## Phase 1 — 环境门禁

至少检测：
- Windows support level；
- Python >= repo minimum；
- Git；
- 需要时 Node/npm；
- 需要时 uv；
- winget；
- Tailscale installation/version/login/online/MagicDNS/Funnel；
- WebGPT state-root 可写；
- reserved port/conflict；
- WebGPT-owned MCPJungle / mcp-auth-proxy binary。

只有 environment report 明确 ready 时才能声称 Edge ready。

## Phase 2 — system dependency bootstrap

缺 prerequisite 时只走 allowlisted official source；健康已有项保留。

Tailscale：
- absent + winget -> approved `Tailscale.Tailscale`；
- installed but old -> controlled upgrade；
- logged out/offline -> 请求 account login；
- online -> preserve；
- Funnel/HTTPS unavailable -> 阻止 public-edge success 并给精确 next action。

## Phase 3 — WebGPT private runtime provisioning

Gateway/Edge runtime dependency 由 WebGPT 管理。缺失 approved artifact 从官方 release 下载，SHA-256 验证后放在机器本地 WebGPT state root。repo 中的 bootstrap baseline 只是已批准基线，不代表永远最新；部署时解析 current stable、比较 compatibility、通过测试后再 promotion。已有 binary 默认保留。

## Phase 4 — MCP inventory 与部署

每个 declared MCP：
1. detect installation；
2. detect process/listener；
3. 安全时 detect installed version；
4. 经 component adapter 查询 upstream latest stable；
5. 可达时 MCP initialize + tools/list；
6. 只调用 manifest-declared safe tool；
7. 分类 preserve / install / upgrade / diagnose / incompatible；
8. 只有 component-specific authority 建立后才 mutation。

不能因为 PATH 中没有 package executable 就重复部署一个健康 instance。

自动安装 channel 明确限定：
- Python MCP：`uv tool`；
- Node MCP：global npm；
- Windows prerequisite：allowlisted winget id；
- WebGPT private binary：official GitHub Release asset + expected identity + SHA-256；
- Remote Desktop Commander 等 hosted/account-pairing integration：deployment report 中显示 manual/authenticated action。

每个自动 adapter 还声明所需 toolchain 与 compatibility window。

installed version、upstream latest、verified compatibility 是独立字段。resolver unavailable 时保持 unknown/blocking；latest 越界时阻止 install/upgrade；已有更新且兼容的版本保留，不降级。

成功 latest lookup 最多缓存 24h，只能重用仍 fresh 且已验证的 evidence；GitHub binary cache 还必须保留 repository asset URL/name/SHA-256。无 valid cache 时 latest 保持 unknown/blocking。缓存 evidence 不能授权 install/upgrade。

fresh machine 缺 uv 或 Node/npm 时，adapter 可经 approved winget 安装所需 toolchain；但如果目标 MCP 已健康，PATH/toolchain 缺失不授权 duplicate install。

只在兼容版本域内做 version compare。不同 product/server 版本族不能仅因都是 dotted number 就比较。

禁止用 `npx package@latest --version` 推断 installed version；它会测/拉 upstream latest。installed evidence 应来自 package-manager metadata、owned receipt、known local binary 或真实 local version command，否则保持 unknown。

## Phase 5 — unified local Gateway

start/preserve MCPJungle。把健康、enabled 的 Streamable HTTP MCP 注册为 WebGPT 私有 Gateway upstream route。route registration 不得改上游 MCP 自己的 config。

初始 migration 可为：
- routing ownership = WebGPT；
- lifecycle ownership = external/preserved。

以后只有经验证的 WebGPT-installed component 才可能获得 lifecycle ownership。

## Phase 6 — OAuth + HTTPS Edge

启动 production Edge：
- private Gateway；
- OAuth proxy；
- compatibility adapter；
- Tailscale Funnel HTTPS。

OAuth credential 只存在机器本地 WebGPT state/secrets。Web Manager 可暴露 status 与显式本地 credential control，但 static asset/repo 不嵌 secret。

## Phase 7 — 深度验证

健康层级依次但独立：
1. process；
2. listener；
3. MCP initialize；
4. tools/list；
5. safe tool call；
6. OAuth metadata；
7. DCR + PKCE；
8. token exchange；
9. protected unauthenticated 401；
10. refresh token；
11. authenticated MCP call；
12. public HTTPS reachability。

低层 green 不证明高层 green。

## Phase 8 — desktop/control plane

安装/刷新透明 one-click `WebGPT-as-Codex.cmd`。repo-managed Desktop launcher 默认 `WEBGPT_CODEX_UI_LANG=zh-CN`；`/en` 和 `/zh` 保持显式路由。

Manager 两个语言页共享同一 JavaScript/CSS control contract，必须展示 environment/deployment readiness、component/version inventory、Gateway route、local/public MCP URL、OAuth local control、Tailscale/HTTPS、backend health、migration/lifecycle ownership、recent action/recovery feedback。

local-config/status 只暴露 configured/readiness，不暴露 plaintext OAuth secret、executable/secret path、private Tailscale DNS。Reveal/Set/Regenerate 是显式 loopback confirmed operation；Regenerate 必须改变值；activity 不得包含明文。

custom migration candidate add/remove 只改 registry visibility，不 apply Gateway route、不 start/restart runtime、不授予 lifecycle authority。built-in deletion 拒绝。

managed launcher 只有在完整已知历史 WebGPT structure 匹配时才可 upgrade；marker 单独不足。

Browser UI 不拥有 runtime lifetime。

Manager liveness 与 generation 分离。活着的 9200 listener/healthz 不证明它已载入当前 Python route table 或 UI contract。reuse 必须有 ownership/process identity + runtime-generation/resource capability；严格识别的 legacy WebGPT Manager 才可 stale refresh；unrelated/ambiguous listener 保留并报告。

Desktop launcher 是普通用户浏览入口，不是 Playwright runtime。已有正常 Edge 时复用 last-used normal profile，否则通过 Windows default URL handler；不创建 temp user-data dir、isolated automation profile 或 InPrivate session。

只属于当前电脑的一键附加能力不得硬编码进 release launcher。手动 Desktop launcher 只识别一个固定本机扩展文件 `%LOCALAPPDATA%\WebGPT-as-Codex\local-launcher-overlay.cmd`，且只在 WebGPT 已经 READY 后调用；fresh install 默认没有该文件，Windows 登录 autostart 不调用它，overlay failure 也不会降级 WebGPT READY。

## Phase 9 — 最终人工步骤

对于 fresh deployment，只剩真正 interactive 的账户/浏览器授权：
1. Remote Desktop Commander：ChatGPT 侧安装/登录/pair。
2. Unified Gateway：把唯一 public MCP URL 加到 ChatGPT，并完成真实 OAuth browser flow。
3. fresh Tailscale account 如需登录/permission approval，按提示完成。

当前已接受主机上，RDC pairing 已不再 pending：恢复后的 fixed 0.2.51 runtime 已通过 connector-side `list_devices`、`ping`、`get_config` 和 read-only host probe。未来 deployment/Doctor 仍只能把 `online` device record 当 control-plane evidence；execution-plane acceptance 必须有真实 command probe。

## Phase 10 — acceptance

只有同时满足以下条件部署才完成：
- 无 duplicate managed MCP；
- 健康 external service 被保留；
- 必需版本 current/compatible；
- local Gateway routing 已证明；
- public HTTPS/OAuth 已证明；
- ChatGPT OAuth flow 已证明；
- desktop launcher + Manager 工作；
- fallback path 已演练；
- concurrency policy 已文档化并测试。

## Stage 19 production identity / recovery

生产 WebGPT 使用一个 canonical `https://<stable-tailnet-dns>/mcp` HTTPS 443 identity。普通 Manager、Gateway、OAuth Edge、WebGPT、Windows restart 不应主动改变这个 identity、issuer 或 OAuth credential。

`Start All` 必须区分 9340 OAuth child 与完整 9341 OAuth Edge。仅有 9340 listener 绝不能满足 Edge readiness；只有 9341 compatibility contract、当前 issuer、repository generation 与 public 401/OAuth metadata 一致时才算 ready。

如果匹配的 9340 child 在 9341 wrapper 缺失时仍然存活，WebGPT 只有验证 canonical issuer 后才可复用它，从而无需 credential rotation 或 connector recreation。unknown/incompatible listener fail closed。

Stage19 真实主机验收已经通过 local 9341 metadata 200、public `/mcp` 401、当前 OAuth metadata、DCR + PKCE、authenticated MCP、refresh continuity，以及 Edge restart 前后相同的 87-tool surface。用户确认 ChatGPT connector 配置成功后，本 Stage 冻结 production Connector/Funnel/OAuth，禁止继续做扰动性 acceptance。

成功配置后没有强制 Windows 整机重启。该项记录为 manual real-reboot acceptance；startup/recovery contract 已实现并测试，但保护刚建立的 production connector 优先于“为了证明而重启”。


## 2026-09-21 启动与公网 Edge 维护补充

当前部署合同新增两个 machine-local 扩展点：

- `%LOCALAPPDATA%\WebGPT-as-Codex\local-prestart.cmd`：在 Desktop launcher 与 Windows-login autostart 的 `Start All` 之前执行，只用于恢复已经批准的外部 MCP backend。它不得包含 Token/密码，也不得修改或占用 WebGPT 的 canonical HTTPS 443。
- `%LOCALAPPDATA%\WebGPT-as-Codex\local-launcher-overlay.cmd`：仍然只在手动 Desktop launcher 已经 READY 之后执行，用于当前主机专属的 post-READY 扩展；autostart 不调用它。

`local-prestart.cmd` 的退出码只是诊断证据，不直接决定 WebGPT 成败。最终结果仍由随后真实的 layered readiness 判断。

OAuth Edge READY 现在必须同时满足：

1. 9341 compatibility edge 正常；
2. 9340 OAuth child identity / issuer / generation 正确；
3. Tailscale Funnel 的真实 HTTPS 443 target 当前就是 `http://127.0.0.1:9341`；
4. public OAuth metadata 与未认证 `/mcp` 401 challenge 正常。

如果运行期间 443 被其它脚本改到别的 target，Edge 必须退出 READY，而不是继续保持“本地端口正常”的假绿状态。

Windows 登录恢复时，launcher 允许在有界时间内等待 required unmanaged backend 被 `local-prestart.cmd` 拉起；超时后仍按真实 missing backend fail closed。
