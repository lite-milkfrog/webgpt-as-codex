# Loop Engineering Evidence Model

[**English**](loop-evidence.md) | [简体中文](zh-CN/loop-evidence.md)

Stage 10 makes Loop Engineering execution evidence durable and machine-recoverable without turning private machine state into repository truth.

## Durable stage state

`webgpt-codex loop` persists one machine-local JSON state per active stage under the external WebGPT-as-Codex state root. The state carries:
- CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE;
- the committed source HEAD and public-safe scope;
- a monotonic closure phase within each closure attempt, plus explicit commit-time contradictory-evidence reopen provenance;
- evidence-backed Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse events;
- prompt SHA-256, handoff first-pass result and bounded recovery classes when known;
- a stage-cost record.

This state is a restart/context-recovery aid. Repository SoT remains authoritative for stage definition and closed evidence.

## Stage-cost evidence

The public-safe schema records:
- stage and source HEAD;
- bounded public-safe scope;
- implementation and closure effort;
- test and documentation effort;
- retry, tool-switch and harness-failure counts;
- handoff first-pass result;
- almost-done incidents;
- split decision/depth/reason;
- closure verification state.

Secrets, private URLs and machine-specific absolute Windows paths are rejected from public text fields. Raw command lines, endpoints, PIDs, cookies, OAuth state and local paths belong in machine-local inventory/logs, not this model.

## Sizing and closure reserve

The approximately 20-minute target is a soft default, not a platform timeout. A stage reserves closure capacity before implementation expands. With insufficient baseline, the default is 20 minutes with a 35% closure reserve.

After at least three verified, non-split, first-pass-handoff stages have cost evidence, the helper recalibrates:
- soft budget from median observed total stage effort, bounded to 15-25 minutes;
- closure reserve from median closure share, bounded to 25-55%.

A projected implementation that consumes the reserved closure budget returns `split`. Automatic split depth is bounded; once exhausted, the action becomes `freeze-and-close` rather than recursive fragmentation.

## Lesson classification

Friction is classified at the narrowest reusable layer:
- general workflow invariant -> Skill;
- MCP-specific usage/failure mechanism -> MCP Operating Guide;
- machine/session binding, endpoint, path or health -> machine-local inventory/config;
- one-off incident -> stage evidence.

A successful fallback is not enough to promote a rule. The original failure mechanism and verification evidence are retained.

## Handoff causality

The committed repository can contain the next-stage handoff *plan*, but never a stale SOURCE_HEAD. Prompt generation injects the real committed HEAD only after closure commit, validates CURRENT/NEXT/AFTER_NEXT/SOURCE_HEAD, hashes the exact prompt, and only then allows Playwright submission.

The final handoff receipt is necessarily post-commit evidence and remains machine-local so writing it cannot invalidate the SOURCE_HEAD already sent to the receiving window.
