# WebGPT-as-Codex — STAGE-15-COMPONENT-INSTALL-UPGRADE-LIFECYCLE

STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2

继续开发 WebGPT-as-Codex。使用 **Computer Agent Skill + Loop Engineering + MCP-routed execution**。

这是自动接力窗口，不是只汇报进度的窗口。只要本 Stage 仍有已授权、可执行的 owned work，就继续执行、验证、更新文档、commit，并继续递归交棒。

Do not stop after reporting progress if owned work remains.

CURRENT_STAGE = STAGE-15-COMPONENT-INSTALL-UPGRADE-LIFECYCLE
NEXT_STAGE = STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK
AFTER_NEXT_STAGE = STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP
SOURCE_HEAD = 6e4ee6385c2650ec011063cbd0767f1b91440de0
PRODUCT_HEAD = 6e4ee6385c2650ec011063cbd0767f1b91440de0

## Stage objective

本 Stage 的唯一产品目标见下面“0. 本棒唯一目标”；这里保留该 canonical marker 以同时满足项目 handoff validator。

## Do not redo

不得重做 Stages 1-14；详细禁止边界见下面“0. 本棒唯一目标”和 Git/ownership 章节。

## Mandatory read order

严格执行下面“2. Computer Agent Skill Bootstrap”和“4. 必读文件清单”的精确顺序；本 marker 也用于项目 handoff validator。

## 0. 本棒唯一目标

把 WebGPT-as-Codex 做成真正的一仓库、一站式、discovery-first 的 MCP / 依赖安装升级系统：

- Agent/用户只从本仓库开始；
- 先检测已有环境和已有 MCP；
- 健康且兼容的已有实例必须 preserve，不重复部署；
- 缺失组件按官方来源自动安装；
- 已安装旧版本受控升级；
- 已安装更高且兼容的版本不降级；
- 默认目标是 upstream 最新 stable，但 latest 只是候选，必须经过来源/版本/兼容性 Gate；
- Coding Tools MCP 只需要本地 backend，**不依赖它自己的 Cloudflare 公网客户端**；
- 统一公网出口仍由已验证的 WebGPT Gateway -> OAuth -> Tailscale HTTPS 提供；
- Remote Desktop Commander 仍是 ChatGPT 侧独立人工安装/登录/配对边界，不把官方配对伪装成 WebGPT 自动流程。

本棒明确不做：

- 不重做 Stage 1-14；
- 不重新设计 Stage 14 已验证的 production Gateway/OAuth/Tailscale Edge；
- **不要 activate/switch 共享 Serena**：用户明确还有另一个任务正在使用 Serena，Stage 15 用 Coding Tools 搜索/读取即可；
- 不为了“统一”去改掉/停掉现有健康 MCP 或公网 endpoint；
- 不把第三方完整源码仓库 vendor 进本仓库；
- 不做 Stage 16 的 Serena 多实例并发隔离；
- 不做 Stage 17 的 Manager UI 动效/双语最终收口；
- 不做 Stage 18 的完整中文镜像最终审计。

前一棒：Stage 14 = CLOSED_LOCAL_VERIFIED。

当前 package version：以启动时 `pyproject.toml` / package metadata 的真实值为准，不从聊天记忆猜。

不得重做：Stages 1-14，除非出现和其 closure 直接矛盾的新证据，只允许 reopen 最小 affected boundary。

## 1. 真实仓库 / Workspace Map

