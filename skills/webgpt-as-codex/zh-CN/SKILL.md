# WebGPT-as-Codex Skill — 简体中文镜像

[English](../SKILL.md) | **简体中文**

版本：\`1.2.0\`。本 profile 与同级 \`../../computer-agent/\` canonical portable
core 一起发行；本文件保留 WebGPT-as-Codex 的产品专项知识，不替代、不裁剪
Computer Agent 的通用 workflow/eval。完整 Experience Ledger 与 canonical
core 无损同步。

本 Skill 用于：网页 AI 需要通过 MCP 操作真实电脑/代码库，并在长任务中可靠持续工作。

## 启动契约
1. 先定位项目本地事实源，再使用 chat memory。
2. 读取 `docs/CURRENT-PROJECT-STATE.md`、owner-stage closure、`AGENTS.md`。
3. 发现真实 tool/service 状态；区分 installed、configured、listening、protocol-healthy、remote-reachable。
4. 不修改无关 repo 和健康 service。

## Tool routing
- semantic code navigation：Serena；
- repo write/test/local Git：绑定正确时用 Coding Tools；
- whole-machine file/process：Desktop Commander；
- browser/Web App DOM：Playwright；
- native Windows UI：Windows-MCP；
- hosted platform API：可用时优先 dedicated connector/API。

优先结构化工具，fallback 前先诊断。详见 `routing.md`。

## Loop Engineering
每个 Stage 一个 owner concern，并显式保存 `CURRENT_STAGE`、`NEXT_STAGE`、`AFTER_NEXT_STAGE`。没有 contradictory evidence 不重审已关闭 Stage。closure/handoff 前先 validation + docs。详见 `loop-engineering.md`。

## 自演进执行
不只执行，而是：
`Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse`

SoT loading、planning、stage sizing、routing、MCP use、implementation、validation、docs、Git、handoff 任何重复 friction 都进入该循环。

一个 failed call 不证明 MCP unavailable。先诊断 binding/session/auth/capability/harness。fallback 有理由时记录原因。

lesson 最窄分类：
- general reusable -> Skill；
- MCP-specific -> MCP Guide；
- machine-specific -> local inventory/config；
- one-off -> stage evidence。

用户指导如果揭示 stable operating principle，也按同样规则分类。

## Durable Loop evidence / sizing
长任务事实不只放 chat。repo stage definition + machine-local closure state + `loop-evidence.md` stage-cost schema 共同提供恢复证据。

约 20 分钟是包含 closure reserve 的软目标，不是平台 timeout。拥有足够 first-pass history 后，用 bounded observed median recalibrate。projected implementation 会吃掉 closure reserve 时，先拆 bounded owner concern；split depth 到顶则 freeze scope + close。

## Local memory
durable fact 在执行过程中写 local SoT。Chat context 只是 transport cache，不是 authority。Git 中的 SoT 不得含 secret。

## Handoff
next-window prompt 从当前 verified state **重新生成**，不是重命名旧 prompt。可先 commit 不含 `SOURCE_HEAD` 的 next-stage plan，closure commit 后再注入真实 HEAD。自动 continuation 时必须验证 submit + new run。

pre-submit 可以重新获取 tab/composer/ref；一旦 send action attempted，就不能再 send。lost response 只查 post-state。

handoff 是递归契约：每个 window 收完自己的 stage 后生成并 Playwright-submit 下一 prompt，保留 CURRENT/NEXT/AFTER_NEXT，直到 planned final stage + Final Overall Acceptance 都关闭。详见 `handoff.md`。

## Experience Ledger
不能因为代码变简单就删除 defensive rule。先追 origin、验证 failure mechanism 是否仍可能，再 keep/relocate/retire-with-evidence。详见 `experience-ledger.md`。

## MCP operating knowledge
Routing 决定 WHICH；Guide 决定 HOW；real evidence 决定是否成功；experience 决定下次如何更好。

不能从 MCP name 推 capability。Guide template 覆盖 mental model、best/poor use、real tools/schema、goal pattern、mistake、diagnosis、verification、performance/cost、lesson、alternative。

## Generic MCP extension
新 MCP discovery-first。默认 `add-mcp` dry-run：validate public-safe manifest、reject credential literal、真实 initialize + tools/list、build/validate Guide、derive routing recommendation。只有显式 apply 才 machine-local mutation。

capability evidence 四态：`success` / `unavailable` / `failed` / `unattempted`。custom component 可进入 registry/Doctor/Manager visibility，但不自动获得 Stage8 lifecycle authority。

Portable Guide 不含 local endpoint/binding/path/health/secrets。machine-local custom manifest / remote schema 都按 untrusted input 处理：不能 shadow built-in 或注入 executable/lifecycle authority，schema string persistence 前 bounded/sanitize。

## Manager boundary
Manager 是 loopback-only local control surface，registry + durable Doctor evidence 驱动。UI 不拥有 runtime。polling bounded/shallow，health level 独立。

Manager action fixed allowlist，real executor 只由 owner stage 提供。Browser request 需 fixed payload、loopback Host/port、present 时 same-origin Origin；异常返回 sanitized class。

Update 是 repo-approved authority，不是 downloader/shell：只有 fixed component + declared version/source/digest/destination 可以替换 machine-local staged artifact；running/owned target 拒绝，pre/post verify + backup，already-current digest 幂等。

中英文 Manager 共用 functional implementation。status/config 不暴露 secret value/path、executable path、private network identity。OAuth Reveal 是显式 confirmed local operation，明文不进入 activity/status；Regenerate 必须 fresh。

environment/custom-component/OAuth mutation 全部 serialize，避免 double-click duplicate side effect。custom MCP create/delete 只改变 registry visibility，不推导 route/lifecycle authority，built-in 不可通过 browser delete。

## Bootstrap / Doctor / Repair
- bootstrap discover first，preserve healthy；installed-but-stopped 不授权自动 restart；
- Doctor 分开 process/listener/protocol/safe-call/OAuth/remote，respect prerequisite；
- listener ≠ protocol proof；unattempted ≠ failed；
- 跳过可能 fetch/update 的 version probe（如 `@latest`），ambiguous dotted banner 不当 version；
- Doctor 结果 recursive sanitize 后只 machine-local；
- local OAuth metadata 可用于 diagnosis，真实 HTTPS 才是 final OAuth authority；
- Repair fixed allowlist + dry-run/confirm/backup，不是 shell；
- runtime start/restart 属 runtime-owner stage。

## Runtime supervisor / launcher discipline
- discovery 只授权 preserve；stop/restart 需 repo-owned PID identity；
- listener/health success 不证明 long-running runtime 已加载当前 generation；Manager 要比较 generation + resource/API contract。legacy listener 只有 strict WebGPT identity 才可 refresh；ambiguous listener fail closed；
- stale PID/PID reuse 通过 birth identity + image reject；
- Start All preserve healthy unmanaged listener/system process，只启动 fixed repo-managed missing runtime；
- required-but-unmanaged missing 单独报告；
- Manager runtime action fixed allowlist；
- browser/Manager/desktop launcher lifetime 不拥有 agent runtime；
- desktop URL opening 与 Playwright automation profile 分离：复用 normal browser profile 或 OS default handler，不创建 temp/isolated/InPrivate automation profile；
- desktop/autostart transparent、reversible、credential-free，unmanaged file 不 overwrite/delete；
- managed launcher format 升级只有完整历史 structure match 才算 ownership；
- integration-test OAuth credential 不可提升为 production/autostart contract。

## Durable local-state discipline
- temp + fsync + atomic replace；
- multi-file apply 先 stage 全部，后续 in-process failure rollback；
- malformed optional/custom machine-local state fail closed/isolate；
- public/API output recursive sanitize，包括字符串中的 private URL；
- connector 从当前 tool session 消失是 harness evidence，不授权弱化 validation。

## 完成标准
Stage 只有在 owned behavior implemented、validation green、post-state verified、affected docs/ledger updated、closure written、stage committed、next prompt 从 committed HEAD 生成/validate/hash、Playwright-submit、sent message + next assistant run verified 后才完成。

约 20 分钟 soft budget 含 closure/handoff。release-facing stage 不能只做 source-tree test；必须 build/install artifact 到 isolated environment，验证代表性 entry point 和 required non-code resource。

## Stage 19 OAuth Edge recovery discipline
- managed OAuth Edge contract 以 9341 compatibility-edge readiness 为准；只有 9340 child 存活属于 degraded，不是 ready。
- 只有 current canonical public issuer 匹配且 local listener identity 无歧义时才复用已有 9340 child。
- Windows venv launcher PID 只有在 strict process + edge-state evidence 后才 rebind 到真实 9341 listener。
- WebGPT/OAuth self-restart 使用独立 repair plane；runtime 恢复后重新获取 tool/browser refs。
- 真实 ChatGPT connector 一旦确认工作，冻结 disruptive Connector/Funnel/OAuth acceptance，除非新的真实 defect 需要 mutation。
