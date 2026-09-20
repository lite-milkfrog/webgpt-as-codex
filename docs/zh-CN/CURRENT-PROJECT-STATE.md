# 当前项目状态

[English](../CURRENT-PROJECT-STATE.md) | **简体中文**

PROJECT = WebGPT-as-Codex  
CURRENT_STAGE = SUPPLEMENTAL-FINAL-ACCEPTANCE
NEXT_STAGE = GLOBAL_LOOP_COMPLETE
AFTER_NEXT_STAGE = TERMINAL

## 已接受主链

Stage 1-12、Final Overall Acceptance、Project Complete 均为 `CLOSED_LOCAL_VERIFIED`。后续用户新增需求形成 supplemental chain，不推翻 Stage 1-12 的既有证据，只负责一仓库部署、生产 Unified Gateway、fresh-machine bootstrap、Remote Desktop Commander 互补恢复、多窗口并发、双语 Manager/桌面体验和完整中文镜像。

## Supplemental chain

- Stage 13: `CLOSED_LOCAL_VERIFIED`
- Stage 14: `CLOSED_LOCAL_VERIFIED`
- Stage 15: `CLOSED_LOCAL_VERIFIED`
- Stage 16: `CLOSED_LOCAL_VERIFIED`
- Stage 17: `CLOSED_LOCAL_VERIFIED`
- Stage 17 post-acceptance Hotfix: `CLOSED_LOCAL_VERIFIED`
- Stage 18: `CLOSED_LOCAL_VERIFIED`
- Stage 19: `CLOSED_LOCAL_VERIFIED`；并完成 REAL_HOST_VERIFIED + REAL_CHATGPT_VERIFIED
- Supplemental Final Acceptance: `IN_PROGRESS`；RDC recovery-plane reconciliation 已 VERIFIED，desktop-launcher/final reconciliation 待合并

## Stage 13 证据

- fresh-machine 环境报告区分 Windows/Python/winget/Tailscale installed/version/login/online/MagicDNS/Funnel，以及 WebGPT 私有 runtime binary readiness。
- 当前主机已验证 Tailscale 1.102.2、online、MagicDNS、Funnel，`ready_for_edge=true`。
- bootstrap 可经 allowlisted winget 安装缺失 Tailscale，同时保留已有安装。
- MCPJungle 与 mcp-auth-proxy 私有 runtime provisioning 使用批准的官方 release URL + SHA-256，默认保留已有 binary。
- Serena 已安装源码证明标准 agent 使用 process-wide active project；切换 project 会关闭前一 project，解释了跨窗口冲突并由 Stage16 处理。
- Coding Tools 实测多个 server-managed command 可重叠执行，但一个 server 只绑定一个 configured workspace；并行 writer 仍需 worktree/workspace 隔离。

Closure: `docs/STAGE-13-CLOSURE.md`。

## Stage 14 证据

- MCPJungle route sync 幂等：相同 name/transport/URL 保留，缺失 route 注册，变化 route 只在 WebGPT 私有 Gateway registry 中替换。
- 实际 Gateway 通过 localhost 聚合 Coding Tools、Serena、Playwright、Windows-MCP，MCP initialize 200，`tools/list=87`。
- production OAuth Edge 成为仓库拥有的 Runtime Supervisor target；外部 MCP backend 仍不受 WebGPT kill/restart。
- OAuth credential 只在机器本地 WebGPT secrets root 生成/复用。
- 真实 Tailscale `:10003` 通过 public OAuth metadata、unauthenticated MCP 401、DCR + PKCE + token、authenticated safe call、受控 Edge restart、refresh continuity、再次 authenticated MCP，工具面仍为 87。
- Edge restart 未重启 Serena、Coding Tools、Playwright、Windows-MCP。
- full gate：120 PASS；Ruff、secret scan、`git diff --check` PASS。

Closure: `docs/STAGE-14-CLOSURE.md`。

## Stage 15 证据

- 8 个 built-in component 都有显式 install/latest-source metadata；自动 adapter 还声明 toolchain 与 compatibility window。
- `webgpt-codex deploy` 从 PyPI/npm/GitHub Releases/winget 解析 latest-stable，并把 installed/latest/compatibility/install/lifecycle authority 分开。
- GitHub Release binary 要求 repository/asset identity 与 release-provided SHA-256。
- healthy listener 优先于 PATH/package 缺失；不会因 PATH 看不到 executable 就重复安装。
- `@latest` 不可作为 installed-version probe。
- latest 超出 compatibility window 时 fail closed；已有更新且兼容的安装保留、不降级。
- Tailscale 等 system-process component 不因没有 MCP HTTP listener 被误判。
- install ownership 是机器本地 receipt，不自动授予 runtime kill/restart；停止的 external install 只有显式 `--adopt-external` 后才能受控升级。
- current-machine dry-run 无 mutation、无 duplicate proposal。PyPI/npm/winget 查询成功；GitHub 查询存在瞬时错误，最终 MCPJungle 恢复 fresh 0.4.6，mcp-auth-proxy 仍 `HTTPError`，因此只该项保持 blocking/unavailable。
- verified latest cache 最多 24h，只是 evidence；标记 `latest_fresh=false` / `latest_provenance=verified-cache`，不得授权 install/upgrade。
- full gate：146 PASS；Ruff、secret scan、`git diff --check` PASS。

