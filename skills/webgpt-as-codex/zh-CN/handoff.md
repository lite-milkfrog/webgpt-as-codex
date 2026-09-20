# Handoff — 简体中文

[English](../handoff.md) | **简体中文**

handoff prompt 只在当前 Stage commit 后从 verified local state 生成，不能把上一 prompt 只改 Stage 名称。

repo 可以先 commit next-stage handoff plan（CURRENT/NEXT/AFTER_NEXT、objective、outputs、boundaries、risks），但 plan 不能冻结 `SOURCE_HEAD`。closure commit 后注入真实 HEAD，再 validate 四个 pointer 并 hash exact bytes。

## Stability gate
每个 prompt 必须包含：
- CURRENT_STAGE
- NEXT_STAGE
- AFTER_NEXT_STAGE
- committed stage 的 SOURCE_HEAD
- mandatory local read order
- one stage objective
- required outputs
- explicit do-not-redo boundary
- known risks/evidence
- MCP routing contract
- failure protocol
- safety contract
- closure contract
- recursive continuation invariant
- automatic Playwright handoff contract

submit 前使用 `webgpt_as_codex.handoff.validate_handoff_prompt`。prompt SHA-256 写 machine-local handoff receipt。

## Before handoff
1. implementation + validation 完成；
2. affected docs / risk / Experience Ledger 更新；
3. stage closure；
4. commit stage；
5. 读取 real committed HEAD；
6. 从该 HEAD 生成 next prompt；
7. validate markers + SOURCE_HEAD；
8. prompt file 在本地存在。

## Recursive invariant
自动 continuation 时每一窗口都：
1. finish + commit CURRENT_STAGE；
2. compute real new HEAD；
3. fresh instantiate NEXT_STAGE prompt，并携带 receiving window 自己的 NEXT_STAGE/AFTER_NEXT_STAGE；
4. validate/hash；
5. Playwright-submit 到新 ChatGPT conversation；
6. verify sent user message + new assistant run；
7. 要求 receiving window 重复整个协议。

中间 Stage boundary 不是停止点。只有 planned final stage + Final Overall Acceptance 都 `CLOSED_LOCAL_VERIFIED` 才结束。

## Automatic continuation
1. 复用已登录 ChatGPT browser context，不新建 isolated profile；
2. 整个 handoff 使用同一个 Playwright MCP session，tab index/ref 不跨 session；
3. new ChatGPT tab 后重新 enumerate/select；不要假设 extension 自动聚焦。pre-submit recovery 若 session 已重建，只有“恰好一个唯一 blank ChatGPT tab”时才可复用，多个候选 fail rather than guess；
4. 用 live DOM geometry/style 找 visible editable composer，focus 后重新 snapshot，再用 fresh active ref；hidden hydration fallback 即使 `[active]` 也不是 valid target；
5. exact prompt 先以 draft 输入，submit disabled；hidden hydration/stale ref/tab ambiguity 只可在 submit 前修复；
6. real submit exactly once；
7. send attempted 后绝不再 Enter/Click Send，只查 sent message 中 SOURCE_HEAD、`/c/` URL、assistant-run evidence；
8. post-state 仍 ambiguous 则 fail as ambiguous submission，不冒 duplicate 风险；
9. machine-local receipt 保存 prompt path/SHA/source HEAD/conversation URL/first-pass/recovery/verification。

filled textbox、click、navigation、prompt file、URL change 单独都不证明 handoff success。输入 hidden fallback 也不算进展。
