# WebGPT-as-Codex — STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP

STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2

继续开发 WebGPT-as-Codex。使用 **Computer Agent Skill + Loop Engineering + MCP-routed execution**。

这是自动接力窗口，不是只汇报进度的窗口。只要本 Stage 仍有已授权、可执行的 owned work，就继续执行、验证、更新文档、commit，并继续递归交棒。

Do not stop after reporting progress if owned work remains.

CURRENT_STAGE = STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP
NEXT_STAGE = STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES
AFTER_NEXT_STAGE = STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE
SOURCE_HEAD = 5c323f45903d7a912def28ccaaf09dd4b5a3292a
PRODUCT_HEAD = 5c323f45903d7a912def28ccaaf09dd4b5a3292a

## Stage objective

把 WebGPT-as-Codex 的 Manager / 桌面入口从“已有基础控制面 + 未完成 WIP”收口成可实际使用的 **中英双语本机 Manager + 默认中文桌面入口 + 明确反馈/可访问性/安全本地配置操作**：

- English + Chinese Manager functional parity；
- 默认中文桌面 launcher/current deployment UX；
- environment/deployment/version/Gateway/OAuth/HTTPS/inventory 状态表面；
- MCP URL copy/open；
- 本机 OAuth password set/reveal/regenerate；
- add/remove migration-candidate flows；
- action feedback/activity log；
- motion 只服务于真实状态变化；
- accessibility + reduced-motion；
- 保留并正确吸收现有 5 个 Stage17/18 WIP，不丢用户已有改动；
- 修复当前 WIP 对 `manager/static/index.zh-CN.html` 的引用与“文件实际不存在”之间的矛盾；
- 保持 Stage16 concurrency/recovery contracts，不把 Manager UX 做成新的并发/恢复旁路。

## Do not redo

- 不重做 Stages 1-16；Stage16 = `CLOSED_LOCAL_VERIFIED`。
- 不重写 Stage14 production Gateway/OAuth/Tailscale Edge public contract。
- 不重做 Stage15 install/upgrade/lifecycle。
- 不重新设计 Stage16 Serena slot/Coding writer/GUI lease/recovery coordinator；若 Stage17 action surface 需要调用这些能力，只做最小集成。
- 不做 Stage18 中文镜像站 / 第三方 notices 最终审计。
- 不做 Stage19 fresh/existing-machine 全量验收。
- 不做 Supplemental Final Acceptance。
- 不自动 push。
- 禁止 reset/clean/stash/drop/force push。
- **不得 activate/switch/restart 用户共享 Serena 9121**。当前共享 direct Serena = 1.7.0，active project = `Jarvis-dev`；如本棒需要 Serena 语义分析，使用 Stage16 fixed-project isolated slot/独立端口，或退回 Coding Tools。
- 不为了 UI 测试重启/杀掉用户现有 Coding Tools、Playwright、Windows-MCP、Remote Desktop Commander、生产 Gateway/Edge。
- 不把真实 OAuth password/Token/Cookie 写入测试输出、文档、prompt、Git。

## 0. 本棒唯一目标

- Stage：`STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP`
- 唯一主目标：完成并验证 **Manager 中英功能对等 + 默认中文桌面 launcher + 本机配置/环境/组件管理 UX + action feedback/accessibility**。
- 前一棒：Stage16 = `CLOSED_LOCAL_VERIFIED`，产品 closure commit = `5c323f45903d7a912def28ccaaf09dd4b5a3292a`。
- 当前 package version：`0.1.0`（来源：Stage16 收口时重新读取 `pyproject.toml`；启动时再次读取实际值）。
- 不得重做：Stages 1-16；只在 Stage17 WIP/source/tests 暴露直接矛盾时 reopen 最小 affected boundary。
- Stage16 final gates：Stage14-16 targeted = 52 PASS；full repo = 167 PASS；Ruff PASS；secret scan PASS；diff check PASS。
- Computer Agent Skill = `1.1.16-local-candidate`；49 scenarios PASS；R48 = MCP concurrency != state isolation；R49 = process mutation timeout 需要 bounded post-state observation。

## 1. 真实仓库 / Workspace Map

