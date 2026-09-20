# 架构

[English](../ARCHITECTURE.md) | **简体中文**

## 平面

1. Agent plane：可复用 Skill、本地 SoT、stage/handoff rules。
2. Control plane：bootstrap、component registry、Doctor/Repair、Manager。
3. Runtime plane：Serena、Coding Tools、Playwright MCP、Windows-MCP。
4. Gateway plane：可替换 MCPJungle adapter + curated Tool Groups。
5. Edge plane：OAuth compatibility adapter -> mcp-auth-proxy -> MCPJungle，经 Tailscale Funnel 发布。
6. Optional full-machine plane：Remote Desktop Commander vendor relay。

## Supplemental deployment topology

WebGPT-as-Codex 是 repository-level deployment authority，用户/Agent 从本仓库开始，不依赖散落在各 MCP 项目的人工 checklist。

```text
ChatGPT
├─ Remote Desktop Commander (independent rescue/control plane)
└─ WebGPT-as-Codex public HTTPS /mcp
   -> OAuth compatibility adapter
   -> mcp-auth-proxy
   -> MCPJungle
   -> localhost MCP backends
```

backend-specific public tunnel 是可选项，不是 unified path 前提。Coding Tools 即使自身提供 Cloudflare remote client，也可继续只在 localhost 运行。

Deployment controller 分离 upstream/source authority、installation/version authority、route authority、lifecycle authority。健康 external MCP 可先被路由，不因此授予 WebGPT kill/restart。WebGPT 新安装实例只有在 identity/ownership evidence 建立后才可能获得 lifecycle authority。

参见 `docs/zh-CN/DEPLOYMENT.md`。

## 互补 rescue plane

RDC 与 Unified Gateway 故意独立。Gateway/backend/local WebGPT runtime 失败且 RDC 可用时，Agent 可经 RDC 恢复本地进程后重试 structured MCP；RDC 失败且 Gateway 健康时，可在权限允许范围通过 Gateway-routed Windows-MCP/Coding Tools/WebGPT 能力恢复 RDC。

public WebGPT endpoint 整体 transport outage 时不能自救。Stage16 的 attempt-scoped recovery coordinator 使用 correlation/attempt id、visited-path set、bounded hop budget 和每 component/attempt 一个 mutation owner；没有 lifecycle authority 的 path 只能 diagnose；timeout/non-zero mutation 先 bounded post-state。

## 并发模型

- Serena：标准 process 只有一个 process-wide active project；Stage16 用 isolated fixed-project slot，shared 9121 永不由 pool 管。
- Coding Tools：independent read/process 可重叠；一个 instance 只有一个 workspace；workspace mismatch 拒绝，同 worktree 一个 writer lease，parallel writer 要不同 worktree/workspace。
- RDC：terminal/filesystem/process 可重叠，实体 GUI focus/mouse/keyboard 是 singleton；Stage16 用 machine-local GUI lease。
- Windows-MCP：共享 native-GUI 规则。
- Playwright：独立 page/context 可并行；同 page/profile/login-state one-writer。

参见 `docs/zh-CN/CONCURRENCY-AND-FALLBACK.md`。

## Trust boundary

Repository source 必须 public-safe。机器 state 在 Git 外。Secret 机器本地生成/保存，永不嵌 manifest。install/restart 前先发现并保留健康服务。

## Component installation / version / ownership plane

Stage15 把 repo 变成 deployment authority，但 discovery 不等于 mutation permission。built-in manifest 可声明 install strategy、package/upstream identity、latest source、mutation 时所需 toolchain、installed/latest 各自 compatibility window、approved Windows artifact mapping、WebGPT-owned machine-local destination。

latest evidence 来自 PyPI/npm/GitHub Releases/winget；GitHub binary 还需 expected repo/asset + release SHA-256。

成功 latest resolution 只在 machine-local cache 保存最多 24h。cache 是 transient API failure 的 resilience evidence，不替代 fresh latest；fresh machine 无 online evidence/valid cache 时 fail closed。installed/latest/compatibility 是三条独立真相；latest 越界 blocking；newer compatible local 保留；network failure 保持 unknown。

Planning discovery-first：
- healthy listener 即使 PATH 没 executable 也保留；
- `@latest` 不是 installed probe；
- system process 可无 HTTP listener；
- running unhealthy => diagnose，不 blind duplicate；
- newer compatible external => preserve；
- older external live => report upgrade-available，不 silent adopt；
- stopped older external => 只有显式 adoption 才可升级并记录 install ownership；
- missing => 可装 resolved stable；
- WebGPT-owned stopped => 可用 approved adapter upgrade。

Install ownership receipt 在 Git 外，记录“谁安装”，不自动授予 kill/restart。Runtime lifecycle authority 是独立契约。fresh-machine 可通过 allowlisted winget provision uv/Node/npm，但 existing healthy MCP 仍是更强 availability evidence。

## Edge contract

