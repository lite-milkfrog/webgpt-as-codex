# WebGPT-as-Codex — STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK

STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2

继续开发 WebGPT-as-Codex。使用 **Computer Agent Skill + Loop Engineering + MCP-routed execution**。

这是自动接力窗口，不是只汇报进度的窗口。只要本 Stage 仍有已授权、可执行的 owned work，就继续执行、验证、更新文档、commit，并继续递归交棒。

Do not stop after reporting progress if owned work remains.

CURRENT_STAGE = STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK
NEXT_STAGE = STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP
AFTER_NEXT_STAGE = STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES
SOURCE_HEAD = c8588b9d73e25bb72c01c73656b9df9e993cfaf2
PRODUCT_HEAD = c8588b9d73e25bb72c01c73656b9df9e993cfaf2

## Stage objective

把 WebGPT-as-Codex 的“多窗口并行 + 双控制路径互补恢复”做成真实、可验证、不会互相抢状态的产品能力：

- Serena 不再依赖一个可被多个 ChatGPT 窗口反复切 project 的共享 mutable active-project；
- WebGPT 提供固定项目 Serena slot / instance pool，任务绑定 stable slot，释放后才复用；
- Coding Tools 明确 workspace/project 并发边界：读/独立进程可并行，同 worktree 单 writer，跨项目/并行 writer 使用隔离 workspace/worktree；
- Remote Desktop Commander / Windows-MCP 的真实 GUI side effect 受 machine-level GUI lease 串行保护；
- WebGPT Unified Gateway 与 Remote Desktop Commander 形成互补 recovery path：一边故障时可由另一边检查/恢复，但不得形成循环重启或双重副作用；
- recovery 必须有 owner、attempt identity、post-state、bounded retry，避免两个路径同时重启同一组件；
- 用并发/恢复测试证明上述边界。

## Do not redo

- 不重做 Stages 1-15；Stage 15 = CLOSED_LOCAL_VERIFIED。
- 不重新设计 Stage 14 production Gateway/OAuth/Tailscale Edge，除非 Stage16 测试暴露直接矛盾，只 reopen 最小 affected boundary。
- 不做 Stage 17 Manager 最终 UX/动效/双语/桌面 launcher 收口。
- 不做 Stage 18 中文镜像/第三方 notices 最终审计。
- 不做 Stage 19 全量 fresh/existing-machine acceptance。
- **不得 activate/switch 用户当前共享 Serena 9121 实例。** 当前共享实例正在被别的任务使用；Stage16 必须通过 Coding Tools 读取源码，并只在独立端口/独立固定 project 测试实例上验证 Serena pool。
- 不为了并发测试重启/杀掉用户现有 Coding Tools、Playwright、Windows-MCP、Remote Desktop Commander 或生产 WebGPT Edge。
- 不自动 push。
- 禁止 reset/clean/stash/drop/force push。

## 0. 本棒唯一目标

- Stage：`STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK`
- 唯一主目标：实现并验证 **Serena fixed-project slot isolation + Coding Tools workspace concurrency boundary + native GUI lease + Gateway/RDC complementary recovery with loop prevention**。
- 前一棒：Stage 15 = `CLOSED_LOCAL_VERIFIED`，产品 closure commit = `c8588b9d73e25bb72c01c73656b9df9e993cfaf2`。
- 当前 package version：`0.1.0`（来源：当前 `pyproject.toml`；启动时必须重新读取，不能从本 prompt 永久继承）。
- 不得重做：Stages 1-15；只在新矛盾证据证明必要时 reopen 最小边界。

Stage 15 已确认的关键前置事实：
- full repo = 146 PASS；
- Stage13-15 targeted = 38 PASS；
- Stage15 narrow = 26 PASS；
- Ruff / secret scan / diff check PASS；
- current-machine lifecycle dry-run 零 mutation、零 duplicate proposal；
- latest cache 只是 non-fresh evidence，不能授权 install/upgrade；
- Computer Agent Skill = `1.1.15-local-candidate`，48 scenarios PASS；
- 新通用经验：MCP request concurrency ≠ project/session state isolation。

## 1. 真实仓库 / Workspace Map

