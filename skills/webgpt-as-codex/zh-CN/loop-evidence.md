# Loop Engineering Evidence Model — 简体中文

[English](../loop-evidence.md) | **简体中文**

Stage10 让 Loop execution evidence durable/machine-recoverable，同时不把 private machine state 变 repo truth。

## Durable state
`webgpt-codex loop` 在 external state root 保存每 active stage 一份 machine-local JSON，包含 CURRENT/NEXT/AFTER_NEXT、committed source HEAD + public-safe scope、monotonic closure phase/reopen provenance、Execute→Reuse events、prompt SHA/handoff result/recovery class、stage-cost。

它用于 restart/context recovery；repo SoT 仍 authoritative。

## Stage-cost
public-safe schema 记录：
- stage + source HEAD；
- bounded scope；
- implementation/closure effort；
- test/docs effort；
- retry/tool-switch/harness-failure；
- handoff first-pass；
- almost-done；
- split decision/depth/reason；
- closure verification。

secret/private URL/absolute machine path 禁止进入 public field；raw command/endpoint/PID/cookie/OAuth/local path 留 machine-local logs/inventory。

## Sizing
默认 20 分钟 + 35% closure reserve，不是 platform timeout。至少 3 个 verified non-split first-pass history 后：
- budget median bounded 15-25；
- closure share median bounded 25-55%。

implementation 会吃 reserve => split；split depth 到顶 => freeze-and-close。

## Lesson scope
- general workflow invariant -> Skill
- MCP-specific -> Guide
- machine/session binding/path/health -> local inventory/config
- one-off -> stage evidence

successful fallback 不足以形成 rule；要保留 original failure mechanism + verification evidence。

## Handoff causality
repo 可 commit next-stage plan，但不能 stale-freeze `SOURCE_HEAD`。closure commit 后注入 real HEAD、validate CURRENT/NEXT/AFTER_NEXT/SOURCE_HEAD、hash exact prompt，再 Playwright-submit。final receipt 是 post-commit machine-local evidence，因此不会改变已发送 HEAD。
