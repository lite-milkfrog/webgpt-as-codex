# Add MCP Workflow — 简体中文

[English](../add-mcp.md) | **简体中文**

Stage9 把 Add MCP 变成 discovery-first onboarding。它学习 capability、建立 operating knowledge、附加 routing/inventory evidence，但不获得任意 lifecycle authority。

## Default
`webgpt-codex add-mcp NAME URL [--role ROLE]` 默认 **dry-run**：
1. build + validate public-safe manifest candidate；
2. reject credential literal；
3. real MCP initialize；
4. reuse returned session；
5. tools/list；
6. classify success/unavailable/failed/unattempted；
7. preserve real exposed tool name/description/input schema；
8. build + validate Guide；
9. 从 real capability evidence derive routing recommendation；
10. 不持久化，只报告 plan。

mutation 要显式 `--apply`。

## Apply
只写 machine-local state：
- `config/components/<id>.json`
- `config/mcp-guides/<id>.json`
- `config/mcp-onboarding/<id>.json`

same manifest apply 幂等；same id + different manifest fail closed；custom id 不可 shadow repo component。

Manager/Doctor 可通过 registry 看 applied component，但它不会自动进入 Stage8 runtime ownership/Manager Restart。

## Capability semantics
- `success`：initialize + tools/list structurally valid。
- `unavailable`：transport/service/session 当前不可达，不能据此反证 capability。
- `failed`：server 可达但 protocol/schema malformed/contradictory。
- `unattempted`：probe 不适用或 prerequisite 缺失。

unavailable != failed；single failed invocation != MCP unavailable。

## Guide
详见 `mcp-operating-guide.md`。覆盖 mental model、best/poor use、real schema、goal patterns、mistakes、diagnosis、verification、performance/context/cost、lessons、alternatives。

Routing 决定 WHICH，Guide 教 HOW。

## Public-safe vs machine-local
repo manifest/portable Guide 只含 reusable public facts。禁止 commit local endpoint/port override、process/PID/health、workspace/path、private URL、OAuth/token/cookie/password/private key、user browser state。

Serena/Coding Tools 已有代表性 public Guide。live Stage9 initialize/tools evidence 是 stage evidence，不是永久 availability。

## Lifecycle boundary
onboarding != runtime supervision。新 MCP 可被 registry/Manager/Doctor 看见，可有 Guide/routing recommendation；但不能仅因 discovered 就 start/kill/restart，也不进入 `MANAGER_RESTARTABLE`。

## Failure protocol
1. manifest/schema validation 与 transport/protocol failure 分开；
2. inspect initialize/tools/list；
3. distinguish unavailable/malformed/failed；
4. fallback 前查 binding/session/auth/harness；
5. 不为 discovery convenience 重启健康 external service；
6. MCP-specific reusable lesson -> Guide；general lesson -> Ledger/Skill。