Closure: `docs/STAGE-15-CLOSURE.md`。

## Stage 16 证据

- `concurrency.py` 提供机器本地 fixed-project Serena slots；shared 9121 被硬排除。
- slot receipt 绑定 project/owner/port/PID birth token/image/launch fingerprint；支持幂等 acquire/release、稳定复用、stale cleanup、occupied-port fail-close。
- 隔离 worker 所用 CLI Serena 自报 1.28.1；shared direct Serena 仍为 1.7.0 / `Jarvis-dev`，Stage16 从未切换/重启 shared 9121。
- 非 9121 的真实隔离 Serena 完成 MCP initialize、`tools/list=29`，探针随后清理。
- Coding Tools 写边界可执行：read/独立 process 不拿 writer lease；workspace mismatch 拒绝；同一 worktree 一个 writer lease；不同 worktree 可独立。
- Remote Desktop Commander / Windows-MCP 原生 GUI side effect 共享 machine GUI lease。
- complementary recovery 带 attempt identity、visited paths、hop budget、one mutation owner；无 lifecycle authority 只能 diagnose；timeout/non-zero mutation 先做 bounded post-state。
- Stage14-16 regression 52 PASS；full 167 PASS；Ruff、secret scan、diff check PASS。
- 生产 listener PID 在探针后保持不变；临时 Serena 9477/9478 最终不存在。
- Computer Agent = `1.1.16-local-candidate`，validator 49 scenarios，含 R48/R49。

Closure: `docs/STAGE-16-CLOSURE.md`。

## Stage 17 证据

- Stage17/18 的 5 个 WIP 文件在不 reset/stash/overwrite 的前提下完成 reconcile；`manager/static/index.zh-CN.html` 成为真实 tracked resource。
- 中英文 Manager 共用 `manager.js` / `manager.css`；`/`、`/zh`、`/en` 语言路由明确；desktop launcher 默认 `WEBGPT_CODEX_UI_LANG=zh-CN`。
- local-config 输出只给 public-safe 的 product/deployment/environment/component/Gateway/OAuth/HTTPS/migration 摘要，过滤 executable path、secret path、Tailscale private DNS。
- OAuth set/reveal/regenerate 受 loopback/control-header/confirm 约束；Regenerate 一定生成新值；plaintext 只在显式 reveal 响应出现，不进入 activity/log。
- 本地环境/component/OAuth mutation 共用 non-blocking Manager lock；unknown field/body overflow fail closed；built-in deletion 禁止；custom create/delete 幂等且不授予 route/lifecycle authority。
- Manager 具备 secret-safe activity、pending/disabled 状态、URL copy/open、focus/label/live-region/reduced-motion。
- Stage8 历史 launcher 只有在完整旧 WebGPT 结构匹配时才可升级到中文默认；单 marker 不够。
- Playwright 使用现有 8931 Extension MCP，在 disposable 9217 Manager 上验证中英文各 7 sections、10 mutation controls、2 live regions、6 labels、2 URL rows、8 component cards；未点击 mutation。
- temp Manager 首次 stop non-zero 后按 R49 复查 listener/PID identity，再做 temp-only force stop；最终 9217 与 temp PIDs 均不存在。
- 生产 Gateway/Windows-MCP/Coding Tools/Playwright/shared Serena PID 未因 Stage17 host/browser 验收改变；shared Serena 未切换。
- target regression 100 PASS；最终 full 176 PASS；Ruff、secret scan、diff check PASS。
- PEP517 isolated wheel build/install PASS；installed layout 读取 English/Chinese HTML + shared CSS/JS。
- Stage17 状态：`LOCAL_IMPLEMENTATION + LOCAL_VERIFIED + REAL_HOST_VERIFIED`。

Closure: `docs/STAGE-17-CLOSURE.md`。

## Stage 17 post-acceptance Hotfix

- 复现了 9200 的 mixed-version Manager：新静态 HTML + 旧 route table。
- Runtime Supervisor 现在记录 runtime generation，检查 Stage17 resource/API contract，只在 ownership/process identity 被证明后刷新 stale process。
- 严格匹配的 legacy WebGPT Manager 可做一次 stale refresh；不相关/不明确的 9200 listener 永不 kill。
- Windows venv launcher indirection 通过把机器本地 receipt 重新绑定到实际 listening Python PID 解决，同时保留 launcher identity 做有界清理。
- desktop opener 复用正常运行的 Microsoft Edge profile；否则交给 Windows default URL handler，不创建 temp/isolated/InPrivate automation profile。
- 真实 Desktop launcher 两次执行均得到当前中文 Manager，CSS/JS/local-config HTTP 200，并保留相同 Manager/Gateway/core-MCP PIDs 与现有 Edge `Default` top-level process。
- Windows-MCP 观察到完整 Manager control tree。
- targeted 31 PASS；full 184 PASS；Ruff、secret scan、diff check PASS。
- Computer Agent = `1.1.17-local-candidate`，validator 51 scenarios，新增 R50/R51。