- Repository：WebGPT-as-Codex local repository。
- Coding Tools workspace root：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\`
- Coding Tools repo path：`webgpt-as-codex\`
- 产品根：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex\`
- branch：`main`
- PRODUCT_HEAD：`c8588b9d73e25bb72c01c73656b9df9e993cfaf2`
- 启动时 actual HEAD：重新 `git rev-parse HEAD`；允许只比 PRODUCT_HEAD 多一个 Stage16 prompt/handoff artifact commit，先读 log/diff 再判断。
- upstream：`origin/main`；Stage15 closure 时 local main ahead 9 / behind 0，启动时重新核实。
- source root：`src/webgpt_as_codex/`
- tests root：`tests/`
- docs/SoT root：`docs/`
- current Stage prompt：`prompts/STAGE-16-NEXT-WINDOW.md`
- previous closure：`docs/STAGE-15-CLOSURE.md`
- Stage16 primary SoT：`docs/CONCURRENCY-AND-FALLBACK.md`
- architecture：`docs/ARCHITECTURE.md`
- runtime/gateway candidate source：`src/webgpt_as_codex/runtime.py`、`gateway.py`、`discovery.py`、`mcp.py`
- Stage15 lifecycle：`src/webgpt_as_codex/lifecycle.py`，只作为 preserve/ownership/recovery evidence，不重做。
- 推荐新 owner modules：优先新建 `src/webgpt_as_codex/concurrency.py` / `recovery.py` 或等价窄模块；是否需要写现有 runtime/gateway 由 source map 证据决定。
- 推荐新 tests：`tests/test_stage16.py`。

### 已知 dirty / WIP — 必须保留

Stage15 closure 后工作树仍故意保留后续 Stage17/18 WIP：

- `pyproject.toml`
- `src/webgpt_as_codex/launcher.py`
- `src/webgpt_as_codex/manager.py`
- `src/webgpt_as_codex/registry.py`
- `tests/test_stage12.py`

这些是 pre-existing WIP。**禁止 reset/clean/stash/drop**。

Stage16 默认不要写这 5 个文件。若实现确实必须碰 `registry.py` 或其它 dirty file：
1. 先 path-scoped `git diff`；
2. 区分 pre-existing Stage17/18 WIP 与 Stage16 必需变化；
3. 只追加 Stage16 最小 owner diff；
4. closure commit 必须 selective stage，绝不吞入后续 WIP。

Tool-local metadata：
- 标准共享 Serena 9121 禁止 activate/switch；
- Stage16 若创建独立 Serena test instance，配置/state 放 machine-local temp/state，不进 Git；
- 若任何工具新建未跟踪 `.serena/`、cache、slot receipts，只算 `TOOL_LOCAL_METADATA`，不得进 product commit；
- 已存在/已跟踪同名目录不得擅删。

## 2. Computer Agent Skill Bootstrap

### Skill 真实入口

- Workspace Skill 根：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.skills\computer-agent\`
- workspace-relative：`.skills/computer-agent/`
- 当前 Stage prompt：`webgpt-as-codex/prompts/STAGE-16-NEXT-WINDOW.md`
- 下一 Stage prompt：`webgpt-as-codex/prompts/STAGE-17-NEXT-WINDOW.md`

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

### Stage15 experience absorption

开始前必须确认：
- Skill version `1.1.15-local-candidate` 或启动时更高版本；
- `.skills/computer-agent/CHANGELOG.md` 最新并发条目；
- `.skills/computer-agent/manifest.json` capability `mcp_concurrency_state_isolation`；
- regression scenario `R48`；
- 规则核心：**并行请求能力 != 并行项目状态隔离；Serena 标准实例 active project 是 process-wide；Coding Tools 一个 server 绑定一个 workspace；GUI side effects 是物理单机共享资源。**

## 3. 当前 MCP / Tool Execution Map

## MCP routing contract

第一条用户可见执行更新必须重新探测并报告 availability / 用途 / fallback，不得直接继承本 prompt 的在线状态。

| MCP | 当前已知 direct/tool | 本机 locator | 本棒用途 | down / direct 未暴露恢复 |
|---|---|---|---|---|
| Coding Tools MCP | 当前 handoff 窗口 direct `mcp__coding_tools_mcp__*` 可用 | trusted `http://127.0.0.1:8766/mcp`；workspace `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\` | **Primary repo writer**；read/search/edit/tests/Git/docs；并发/workspace source truth | `D:\AgentData\20_State\coding-tools-mcp\start-trusted.ps1`；direct 不暴露时 initialize -> tools/list -> `server_info` |
| Serena | direct schema 可能可见，但共享标准实例禁止改变 | standard `http://127.0.0.1:9121`；本机 executable `%USERPROFILE%\.local\bin\serena.exe` | **只做只读 availability/source evidence，不对共享 9121 activate/switch**；Stage16 允许启动独立固定-project test instance/unused port | 共享 9121 不抢占、不重启；Stage16 isolated slot 由项目实现选择独立 port/state；语义 fallback = Coding Tools search/read |
| Remote Desktop Commander | 当前 handoff 窗口 direct connector 可见 | 无稳定 localhost HTTP；package `@wonderwhy-er/desktop-commander` | host/process/log rescue evidence；验证 complementary recovery；不得与 Coding Tools 双写 repo | direct 不暴露时动态发现 package/runtime，临时 stdio initialize -> tools/list -> get_config/最小只读 probe；不硬编码 npm cache hash |
| Playwright MCP | 当前 handoff 窗口 direct schema 未暴露 | `http://localhost:8931/mcp`；deployment `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.tools\playwright-mcp\` | 最终 ChatGPT handoff；必要时 Web UI evidence | `.tools/playwright-mcp/status.cmd`；需要登录态用 `start-extension.cmd`；同一 `mcp-session-id` 完成全链；可用 `.skills/computer-agent/scripts/chatgpt-loop-handoff.mjs` |
| Windows-MCP | direct schema 可能未暴露 | `http://127.0.0.1:8001/mcp`；launcher `%USERPROFILE%\.windows-mcp\start-server.cmd` | native GUI lease/fallback contract 的实现/模拟；真实 GUI 仅在必要的 read-only/controlled probe | initialize -> tools/list；只有需要真实 GUI 时才启动/使用；网页 DOM 不用它代替 Playwright |
| WebGPT Unified Gateway | 本项目 CLI/runtime | local `http://127.0.0.1:9330/mcp`；Stage14 production Edge 已验证 | recovery route owner；验证 Gateway -> backend 与 R-D-C complementary model | 只重启 WebGPT-owned Gateway/Edge；不得重启外部 backend |
| Remote Desktop Commander ChatGPT integration | vendor/direct integration | 无稳定本地 HTTP | independent rescue path；验证 paired presence/可执行只读动作 | 安装/登录/配对仍是人工/vendor边界，不伪造 OAuth/pairing |

