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
7. generate the exact next prompt;
8. continue or hand off.

## Reopening a closed stage
Allowed only when later evidence contradicts the closure.
Record the contradiction and reopen the minimum affected scope.

## Parallel writers
Use separate Git worktrees/branches.
Never let two agents write the same working tree concurrently.
Merge only after each worker has its own validation evidence.
