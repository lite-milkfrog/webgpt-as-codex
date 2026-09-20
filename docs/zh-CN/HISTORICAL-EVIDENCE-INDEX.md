# 历史证据中文索引

本文件为中文读者解释未逐份翻译的 canonical 历史证据。**历史原文件保持原样**，避免翻译造成已经验收的时间线、命令、hash、测试数量或措辞产生第二套事实。

## Closure 证据

以下文件统一分类为 `HISTORICAL_EVIDENCE_PRESERVED_WITH_INDEX`：
- `docs/STAGE-1-CLOSURE.md` … `docs/STAGE-17-CLOSURE.md`
- `docs/STAGE-17-POST-ACCEPTANCE-HOTFIX-CLOSURE.md`
- `docs/FINAL-OVERALL-ACCEPTANCE-CLOSURE.md`
- `docs/PROJECT-COMPLETE-CLOSURE.md`
- 当前 Stage 收口后生成的 `docs/STAGE-18-CLOSURE.md`
- `docs/RDC-FINAL-RECOVERY-PLANE-CLOSURE.md`
- `docs/SUPPLEMENTAL-FINAL-ACCEPTANCE-CLOSURE.md`

阅读当前事实时优先看：
1. `docs/zh-CN/CURRENT-PROJECT-STATE.md`
2. 对应最新 closure 英文原件
3. `docs/zh-CN/DECISIONS-AND-RISKS.md`

## Cost / machine-readable evidence

`docs/evidence/STAGE-10-COST.json`、`STAGE-11-COST.json`、`STAGE-12-COST.json` 是机器证据，数字/key/hash 不翻译。

## Prompt / handoff 历史

`prompts/` 下已提交的 PLAN、NEXT-WINDOW、stable contract 是 handoff 历史/传输 artifact。它们的 CURRENT/NEXT/AFTER_NEXT、SOURCE_HEAD、路径、命令和 hash 必须保持原始语义，因此不生成逐文件中文副本。未来 prompt 也由 translation manifest 的 dynamic historical rule 处理。

当前 handoff 规则的中文阅读入口是：
- `skills/webgpt-as-codex/zh-CN/handoff.md`
- `skills/webgpt-as-codex/zh-CN/loop-engineering.md`

## Experience Ledger

`skills/webgpt-as-codex/experience-ledger.md` 是跨 Stage 累积的 evidence/provenance 日志，保持 canonical 英文单份，避免把旧 incident 改写。当前可执行规则应从 `SKILL.md`、`routing.md`、Guide 和 live docs 读取；Stage18 新 lesson 继续追加到 canonical ledger。