### Serena 本棒硬约束

- **禁止**对共享 9121 执行 `activate_project` / project switch。
- 当前共享 direct Serena 可能指向另一个工程，这正是 Stage16 要解决的问题，不是“请先把它切过来”。
- source analysis 优先 Coding Tools。
- 若测试 Serena slot：启动 **新的独立进程 + 独立 loopback port + fixed project argument/state**；必须记录 PID/port/owner receipt，并在测试结束只清理该 worker 创建的 isolated instance。
- 不杀、不重启、不修改共享 9121。

### Coding Tools

- Primary writer。
- 独立 read/process 可以 overlap；同一 repo 文件仍 single writer。
- 如果 Stage16 要验证 parallel writer，必须用 isolated temp/worktree fixture，不在当前产品 worktree 制造真实竞争写。
- 不把“能同时跑两个 command”误写成“一个 server 提供 conversation workspace isolation”。

### Remote Desktop Commander / Windows-MCP

- filesystem/process/terminal 类结构化动作可并行，但真实 mouse/keyboard/focus/clipboard/native dialog 共享 **machine GUI lease**。
- Stage16 应优先用 unit/integration fixture 验证 lease；真实 GUI probe 只做最小、可逆、无业务副作用验证。
- 两条 recovery path 不得同时 restart 同一 component。

## Mandatory read order