- Repository：WebGPT-as-Codex local repository。
- Coding Tools workspace root：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\`
- Coding Tools repo path：`webgpt-as-codex\`
- 实际产品根：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex\`
- branch：`main`
- PRODUCT_HEAD：`6e4ee6385c2650ec011063cbd0767f1b91440de0`
- 当前实际 HEAD：启动时必须重新 `git rev-parse HEAD`。允许只比 PRODUCT_HEAD 多一个 handoff artifact/prompt commit；先读 log/diff 再判断，不把 prompt artifact 误判成产品实现变化。
- upstream：`origin/main`；Stage 14 commit 时 local main 仍在本地领先状态，启动时重新核实 ahead/behind。
- source root：`src/webgpt_as_codex/`
- tests root：`tests/`
- docs/SoT root：`docs/`
- component manifests：`components/*.json`
- project Skill：`skills/webgpt-as-codex/`
- installer/bootstrap core：`src/webgpt_as_codex/bootstrap.py`、`prerequisites.py`、`provision.py`、`registry.py`、`discovery.py`、`doctor.py`、`runtime.py`
- Stage 13 closure：`docs/STAGE-13-CLOSURE.md`
- Stage 14 closure：`docs/STAGE-14-CLOSURE.md`
- supplemental goals：`docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`
- deployment contract：`docs/DEPLOYMENT.md`
- roadmap：`docs/ROADMAP-2026-09-20.md`
- concurrency/fallback：`docs/CONCURRENCY-AND-FALLBACK.md`

### 已知 dirty / WIP — 必须保留

Stage 14 product commit 后，工作树故意保留了后续 Stage WIP：

- `pyproject.toml`
- `src/webgpt_as_codex/launcher.py`
- `src/webgpt_as_codex/manager.py`
- `src/webgpt_as_codex/registry.py`
- `tests/test_stage12.py`

这些主要属于 Stage 17/18 的双语 Manager、桌面 launcher、Manager API/custom component UI 和 packaging 工作。

**禁止 reset/clean/stash/drop。**
Stage 15 如果不需要这些文件，保持原样不写不提交。
如果 Stage 15 确实必须修改其中某个文件，先 path-scoped diff，证明 owner overlap，再只合并 Stage 15 必需的最小变化。

Tool-local metadata：
- 如果任何语义/IDE 工具会创建新 `.serena/`、cache/local config，先记录 Git pre-state；
- 本棒用户明确要求不要占用共享 Serena，因此默认不要激活 Serena；
- 当前 worker 新建、此前不存在的未跟踪工具元数据不得进入产品 commit；
- 已存在/已跟踪的同名目录不得擅删。

禁止：
- `git reset --hard`
- `git clean`
- force push
- 修改无关仓库
- 为了验证安装器而破坏现有健康实例
- 把 secrets/private public URLs 写进 Git

## 2. Computer Agent Skill Bootstrap

### Skill 真实入口

- Workspace Skill 根：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.skills\computer-agent\`
- Workspace-relative canonical Skill path marker：`.skills\computer-agent\SKILL.md`
- 当前 Stage prompt：本文件 `prompts/STAGE-15-NEXT-WINDOW.md`
- 上一 Stage closure：`docs/STAGE-14-CLOSURE.md`
- 下一 Stage prompt：Stage 15 closure 后生成 `prompts/STAGE-16-NEXT-WINDOW.md`

启动后按顺序精确读取：

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

默认用 Coding Tools `read_file` 读取，不用 GUI 打开文件。

如果无法访问 Skill 根：
- 明确记录 `COMPUTER_AGENT_SKILL_NOT_EXPOSED`；
- 使用本 prompt + repo Skill 作为 fallback；
- 不得声称“已经读过本机 Computer Agent Skill”。

## 3. 当前 MCP / Tool Execution Map

## MCP routing contract

本节以下表格和职责说明就是本 Stage 的 MCP routing contract。

第一条用户可见执行更新必须报告本 Stage 实际 MCP availability、用途、fallback 和第一批动作。

### MCP Locator Table

| MCP | 当前已知 direct/tool | 本机 locator | 在线/schema 验证 | down 时恢复 | direct 未暴露时 reconnect |
|---|---|---|---|---|---|
| Coding Tools MCP | 当前上一棒 direct namespace 为 `mcp__coding_tools_mcp__*` | trusted backend `http://127.0.0.1:8766/mcp`；workspace `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\` | `server_info` + workspace truth；需要 HTTP 时 initialize -> tools/list -> `server_info` | `D:\AgentData\20_State\coding-tools-mcp\start-trusted.ps1` | 优先当前 direct namespace；HTTP only if direct surface unavailable |
| Serena | **本棒按用户约束不使用共享实例** | `http://127.0.0.1:9121`；但另一个任务可能正在使用 active project | 不要 activate/switch；最多只读 listener/process evidence if installer detection needs it | 本棒不要抢占/重启，除非用户之后明确释放 | Stage 15 semantic fallback = Coding Tools search/read |
| Playwright MCP | 当前会话上一棒 direct schema 未暴露 | Extension/shared context `http://localhost:8931/mcp`；deployment root `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.tools\playwright-mcp\` | status/listener -> initialize -> tools/list -> minimal browser probe | `.tools\playwright-mcp\start-extension.cmd` for authenticated ChatGPT handoff; standalone only if auth state not needed | `.skills/computer-agent/scripts/mcp-http-client.mjs`；handoff 用 `chatgpt-loop-handoff.mjs`；整个 tabs/type/submit/verify 必须同一 mcp-session-id |
| Desktop / Remote Desktop Commander | 当前上一棒无 direct namespace | 无稳定 localhost HTTP；package `@wonderwhy-er/desktop-commander`，Remote vendor path independent | direct connector when exposed；必要时动态发现 package runtime，临时 stdio initialize -> tools/list -> get_config | 不硬编码 npm cache hash；按当前 process/package discovery | 若 Stage 15 确需 workspace 外 host/process 能力再恢复；不要与 Coding Tools 双写 repo |
| Windows-MCP | direct schema 可能未暴露 | `http://127.0.0.1:8001/mcp`，local 8000，remote OAuth 9142 | initialize -> tools/list；最小只读 Snapshot only when GUI truly needed | `%USERPROFILE%\.windows-mcp\start-server.cmd` / registered config | 本棒默认 NOT_NEEDED；只有 installer/native dialog 无 CLI 时才使用 |
| WebGPT Unified Gateway | 通过本项目 CLI/runtime | local `http://127.0.0.1:9330/mcp`；OAuth compat local 9341；dedicated Tailscale public port 10003 | initialize -> tools/list；Stage 14 已实测 87 tools；public OAuth E2E | Runtime Supervisor 只重启 WebGPT-owned Gateway/Edge | 不把 backend-specific public tunnel当依赖 |
| Remote Desktop Commander ChatGPT integration | vendor/direct integration | 无稳定本地 HTTP，应由 ChatGPT 官方/供应商连接路径配对 | connector presence + real minimal read-only action | 用户侧安装/登录/配对是人工边界 | 不伪造自动 OAuth/pairing |

### 本棒职责

Coding Tools：
- **Primary writer**；
- repo read/search/edit/tests/Git/docs/next prompt；
- 一个 repo 文件同时只能由它一个 writer 负责。

Serena：
- 本棒不要使用共享 active project；
- 不要因为 Computer Agent 默认语义路由而违反用户“Serena 正在给其他任务用”的显式约束；
- Coding Tools search/read 是本棒 semantic fallback。

Desktop Commander：
- 只在 Coding Tools 无法处理 workspace 外安装/host evidence 时使用；
- direct 未暴露不等于服务不存在；
- 不和 Coding Tools 同时改 repo。

Playwright：
- 本棒产品实现阶段不用于源码；
- 最终自动 handoff 必须使用；
- direct 未暴露时按本机 8931 自恢复；
- 同一 session 完成 new tab -> composer -> fill -> submit once -> sent message -> /c/ -> assistant run。

Windows-MCP：
- 仅 native GUI fallback；
- 不为了“证明所有 MCP 活着”主动启动。

## 4. 必读文件清单

| 顺序 | 精确路径 | 分类 | 为什么读 | 工具 | 读法 |
|---|---|---|---|---|---|
| 1 | `webgpt-as-codex/AGENTS.md` | SoT | repo invariants | Coding Tools | 全文 |
| 2 | `webgpt-as-codex/docs/CURRENT-PROJECT-STATE.md` | SoT | 当前 supplemental pointers/证据 | Coding Tools | 全文 |
| 3 | `webgpt-as-codex/docs/STAGE-14-CLOSURE.md` | Evidence | 生产 Gateway/Edge 已验证边界 | Coding Tools | 全文 |
| 4 | `webgpt-as-codex/docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md` | SoT | 最新用户目标 | Coding Tools | 全文 |
| 5 | `webgpt-as-codex/docs/DEPLOYMENT.md` | SoT | fresh/existing machine 部署合同 | Coding Tools | 全文 |
| 6 | `webgpt-as-codex/docs/ROADMAP-2026-09-20.md` | SoT | Stage ordering | Coding Tools | 全文 |
| 7 | `webgpt-as-codex/docs/CONCURRENCY-AND-FALLBACK.md` | SoT | Stage 16 边界，避免越界 | Coding Tools | 全文 |
| 8 | `webgpt-as-codex/docs/ARCHITECTURE.md` | SoT | planes/ownership/trust | Coding Tools | relevant + Stage14 production Edge sections |
| 9 | `webgpt-as-codex/docs/DECISIONS-AND-RISKS.md` | Decision/Risk | 已定安全/安装边界 | Coding Tools | supplemental + Stage14 sections |
| 10 | `webgpt-as-codex/components/*.json` | Manifest | 当前 install hints/version/source/endpoint | Coding Tools | 批量读取/解析 |
| 11 | `webgpt-as-codex/src/webgpt_as_codex/prerequisites.py` | Source | 系统环境 gate | Coding Tools | 全文/符号定向 |
| 12 | `webgpt-as-codex/src/webgpt_as_codex/provision.py` | Source | WebGPT-owned binary provisioning | Coding Tools | 全文 |
| 13 | `webgpt-as-codex/src/webgpt_as_codex/bootstrap.py` | Source | deployment orchestration | Coding Tools | 全文 |
| 14 | `webgpt-as-codex/src/webgpt_as_codex/discovery.py` | Source | prevent duplicate deployment | Coding Tools | 定向读 discovery/version |
| 15 | `webgpt-as-codex/src/webgpt_as_codex/doctor.py` | Source | protocol/safe/version health evidence | Coding Tools | 定向读 version + deep checks |
| 16 | `webgpt-as-codex/src/webgpt_as_codex/update.py` | Source | Stage11 fixed update authority; reuse safety | Coding Tools | 全文 |
| 17 | `webgpt-as-codex/tests/test_stage13.py` | Test | prerequisite/provision baseline | Coding Tools | 全文 |
| 18 | `webgpt-as-codex/tests/test_stage14.py` | Test | Gateway Edge preservation contract | Coding Tools | 全文 |
| 19 | `webgpt-as-codex/skills/webgpt-as-codex/SKILL.md` | Project Skill | portable execution contract | Coding Tools | 全文 |
| 20 | `webgpt-as-codex/skills/webgpt-as-codex/experience-ledger.md` | Experience | don't repeat install/update mistakes | Coding Tools | latest relevant entries |

## 5. 当前已确认事实 / 假设 / 限制

### CONFIRMED

- Stage 13 fresh-machine environment gate/provision foundation CLOSED_LOCAL_VERIFIED。
- Stage 14 production Unified Gateway/Edge CLOSED_LOCAL_VERIFIED。
- 当前 product closure HEAD = `6e4ee6385c2650ec011063cbd0767f1b91440de0`。
- Stage 14 live Gateway：localhost 9330，4 core backends，`tools/list=87`。
- Stage 14 real public Edge：OAuth metadata、401、DCR、PKCE、token、authenticated MCP、restart、refresh continuity 全 PASS。
- Stage 14 full repo gate = 120 PASS + Ruff PASS + secret scan PASS + diff check PASS。
- 当前机器已有并正在使用多套 MCP；**不能用“命令不在 PATH”推断没安装**。
- Coding Tools 当前 trusted server 为 8766，server version 上一棒实测 0.3.0，workspace = coding-tools-mcp-demo。
- Serena 标准 server 的 active project 是 process-wide；用户另一个任务可能在使用它，本棒不得切换。
- Playwright shared Edge 登录态 endpoint = `http://localhost:8931/mcp`，Computer Agent 已有同 session 自动 handoff 脚本。
- WebGPT production Edge 新增的 Tailscale port 10003 在 Stage14 启动前为空，不覆盖现有 443/8443/10000/10001/10002。

### WORKING_HYPOTHESIS

- Serena / Coding Tools / Windows-MCP 适合用 Python package/PyPI 或上游 release metadata 做 latest-stable resolver；必须从实际上游验证，不能直接假定。
- Playwright MCP 适合用 npm package metadata 解析 latest stable；必须区分 package version 和运行实例版本。
- Git/Node/npm/uv 可作为 component requirements，而不是无条件全部安装。
- Stage 15 应把“latest upstream / verified compatible / installed”分开建模，而不是只有一个 version 字段。

### BLOCKED_ENV / LIMITATION

- Remote Desktop Commander ChatGPT vendor pairing 不是本 Stage 可自动伪造的流程；检测/说明即可。
- 用户明确要求本棒不要占用共享 Serena。
- 当前工作树有 Stage17/18 WIP，path ownership 必须严格。
- 如果某上游没有可靠机器可读 stable release/version API，必须 fail closed 或保留 verified baseline，不得猜 latest。

## 6. 本棒精确执行步骤

### Step A — Baseline + component/version model

Goal：
- 读取所有 manifest/现有 discovery/update code；
- 建立 component install/version/source/requirements/ownership 模型。

Primary：Coding Tools。

Exact scope：
- `components/*.json`
- `registry.py`
- `discovery.py`
- `doctor.py`
- `prerequisites.py`
- `provision.py`
- `update.py`

Expected：
- 明确每个 component 的 installer family、version source、latest resolver、installed resolver、required system deps、ownership transition。

Exit：
- 模型可测试；没有根据 PATH 单点判断 absent。

### Step B — Latest-stable resolvers + compatibility gate

Goal：
- 实现 upstream latest stable discovery；
- 分开 `installed_version / upstream_latest / verified_compatible`；
- 不盲目 `@latest` 更新运行环境。

Primary：Coding Tools。

要求：
- official GitHub release / PyPI / npm metadata only；
- network failure 不能伪装成“已是最新”；
- prerelease 默认排除，除非 manifest 明确允许；
- newer installed compatible -> preserve；
- older -> candidate upgrade；
- latest candidate compatibility failure -> 不宣告部署完成。

### Step C — Installer adapters

Goal：
- 为当前选定 MCP 建立一站式安装路径。

至少覆盖：
- Serena
- Coding Tools MCP
- Playwright MCP
- Windows-MCP
- Tailscale
- MCPJungle
- mcp-auth-proxy

Remote Desktop Commander：
- 只检测/输出人工 ChatGPT integration step；
- 不伪造 vendor pairing。

Coding Tools：
- 安装本地 backend；
- Cloudflare remote client 不是 WebGPT required dependency。

适配器必须：
- discovery-first；
- preserve healthy；
- install missing；
- controlled upgrade；
- no downgrade；
- no duplicate listener/service；
- mutable action 有明确 confirmation/authority；
- WebGPT-installed instance 才能进入 lifecycle ownership。

### Step D — Existing-machine live dry-run

在当前机器先做 **dry-run / plan**：
- 不重装现有健康 MCP；
- 输出每组件 decision + installed/latest/health/source；
- 检查是否出现 duplicate proposal。

只有确认不会破坏现有服务后，才允许对“真正缺失且本 Stage 必需”的依赖做安装。

### Step E — Fresh-machine simulation/tests

用 tmp state/mocks/isolated fixture 模拟：
- missing all；
- already healthy latest；
- old version；
- newer version；
- binary exists but PATH absent；
- listener healthy but package resolver absent；
- upstream latest unavailable；
- compatibility gate fail；
- duplicate endpoint conflict。

### Step F — Gates + docs

- targeted tests；
- full pytest；
- Ruff；
- secret scan；
- `git diff --check`；
- path-scoped status/diff；
- live SoT/risks/experience 更新；
- closure；
- selective commit，绝不混入 Stage17/18 WIP。

### Step G — Recursive Playwright handoff

Stage 15 commit 后：
- real HEAD；
- 从 **当前 Computer Agent handoff-template** 重新生成 Stage16 prompt；
- 不复制本 prompt 改标题；
- prompt 包含完整 Recursive Handoff Invariant；
- 本地 Playwright 8931 direct schema 未暴露时先 reconnect；
- 同一 MCP session 新建 ChatGPT tab、填入、hash 校验、submit once、验证 sent message + /c/ + assistant run；
- 写 machine-local handoff receipt；
- 成功后当前窗口停止。

## 7. 失败恢复策略

## Failure protocol

下面恢复状态机是本 Stage 的 failure protocol。

固定顺序：

`POST_STATE_CHECK -> FAILURE_CLASSIFICATION -> SAME_TOOL_ADAPTATION -> KNOWN_LOCAL_MCP_RECOVERY -> STRUCTURED_FALLBACK -> CROSS_TOOL_FALLBACK -> BLOCKED`

普通故障状态 = `ACTIVE_RECOVERY`，不是暂停。

- Coding Tools revision mismatch：重新 read 最新 revision，再 edit；不 force overwrite。
- Coding Tools long command = running：poll `write_stdin/read_output`，不重复启动。
- upstream network/version query fail：保留 unknown/unavailable；使用 verified baseline 只能作为 fallback evidence，不能谎称 latest。
- installer non-zero：先查 package/process/listener/post-state，防止其实安装成功后又重复执行。
- Playwright handoff type/fill timeout：先查 composer normalized hash，不盲重填。
- Playwright submit/click error：先查 URL/composer/user message/send/generating；已经提交则绝不第二次 submit。
- Windows-MCP native dialog：每次状态变化重新 Snapshot；只有无 CLI/API 路径时用 GUI。
- Serena：**本棒用户约束优先，不执行 activate_project，不因 direct availability 去抢共享 active project。**
- 安全门/权限拒绝不是工具故障，不得用更宽 MCP 绕过。

只有所有已授权恢复路径都穷尽、且 remaining mandatory gate 真实依赖用户独占凭证/权限/设备，才可 `PAUSED_EXTERNAL_BLOCKER`。

## 8. Tests / Gates

## Self-evolving execution contract

整个 Stage 持续执行：
`Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse`。

重复 friction、错误 fallback、安装器副作用、版本误判、handoff 不稳定都必须判断是否需要沉淀进 Project Experience Ledger / Computer Agent Skill / eval。

维持约 20-minute soft stage budget（包含 docs/commit/handoff）；这是规划启发式，不是平台超时声明。实现扩张威胁 closure reserve 时按 Loop Engineering 拆 bounded sub-stage，而不是把 docs/handoff 留成尾债。

开工 baseline：
- 重新运行 targeted Stage13/14 + current full suite；
- 记录 exact baseline，不继承聊天里的 120 PASS 当永久事实。

每 slice：
- version resolver tests；
- decision engine tests；
- adapter tests；
- duplicate prevention；
- ownership tests；
- bootstrap/install-plan tests。

完成必须：
- full pytest PASS；
- Ruff PASS；
- secret scan PASS；
- git diff check PASS；
- existing-machine dry-run 证明不重复部署；
- 至少对可安全查询的真实 upstream/latest 做 live metadata evidence；
- 不能把网络 BLOCKED 当 PASS。

Historical failures：
- PATH absence ≠ service absence；
- version banner ambiguous；
- `@latest` 不能在 Doctor 里作为只读 version probe；
- integration instance 不得切共享 Serena；
- route ownership ≠ lifecycle ownership。

## 9. 文档与进度更新

在 next prompt **之前**逐项检查：

- `docs/CURRENT-PROJECT-STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS-AND-RISKS.md`
- `docs/DEPLOYMENT.md`
- `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`
- `docs/ROADMAP-2026-09-20.md`
- `skills/webgpt-as-codex/experience-ledger.md`
- relevant component manifests
- Stage 15 closure
- 如果出现通用 Computer Agent 新坑：检查 `.skills/computer-agent/maintenance.md`、对应 workflow/routing、`evals/scenarios.json` 和 skill validation。

每个 live doc 记录：
- `UPDATED_WITH_NEW_EVIDENCE`
- `CHECKED_NO_CHANGE_REQUIRED`
- 或 `NOT_APPLICABLE_THIS_STAGE`

硬顺序：

`ALL live-doc checks -> product closure commit -> read real HEAD -> reload handoff-template + final SoT -> generate Stage16 prompt -> validate/hash -> optional path-scoped handoff artifact commit -> Playwright handoff`

Docs-before-prompt is mandatory.

进度口径同时写：
- Stage %
- supplemental overall %
- `LOCAL_IMPLEMENTATION / LOCAL_VERIFIED / REAL_HOST_VERIFIED`

## 10. Git / Commit 纪律

Write owner：Coding Tools。

- 单工作树单 writer；
- 不要让 Desktop Commander/Windows-MCP 同时写 repo；
- path-scoped status/diff；
- 后续 WIP 不得混入 Stage15 commit；
- Stage product closure commit 与 prompt/handoff artifact commit 可以分开；
- prompt 中 `PRODUCT_HEAD/SOURCE_HEAD` 指向产品 closure commit；
- 如果 actual HEAD 只多 handoff artifact，下一 worker记录即可；
- 本棒默认不 push；
- 禁止 reset/clean/force push；
- 禁止自动删除用户现有 MCP 配置。

## 11. 本棒 Exit Criteria

## Closure contract

严格 closure 顺序：
`implementation -> targeted/full gates -> post-state/diff -> ALL live docs -> product closure commit -> real HEAD -> reload Stable Core + SoT -> next prompt -> validate/hash -> handoff artifact -> Playwright submit once -> sent-message + /c/ + assistant-run verify -> receipt`。

全部满足才可结束 Stage 15：

- [ ] component install/version/source/requirements model implemented
- [ ] latest stable resolvers use official metadata
- [ ] installed/latest/verified-compatible separated
- [ ] preserve/install/upgrade/diagnose/incompatible decisions tested
- [ ] existing healthy service not duplicated
- [ ] newer compatible install not downgraded
- [ ] Coding Tools unified deployment不依赖其 Cloudflare remote client
- [ ] selected MCP install adapters implemented/tested
- [ ] WebGPT lifecycle authority only for owned install
- [ ] current-machine dry-run does not propose destructive duplicate installs
- [ ] targeted tests PASS
- [ ] full suite PASS
- [ ] Ruff PASS
- [ ] secret scan PASS
- [ ] diff check PASS
- [ ] all live docs checked/updated before prompt
- [ ] Stage15 closure committed
- [ ] Stage16 prompt generated from real product HEAD
- [ ] prompt stable-core/markers/hash PASS
- [ ] Playwright exact-once handoff verified
- [ ] handoff receipt persisted

若产品 closure 完成但交棒 transport 失败：
`PRODUCT_STAGE_COMPLETE=true`
`HANDOFF_COMPLETE=false`
状态只能为 `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`，恢复只做 handoff 层，禁止重做 Stage15 产品代码。

## 12. 下一棒定义

- CURRENT_STAGE：`STAGE-15-COMPONENT-INSTALL-UPGRADE-LIFECYCLE`
- NEXT_STAGE：`STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK`
- AFTER_NEXT_STAGE：`STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP`

Stage 16 唯一目标：
- Serena multi-instance/fixed-project slot isolation；
- Coding Tools workspace/project concurrency boundary；
- GUI lease for Remote Desktop Commander/Windows-MCP；
- WebGPT Unified Gateway <-> Remote Desktop Commander complementary recovery；
- recovery loop prevention + concurrency tests。

Stage 16 next prompt 精确路径：
`prompts/STAGE-16-NEXT-WINDOW.md`

不得提前写死 Stage16 结果。

Batch/Stage 结束不是 Loop 停止条件。必须继续 Stage17 -> Stage18 -> Stage19 -> Supplemental Final Acceptance，除非 canonical SoT 真正满足 `GLOBAL_LOOP_COMPLETE` 或用户明确 `USER_STOPPED`。

## 13. Playwright 自动交棒手册

Loop continues，因此本节是 mandatory。

1. 先读：
   - `.skills/computer-agent/workflows/browser.md`
   - `.skills/computer-agent/environment.local.md`
2. docs/commit/next prompt 全部完成后才允许 handoff。
3. 当前已知 local Playwright endpoint：`http://localhost:8931/mcp`；deployment root：`D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.tools\playwright-mcp\`。
4. direct schema 未暴露时：
   - `.tools/playwright-mcp/status.cmd`
   - listener/process
   - standard MCP initialize
   - tools/list
   - minimal browser probe
5. 需要 ChatGPT 登录态时必须 Extension/shared-context；8931 down 时可用 `.tools/playwright-mcp/start-extension.cmd` 恢复。
6. local HTTP 多步操作保持同一 `mcp-session-id`。
7. 优先复用 `.skills/computer-agent/scripts/chatgpt-loop-handoff.mjs`。
8. 新建空白 ChatGPT tab，不复用旧 tab index/ref。
8.1 必须等待并验证 real active composer；hidden hydration fallback 不算可用 composer。
9. 从 repo 读取完整 prompt。
10. fill/type timeout 后先查 composer normalized SHA-256；未证明缺失前不重填。
11. 只 submit 一次。
12. submit 异常先查 post-state；已经出现 user message 或 composer 清空不得第二次发送。
13. 验证：
    - prompt user message 已出现；
    - 包含 SOURCE_HEAD；
    - URL 为 `/c/...`；
    - composer empty；
    - assistant run generating 或已有 assistant response。
    - new assistant run/response begins.
14. 全部 transport 都失败才记录 `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`。
15. handoff verified 后当前 worker 停止。

## 14. 第一条用户可见执行更新

第一条更新必须直接说明：

- 当前 Stage = Stage 15；
- Coding Tools / Serena / Playwright / Desktop Commander / Windows-MCP 当前 availability；
- 明确 Serena 本棒因用户约束不使用共享实例；
- 每个 MCP 本棒用途/fallback；
- 第一批动作：Skill bootstrap -> Git/SoT -> baseline -> component model。

不要只说“我开始了”。

## 15. 现在开始

严格执行：

`Computer Agent Skill bootstrap -> MCP map -> Git/SoT truth -> baseline -> component/version/source model -> latest resolvers -> install/upgrade decision engine -> adapters -> existing-machine dry-run -> tests/gates -> ALL live-doc checks/updates -> product closure commit -> reload Stable Core + final SoT -> Stage16 prompt -> validate/hash -> handoff artifact -> Playwright exact-once handoff`

不要停在规划阶段。
不要越过证据下结论。
不要吞掉下一 Stage。

## Recursive continuation invariant

### 16. Recursive Handoff Invariant — REQUIRED / MUST PROPAGATE IN FULL

下面规则必须由本 worker 在生成 Stage 16 prompt 时再次完整携带；Stage 16 也必须继续传给 Stage 17，之后逐棒递归。

1. **Handoff 是递归链。** 当前 worker 不只负责 `CURRENT_STAGE -> NEXT_STAGE`；NEXT_STAGE worker 必须被明确要求，在自己的产品 closure 后继续 `NEXT_STAGE -> AFTER_NEXT_STAGE`。
2. **每一棒必须显式携带三个指针：** `CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE`。不得只写“继续下一阶段”。
3. **跨 Batch/模块继续。** 一个 Stage 或 Batch 结束不等于 Global Loop Stop Condition。必须重新读 canonical roadmap 解析下一棒。
4. **每份 next prompt 必须 Zero-Guess、自包含：** repo/worktree/branch/PRODUCT_HEAD/actual HEAD/upstream/source/tests/SoT/Computer Agent Skill root/MCP locator/gates/dirty WIP/BLOCKED_ENV/failure recovery 全部明确。
5. **PRODUCT_STAGE_COMPLETE 与 HANDOFF_COMPLETE 独立。** 产品实现/验证/commit 完成但 Playwright handoff 失败时，只能写 `STAGE_COMPLETE_HANDOFF_PENDING`；恢复时只修 handoff transport，禁止重做已封板产品 Stage。
6. **任何 timeout/non-zero/连接中断后先查后态。** 特别是 fill/submit/commit/install/update 等可能有副作用的动作，禁止 blind retry，禁止重复发送。
7. **长 prompt 强校验。** prompt 文件与浏览器 composer 使用相同的 whitespace normalization 后做 SHA-256；不要混淆 UTF-8 byte count、JS characters 和 DOM text length。
8. **每一棒重新发现 MCP。** direct schema 未暴露 ≠ local service down。对已登记且本棒需要的 MCP，先 listener/process -> authorized auto-start -> initialize -> tools/list -> minimal probe；Playwright long chain 必须保持同一 `mcp-session-id`。
9. **Experience Absorption 递归传播。** 遇到可复用失败，执行 `RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE`；不能只绕过本次事故。
10. **Program state 必须区分：** `ACTIVE / PAUSED_EXTERNAL_BLOCKER / USER_STOPPED / GLOBAL_LOOP_COMPLETE`。用户停止和不可恢复外部阻塞都仍是未完成；只有 canonical Program Completion Gate 全部满足才允许 `GLOBAL_LOOP_COMPLETE`。
11. **下一 worker 生成下下一棒 prompt 时，必须再次完整复制本 invariant。** 不得缩成一句“遵循 loop-engineering.md”。
12. **如果 next prompt 缺失本完整 invariant，Zero-Guess / Recursive Handoff gate 失败，不得自动提交。**

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
- production Gateway/OAuth/HTTPS 被验证；
- multi-window concurrency/fallback 被验证；
- English + Chinese release/mirror/Manager 被验证；
- desktop launcher/Manager/package artifacts 可实际使用；
- 没有 active RED / expected-fail / 未豁免 mandatory blocker；
- 最终 SoT、closure、release-facing docs 与真实 HEAD 一致。

否则状态保持 `ACTIVE` 或对应未完成状态，禁止因为“暂时没别的事”写完成。

## Automatic handoff contract

自动接力已经授权。

本 Stage closure 后：

1. 使用已登录 ChatGPT 浏览器状态的 Playwright MCP；
2. 一个 MCP session 完成 tabs/new/select/composer/fill/submit/post-state；
3. 新建 ChatGPT 对话；
4. 获取 real visible composer；
5. 填入 exact validated prompt file；
6. 校验 normalized hash；
7. 只提交一次；
8. 提交后绝不重复 Enter/click Send；
9. 查询 sent user message、`/c/` URL、assistant generating/response；
10. verified 后写 machine-local handoff receipt；
11. 下一窗口必须继续本 Recursive Handoff Invariant；
12. 当前窗口停止。

如果 Playwright service/browser automation正常但 authenticated shared context 真正无法恢复，按 Computer Agent Browser workflow 允许的最后 handoff transport fallback 处理；仍必须 submit once + post-state verify。

现在开始执行 Stage 15。