- Repository：WebGPT-as-Codex local repository。
- Coding Tools workspace root：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\`
- Coding Tools repo path：`webgpt-as-codex\`
- 产品根：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex\`
- branch：`main`
- PRODUCT_HEAD：`5c323f45903d7a912def28ccaaf09dd4b5a3292a`
- 启动时 actual HEAD：重新 `git rev-parse HEAD`；允许只比 PRODUCT_HEAD 多一个 Stage17 prompt/handoff artifact commit，先读 log/diff 再判断。
- upstream：`origin/main`；Stage16 product closure 后 local main ahead 11 / behind 0，启动时重新核实。
- source root：`src/webgpt_as_codex/`
- UI root：`manager/static/`
- tests root：`tests/`
- docs/SoT root：`docs/`
- current Stage prompt：`prompts/STAGE-17-NEXT-WINDOW.md`
- previous closure：`docs/STAGE-16-CLOSURE.md`
- Stage17 primary UI/source：`src/webgpt_as_codex/manager.py`、`src/webgpt_as_codex/launcher.py`、`src/webgpt_as_codex/registry.py`、`manager/static/index.html`、目标 `manager/static/index.zh-CN.html`
- release/package boundary：`pyproject.toml`、`tests/test_stage12.py`
- relevant manager/security tests：`tests/test_stage6.py`、`tests/test_stage11.py`、`tests/test_stage12.py`
- recommended new tests：`tests/test_stage17.py`
- Stage16 preserved contracts：`src/webgpt_as_codex/concurrency.py`、`src/webgpt_as_codex/recovery.py`、`tests/test_stage16.py`

### 已知 dirty / WIP — **必须吸收，不得覆盖或丢失**

Stage16 product closure 后仍故意保留 5 个 pre-existing Stage17/18 WIP：

1. `pyproject.toml`
   - WIP 已把 Manager static package resources 从只含 `index.html` 改成同时声明 `index.zh-CN.html`。
2. `src/webgpt_as_codex/launcher.py`
   - WIP 已在生成的桌面 launcher 中设置 `WEBGPT_CODEX_UI_LANG=zh-CN`。
3. `src/webgpt_as_codex/manager.py`
   - WIP 已开始加入语言选择、`/zh` / `/en`、`/api/local-config`、environment operation、custom component create/delete、OAuth password reveal/generate/set 等本地控制面。
4. `src/webgpt_as_codex/registry.py`
   - WIP 已加入 `delete_custom_component`。
5. `tests/test_stage12.py`
   - WIP 已把 release asset expectation 改成需要 `index.zh-CN.html`。

**关键矛盾：**
- Stage16 closure 后实测 `manager/static/` 只有 `index.html`；
- `manager/static/index.zh-CN.html` **当前不存在**；
- 因此 pyproject/test 中的中文资源声明不是“已完成证据”，而是 Stage17 必须 reconcile 的未完成 WIP。

启动时必须：
1. path-scoped `git diff` 重新读取这 5 个文件；
2. 检查 `manager/static/index.zh-CN.html` 是否仍不存在；
3. 区分 Stage17/18 pre-existing WIP、当前 worker 新增变化、tool-local metadata；
4. 任何 closure commit 都必须 selective stage；
5. 禁止 reset/clean/stash/drop。

Tool-local metadata：
- isolated Serena slot receipts/cache/state 放 machine-local state，不进 Git；
- 临时 Manager/OAuth 测试 state 使用 `WEBGPT_CODEX_STATE_DIR` 指向 disposable machine-local temp；
- 浏览器 profile/session、handoff receipt、OAuth password 不进 Git；
- 已存在/已跟踪同名目录不得擅删。

## 2. Computer Agent Skill Bootstrap

### Skill 真实入口

- Workspace Skill 根：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.skills\computer-agent\`
- workspace-relative：`.skills/computer-agent/`
- 当前 Stage prompt：`webgpt-as-codex/prompts/STAGE-17-NEXT-WINDOW.md`
- 下一 Stage prompt：`webgpt-as-codex/prompts/STAGE-18-NEXT-WINDOW.md`

启动后按顺序读取：

1. `.skills/computer-agent/SKILL.md`
2. `.skills/computer-agent/MCP-SKILLS-INVENTORY.md`
3. `.skills/computer-agent/routing.md`
4. `.skills/computer-agent/workflows/loop-engineering.md`
5. `.skills/computer-agent/workflows/coding.md`
6. `.skills/computer-agent/workflows/cross-tool.md`
7. `.skills/computer-agent/environment.local.md`
8. `.skills/computer-agent/workflows/handoff-template.md`
9. 交棒前 `.skills/computer-agent/workflows/browser.md`
10. 权限不明时 `.skills/computer-agent/permissions.md`
11. 完成前 `.skills/computer-agent/validation.md`

默认用 Coding Tools `read_file`。不要用 Windows-MCP/GUI 打开这些文件。

如果 Skill 根无法访问：
- 记录 `COMPUTER_AGENT_SKILL_NOT_EXPOSED`；
- 使用本 prompt + repo Skill fallback；
- 不得声称已读取本机 Skill。

### Stage16 experience absorption

开始前必须确认：
- Skill version `1.1.16-local-candidate` 或启动时更高版本；
- `.skills/computer-agent/CHANGELOG.md` 最新条目；
- `.skills/computer-agent/manifest.json` capability `mcp_concurrency_state_isolation`；
- regression R48 / R49；
- R49 核心：stop/restart/kill timeout 或 non-zero 后必须进入 bounded post-state observation，持续核对 listener + PID birth/image identity，禁止瞬时一次检查后 blind retry。
- R48 核心：request concurrency != shared project/session state isolation。

## 3. 当前 MCP / Tool Execution Map

### MCP routing contract

第一条用户可见执行更新必须重新探测并报告 availability / 用途 / fallback，不得直接继承本 prompt 的在线状态。

| MCP | Stage16 最后实测 / locator | Stage17 用途 | 明确不用 | down / direct 未暴露恢复 |
|---|---|---|---|---|
| Coding Tools MCP | direct `mcp__coding_tools_mcp__*`；trusted `http://127.0.0.1:8766/mcp`；workspace `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\`；0.3.0 | **Primary repo writer**；WIP reconciliation、source/UI/tests/docs/Git；临时 Manager HTTP probe | 不跨 workspace 静默写；不与 RDC 双写 repo | `D:\AgentData\20_State\coding-tools-mcp\start-trusted.ps1`；listener -> initialize -> tools/list -> server_info |
| Serena | shared direct 可见；shared 9121 最后状态 = Serena 1.7.0 / Jarvis-dev | 仅在 Stage17 source semantic map 真有收益时，用 **isolated fixed-project slot**；否则 Coding Tools 足够 | **禁止 shared 9121 activate/switch/restart** | 用 `SerenaSlotPool` 在独立端口固定 WebGPT project；失败 fallback Coding Tools search/read |
| Remote Desktop Commander | direct connector 最后可用；0.2.50；无稳定 localhost HTTP | host/process/log evidence；必要时验证 desktop launcher 文件/进程后态 | 不编辑 repo；不替代 Manager HTTP/DOM 验收 | direct 未暴露时动态发现 package/runtime，临时 stdio initialize/tools/list/get_config；不硬编码 cache hash |
| Playwright MCP | `http://localhost:8931/mcp`；deployment `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.tools\playwright-mcp\`；Stage16 final listener PID 53880 | Manager Web UI E2E（若需要）、最终 ChatGPT handoff | 不读写源码/Git | `.tools/playwright-mcp/status.cmd`；需登录态用 `start-extension.cmd`；同一 mcp-session-id 完成长链；可复用 `.skills/computer-agent/scripts/chatgpt-loop-handoff.mjs` |
| Windows-MCP | `http://127.0.0.1:8001/mcp`；Stage16 final listener PID 50508 | 只有 native desktop/browser chrome/system dialog 或 handoff-only fallback | Manager 网页 DOM 不用它；不做 repo 写 | launcher `%USERPROFILE%\.windows-mcp\start-server.cmd`；initialize -> tools/list；只有确需 native GUI 才调用 |
| WebGPT Unified Gateway | local `http://127.0.0.1:9330/mcp`；Stage16 final PID 77084 | 只读状态/URL/Manager surface 的真实环境 evidence；保持 Stage14 public contract | 不为 Stage17 UI 重设计 Edge/OAuth | 只允许 WebGPT-owned runtime lifecycle；外部 backend 无 authority 不重启 |
| Remote Desktop Commander ChatGPT integration | vendor/direct integration | independent host rescue evidence | 不伪造 vendor pairing/OAuth | pairing 不可用则标 external limitation；结构化 repo work 继续由 Coding Tools 完成 |