| 顺序 | 精确路径 | 分类 | 为什么读 | 工具 | 读法 |
|---|---|---|---|---|---|
| 1 | `webgpt-as-codex/AGENTS.md` | SoT | repo invariants / ownership | Coding Tools | 全文 |
| 2 | `webgpt-as-codex/docs/CURRENT-PROJECT-STATE.md` | SoT | Stage15 closure pointers / current state | Coding Tools | 全文 |
| 3 | `webgpt-as-codex/docs/STAGE-15-CLOSURE.md` | Evidence | exact Stage15 outputs/gates/dirty boundary | Coding Tools | 全文 |
| 4 | `webgpt-as-codex/docs/CONCURRENCY-AND-FALLBACK.md` | SoT | Stage16 canonical contract | Coding Tools | 全文 |
| 5 | `webgpt-as-codex/docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md` | SoT | user supplemental goal | Coding Tools | concurrency/fallback sections +全文必要时 |
| 6 | `webgpt-as-codex/docs/ROADMAP-2026-09-20.md` | SoT | Stage ordering / next pointers | Coding Tools | 全文 |
| 7 | `webgpt-as-codex/docs/ARCHITECTURE.md` | SoT | planes/ownership/trust | Coding Tools | concurrency/runtime/gateway sections |
| 8 | `webgpt-as-codex/docs/DECISIONS-AND-RISKS.md` | Decision/Risk | prior ownership/security constraints | Coding Tools | Stage13-16 relevant sections |
| 9 | `webgpt-as-codex/src/webgpt_as_codex/runtime.py` | Source | process/lifecycle owner & supervisor primitives | Coding Tools | symbols/full relevant functions |
| 10 | `webgpt-as-codex/src/webgpt_as_codex/gateway.py` | Source | backend route binding/ownership | Coding Tools | symbols + route lifecycle |
| 11 | `webgpt-as-codex/src/webgpt_as_codex/discovery.py` | Source | health/listener/process identity | Coding Tools | relevant functions |
| 12 | `webgpt-as-codex/src/webgpt_as_codex/mcp.py` | Source | MCP sessions/protocol utilities | Coding Tools | relevant functions |
| 13 | `webgpt-as-codex/src/webgpt_as_codex/lifecycle.py` | Source | Stage15 ownership/adoption semantics reused by recovery | Coding Tools | ownership + plan/apply only |
| 14 | `webgpt-as-codex/tests/test_stage14.py` | Test | Gateway/Edge regression boundary | Coding Tools | 全文 |
| 15 | `webgpt-as-codex/tests/test_stage15.py` | Test | lifecycle/ownership regression boundary | Coding Tools | 全文 |
| 16 | `webgpt-as-codex/skills/webgpt-as-codex/SKILL.md` | Project Skill | portable execution contract | Coding Tools | 全文 |
| 17 | `webgpt-as-codex/skills/webgpt-as-codex/experience-ledger.md` | Experience | recovery/concurrency lessons | Coding Tools | latest relevant entries |
| 18 | installed Serena source, only through host/Coding Tools file search | External source evidence | confirm fixed-project/active-project semantics if needed | Coding Tools / RDC read-only | **不要调用共享 Serena project switch** |

## 5. 当前已确认事实 / 假设 / 限制

### CONFIRMED

- Stage 15 product closure HEAD = `c8588b9d73e25bb72c01c73656b9df9e993cfaf2`。
- Stage15 full repo = 146 PASS；targeted Stage13-15 = 38 PASS；narrow Stage15 = 26 PASS。
- Serena 1.7.0 standard `SerenaAgent` active project 是 process-wide；切 project 会 shutdown previous active project。该事实来自已安装 source + Computer Agent 1.1.15 经验。
- 同一共享 Serena 9121 不适合多个 ChatGPT conversation 用 project switching 实现并行项目。
- Coding Tools trusted server 0.3.0 绑定一个 configured workspace；独立 command/process 可以 overlap，但同 worktree 写仍需 single writer。
- Remote/Desktop Commander 与 Windows-MCP 最终都作用于同一物理桌面；mouse/keyboard/foreground/clipboard/native dialog 不能无锁并行。
- Gateway 与 Remote Desktop Commander 是两个独立控制路径，适合互补恢复；同一路径不能在 public endpoint 全挂时自救。
- Stage14 production Gateway/OAuth/Tailscale Edge 已封板，Stage16 不改其 public contract。
- Stage17/18 WIP 仍存在于 5 个 dirty 文件，Stage16 必须 selective ownership。

### WORKING_HYPOTHESIS

