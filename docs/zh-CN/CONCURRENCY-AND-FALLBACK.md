# 并发与互补 Fallback

[English](../CONCURRENCY-AND-FALLBACK.md) | **简体中文**

## 为什么 Serena 会在多个 ChatGPT 窗口冲突

当前 Serena 标准 MCP server process 中，一个 `SerenaAgent` 只保存一个 process-wide `_active_project`。已安装源码表明：
- 切换 project 会先 shutdown 原 active project；
- `active_project_context` 暂时覆写同一 agent field；
- read-only ProjectServer 也明确 active project 是 process-wide state，并用 `_active_project_lock` 包住 project-scoped execution。

因此两个 ChatGPT conversation 共用一个标准 Serena process 且分别切不同 project 时会互相踩状态。这是 backend shared-state 问题，不是 ChatGPT window limitation。

### WebGPT 解法

不能把一个 mutable Serena process 当作 universal parallel backend。支持：
- 每个 active project slot 一个 fixed-project Serena instance，各自 loopback port/state identity；或
- 对它支持的操作使用 read-only multi-project ProjectServer。

Gateway 必须把 request/task/project 稳定绑定到 Serena slot。owner task release 后 slot 可复用；shared slot 内 project switching 不是安全并发 primitive。

## Coding Tools 并发

一个 server 绑定一个 workspace。多个 command/process 可同时 active；Stage16 live test 证明两个 server-managed command execution window 可重叠。

但同一 working tree 的 concurrent write 仍不安全：
- independent read/process 可并行；
- one file one writer；
- parallel coding writer 使用独立 Git worktree/workspace；
- destructive/shared Git operation 串行；
- 单个 Coding Tools instance 不提供 per-conversation workspace isolation。

不同项目优先 one Coding Tools instance per workspace/project binding，或未来 workspace-pool adapter。

## Remote Desktop Commander 并发

独立 terminal/filesystem/process session 可并行，但实体 GUI 是共享 singleton：
mouse、keyboard、foreground window、clipboard-sensitive workflow、native modal dialog。

因此 independent filesystem/process/terminal 可重叠；GUI side effect 受 machine-level GUI lease 串行；每次 GUI state mutation 后重新获取视觉/UI evidence。

## Windows-MCP 与 Playwright

Windows-MCP 遵循同一 native-GUI 共享规则。Playwright 可在独立 page/context 并行，但同一 page/profile/login state 同时只允许一个 writer/owner。

## 互补 fallback

```text
A. ChatGPT -> WebGPT Unified Gateway -> structured MCP backends
B. ChatGPT -> Remote Desktop Commander -> host filesystem/process/terminal/GUI
```

### A 失败 -> RDC rescue
1. 分类 public-edge / Gateway / backend failure；
2. RDC 检查本地 WebGPT/backend process、logs、ports、state；
3. 只做 allowlisted recovery 或调用 repo CLI；
4. 验证 listener/protocol；
5. 重试 structured Gateway。

### B 失败 -> Gateway rescue
1. 依情况使用 Gateway-routed Windows-MCP/Coding Tools/WebGPT capability；
2. 检查 RDC runtime/process；
3. 只有 lifecycle authority + safety policy 允许时恢复；
4. 验证 RDC reconnect 后再依赖。

### 硬限制

整个 public WebGPT endpoint 不可达时不能通过自身自救，必须选 independent RDC 或本地人工动作。RDC 若在 vendor relay 层 offline/unpaired，也不能假设能救援。

## Recovery rules

- preferred structured capability first；
- diagnose before fallback；
- fallback 不弱化 auth/security；
- 一个 external side effect 尝试一次，然后查 post-state；
- recovery 要有 evidence 与 bounded ownership；
- 两条 recovery path 不得同时 restart 同一 component。

## Stage16 实现

### Serena fixed-project slots
`src/webgpt_as_codex/concurrency.py` 的 `SerenaSlotPool`：
- 9121 硬排除；
- slot 固定 project/port/owner/PID/birth token/image/launch fingerprint；
- live slot 不被别的 owner 抢；
- released compatible slot 可复用；
- 同 project 的并发 owner 仍拿不同 live slot；
- stale receipt 只在 process identity mismatch/death 后移除；
- occupied candidate port 跳过/fail closed；
- release 幂等；destroy 只作用于 receipt 与 live identity 仍匹配的 process。

CLI Serena real probe 自报 1.28.1，源码仍是单 `_active_project`；shared direct Serena 为独立 1.7.0 / `Jarvis-dev`，从未切换。两个版本都证明 isolation 仍需要。

### Coding Tools writer boundary
`CodingWorkspacePolicy` 显式表示 configured workspace。read/independent process 不拿 writer lease；writer 需按 worktree identity 获取机器本地 lease；同 worktree 第二 owner 被拒绝；不同 worktree 可有独立 writer。configured workspace 外 path fail with binding mismatch。

### Machine GUI lease
`MachineGuiLease` 串行 RDC + Windows-MCP 的 native GUI side effect，记录 owner/action/acquisition/heartbeat/expiry，支持幂等 release 与 expired stale reclaim。filesystem/process/terminal 不需要 GUI lease。

### Recovery coordinator
`src/webgpt_as_codex/recovery.py`：
- Gateway failure 可选 independent RDC；
- RDC failure 可选 healthy Gateway；
- visited-path + hop budget 阻止 A -> B -> A loop；
- 每 component/attempt 只有一个 mutation owner；
- 无 lifecycle authority => diagnose-only；
- mutation timeout/non-zero 后 bounded post-state，禁止 blind duplicate restart；
- 未取得 mutation authority 的第二条 path 可以观察第一条已恢复并返回 recovered-by-other-path。

## Stage16 verification

Stage14-16 regression 52 PASS；full 167 PASS；Ruff、secret scan、diff check PASS。真实 isolated Serena 在 non-9121 slot 完成 initialize 与 `tools/list=29`，临时 listener 最终不存在。shared/production listener 保持 baseline PID，shared Serena 仍为 1.7.0 / `Jarvis-dev`。Computer Agent 1.1.16 validator 49 scenarios。shutdown race 经验被固化为 R49：stop timeout/non-zero 后先做 bounded post-state，而不是立刻第二次 mutation。

## Stage 19 — self-restart control-plane recovery

runtime-plane connector 不能成为自己 restart 的唯一维修路径。WebGPT/OAuth restart 时，由独立 repair plane（本地 Agent shell/filesystem/process 或 Remote Desktop Commander）执行 mutation 与 post-state verification。

WebGPT/OAuth restart 后不得复用旧 MCP session 或 browser ref；必须重新获得 readiness 与 fresh tool/page state。

Stage19 明确区分 child liveness 与 wrapper readiness：9340 OAuth child up + 9341 Edge down 是 degraded，不是 healthy，Start All/Doctor 不能 false-green。

只有 canonical issuer identity 匹配时才允许复用现存 9340 child；这是 preserve/reconciliation，不是第二次 mutation。ambiguous child identity fail closed。

真实 ChatGPT connector 一旦配置成功，后续 acceptance 优先 read-only verify；反复 restart/re-register 不是增加信心的合理方式，因为它会把已知 good integration 置于风险中。