### Stage17 concurrency hard rule

- 同 worktree 单 writer = Coding Tools。
- 如果需要并行 writer，必须 isolated worktree/workspace；默认不为了 Stage17 强行并行写。
- shared Serena 9121 不可切 project。
- native GUI side effects 若同时存在 RDC/Windows-MCP，必须遵守 Stage16 machine GUI lease，不允许抢焦点。
- Manager HTTP/UI tests 优先 loopback + disposable state，不触碰真实 OAuth secret。
- direct schema 未暴露 != service down。

## 4. Mandatory read order

| 顺序 | 精确路径 | 分类 | 为什么读 | 工具 | 读法 |
|---|---|---|---|---|---|
| 1 | `webgpt-as-codex/AGENTS.md` | SoT | repo invariants / ownership | Coding Tools | 全文 |
| 2 | `webgpt-as-codex/docs/CURRENT-PROJECT-STATE.md` | SoT | Stage16 closure pointers / current Stage17 state | Coding Tools | 全文 |
| 3 | `webgpt-as-codex/docs/STAGE-16-CLOSURE.md` | Evidence | exact Stage16 contracts/gates/dirty WIP | Coding Tools | 全文 |
| 4 | `webgpt-as-codex/docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md` | SoT | Stage17 product UX goal | Coding Tools | Manager/desktop/bilingual sections + 必要全文 |
| 5 | `webgpt-as-codex/docs/ROADMAP-2026-09-20.md` | SoT | Stage ordering / Stage17 outputs | Coding Tools | 全文 |
| 6 | `webgpt-as-codex/docs/ARCHITECTURE.md` | SoT | control plane/trust/concurrency | Coding Tools | Manager/Gateway/concurrency sections |
| 7 | `webgpt-as-codex/docs/DECISIONS-AND-RISKS.md` | Decision/Risk | Manager security + Stage16 ownership | Coding Tools | Stage6/11/14/16 + supplemental |
| 8 | `webgpt-as-codex/src/webgpt_as_codex/manager.py` | Source/WIP | current local Manager API + language WIP | Coding Tools | **先 diff，再全文/相关 symbols** |
| 9 | `webgpt-as-codex/manager/static/index.html` | Source | current English Manager canonical UI | Coding Tools | 全文 |
| 10 | `webgpt-as-codex/manager/static/index.zh-CN.html` | Expected WIP target | 当前 Stage16 后实测缺失；启动时重新确认 | Coding Tools | existence check；存在则全文，不存在则记录 confirmed missing |
| 11 | `webgpt-as-codex/src/webgpt_as_codex/launcher.py` | Source/WIP | default Chinese desktop launcher | Coding Tools | path diff + launcher functions |
| 12 | `webgpt-as-codex/src/webgpt_as_codex/registry.py` | Source/WIP | custom component delete boundary | Coding Tools | path diff + custom component functions |
| 13 | `webgpt-as-codex/pyproject.toml` | Package/WIP | bilingual static resource packaging | Coding Tools | path diff + data-files |
| 14 | `webgpt-as-codex/tests/test_stage12.py` | Test/WIP | release asset WIP expectation | Coding Tools | path diff + relevant tests |
| 15 | `webgpt-as-codex/tests/test_stage6.py` | Test | Manager HTTP/action behavior | Coding Tools | 全文/Manager tests |
| 16 | `webgpt-as-codex/tests/test_stage11.py` | Test | loopback/origin/payload/security | Coding Tools | Manager/security tests |
| 17 | `webgpt-as-codex/src/webgpt_as_codex/edge_runtime.py` | Source | OAuth password machine-local helpers | Coding Tools | password functions only |
| 18 | `webgpt-as-codex/src/webgpt_as_codex/prerequisites.py` | Source | environment/Tailscale reporting/allowed actions | Coding Tools | environment report + install boundary |
| 19 | `webgpt-as-codex/src/webgpt_as_codex/concurrency.py` | Closed Stage16 source | preserve leases/isolation | Coding Tools | public owner APIs only |
| 20 | `webgpt-as-codex/src/webgpt_as_codex/recovery.py` | Closed Stage16 source | preserve recovery attempt semantics | Coding Tools | public owner APIs only |
| 21 | `webgpt-as-codex/tests/test_stage16.py` | Regression | Stage16 boundary must stay green | Coding Tools | relevant regressions |
| 22 | `webgpt-as-codex/skills/webgpt-as-codex/experience-ledger.md` | Experience | prior Manager/browser/recovery lessons | Coding Tools | latest relevant entries |

