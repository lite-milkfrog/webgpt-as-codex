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

## Soft stage budget and dynamic split
Target roughly 20 minutes per stage including closure and handoff. This is a soft planning budget, not a platform timeout or complexity unit.

If continued implementation threatens tests, docs, commit or verified handoff, stop expanding the owner concern and split into bounded sub-stages. Preserve one concern/one owner, SoT continuity and CURRENT/NEXT/AFTER_NEXT.

Collect a baseline across the next 5-10 stages: implementation/closure effort, changed files/tests, major tool switches/calls, retries, harness failures, docs effort, first-pass handoff success, almost-done incidents and emergency splits. Adjust the sizing heuristic from evidence.

## Self-evolution loop
Observe the whole execution chain, not only target code. Repeated friction is a candidate workflow defect:
Execute -> Observe -> Diagnose -> Explore -> Compare -> Select -> Verify -> Record -> Reuse.
Ask the user only after reasonable independent exploration cannot resolve the issue or the missing information is genuinely user-exclusive.

## Reopening a closed stage
Allowed only when later evidence contradicts the closure.
Record the contradiction and reopen the minimum affected scope.

## Parallel writers
Use separate Git worktrees/branches.
Never let two agents write the same working tree concurrently.
Merge only after each worker has its own validation evidence.