Hotfix closure: `docs/STAGE-17-POST-ACCEPTANCE-HOTFIX-CLOSURE.md`。

## Stage18 收口

Stage18 只拥有仓库/发布层面的完整中文镜像与第三方 provenance。它不得重开 Stage17 Manager runtime/profile Hotfix，不得改变 Gateway/OAuth/Tailscale/concurrency 行为，不得切换 shared Serena 9121。

Stage18 的事实源包括：
- 英文 live SoT；
- `docs/TRANSLATION-COVERAGE.json` 的逐文件 classification；
- `docs/THIRD-PARTY-PROVENANCE.json`；
- 原始 `LICENSE` 与非约束 `LICENSE.zh-CN.md`；
- 中英文 `THIRD_PARTY_NOTICES*`。

Stage18 已完成 155 个文本格式候选的显式分类、当前 live docs / Product
Skill/Guides 中文镜像、原始 `LICENSE` hash 保持、非约束中文阅读译本、
8 个 component + 4 个 Python dependency provenance、双语 notices 与
9 个 wheel release resource。targeted 27 PASS，full 191 PASS，Ruff、
secret scan、diff check PASS；源码 checkout 外 isolated wheel 安装验证
通过。Stage18 状态为 `LOCAL_IMPLEMENTATION + LOCAL_VERIFIED`，不声称
新的 real-host/device acceptance。

Closure: `docs/STAGE-18-CLOSURE.md`。

Stage18 完成后，程序状态仍为 `ACTIVE`，必须递归交接 Stage19。

## Stage 19 证据

- canonical public MCP identity 固定为 HTTPS 443，不再依赖显式旧端口；真实 Funnel 指向 loopback 9341 OAuth compatibility edge。
- 真实恢复事故证明：9340 OAuth child 存活不等于 Edge ready。此前 Start All 会在 9341 缺失时因为 9340 仍监听而错误报 fully ready；现已改为以仓库拥有的 9341 contract 为准。
- 已运行 OAuth proxy 只有在 9340 listener 与当前 canonical public issuer 完全匹配时才允许复用；随后由 compatibility edge 恢复 9341，不旋转 OAuth 密码、不改变 public identity。
- Windows venv launcher 到真实 listener 的 PID rebinding 现在也覆盖 OAuth Edge，receipt 会绑定真实 9341 listener，避免 generation/contract 假红。
- 真实主机恢复后：9341 OAuth metadata = 200，public /mcp = 401，public OAuth metadata = 200，URL/issuer 保持不变。
- production OAuth E2E 通过 metadata、401、DCR + PKCE token、87 tools authenticated MCP、Edge restart、refresh continuity、restart 后再次 87 tools authenticated MCP。
- 用户随后已在 ChatGPT 端重新配置成功；从该成功点开始，本 Stage 冻结 production connector/Funnel/OAuth，禁止为了验收再次做扰动性 restart。
- full repository gate：205 PASS；Ruff PASS；SECRET_SCAN_PASS；git diff --check PASS。
- fresh wheel 在 repo 外新 venv 安装并验证 8 component manifests、4 Manager resources、9 release resources、LICENSE hash 与 CLI 0.1.0。

Closure: `docs/STAGE-19-CLOSURE.md`。

## Supplemental RDC recovery-plane 证据

- RDC 保持 independent complementary full-machine repair/control plane，不是 Gateway child、WebGPT READY prerequisite、OAuth/Funnel component 或 Gateway lifecycle dependency。
- 当前恢复后的 RDC runtime 固定为 0.2.51，不再每次 startup 动态解析 `@latest`。
- health 明确拆为 installation / local process / control plane / execution plane 四层。
- 历史 incident 已证明 device visible/authenticated/online 时 live command transport 仍可能不可用，因此 control-plane `online` 永远不能单独证明 usable。
- local recovery 加固 startup/session handling，并在 presence 已 tracked 但 broadcast transport capability 未成功写入时自恢复重试。
- connector-side 真实通过 `list_devices`、`ping` -> `pong`、`get_config`、read-only host file probe，且 `transport_broadcast_v1` present。
- 因此当前 acceptance snapshot 的 `RDC_INSTALLATION`、`RDC_LOCAL_PROCESS`、`RDC_CONTROL_PLANE`、`RDC_TRANSPORT_BROADCAST_V1`、`RDC_EXECUTION_PLANE` 均为 VERIFIED。
- fallback 非递归：healthy WebGPT 可修 unhealthy RDC；healthy RDC 可修 unhealthy WebGPT；unhealthy plane 不得成为 active recovery executor；both-down 需要 local startup/reboot/human-local recovery。
- RDC 与 Windows-MCP 共用 physical desktop GUI state，mouse/keyboard/focus/clipboard/native dialog mutation 继续由 machine GUI lease 串行。
- 本 RDC closure 没有强制新的 physical Windows reboot。process restart/session restore 与 idempotent local startup 已验证；full-reboot claim 必须来自独立真实 reboot evidence。

Closure: `docs/RDC-FINAL-RECOVERY-PLANE-CLOSURE.md`。