## 5. 当前已确认事实 / 假设 / 限制

### CONFIRMED

- Stage16 product closure HEAD = `5c323f45903d7a912def28ccaaf09dd4b5a3292a`。
- Stage16 final gates = Stage14-16 52 PASS；full 167 PASS；Ruff/secret/diff PASS。
- Stage16 已实现 fixed-project Serena slots、Coding Tools writer policy、MachineGuiLease、RecoveryCoordinator；Stage17 必须 preserve。
- shared Serena 9121 在 Stage16 后仍是 PID 38924，direct Serena 1.7.0 / active project `Jarvis-dev`；禁止切换。
- current CLI Serena isolated worker 自报 1.28.1；其 source 仍有 process-wide active project semantics。
- Stage17 WIP 当前正好在 5 个文件中：`pyproject.toml`、`launcher.py`、`manager.py`、`registry.py`、`tests/test_stage12.py`。
- `manager/static/index.zh-CN.html` 在 Stage16 closure 后真实不存在，而 WIP pyproject/test 已引用它。
- Manager Stage11 已有 loopback Host/Origin/control-header/payload hardening；Stage17 新 local endpoints 不得削弱这些边界。
- OAuth password 是 machine-local secret；真实值不得进 logs/docs/tests/Git。
- Stage14 production Gateway/OAuth/Tailscale Edge 已封板，Stage17 只消费/展示状态，不重设计 public security contract。
- Computer Agent = 1.1.16-local-candidate / 49 scenarios；R49 来自 Stage16 isolated Serena shutdown race。

### WORKING_HYPOTHESIS

- English UI 可作为功能/结构 canonical base，再生成/维护 Chinese mirror；但是否共用 JS/data contract 或两份完整 HTML，必须先读现有 index.html/WIP 后决定，不能猜。
- WIP `manager.py` 中 `/api/local-config`、environment/components/oauth endpoints 可能可复用，但必须经过 Stage11 security contract、payload schema、secret leakage、idempotence 和 test evidence 才能保留。
- default Chinese desktop launcher 可能通过 `WEBGPT_CODEX_UI_LANG=zh-CN` 完成，但必须证明 launcher install/upgrade/reopen 和 packaged resource 都成立。
- add/remove migration candidate 应默认 machine-local registry mutation，不自动赋予 route/lifecycle authority；具体 UI wording/next action从当前 registry/Gateway contract确认。
- motion/accessibility 应绑定真实 functional state，不引入纯装饰性阻塞或 reduced-motion 违约。

### BLOCKED_ENV / LIMITATION

- shared Serena 正被别的项目使用；Stage17 不能 switch。
- Windows-MCP direct schema 当前上一棒未暴露；listener 存在不等于当前窗口 direct tool surface 已暴露。
- 真正用户桌面 launcher 的最终点击体验可能需要 minimal native probe；优先先做生成内容 + temp install + HTTP/browser evidence，不为了验收关闭用户窗口或改真实账号状态。
- OAuth password reveal 的真实值属于 secret；host验收只能验证操作成功/长度/changed/restart_required 等非秘密后态，不能记录 plaintext。
- Stage18 notices/mirror 与 Stage19 full deployment acceptance 仍未完成，所以 Stage17 closure不能写 GLOBAL_LOOP_COMPLETE。

## 6. 本棒精确执行步骤

### Step A — Skill / MCP / Git / WIP reconciliation

Goal：
- 重新建立 actual HEAD/upstream/dirty baseline；
- 读完整 Stage17 WIP diff；
- 确认中文 HTML 缺失/存在的真实状态；
- 建立 Stage17 owner map，不覆盖 Stage16或Stage18后续边界。

Primary：Coding Tools。

Exact scope：
- 5 个 dirty files；
- `manager/static/`；
- Stage16 closure/SoT；
- current package version。

Expected：
- WIP evidence table；
- exact source/test/UI owner map；
- no accidental staging/reset。

Exit：
- 能逐项解释现有 WIP 是什么、缺什么、哪些保留、哪些必须改。

### Step B — Manager API/security contract reconciliation

Goal：
- 审核并完成 WIP Manager local config/environment/components/oauth endpoints；
- 保持 Stage11 loopback/origin/control-header/payload boundary；
- secret never leaks into status/log/docs；
- mutation action explicit confirmation + idempotent post-state。

Primary：Coding Tools。

