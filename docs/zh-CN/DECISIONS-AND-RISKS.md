# 决策与风险

[English](../DECISIONS-AND-RISKS.md) | **简体中文**

本镜像覆盖当前英文决策日志中的现行决策/风险。英文文件继续是 canonical engineering record；历史 commit/hash/identifier 保持原值。

## Stage 5 — OAuth/Tailscale Edge

### 决策：一个 public MCP endpoint
自托管栈只发布 unified Gateway path；core MCP backend 保持 loopback/private。

### 决策：保留 OAuth compatibility adapter
当前 mcp-auth-proxy 需要正确 forwarded HTTPS host/proto 与 consent-session continuity。adapter 是通用项目代码，不嵌机器 secret/public hostname。

### 决策：最终 OAuth acceptance 必须走真实 HTTPS
localhost HTTP 会扭曲 Secure-cookie 行为；Stage5 authoritative gate 通过真实临时 Tailscale Funnel HTTPS 跑 DCR、PKCE、login/consent、token、refresh、MCP。

### 风险
upstream OAuth 行为会变，adapter 边界要小并在 mcp-auth-proxy 更新时重新验证；Doctor 分开 metadata/DCR/PKCE/refresh。Tailscale Funnel 是 edge adapter，不是 repo security boundary；无 public Funnel 时 local stack 仍可用。

## 跨 Stage — 递归已验证 handoff

每个 Stage 都必须先 commit，再从 committed HEAD 生成 next prompt，携带 CURRENT/NEXT/AFTER_NEXT + recursive invariant，validate/hash，单一 Playwright MCP session 提交，并验证 sent SOURCE_HEAD + assistant run + `/c/` URL；receiving window 必须重复。只有 planned final stage 与 Final Overall Acceptance 都关闭时链条才结束。

## 跨 Stage — 自演进 Skill / operating knowledge

即时任务成功不代表 execution complete。reusable friction 要诊断/验证并写入最窄 durable layer：general -> Skill；MCP-specific -> Guide；machine fact -> local inventory/config；one-off -> stage/ledger。

Routing 负责 WHICH，Guide 负责 HOW；tool name 不证明 capability。用户指导如果揭示 stable principle，可以成为 reusable evidence，但应记录 mental model/goal/constraint/verification/failure signal，而不是脆弱 click recipe。

### 决策：stage sizing 保护 closure
约 20 分钟是包含 closure 的 soft planning budget，不是声称平台有 25 分钟硬限制。宁愿短而完整收口，不接受 implementation 做完却 docs/commit/handoff 欠债。基线数据需收集 implementation/closure effort、tests/files、tool switch/retry/harness failure、docs、handoff first-pass、almost-done、split，再 recalibrate。

### 风险：Skill 膨胀/过拟合
不能把每次事故都写 core rule；要合并重复、带 provenance 地 retire obsolete method、把 machine detail 移出 portable docs、MCP-specific detail 放 Guide。

## Stage 6 — Manager control plane

- Reference Manager `127.0.0.1:9199` 只读作为 evidence，不复制 machine-specific inventory/address/auth/recovery。
- Manager 只 shallow cached polling；deep initialize/tools/safe-call/OAuth/remote 来自 durable Doctor。
- Stage6 只暴露 Start All/Restart/Doctor/Repair/Update fixed contracts，不实现 arbitrary executor；后续 owner stage 注入。
- stale Doctor evidence 必须显示 unknown，不把 listener 推导成 protocol health。
- Coding Tools workspace drift 是 harness/binding issue；用 workspace 内 dedicated worktree，而不是绕过 path policy。

## Stage 7 — Bootstrap / Doctor / Repair

- bootstrap discover-before-mutate；healthy listener preserve；apply 只建立 state dirs + plan，start/restart 属 Stage8。
- health evidence prerequisite-aware：process/listener/protocol/safe-call/OAuth/remote 独立，未满足 prerequisite 的深层 check 为 unknown。
- Doctor 对 OAuth authority read-only；完整 DCR/PKCE/consent/token/refresh 仍由 explicit real-HTTPS gate。
- Repair fixed allowlist + confirm + backup，无 shell surface。
- version parser 只接受明确 labelled/exact semver，否则回 manifest evidence，避免把 dotted address 当版本。
- live Doctor 可以 red 而 Stage7 green：Stage closure 证明诊断契约，不表示擅自启动 later-stage runtime。
- shared editable venv 可能 import 错 worktree；isolated validation 要显式 source root，harness import failure 不等于 target failure。

