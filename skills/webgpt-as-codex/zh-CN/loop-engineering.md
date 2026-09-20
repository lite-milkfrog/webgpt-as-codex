# Loop Engineering — 简体中文

[English](../loop-engineering.md) | **简体中文**

## Stage invariant
每个 stage document 明确：
- CURRENT_STAGE
- NEXT_STAGE
- AFTER_NEXT_STAGE
- owner concern
- inputs/evidence
- outputs
- validation
- do-not-redo boundary

## Closure order
1. implement owner concern；
2. narrow tests；
3. required stage/full gates；
4. inspect diff/post-state；
5. update SoT + decisions/risks；
6. write closure；
7. commit closed stage；
8. read real committed HEAD；
9. 从该 HEAD 生成 exact next prompt；
10. validate + hash；
11. Playwright-submit；
12. verify sent message / `/c/` / next assistant run；
13. persist handoff receipt，继续递归。

handoff 是 Stage work，不是 optional tail。

## Soft budget / closure reserve
约 20 分钟是 default soft target，不是平台 timeout。closure capacity 是预留预算，不是剩余时间。Stage10 helper 默认 35% closure reserve。

至少 3 个 verified non-split first-pass handoff history 后：
- total budget 取 observed median，bounded 15-25 分钟；
- closure reserve 取 closure-share median，bounded 25-55%。

projected implementation 会消耗 reserve 时先 split bounded owner concern；split depth 到顶则 freeze-and-close。

public-safe stage-cost 记录 implementation/closure/test/docs effort、retry/tool-switch/harness failure、handoff first-pass、almost-done、split。详见 `loop-evidence.md`。

## Self-evolution
完整 chain 都可产生 workflow defect：
`Execute -> Observe -> Diagnose -> Explore -> Compare -> Select -> Verify -> Record -> Reuse`

只有独立探索仍无法解决或信息真正 user-exclusive 时才问用户。

## Durable closure state
`webgpt-codex loop start/step/phase/reopen/cost/handoff/show` 把 state 写 Git 外 machine-local。closure phase 在一个 attempt 内 monotonic。commit-time contradictory evidence 可 `loop reopen` 最小边界，记录 public-safe reason/count、清 stale prompt/handoff state、保留旧 evidence。repo SoT 仍 authoritative。

## Reopen closed stage
仅后来 evidence contradiction 才允许，且只 reopen minimum affected scope。

## Parallel writers
使用独立 Git worktree/branch。一个 working tree 不允许两个 active writer。每个 worker 有独立 validation 后再 merge。