至少检查：
- `/api/local-config` 输出 public-safe；
- OAuth reveal/set/regenerate 仅 loopback + control header + confirm；test 使用 disposable state；
- generate 真正 regenerate，而不是“ensure existing”后假装生成；
- component create/delete 不可删除 built-ins，不自动 route/restart，无生命周期 authority；
- Tailscale install 只在明确 confirm + allowlisted adapter；如果已安装健康，UI显示 preserve/ready；
- exceptions只返回 sanitized classes/codes；
- request body limit/unknown fields/invalid ids 有测试。

Fallback：
- semantic impact map需要时用 isolated Serena；shared 9121 禁止切换。

### Step C — English + Chinese functional parity

Goal：
- 建立真实 `index.zh-CN.html`；
- English/Chinese 展示同一功能、数据字段、action capability；
- language route/default launcher behavior一致。

要求：
- 中文不是静态截图/删减版；
- 每个 English control 在 Chinese 有对应功能；
- 每个 Chinese control 走同一安全 API/contract；
- 明确 `/en`、`/zh`、default language；
- package wheel 必须真实包含两份资源；
- 无内嵌 secret/private endpoint；
- URL复制/打开使用明确、安全、可访问控件。

优先策略：
- 能抽公共 JS/CSS/data contract就减少双份漂移；
- 若当前无构建链，不为了“现代化”引入重量前端框架。

### Step D — Manager information architecture + activity feedback

Goal：
Manager至少清楚展示：
- environment readiness；
- installed/current component versions（现有 API证据能提供多少就显示多少，不编造）；
- Gateway / OAuth / HTTPS/public endpoint 状态；
- MCP inventory / migration state；
- local/public MCP URL；
- OAuth password configured state；
- add/remove custom MCP / migration candidate；
- action pending/success/failure；
- activity log / recent actions。

要求：
- loading/pending/disabled/error/success 是真实状态；
- mutation button 不允许多击并发重复副作用；
- action完成后 refresh真实后态；
- activity log不记录 plaintext password/token；
- unavailable/blocked 与 failed 分开。

### Step E — Desktop launcher / default Chinese UX

Goal：
- 默认桌面 launcher 打开中文 Manager；
- CLI/manual English route仍可用；
- launcher install/refresh idempotent；
- 当前 deployment/start-all semantics不被破坏。

Primary：Coding Tools。
Host evidence：可先在 disposable path 验证生成的 CMD/content；若安全且已有合同允许，再最小验证真实 desktop launcher existence/open behavior。

禁止：
- 删除用户其它桌面快捷方式；
- 关闭用户其它窗口；
- 重启生产 MCP只为了看 UI。

### Step F — Motion / accessibility

至少覆盖：
- keyboard navigation；
- visible focus；
- labels/ARIA where needed；
- status not color-only；
- controls disabled while mutation pending；
- `prefers-reduced-motion`；
- animation tied to loading/state transition, not endless decorative motion；
- language text仍可读、布局不溢出。

### Step G — Tests / real Manager evidence

至少新增/覆盖：
- English + Chinese resource both exist/package；
- default Chinese root route under launcher env；
- `/en` / `/zh`；
- same API/action functionality in both languages；
- local-config public-safe；
- OAuth set/reveal/regenerate with temp secret state，plaintext只在 local response test object，不写日志/file snapshot；
- regenerate changes value and does not just reuse existing；
- invalid/unknown payload rejected；
- built-in component delete blocked；
- custom create/delete idempotence；
- create does not imply route/lifecycle authority；
- environment operation confirm gate；
- action activity/result state；
- reduced-motion/accessibility static contract；
- Stage11 Manager security regressions；
- Stage12 release packaging；
- Stage14-16 regressions remain green。

Real safe host：
- temporary Manager on unused loopback port or isolated state；
- HTTP GET English/Chinese + local-config；
- controlled POST只对 disposable state；
- if Playwright used，DOM-level Manager checks，不用 Windows-MCP点网页；
- production 9200/9330/934x listeners不因测试被重启。

### Step H — Gates + docs + closure

必须完成：
- Stage17 targeted；
- Stage11/12/14/15/16 relevant regressions；
- full pytest；
- Ruff；
- secret scan；
- `git diff --check`；
- Computer Agent validator；
- wheel build + isolated resource check if package assets changed（**本棒 assets 已有 WIP，故 mandatory**）；
- path-scoped staged/unstaged review；
- all live-doc checks；
- Stage17 product closure commit；
- read real HEAD；
- reload handoff-template + final SoT；
- Stage18 prompt；
- prompt validate/hash；
- optional path-scoped handoff artifact commit；
- Playwright exact-once handoff。

## 7. 失败恢复策略

固定总序：

`POST_STATE_CHECK -> FAILURE_CLASSIFICATION -> SAME_TOOL_ADAPTATION -> KNOWN_LOCAL_MCP_RECOVERY -> STRUCTURED_FALLBACK -> CROSS_TOOL_FALLBACK -> BLOCKED`

普通故障 = `ACTIVE_RECOVERY`。