- Serena fixed-project slots 可由独立 server process + unique port + fixed project configuration 实现；具体 CLI flags/启动参数必须从当前 installed Serena help/source 验证，不能猜。
- WebGPT 可以用 machine-local slot receipt / lease record 表达 Serena slot owner、project、pid/port、birth identity、release state。
- Coding Tools pool 可能先以 policy + binding identity + test fixtures 收口，而不是在 Stage16 直接实现完整多-server manager；若 roadmap 只要求 boundary，应选择最小可验证实现。
- GUI lease 应可使用 machine-local atomic lock/lease + owner/expiry/birth identity；必须防 stale lease，不可永久死锁。
- recovery loop prevention 应有 recovery attempt/correlation identity + component owner + hop budget / visited path，避免 Gateway/RDC 互相递归调用。
- 以上都是待 source/test 证据验证的假设，不得直接写 closure 事实。

### BLOCKED_ENV / LIMITATION

- 用户共享 Serena 正被其它任务使用；不能切换、重启或占用。
- Remote Desktop Commander vendor pairing 若未暴露是人工边界；Stage16 只能验证存在的 direct connector/本机 runtime，不伪造 pairing。
- 真正多 ChatGPT 窗口并发的自动化可能受当前 tool surface 限制；可用 isolated process/session integration tests + 最小真实 host probe，不能把 BLOCKED 伪成 PASS。
- 5 个 Stage17/18 dirty WIP 必须保留。
- Windows-MCP/Playwright direct schema 可能不在当前 ChatGPT tool surface；NOT_EXPOSED != NOT_RUNNING。

## 6. 本棒精确执行步骤

### Step A — Baseline + source map

Goal：
- 重新建立 Git/dirty/tests baseline；
- 找到 runtime/Gateway/process ownership/call chain；
- 找 Serena fixed-project CLI/source truth。

Primary：Coding Tools。

Exact scope：
- `runtime.py`、`gateway.py`、`discovery.py`、`mcp.py`、`lifecycle.py`
- installed Serena executable/source/help（只读）
- Stage14/15 tests。

Expected：
- exact owner/call-chain map；
- Serena isolated-instance launch contract；
- Stage16 owner path proposal。

Exit：
- 不需要共享 Serena project switch；
- 写路径已界定，不会踩 Stage17 dirty WIP。

### Step B — Serena fixed-project slot / pool

Goal：
- 实现 stable project -> isolated Serena slot binding；
- slot 有 unique port/state/owner identity；
- slot release 后才复用；
- stale slot 可安全诊断/回收；
- 共享 9121 永不被 Stage16 pool 管理。

Primary：Coding Tools。

要求：
- machine-local state，不把 project absolute private state写入 Git；
- process identity 至少含 pid + birth/image/launch evidence，不能只信 pid；
- create/acquire/release idempotent；
- same project 可稳定复用 compatible free slot；
- different project 不共享 mutable active project；
- duplicate acquisition / port conflict / stale receipt fail closed；
- isolated test process 只能清理本 worker 自己创建的实例。

如需要真实 Serena probe：
- 选未占用 loopback port；
- fixed project 指向 disposable fixture 或当前 repo read-only test slot；
- 不用 9121；
- 最后验证共享 9121 process/port 未变化。

### Step C — Coding Tools concurrency boundary

Goal：
- 把 one-workspace server、single-writer/worktree 隔离做成代码/contract/test 可验证边界。

Primary：Coding Tools。

至少覆盖：
- reads/independent commands can overlap；
- same worktree same file write requires one owner；
- different parallel writer requires distinct worktree/workspace identity；
- workspace binding mismatch -> diagnose/reject，而不是 silently mutate elsewhere；
- 不需要为了“pool”强行自动复制用户仓库，除非 source evidence/SoT明确要求。

### Step D — Machine GUI lease

Goal：
- 为 Remote Desktop Commander / Windows-MCP native GUI side effects建立共享 machine lease。

要求：
- filesystem/process/terminal 不必拿 GUI lease；
- mouse/keyboard/foreground/clipboard-sensitive/native dialog mutation 必须 acquire；
- lease machine-local；
- owner + acquired_at + expiry/heartbeat + stale recovery；
- release idempotent；
- two owners simultaneous acquisition only one wins；
- crash/stale lease 可 bounded reclaim；
- 不使用“全局永久 mutex 无恢复”。

真实 host probe可最小化，不做业务点击。

### Step E — Complementary recovery routing + loop prevention

Goal：
- Gateway/backend failure -> RDC rescue；
- RDC failure -> Gateway-routed structured rescue；
- no recovery cycle / no duplicate restart。