## Stage 8 — Runtime supervisor / launcher / autostart

- lifecycle ownership 需要 fixed runtime adapter + machine-local PID receipt，并验证 PID birth token + image；discovery 只够 preserve，不够 stop/restart。
- Start All discovery-first，可 action success 但 full stack partial；required-unmanaged 单独报告。
- Stage5 E2E credential 不提升为 autostart authority；无生产 credential contract 时 mcp-auth-proxy 留 unmanaged。
- Manager Restart 比 component discovery 更窄，只允许 fixed allowlist，不接 arbitrary shell/PID/path/URL/argv。
- Windows Startup `.cmd` 是有界 autostart，transparent/reversible，exact managed content，拒绝 overwrite/delete user-owned；service context 缺 USERPROFILE/APPDATA 时用安全 shell-folder 解析。
- graceful shutdown component-dependent；必要的 force fallback 要如实报告。
- process-only evidence 只决定“不启动/不 kill”，不升级为 protocol/OAuth/remote health。

## Stage 9 — Generic Add MCP / Operating Guides

- capability discovery 在 routing 之前，必须真实 initialize + tools/list；server/manifest/tool name 只作 hint。
- `unavailable`、`failed`、`unattempted` 分开保存。
- `add-mcp` 默认 dry-run；`--apply` 才写 machine-local custom manifest/Guide/routing receipt；same manifest 幂等，同 id 不同内容 fail closed，custom 不可 shadow built-in。
- Guide 是 portable operating knowledge，不是 inventory；endpoint/path/workspace/PID/health/secret 留 machine-local。
- onboarding visibility 不授予 lifecycle authority；Stage8 ownership 仍 authoritative。
- schema 可描述 token/password field，但 secret scan 只拒绝 credential literal，不能把 schema structure 本身误判。
- live Stage9：Coding Tools 18 tools，Serena 29 tools；这是当时 health evidence，不是永久 availability truth。

## Stage 10 — Loop Engineering dogfood

- closure budget 显式且 evidence-driven；只有至少 3 个 verified non-split first-pass-handoff record 后才 recalibrate，total 15-25 分钟、closure share 25-55% bounded。
- chat context 不是 execution state；machine-local durable closure state 在 Git 外，commit-time contradiction 可 reopen minimum boundary 并 invalidate stale prompt。
- prompt plan 可 durable commit，但 `SOURCE_HEAD` late-bound 到 closure commit。
- handoff preparation 可 retry；send exactly-once；ambiguous response 只查 post-state。
- 风险：stage-cost fake precision。未知就保持未知，不能从小样本推断平台 timeout。
- live dogfood 证明 “Serena config says ready” 不是 semantic-call proof；实际 `get_symbols_overview` 无 active language server，合理 fallback 但不改变 routing role。

## Stage 11 — Security / reliability

- Manager Update 是 repository-approved、offline-by-default authority：fixed component + declared release/source/digest/destination，只消费 staged artifact，pre/post digest，running/owned target 拒绝，replacement backup，already-current 幂等。
- machine-local config 是 untrusted input：custom manifest 每次 load revalidate，不能 shadow built-in、注入 lifecycle/version command 或擅自 safe-call；malformed entry isolate；external schema bounded/sanitized。
- durable write fail closed：temp + fsync + atomic replace；multi-file apply 先 stage 全部，后续失败 rollback 已替换项。
- loopback 并不足以证明 browser origin；Manager 校验 Host/port、Origin、control header、payload schema，error 文本 sanitize。
- connector/tool exposure 可独立于 target health 漂移；Stage11 Coding Tools connector 消失属于 harness evidence，不能自动判 repo failure。

## Stage 12 — README / release / final preparation