- Coding Tools revision mismatch：reread latest revision，再 edit；不 force overwrite。
- Coding Tools command running：poll/read output；不重复启动。
- 同 worktree writer冲突：读取真实 diff/index/owner lease；不覆盖；必要时 isolated worktree。
- Serena：shared 9121 禁止 activate/switch/restart。需要语义时用独立 fixed-project slot；失败 fallback Coding Tools。
- process stop/restart timeout/non-zero：按 R49，在 bounded observation window 内持续查 listener + PID birth/image；禁止 blind second kill/restart。
- Manager temp server start timeout：先查 listener/process/log/post-state；若已起不重复启动。
- OAuth mutation response timeout：先读 temp-state/post-state，确认是否已 set/regenerated，再决定下一步；绝不把 plaintext secret打日志。
- package build harness缺依赖：区分 harness failure vs release defect；使用正常 isolated PEP517 build，不降低 package resource gate。
- Playwright fill/submit timeout：先查 composer/message/URL/generating/hash；已提交绝不第二次 submit。
- Windows-MCP 卡住：只在真正 native GUI任务才恢复；网页Manager回到 Playwright/HTTP evidence。
- 安全门/权限拒绝不是 tool failure，不能换更宽 MCP 绕过。

### Experience absorbed in previous stage

- Computer Agent Skill：`1.1.16-local-candidate`。
- 真实失败：isolated Serena worker stop confirmation timeout，但进程随后退出；如果盲重试会产生 duplicate destructive side effect。
- 新规则：
  - `.skills/computer-agent/SKILL.md`
  - `.skills/computer-agent/workflows/cross-tool.md`
  - `.skills/computer-agent/manifest.json`
  - `.skills/computer-agent/CHANGELOG.md`
  - `.skills/computer-agent/evals/scenarios.json`
- regression：`R49`；R48 继续保护 concurrency/state isolation。
- Stage17 收口前重新跑 `.skills/computer-agent/scripts/validate_skill.py`。
- 若 Stage17 再产生通用 Manager/browser/secret/UX自动化经验，执行：
  `RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE`。

## 8. Tests / Gates

### 开工 baseline

先重新跑，不硬继承 167：

- `.venv\Scripts\python.exe -m pytest tests/test_stage11.py tests/test_stage12.py tests/test_stage16.py -q`
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe -m ruff check src tests`
- `.venv\Scripts\python.exe scripts\secret_scan.py`

因为 5 个 Stage17 WIP 已经存在，baseline 如果 RED：
- 先判断 RED 是否正是 WIP 未完成（例如缺 `index.zh-CN.html`）；
- 记录为 Stage17 owned RED；
- 不 reset WIP 来伪造 green baseline。

### Targeted

- new `tests/test_stage17.py`
- Manager tests from Stage6/11
- release packaging from Stage12
- Stage16 concurrency/recovery regression
- relevant launcher/registry tests

### Mandatory PASS before closure

- Stage17 targeted；
- relevant Stage11-17 regression；
- full pytest；
- Ruff；
- repository secret scan；
- `git diff --check`；
- wheel build；
- isolated wheel install/resource smoke：English + Chinese Manager resources both present and loadable；
- Computer Agent validator；
- path-scoped Git review；
- no secret in tracked files/log evidence；
- no active RED / expected-fail mandatory gate；
- production listeners not accidentally restarted；
- safe real Manager host evidence complete or explicitly BLOCKED_ENV without false PASS。

Historical failures to guard：
- source-tree UI works but wheel misses static resource；
- local status endpoint leaks secret；
- control endpoint bypasses Host/Origin/control-header；
- regenerate actually reuses old secret；
- custom component flow silently gains route/lifecycle authority；
- bilingual pages drift functionally；
- launcher references missing Chinese asset；
- mutation double-click/timeout causes duplicate side effect；
- Stage16 recovery/lease contracts regressed。

## 9. 文档与进度更新

next prompt 之前逐项检查：

- `docs/CURRENT-PROJECT-STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS-AND-RISKS.md`
- `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`
- `docs/ROADMAP-2026-09-20.md`
- `docs/DEPLOYMENT.md`
- `README.md`（Manager/desktop user-facing contract changed时）
- `skills/webgpt-as-codex/SKILL.md`（portable user workflow changed时）
- `skills/webgpt-as-codex/experience-ledger.md`
- Stage17 closure
- 如出现通用 Computer Agent 新坑：
  - `.skills/computer-agent/maintenance.md`
  - relevant workflow/routing
  - `.skills/computer-agent/evals/scenarios.json`
  - validator

每个 live doc 标记：
- `UPDATED_WITH_NEW_EVIDENCE`
- `CHECKED_NO_CHANGE_REQUIRED`
- `NOT_APPLICABLE_THIS_STAGE`

硬顺序：

`ALL live-doc checks -> product closure commit -> read real HEAD -> reload handoff-template + final SoT -> generate Stage18 prompt -> validate/hash -> optional path-scoped handoff artifact commit -> Playwright handoff`

进度同时写：
- Stage %
- supplemental overall %
- `LOCAL_IMPLEMENTATION / LOCAL_VERIFIED / REAL_HOST_VERIFIED`

## 10. Git / Commit 纪律

Write owner：Coding Tools。

- 单 worktree 单 writer。
- Stage17 **必须吸收** 5 个 pre-existing WIP；不能 reset、stash、覆盖。
- 启动时先 path-scoped diff，结束时按最终 owner结果 selective stage。
- Desktop Commander/Windows-MCP 不编辑 repo。
- tool-local temp state/browser profiles/OAuth secrets/receipts不得进 Git。
- product closure commit 与 Stage18 prompt artifact commit分开。
- Stage18 prompt 中 `PRODUCT_HEAD/SOURCE_HEAD` 指向 Stage17 product closure commit。
- 本棒默认不 push。
- 禁止 reset/clean/stash/drop/force push。
- 不通过 Git 操作删除用户 MCP/runtime config。
- 对 `index.zh-CN.html`：如果 Stage17 创建它，它是正式产品资源，应被跟踪；不要把它误归类成 tool-local metadata。

## 11. 本棒 Exit Criteria

严格顺序：

`implementation -> targeted/full/package gates -> post-state/diff -> ALL live docs -> product closure commit -> real HEAD -> reload Stable Core + SoT -> Stage18 prompt -> validate/hash -> handoff artifact -> Playwright submit once -> sent-message + /c/ + new assistant run/response begins -> receipt`

全部满足才结束 Stage17：

- [ ] 5 个 pre-existing WIP 已逐项 reconcile，无用户改动丢失
- [ ] missing `index.zh-CN.html` contradiction closed
- [ ] English Manager functional surface complete
- [ ] Chinese Manager functional parity complete
- [ ] default desktop launcher opens Chinese UX
- [ ] `/en` / `/zh` / default language tested
- [ ] environment/deployment/Gateway/OAuth/HTTPS/inventory surfaces verified
- [ ] MCP URL copy/open UX verified
- [ ] OAuth password set/reveal/regenerate tested without secret leakage
- [ ] regenerate actually changes password in disposable state
- [ ] add/remove migration candidate flows verified
- [ ] custom flow does not silently grant route/lifecycle authority
- [ ] action feedback/activity log verified and secret-safe
- [ ] accessibility/reduced-motion verified
- [ ] Stage11 security boundaries remain green
- [ ] Stage16 concurrency/recovery boundaries remain green
- [ ] targeted tests PASS
- [ ] full suite PASS
- [ ] Ruff PASS
- [ ] secret scan PASS
- [ ] diff check PASS
- [ ] wheel build PASS
- [ ] isolated wheel contains/loads both Manager languages
- [ ] Computer Agent Skill validation PASS
- [ ] safe host evidence complete or explicitly BLOCKED_ENV
- [ ] all live docs checked before prompt
- [ ] Stage17 closure committed
- [ ] Stage18 prompt regenerated from real product HEAD
- [ ] prompt markers/hash PASS
- [ ] Playwright exact-once handoff verified
- [ ] handoff receipt persisted machine-local

如果产品 closure 完成但 handoff transport失败：

`PRODUCT_STAGE_COMPLETE=true`
`HANDOFF_COMPLETE=false`

状态只能为 `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`；恢复只做 transport，不重做 Stage17 产品代码。

## 12. 下一棒定义

- CURRENT_STAGE：`STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP`
- NEXT_STAGE：`STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES`
- AFTER_NEXT_STAGE：`STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE`

Stage18 唯一目标：
- README/website/release-facing Chinese mirror 与 English source parity；
- third-party notices/license attribution 完整审计；
- release-facing 文档/镜像不泄露 machine-local/private state；
- 不重做 Stage17 Manager functional implementation；
- 完成后继续 Stage19，不得 stop。

Stage18 next prompt：
`prompts/STAGE-18-NEXT-WINDOW.md`

Stage18 closure 后必须继续 Stage19，并继续完整 Recursive Handoff Invariant。

## 13. Playwright 自动交棒手册

1. 先读：
   - `.skills/computer-agent/workflows/browser.md`
   - `.skills/computer-agent/environment.local.md`
2. docs/commit/next prompt完成后才允许 handoff。
3. Playwright endpoint：`http://localhost:8931/mcp`；deployment：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.tools\playwright-mcp\`。
4. direct schema 未暴露：
   - `.tools/playwright-mcp/status.cmd`
   - listener/process
   - initialize
   - notifications/initialized
   - tools/list
   - minimal browser probe