要求：
- recovery request 包含 attempt/correlation id；
- visited path/hop budget；
- component mutation owner；
- exactly-once side effect semantics：mutation timeout/non-zero 后先查后态；
- 同一 component 同一 attempt 只能一个 path 获得 mutation authority；
- external backend 无 ownership 时只能 diagnose/recommend/manual，不可 kill/restart；
- public WebGPT endpoint 全挂时必须能选择 independent RDC，不能让 Gateway 自调用自救；
- RDC unpaired/offline 时必须报告 external limitation，不伪造成功。

### Step F — Concurrency / recovery tests

至少模拟：
- two projects acquire Serena slots concurrently -> different fixed slots；
- same project safe reuse；
- stale slot receipt；
- occupied port；
- shared 9121 explicitly excluded；
- Coding Tools same-worktree writer conflict；
- different-worktree writer allowed；
- two GUI owners -> one lease；
- stale GUI lease recovery；
- Gateway -> RDC recovery；
- RDC -> Gateway recovery；
- both paths trying same restart -> one mutation owner；
- recovery cycle A->B->A blocked by visited/hop budget；
- timeout/non-zero followed by post-state success -> no second mutation；
- lack of lifecycle authority -> diagnose only；
- Stage15 lifecycle/Stage14 gateway regressions remain green。

### Step G — Real safe host evidence

- 重新检查共享 Serena 9121 的 listener/process identity before/after；不得 switch。
- 如可安全运行 isolated Serena slot，验证独立 port + fixed project + tools/list/minimal read-only call，然后只停止该 isolated instance。
- Remote Desktop Commander direct 存在时做 minimal read-only host/process probe；不要为了测试点击真实 GUI。
- 如果 Windows-MCP direct/HTTP 可用，最多验证 schema/lease integration，不做不必要 GUI mutation。
- 验证 production Gateway/Edge 未被 Stage16 测试重启。

### Step H — Gates + docs + closure

完成：
- Stage16 targeted；
- Stage14-16 regression；
- full pytest；
- Ruff；
- secret scan；
- `git diff --check`；
- path-scoped staged/unstaged review；
- all live-doc checks；
- Stage16 closure；
- selective product commit；
- real HEAD；
- reload template/SoT；
- Stage17 prompt；
- prompt validate/hash；
- optional prompt artifact commit；
- Playwright exact-once handoff。

## 7. 失败恢复策略

## Failure protocol

固定顺序：

`POST_STATE_CHECK -> FAILURE_CLASSIFICATION -> SAME_TOOL_ADAPTATION -> KNOWN_LOCAL_MCP_RECOVERY -> STRUCTURED_FALLBACK -> CROSS_TOOL_FALLBACK -> BLOCKED`

普通故障状态 = `ACTIVE_RECOVERY`。

- Coding Tools revision mismatch：重新 read latest revision，再 edit；不 force overwrite。
- Coding Tools command running：poll `write_stdin/read_output`；不重复启动。
- 发现同 worktree 另一个 writer：先查真实 diff/mtime/index；不要覆盖；分离 owner path或使用 isolated worktree/fixture。
- Serena：共享 9121 **禁止 activate/switch/restart**。isolated slot 失败先查新 port/process/post-state；只清理当前 worker 创建的 isolated instance。semantic fallback = Coding Tools。
- Serena launch flag不确定：从 installed `serena --help` / source确认，禁止猜参数。
- GUI lease acquire失败：读取 lease owner/expiry/post-state；未 stale 不抢；stale reclaim 必须满足 identity/expiry contract。
- recovery mutation non-zero/timeout：先查 listener/process/receipt/health，证明未发生才允许新 attempt；已经恢复则记录 success，不重复 restart。
- Gateway path失败：若 RDC independent path可用，走 RDC diagnose；不得降低 auth。
- RDC path失败：若 Gateway structured path可用，走 Gateway rescue；visited/hop contract阻止来回循环。
- Playwright handoff fill/submit timeout：先查 composer/hash/user message/URL/generating；已经提交绝不第二次 submit。
- Windows-MCP 卡住：重新 Snapshot；只有真正需要 native GUI时用；不得用更宽工具绕过权限门。
- 安全门/权限拒绝不是 tool failure，不能换更宽 MCP 绕过。

只有所有已授权恢复路径穷尽、且其余 Stage16 work 完成后，mandatory gate 仍依赖用户独占凭证/设备/人工 pairing，才允许 `PAUSED_EXTERNAL_BLOCKER`。