- release verification 必须测试 installed artifact，不能只靠 source checkout。
- installed runtime resource 原先显式最小化为 public component manifests + Manager static UI。
- 已解决 source-layout false green：首个 wheel 虽安装成功但 built-in=0/Manager static missing；修正 package/resource resolution 后 isolated wheel 成功加载 8 manifests + Manager UI。

Stage18 在此基础上只扩展 bounded public release/legal/provenance resource，不把全部 docs/Skill 打进 wheel。

## Stage 17 — bilingual Manager / desktop UX

- 中英文 language shell 共用 packaged JS/CSS/API，避免 duplicated control logic。
- explicit secret control 与 status 分离：status 只给 configured；reveal/set/regenerate confirmed loopback mutation；regenerate fresh；plaintext 不进 activity/docs/evidence。
- migration visibility 不创造 authority：custom add/remove 仅 registry，`route_applied=false`、`lifecycle_authority=false`；built-in delete blocked。
- launcher exact-content change 可能让旧 managed launcher 看似 unmanaged，因此只对完整历史 WebGPT structure 做 upgradeable match；单 marker 不够。
- local mutation timeout 有 duplicate side-effect 风险；UI/Manager serialize mutation，process stop timeout/non-zero 继续执行 R49 bounded post-state。

## Final Overall Acceptance

- final acceptance 同时要求 source-tree 与 freshly built/isolated installed artifact evidence。
- transient MCP/session drift 在无 target contradiction 时不成为 release blocker。
- 已接受 Stages0-12 未发现未解决 release/security/ownership blocker；wheel 加载 8 manifests + Manager，fixed Manager action contracts 保持。
- residual risk：external service health 会漂移；后续 listener/session drift 不能倒推历史 acceptance 失败，除非产生 repository-owned contradiction。

## Supplemental chain — one-repo deployment / Gateway / concurrency

- repo 是 single deployment authority；无需 vendoring whole third-party tree。
- latest-stable intent 必须经过 compatibility gate，不把 latest 等同可安全 mutation。
- route ownership 与 lifecycle ownership 分离。
- RDC 与 Unified Gateway 互补而非替代。
- 单 Serena process 不是多项目 parallel slot；Stage16 fixed-project pool。
- Coding Tools parallelism 由 workspace/write ownership 限制，不是 one-call global mutex；read/process 可重叠，writer worktree 隔离。
- 风险：自动部署可能重复健康服务，因此 install 前查 listener/protocol/process/install evidence。
- fresh machine 可能无 Tailscale/session；安装可自动，account login 是 interactive boundary。
- fresh binary bootstrap 不能变 unbounded downloader；MCPJungle/mcp-auth-proxy 只用 approved official origin + SHA-256，latest 仍需 source/compatibility gate。

## Stage17 post-acceptance Hotfix

- listener health != runtime-generation proof；只有 ownership/process identity + current runtime/resource contract 才允许 preserve；stale owned/strict legacy 可 refresh；ambiguous 9200 永不 terminate。
- Windows venv launch wrapper 可能不是实际 listener；receipt 绑定 real listener PID/birth/image，launcher identity 只做 bounded cleanup。
- desktop browser continuity 与 Playwright profile lifecycle 分离；复用 normal Edge profile，否则 default URL handler，禁止 temp/InPrivate/automation blank profile。
- live acceptance：真实 stale 9200 被安全替换后 `/`、`/en`、`/zh`、CSS/JS/local-config 全部当前；连续两次 Desktop launch 保留 core listener 与 Edge `Default` process。

## Stage16 — concurrency / recovery

- shared state 都有显式 authority：Serena fixed-project process/port + machine-local receipt，shared 9121 排除；Coding Tools writer per-worktree lease；RDC/Windows-MCP native GUI 共用 one machine GUI lease。
- recovery attempt 有 attempt id/visited/hop budget，一个 component/attempt 一个 mutation owner；无 lifecycle authority => diagnose-only。
- process shutdown acknowledgement 可能落后实际 exit；timeout/non-zero 是 ambiguous result，要 bounded observe listener + PID identity，不能第二次盲 kill。
- local lease 可 stale，只有 expiry/identity evidence 后 reclaim，不能因另一个窗口想用就抢 active owner。

## Stage15 — install / upgrade / lifecycle

