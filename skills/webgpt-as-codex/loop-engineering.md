# Loop Engineering

## Stage invariant
Each stage document states:
- CURRENT_STAGE
- NEXT_STAGE
- AFTER_NEXT_STAGE
- owner concern
- inputs/evidence
- outputs
- validation
- do-not-redo boundary

## Closure order
1. implement the owner concern;
2. run narrow tests first;
3. run stage/full gates required by the plan;
4. inspect diff/post-state;
5. update durable SoT and decisions/risks;
6. write closure;
7. commit the closed stage;
8. read the real committed HEAD;
9. generate the exact next prompt from that HEAD;
10. validate + hash the prompt;
11. Playwright-submit it;
12. verify the sent user message, /c/ conversation and next assistant run;
13. persist the handoff receipt and continue.

Handoff is Stage work, not optional tail work.

## Soft stage budget, closure reserve and dynamic split
Target roughly 20 minutes per stage including closure and handoff. This is a soft planning default, not a platform timeout or complexity unit.

Treat closure capacity as owned budget, not leftover time. The Stage 10 helper defaults to a 35% closure reserve. After at least three verified, non-split stages with first-pass handoffs, recalibrate the soft budget from median observed total effort (bounded to 15-25 minutes) and closure reserve from median closure share (bounded to 25-55%).

If projected implementation consumes the reserved closure budget, stop expanding the owner concern and split before tests/docs/commit/handoff become tail debt. Preserve one concern/one owner, SoT continuity and CURRENT/NEXT/AFTER_NEXT. Automatic split depth is bounded; when exhausted, freeze scope and close rather than recursively fragmenting.

Record implementation/closure effort, test/docs effort, retries, tool switches, harness failures, first-pass handoff success, almost-done incidents and split decisions in the public-safe stage-cost model. See `loop-evidence.md`.

## Self-evolution loop
Observe the whole execution chain, not only target code. Repeated friction is a candidate workflow defect:
Execute -> Observe -> Diagnose -> Explore -> Compare -> Select -> Verify -> Record -> Reuse.
Ask the user only after reasonable independent exploration cannot resolve the issue or the missing information is genuinely user-exclusive.

## Durable closure state
`webgpt-codex loop start/step/phase/reopen/cost/handoff/show` persists machine-local stage state outside Git. Closure phase is monotonic within one closure attempt and survives chat/window loss. After commit-time contradictory evidence, `loop reopen` may reopen only the minimum affected boundary, records a public-safe reason/count, clears stale prompt/handoff state and preserves prior evidence. Repository SoT remains authoritative; durable state is execution evidence and recovery support, not a replacement for committed closure.

The machine-local state may contain only sanitized/public-safe stage descriptions. Endpoints, secrets, raw process details and private absolute paths belong in the existing machine-local inventory/log layers.

## Reopening a closed stage
Allowed only when later evidence contradicts the closure.
Record the contradiction and reopen the minimum affected scope.

## Parallel writers
Use separate Git worktrees/branches.
Never let two agents write the same working tree concurrently.
Merge only after each worker has its own validation evidence.