### Experience absorbed in previous stage

- Computer Agent Skill：`1.1.15-local-candidate`（启动时如更高，以实际为准）。
- 真实失败：多窗口共享 Serena active project 会互相切换；一个 MCP 能并发请求不等于 project/session isolation。
- 规则路径：
  - `.skills/computer-agent/SKILL.md`
  - `.skills/computer-agent/routing.md`
  - `.skills/computer-agent/environment.local.md`
  - `.skills/computer-agent/workflows/coding.md`
  - `.skills/computer-agent/manifest.json`
  - `.skills/computer-agent/CHANGELOG.md`
  - `.skills/computer-agent/evals/scenarios.json`
- regression：`R48`。
- Stage16 收口前重新跑 `.skills/computer-agent/scripts/validate_skill.py`。
- 若 Stage16 产生新的通用并发/lease/recovery经验，执行 `RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE`。

## 8. Tests / Gates

## Self-evolving execution contract

持续执行：

`Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse`

维持 **20-minute soft stage budget**，包含 docs/commit/handoff；这是规划启发式，不是平台超时承诺。若实现扩张威胁 closure reserve，拆 bounded Stage16 slice，但仍属于 Stage16 owner concern，不把 docs/handoff留成尾债。

开工 baseline：
- `.venv\Scripts\python.exe -m pytest tests/test_stage14.py tests/test_stage15.py -q`
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe -m ruff check src tests`
- 记录 actual counts，不硬继承 146。

Targeted：
- `tests/test_stage16.py`
- relevant runtime/gateway/lifecycle regressions。

必须 PASS：
- Stage16 concurrency/recovery tests；
- Stage14-16 targeted；
- full pytest；
- Ruff；
- secret scan；
- `git diff --check`；
- Computer Agent validator；
- path-scoped Git review；
- shared Serena 9121 before/after identity unchanged；
- real isolated Serena probe：如果环境允许必须验证；若真实外部限制则明确 `BLOCKED_ENV`，不能拿 unit test冒充 host PASS；
- zero unauthorized restart/kill of external MCP；
- no active RED / expected-fail mandatory gate。

Historical failures to guard：
- shared Serena active project collision；
- same worktree multi-writer race；
- GUI focus/mouse ownership collision；
- fallback A->B->A loop；
- mutation timeout blind retry；
- route ownership mistaken for lifecycle authority；
- direct-not-exposed mistaken as service-down。

## 9. 文档与进度更新

next prompt 之前逐项检查：

- `docs/CURRENT-PROJECT-STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS-AND-RISKS.md`
- `docs/CONCURRENCY-AND-FALLBACK.md`
- `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`
- `docs/ROADMAP-2026-09-20.md`
- `docs/DEPLOYMENT.md`（如 recovery/deployment contract改变）
- `skills/webgpt-as-codex/experience-ledger.md`
- Stage16 closure
- 如出现通用 Computer Agent 新坑：
  - `.skills/computer-agent/maintenance.md`
  - relevant routing/workflow
  - `.skills/computer-agent/evals/scenarios.json`
  - `.skills/computer-agent/scripts/validate_skill.py`

每个 live doc 标记：
- `UPDATED_WITH_NEW_EVIDENCE`
- `CHECKED_NO_CHANGE_REQUIRED`
- `NOT_APPLICABLE_THIS_STAGE`

硬顺序：

`ALL live-doc checks -> product closure commit -> read real HEAD -> reload handoff-template + final SoT -> generate Stage17 prompt -> validate/hash -> optional path-scoped handoff artifact commit -> Playwright handoff`

进度同时写：
- Stage %
- supplemental overall %
- `LOCAL_IMPLEMENTATION / LOCAL_VERIFIED / REAL_HOST_VERIFIED`

## 10. Git / Commit 纪律

Write owner：Coding Tools。

- 单 worktree 单 writer。
- Desktop Commander/Windows-MCP 不编辑 repo。
- 5 个 pre-existing Stage17/18 WIP 不得混入 Stage16 commit。
- new tool-local Serena slot/cache/lease state 不得进入 Git。
- product closure commit 与 prompt artifact commit 分开。
- Stage17 prompt 中 `PRODUCT_HEAD/SOURCE_HEAD` 指向 Stage16 product closure commit。
- 本棒默认不 push。
- 禁止 reset/clean/stash/drop/force push。
- 禁止通过 Git 操作删除用户现有 MCP 配置或 runtime state。

## 11. 本棒 Exit Criteria

## Closure contract

严格顺序：

`implementation -> targeted/full gates -> post-state/diff -> ALL live docs -> product closure commit -> real HEAD -> reload Stable Core + SoT -> Stage17 prompt -> validate/hash -> handoff artifact -> Playwright submit once -> sent-message + /c/ + new assistant run/response begins -> receipt`

全部满足才结束 Stage16：

- [ ] Serena fixed-project slot/pool implemented/tested
- [ ] shared 9121 excluded from mutation and before/after unchanged
- [ ] slot acquire/reuse/release/stale/port conflict tested
- [ ] Coding Tools workspace/worktree concurrency boundary implemented/tested
- [ ] machine GUI lease implemented/tested
- [ ] stale GUI lease recovery tested
- [ ] Gateway -> RDC rescue modeled/tested
- [ ] RDC -> Gateway rescue modeled/tested
- [ ] recovery loop prevention tested
- [ ] one component / one recovery attempt / one mutation owner tested
- [ ] mutation timeout post-state prevents duplicate restart
- [ ] no lifecycle authority -> diagnose only
- [ ] targeted tests PASS
- [ ] full suite PASS
- [ ] Ruff PASS
- [ ] secret scan PASS
- [ ] diff check PASS
- [ ] Computer Agent Skill validation PASS
- [ ] safe host evidence complete or explicitly BLOCKED_ENV without false PASS
- [ ] all live docs checked before prompt
- [ ] Stage16 closure committed
- [ ] Stage17 prompt regenerated from real product HEAD
- [ ] prompt markers/hash PASS
- [ ] Playwright exact-once handoff verified
- [ ] handoff receipt persisted machine-local

如果产品 closure 完成但 handoff transport失败：

`PRODUCT_STAGE_COMPLETE=true`
`HANDOFF_COMPLETE=false`

状态只能为 `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`；恢复只做 transport，不重做 Stage16 产品代码。

## 12. 下一棒定义

- CURRENT_STAGE：`STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK`
- NEXT_STAGE：`STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP`
- AFTER_NEXT_STAGE：`STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES`

Stage17 唯一目标：
- English + Chinese Manager functional parity；
- default Chinese desktop launcher/current deployment UX；
- environment/deployment/version/Gateway/OAuth/HTTPS/inventory surfaces；
- MCP URL copy/open；
- local OAuth password set/reveal/regenerate；
- add/remove migration-candidate flows；
- action feedback/activity log；
- requested motion tied to functional state；
- accessibility/reduced-motion；
- 吸收并妥善合并当前 5 个 Stage17/18 WIP，不丢用户已有改动。

Stage17 next prompt：
`prompts/STAGE-17-NEXT-WINDOW.md`

Stage17 closure后必须继续 Stage18，不得在 Stage17 stop。

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

- 当前 Stage = Stage16；
- Coding Tools / Serena / RDC / Playwright / Windows-MCP availability；
- **明确共享 Serena 不切 project、不重启，只用 isolated fixed-project instance测试**；
- 每个 MCP 本棒用途/fallback；
- 第一批动作：Skill bootstrap -> Git/SoT -> baseline -> concurrency/recovery source map。

不要只说“开始了”。

## 15. 现在开始

严格执行：

`Skill bootstrap -> MCP map -> Git/SoT truth -> baseline -> concurrency/recovery source map -> Serena fixed-project slots -> Coding Tools concurrency boundary -> GUI lease -> complementary recovery + loop prevention -> targeted/host evidence -> full gates -> ALL live-doc checks -> product closure commit -> reload Stable Core + final SoT -> Stage17 prompt -> validate/hash -> handoff artifact -> Playwright exact-once handoff`

不要停在规划阶段。
不要越过证据下结论。
不要吞掉下一 Stage。

## Recursive continuation invariant

## 16. Recursive Handoff Invariant — REQUIRED / MUST PROPAGATE IN FULL

下面规则必须由本 worker 在生成 Stage 17 prompt 时再次完整携带；Stage 17 也必须继续传给 Stage 18，之后逐棒递归。

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

recursive continuation ends only after the planned final stage and Final Overall Acceptance are both CLOSED_LOCAL_VERIFIED.

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

Stage16 closure后：

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