- latest stable 部署时解析，但不是 blind mutation authority；GitHub binary 需 release SHA-256 + expected asset；compatibility window 独立验证。
- healthy live availability 优先于 PATH absence。
- install ownership 与 runtime lifecycle ownership 分离，receipt 仍 `runtime_lifecycle_authority=false`。
- Tailscale 有 process-only healthy state，不因无 MCP listener red。
- 不同 version domain 不做假比较。
- upstream latest metadata 可暂时 unavailable；verified cache 最多 24h 且 evidence-only，`latest_fresh=false` / `verified-cache` 不授权 mutation。
- pre-closure prompt 可 stale；`d08603a` 只作历史 evidence，Stage16 prompt 必须从真实 Stage15 closure HEAD 再生成。

## Stage14 — Production Unified Gateway / Edge

- route sync 幂等且仅修改 WebGPT 私有 MCPJungle registry；identical preserve，missing register，changed same-name 才 force replace。
- owned runtime 是 production Edge wrapper + child OAuth process，不是 routed Serena/Coding Tools/Playwright/Windows-MCP。
- production OAuth credential 与 Stage5 E2E state 分离，只在 machine-local。
- real production acceptance 通过 protected-resource metadata、401、DCR、PKCE token、authenticated 87 tools + safe Coding Tools call、Runtime Supervisor restart、refresh、再次 authenticated 87 tools。
- 每次 start 都 `register --force` 会破坏 registry continuity，因此先查询当前 route，只在真实变化时 force。

## Stage18 — 中文镜像 / provenance

### 决策：镜像采用确定性路径
根入口用同级 `*.zh-CN.md`；live docs 用 `docs/zh-CN/`；Product Skill/Guide 用 `skills/webgpt-as-codex/zh-CN/`。protocol/schema/code/hash 不机械翻译。

### 决策：历史证据保持单一 canonical 原文
Stage closure、cost evidence、handoff prompt 不为“视觉双语”改写；`TRANSLATION-COVERAGE.json` 明确分类，并由中文 historical index 提供导航。

### 决策：法律原文与阅读翻译分离
根 `LICENSE` 必须保持 Stage18 基线 SHA-256；`LICENSE.zh-CN.md` 明确 non-binding，冲突时英文原文控制。

### 决策：provenance 由 repo authority 对齐
`docs/THIRD-PARTY-PROVENANCE.json` 逐项对应 8 个 component manifest，并补上 `pyproject.toml` 的 setuptools/requests/pytest/ruff build/runtime/dev dependency。notice 不复制整份 upstream license。

### 风险：中文镜像可能漂移
Stage18 使用 machine-readable coverage + tests 把 mirror existence、legal hash、provenance、package resource 变成 regression gate。后续修改 live source 时必须同步 mirror 或显式更新 disposition。

## Stage 19 — OAuth Edge readiness 决策

### 决策：9340 child liveness 不等于 OAuth Edge readiness
产品 contract 在 9341 repository compatibility edge 上收口，再进入 9340 child OAuth proxy。因此 9341 缺失时，即使 9340 listener 存活，Start All 也不能报告 fully ready。

### 决策：兼容 child 优先 preserve，不旋转 state
当现存 9340 child 广播当前 canonical public issuer 时，新 9341 wrapper 可以复用它，避免无意义的 password rotation、OAuth DB churn 与 connector recreation。issuer mismatch 或 listener identity ambiguous 时 fail closed。

### 决策：receipt identity 跟随真实 OAuth Edge listener
Windows venv launch wrapper 的 launch PID 可能不同于 listener PID。Stage19 把 Manager 的 reconciliation 模式扩展到 OAuth Edge，只在 strict process identity + `edge.json` evidence 成立时 rebind。

### 风险：self-restart 会切断 control plane
如果 ChatGPT 当前正通过 WebGPT 操作，restart WebGPT 可能切断本轮 tool transport。因此 restart acceptance 由 independent repair plane 执行，恢复后重新获取 session/tool refs。

### 风险：重复 production acceptance 会破坏 known-good connector
用户确认真实 ChatGPT connector 配置成功后，后续验收冻结 disruptive Connector/Funnel/OAuth mutation。Windows reboot 记录为显式 manual acceptance，而不是 closure 时强制执行。