公网路径只有一个 HTTPS MCP endpoint。Tailscale Funnel 终止 HTTPS 并转发 local OAuth compatibility adapter；adapter 保留 forwarded HTTPS host/proto 与 consent continuity；mcp-auth-proxy 负责 OAuth 2.1、DCR、PKCE、access/refresh token 与 backend authorization；MCPJungle 只负责 protocol aggregation。

production Edge wrapper：
- 等 local Gateway；
- 只 sync healthy enabled Streamable HTTP backend 到私有 MCPJungle；
- identical route preserve；
- machine-local `secrets/` 中创建/复用 OAuth credential；
- 启动 mcp-auth-proxy + compatibility adapter；
- 通过 dedicated Tailscale Funnel port 发布；
- 只把 non-secret Edge status/public URL 写到 machine-local state；
- teardown 只处理 owned Funnel/child process。

Edge wrapper 的 lifecycle authority 不传递给 routed backend MCP。

## Health model

`Process -> listener -> MCP initialize -> tools/list -> safe tool call -> OAuth metadata -> DCR/PKCE -> refresh -> remote endpoint`

每层独立报告。

## Performance model

Gateway 优先 curated Tool Group，不因“已安装”就重复暴露重叠 MCP。Routing 属于 Skill；protocol aggregation 属于 Gateway。

## 自演进 operating knowledge

执行循环：
`Execute -> Observe -> detect friction -> Diagnose -> Explore -> Compare -> Select -> Verify -> Record -> Reuse`

覆盖 SoT loading、stage sizing、routing、MCP use、implementation、tests、docs、commit、prompt generation、Playwright submit、next-run verification。重复 almost-finished、可避免 retry、premature fallback、incomplete docs 或 handoff failure 都是 process defect。

知识按 scope 分层：
- `routing.md` 决定 WHICH capability；
- MCP Guide 描述 HOW；
- inventory 保存 installed/configured/available 与 machine facts；
- Experience Ledger 保存 evidence-backed lesson/provenance；
- one-off incident 不进入长期 Skill，除非暴露 reusable mechanism。

Stage9 productize Guide/onboarding；Stage10 productize Loop self-evolution/sizing。约 20 分钟是包含 closure/handoff 的 soft budget，不是硬 timeout；如 implementation 会吃掉 closure reserve，则拆 owner concern。

## Manager control plane

Manager 只绑定 loopback，默认 `127.0.0.1:9200`；历史/reference 9199 只读证据，不复制、不修改。

Manager status 来自 registry，每 component 分开 process/listener/protocol/safe-call/OAuth/remote；UI 只做 bounded shallow listener probe，deep evidence 读最后 Doctor，避免 polling tax。

`config/manager.json` 在 machine-local state，可含 credential-free `public_mcp_url`；secret-like key、bearer、private/loopback URL 输出前 recursive redact。

UI 生命周期不拥有 runtime。Stage6 只定义 Start All/Restart/Doctor/Repair/Update fixed contracts，无 arbitrary command；mutation 需 confirm + same-origin control header，executor 由后续 owner stage 注入；Stage11 加 Host/Origin 与 payload field validation。

Stage17 中英文 `index.html` / `index.zh-CN.html` 是 language shell，共用 `manager.js` / `manager.css`，`/` 随 `WEBGPT_CODEX_UI_LANG`，managed desktop 当前设 `zh-CN`。两种语言走同一 API、pending lock、component mutation、URL control/activity。

local-config 只暴露 readiness/configured/version/migration；剥离 executable/secret path/private Tailscale DNS。OAuth reveal 是独立 confirmed loopback operation，plaintext 不进入 status/activity。

Hotfix 后，listener health 不等于 runtime generation；supervisor 比较 runtime generation + required resource/API contract，仅在 strict WebGPT identity 下刷新 stale owned/legacy Manager，ambiguous 9200 fail closed。Windows receipt 跟随实际 listener interpreter。

Desktop URL opening 与 Playwright automation 分离：优先正常 Edge profile，否则 Windows default handler，不创建 temp/InPrivate/automation profile。

所有 Stage17 local mutation 共用 Manager-local non-blocking lock；HTTP boundary 继续要求 loopback Host/Origin + control header + confirmation，unknown/oversize fail closed，error 只返回 sanitized class。custom create/delete 仅 registry visibility；built-in 不可删除。

## Bootstrap / Doctor / Repair

Bootstrap discovery-first + idempotent；healthy listener preserve；installed-but-stopped 不授权启动；apply 只建立 machine-local layout + sanitized plan。

Doctor 分开 process/listener/protocol/safe-call/OAuth/remote，并尊重 prerequisite；listener 不证明 protocol。safe call 只调用 manifest safe tool；`@latest` 等 network-capable version command 不用于 probe；ambiguous banner 不猜版本。结果 recursive sanitize 后只写 machine-local `doctor/last-result.json`。

OAuth Doctor read-only：local metadata 只是诊断，真实 public HTTPS 才是最终 authority；可验证 protected-resource metadata + unauthenticated 401，但普通 Doctor 不创建 DCR client/token。