5. 需要 ChatGPT login state：Extension/shared-context；8931 down 时 `.tools/playwright-mcp/start-extension.cmd`。
6. 一条长链必须同一 `mcp-session-id`。
7. 优先复用 `.skills/computer-agent/scripts/chatgpt-loop-handoff.mjs`。
8. 新建空白 ChatGPT tab，不复用旧 tab index/ref。
9. 必须等待并验证 **real active composer**；hidden hydration fallback不算。
10. 从 repo读取 exact prompt。
11. fill/type timeout后先查 composer normalized SHA-256，不盲重填。
12. 只 submit 一次。
13. submit异常后只查 post-state；若 user message出现或 composer清空，禁止第二次 submit。
14. 验证：
   - sent user message存在；
   - 包含 SOURCE_HEAD；
   - URL = `/c/...`；
   - composer empty；
   - assistant generating/已有 response；
   - **new assistant run/response begins**。
15. Playwright authenticated shared context真正不可恢复时，按 browser workflow 的 handoff-only Windows-MCP fallback；仍只提交一次并验证后态。
16. 全 transport失败才记录 `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`。

## 14. 第一条用户可见执行更新

下一 worker 第一条更新必须直接说明：

- 当前 Stage = Stage17；
- Coding Tools / Serena / RDC / Playwright / Windows-MCP availability；
- **明确共享 Serena 9121 不切 project、不重启；语义需要时走 Stage16 isolated fixed-project slot**；
- 每个 MCP 本棒用途/fallback；
- 第一批动作：Skill bootstrap -> Git/SoT -> 5-file WIP diff + missing Chinese asset reconciliation -> baseline tests -> Manager API/UI map。

不要只说“开始了”。

## 15. 现在开始

严格执行：

