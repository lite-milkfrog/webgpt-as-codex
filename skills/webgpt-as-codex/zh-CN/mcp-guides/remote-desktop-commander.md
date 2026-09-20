# Remote Desktop Commander Operating Guide — 简体中文

[English](../../../mcp-guides/remote-desktop-commander.md) | **简体中文**

Component: `remote-desktop-commander`

## Mental model

Remote Desktop Commander（RDC）是独立 full-machine repair/control plane，与 WebGPT-as-Codex 互补，不在 Unified Gateway 内部。适合 host filesystem/process/terminal，以及 WebGPT structured path 不可用时的 bounded recovery。

RDC 不是 Gateway child，不属于 OAuth/Funnel，也不是 WebGPT READY prerequisite。

## Health model

RDC health 必须分四层：

1. installation/runtime；
2. local agent process；
3. control plane 的 intended device + auth/session；
4. execution plane 真实能接收并执行 command。

device status=`online` 只能证明 control-plane presence，不能证明 live command transport。

## Real acceptance evidence

Supplemental Final Acceptance 已恢复并验证 fixed local 0.2.51 runtime。active device control plane online/authenticated，broadcast transport capability 存在，并且 connector-side 真实通过：

- `list_devices`；
- `ping` -> `pong`；
- `get_config`；
- read-only host file metadata probe。

因此可写 `RDC_EXECUTION_PLANE = VERIFIED`。

## Best use

- Coding Tools workspace 外的 host filesystem/process/log；
- WebGPT 自身 unavailable 时独立检查/恢复 Gateway/OAuth/Manager/startup；
- 分类 failure layer 后做 bounded terminal/process recovery；
- 拿到 shared machine GUI lease 后做 native GUI repair。

## Poor use

- Coding Tools 健康且 binding 正确时替代 repo edit/build/test/Git；
- 替代 Playwright 做 browser DOM；
- 把 `online` badge 当 health proof；
- 让 broken WebGPT 与 broken RDC 递归互救。

## Recovery matrix

- WebGPT healthy / RDC unhealthy：WebGPT 继续 READY；用 structured host capability 在授权范围修 RDC。
- RDC healthy / WebGPT unhealthy：RDC 检查 filesystem/process/log/startup，只做 allowlisted recovery；WebGPT 回来后重新获取 fresh connector/tool refs。
- 两者 healthy：project/code structured work -> WebGPT；独立 full-machine recovery -> RDC。
- 两者 unhealthy：local startup/reboot/human-local recovery；不能假装 dead remote plane 能自救。

## Mistakes

只看 device/auth/status；execution probe 还没失败就 delete/re-pair；每次 boot 依赖 `@latest` 导致 version drift；把 token/refresh token/pairing secret 写进 Git；RDC 与 Windows-MCP 同时抢实体 GUI。

## Diagnosis

1. 查 installed/fixed runtime 与 local process；
2. 查 active device/control plane；
3. 做 `ping` / `get_config` 等真实 execution probe；
4. control online 但 execution fail 时，先查 realtime/broadcast capability registration 与 session persistence，不先做 destructive re-pair；
5. 只选一个 healthy recovery owner，一次 mutation 后查 post-state。

## Verification

intended device online/authenticated；需要时 broadcast transport capability 存在；`ping` 成功；`get_config` 或等价 read-only remote host call 成功；recovery 不降级 WebGPT READY，也不改 unrelated Gateway/OAuth credential。

## GUI concurrency

filesystem/process/terminal read 在独立安全时可重叠；mouse/keyboard/focus/clipboard/foreground/native dialog 与 Windows-MCP 共用 physical desktop，必须 machine GUI lease 串行。

## Security

token、refresh token、pairing secret、relay credential、account secret 永不进入 repo/public guide。local runtime/session state 留在 Git 外。

## Protected lesson

control-plane presence != execution-plane liveness。历史 fake-online incident 已转成 routing invariant：真实 remote command 成功前，不得把 RDC 判定为 usable。