Repair 是 fixed allowlist，不是 shell；mutation 需 confirm，config edit 先 backup。Stage11 用 temp + fsync + atomic replace 统一 machine-local persistence；multi-file apply 先 stage 全部，再有界 rollback。

## Runtime lifecycle / desktop / autostart

Stage8 Runtime Supervisor 要求 fixed adapter + machine-local PID receipt，receipt 必须与 live PID birth token + image 匹配；stale/dead/reused/mismatch fail closed。

Start All 先 preserve healthy listener/system process，只启动 fixed repository-managed missing runtime；installed/required 不等于 lifecycle ownership。当前 Stage8 managed set 是 local Manager + MCPJungle；健康 Serena/Coding Tools/Playwright/Windows-MCP/Tailscale/RDC 仍 unmanaged。

MCPJungle 使用 machine-local DB/log/PID/state。Stop/restart 再次验证 ownership，先 bounded graceful，再必要时 bounded force；unmanaged listener 不 restart。Manager Restart 只接受 explicit allowlist，不接受 raw command/argv/path/PID。

Start All 区分 action success 与 full-stack readiness，可能返回 `complete-with-unmanaged-required`。Stage8 不复用 Stage5 E2E OAuth secret 做 production authority。

Windows launcher 是 control surface，不是 process-parent contract；可退出而 runtime 继续。Desktop/Startup `.cmd` transparent/reversible/credential-free，拒绝覆盖 user-owned 文件。Stage17 只有完整历史 managed structure 匹配才能 in-place upgrade。

## Generic MCP onboarding / Guide plane

Stage9 chain：
`manifest validation -> credential rejection -> initialize -> tools/list -> capability classification -> Guide validation -> routing recommendation -> dry-run -> explicit machine-local apply`

status 保留 success/unavailable/failed/unattempted。machine-local apply 保存 custom manifest、machine-readable Guide、onboarding/routing receipt；Stage11 每次 load 都重新验证，custom 不能 shadow built-in、注入 lifecycle/version command 或凭空获得 safe-call。schema text bounded/sanitized。

Serena/Coding Tools 是首批 public-safe Guide。Onboarding 绝不创造 lifecycle ownership。

## Stage10 Loop plane

`loop.py` 管 public-safe stage-cost、bounded sizing、machine-local closure state。phase 在 closure attempt 内单调；commit-time contradiction 可 bounded reopen 最小边界并 invalid stale prompt/handoff。

初始 soft budget 20 分钟 + closure reserve；有足够 verified history 后用 bounded median recalibrate，不当平台 timeout detector。

Handoff 因果分离：committed plan 不冻结 `SOURCE_HEAD`；closure commit 后注入真实 HEAD，验证 CURRENT/NEXT/AFTER_NEXT/SOURCE_HEAD 并 hash。Playwright pre-submit 可恢复 hydration/ref/tab；一旦 send attempted 就 exactly-once，ambiguous transport 只查 post-state，不第二次发送。receipt 在 commit 外机器本地保存。

## Release packaging boundary

Stage12 规定 installed wheel 与 source checkout 是不同环境。原边界为 Python runtime + `share/webgpt-as-codex/components` + `share/webgpt-as-codex/manager/static`。

Stage18 在不改变 runtime authority 的前提下增加一个**有界公开 release resource 集**：双语 README、原始 `LICENSE`、非约束中文阅读译本、双语 third-party notices、provenance JSON、translation coverage manifest/docs，安装到 `share/webgpt-as-codex/release`。Stage closure、prompt、完整 Skill source、machine-local state/secrets/update/handoff/PID/browser-account evidence 仍不进入 wheel。

## Stage 19 — canonical OAuth Edge 恢复

生产 public identity 固定为 HTTPS 443。Tailscale Funnel 指向 loopback 9341 的 repository compatibility edge；child OAuth proxy 仍在 9340，Unified Gateway 在 9330。

Stage19 关闭了一个 false-green：9340 child 存活不等于 repository-owned OAuth Edge ready。`Start All` 现在以 9341 runtime contract 判断 managed Edge，而不是把 raw child listener 当成完整 Edge。

只有当现存 9340 child 的 listener 端口正确、advertised issuer 与当前 canonical public base 完全一致时才允许复用。随后 9341 compatibility edge 可以围绕它恢复，不旋转 credential、不改变 public identity。incompatible/ambiguous generation fail closed。

Windows venv launcher indirection 也纳入 OAuth Edge reconciliation：managed receipt 只有在 process identity + `edge.json` 都匹配时，才从 launch PID rebind 到真实 9341 listener。因此 generation/readiness 描述真实 listener，而不是 wrapper PID。

repair plane 与 runtime plane 保持独立。完整本地 Agent 或 Remote Desktop Commander 可以在 public WebGPT connector 不可用时维修 WebGPT；坏掉的 public endpoint 绝不能成为修复自身的前置依赖。