`Skill bootstrap -> MCP map -> Git/SoT truth -> WIP reconciliation -> baseline -> Manager API/security -> bilingual functional parity -> desktop launcher -> feedback/accessibility -> targeted/real host/package evidence -> full gates -> ALL live-doc checks -> product closure commit -> reload Stable Core + final SoT -> Stage18 prompt -> validate/hash -> handoff artifact -> Playwright exact-once handoff`

不要停在规划阶段。
不要越过证据下结论。
不要吞掉下一 Stage。

## 16. Recursive Handoff Invariant — REQUIRED / MUST PROPAGATE IN FULL

下面规则必须由本 worker在生成 Stage18 prompt 时再次完整携带；Stage18也必须继续传给Stage19，之后逐棒递归。

1. **Handoff 是递归链。** 当前 worker 不只负责 `CURRENT_STAGE -> NEXT_STAGE`；NEXT_STAGE worker 必须被明确要求，在自己的产品 closure 后继续 `NEXT_STAGE -> AFTER_NEXT_STAGE`。
2. **每一棒必须显式携带三个指针：** `CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE`。不得只写“继续下一阶段”。
3. **跨 Batch/模块继续。** 一个 Stage 或 Batch 结束不等于 Global Loop Stop Condition。必须重新读 canonical roadmap 解析下一棒。
4. **每份 next prompt 必须 Zero-Guess、自包含：** repo/worktree/branch/PRODUCT_HEAD/actual HEAD/upstream/source/tests/SoT/Computer Agent Skill root/MCP locator/gates/dirty WIP/BLOCKED_ENV/failure recovery 全部明确。
5. **PRODUCT_STAGE_COMPLETE 与 HANDOFF_COMPLETE 独立。** 产品实现/验证/commit完成但 Playwright handoff失败时，只能写 `STAGE_COMPLETE_HANDOFF_PENDING`；恢复时只修 handoff transport，禁止重做已封板产品 Stage。
6. **任何 timeout/non-zero/连接中断后先查后态。** 特别是 fill/submit/commit/install/update/restart/lease acquire 等可能有副作用的动作，禁止 blind retry，禁止重复发送/重复重启。
7. **长 prompt 强校验。** prompt 文件与浏览器 composer 使用相同 whitespace normalization 后做 SHA-256；不要混淆 UTF-8 byte count、JS characters 和 DOM text length。
8. **每一棒重新发现 MCP。** direct schema 未暴露 ≠ local service down。对已登记且本棒需要的 MCP，先 listener/process -> authorized auto-start -> initialize -> tools/list -> minimal probe；Playwright long chain 必须保持同一 `mcp-session-id`。
9. **Experience Absorption 递归传播。** 遇到可复用失败，执行 `RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE`；不能只绕过本次事故。
10. **Program state 必须区分：** `ACTIVE / PAUSED_EXTERNAL_BLOCKER / USER_STOPPED / GLOBAL_LOOP_COMPLETE`。用户停止和不可恢复外部阻塞都仍是未完成；只有 canonical Program Completion Gate 全部满足才允许 `GLOBAL_LOOP_COMPLETE`。
11. **下一 worker 生成下下一棒 prompt 时，必须再次完整复制本 invariant。** 不得缩成一句“遵循 loop-engineering.md”。
12. **如果 next prompt 缺失本完整 invariant，Zero-Guess / Recursive Handoff gate失败，不得自动提交。**

recursive continuation ends only after the planned final stage and Supplemental Final Acceptance are both CLOSED_LOCAL_VERIFIED.

### Program Completion Gate

本 supplemental program 只有同时满足以下条件才允许 `GLOBAL_LOOP_COMPLETE`：

- Stage 15 CLOSED_LOCAL_VERIFIED；
- Stage 16 CLOSED_LOCAL_VERIFIED；
- Stage 17 CLOSED_LOCAL_VERIFIED；
- Stage 18 CLOSED_LOCAL_VERIFIED；
- Stage 19 CLOSED_LOCAL_VERIFIED；
- Supplemental Final Acceptance CLOSED_LOCAL_VERIFIED；
- mandatory full tests/lint/secret/diff/package/install gates PASS；
- fresh/existing-machine deployment合同被验证；
- production Gateway/OAuth/HTTPS被验证；
- multi-window concurrency/fallback被验证；
- English + Chinese release/mirror/Manager被验证；
- desktop launcher/Manager/package artifacts可实际使用；
- 没有 active RED / expected-fail / 未豁免 mandatory blocker；
- 最终 SoT、closure、release-facing docs与真实 HEAD一致。

否则状态保持 `ACTIVE` 或对应未完成状态，禁止因为“暂时没别的事”写完成。

## Automatic handoff contract

自动接力已经授权。

Stage17 closure后：

1. 使用已登录 ChatGPT 浏览器状态的 Playwright MCP；
2. 一个 MCP session 完成 tabs/new/select/composer/fill/submit/post-state；
3. 新建 ChatGPT 对话；
4. 获取 real active composer；
5. 填入 exact validated prompt file；
6. 校验 normalized hash；
7. 只提交一次；
8. 提交后绝不重复 Enter/click Send；
9. 查询 sent user message、`/c/` URL、assistant generating/response；
10. verified 后写 machine-local handoff receipt；
11. 下一窗口必须继续本 Recursive Handoff Invariant；
12. 当前窗口停止。

如果 Playwright service/browser automation正常但 authenticated shared context真正无法恢复，按 Computer Agent Browser workflow允许的最后 handoff transport fallback处理；仍必须 submit once + post-state verify。
