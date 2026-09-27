# Real-task agent evaluation

This harness answers one question with evidence instead of anecdote: does an
agent finish real coding tasks more reliably through this MCP server than
through its own native tools? It runs the same model, the same prompt, and the
same tasks on both sides, and scores the outcome.

The harness lives in `benchmarks/agent_eval/`. It needs no model access of its
own — the agent under test is an external command — so it can be exercised in
CI with a scripted stand-in and pointed at a real model when someone has the
budget for a full run.

## Why the harness drives the loop

The agent is never asked to report on itself. The harness prepares the
workspace, invokes the agent, runs the verification command, and repeats until
the task is green or the round budget is spent. That is what makes
`rounds_to_green` and `first_attempt_success` measurable for an agent that
reports nothing, and it keeps both arms measured identically: neither side gets
credit for claiming success.

A task whose verification already passes before the agent runs measures
nothing, so it is recorded as invalid rather than as a free success for both
arms.

## Arms

An arm is one side of the comparison, given as `name=command` or
`name:mcp=command`:

- **native** — the agent command runs directly in the task workspace with
  whatever file and shell tools it already has.
- **mcp** — the harness starts this repository's MCP server bound to the task
  workspace on a free port and passes its URL to the agent in
  `CODING_TOOLS_MCP_URL`. The agent is expected to do its work through that
  server.

Both arms receive the prompt on stdin and in `CODING_TOOLS_EVAL_PROMPT`, and
the task id in `CODING_TOOLS_EVAL_TASK`. Everything else about the agent is the
operator's business; the harness only observes the working tree and the exit
code.

## Tasks

Tasks are data, so the 30-task run the release gate asks for is a manifest edit
rather than a code change. Each entry is validated strictly before anything
runs — a typo in task 27 should not surface an hour into an evaluation.

| Field | Meaning |
| --- | --- |
| `id` | Unique within the manifest. |
| `prompt` | What the agent is told to do. |
| `verify` | Must fail before the agent runs and pass after. |
| `regression_verify` | Must pass before and keep passing after. |
| `repo`, `commit` | Git source cloned into a fresh workspace. |
| `fixture` | Directory, relative to the manifest, copied into the workspace. |
| `setup` | Command run once before the agent sees the workspace. |
| `category`, `tags` | Reporting labels. |
| `timeout_s` | Per-agent-invocation and per-check budget. |
| `max_rounds` | How many attempts before the task is scored unsolved. |

A task needs at least one of `repo`, `fixture`, or `setup`. Every workspace
gets a git baseline commit so the agent's work is diffable even when the
fixture was produced by `setup`.

`manifests/starter.json` ships three hermetic Python tasks that need no
network and no clone. They exist to prove the harness end to end; the release
run adds real `repo`/`commit` tasks alongside them.

## Running it

Validate a manifest without running anything:

```bash
make agent-eval-validate
```

Run the starter tasks against two arms:

```bash
python3 benchmarks/agent_eval/run_eval.py \
  --arm "native=my-agent --prompt-stdin" \
  --arm "mcp:mcp=my-agent --prompt-stdin --mcp-url \$CODING_TOOLS_MCP_URL" \
  --runs-out reports/agent-eval/runs.json \
  --report-out reports/agent-eval/report.json
```

The runner exits non-zero when the gated arm misses the release gates, so it
can be wired into a release check once a real run exists.

## Metrics

Rates are reported with their numerators and denominators so a small sample
cannot be mistaken for a large one. Invalid tasks are excluded from every
denominator.

- **final pass rate** — tasks where `verify` and `regression_verify` both pass
  at the end.
- **first-attempt success rate** — tasks green after round 1.
- **median rounds to green** — over solved tasks only.
- **regressions introduced** — tasks whose `regression_verify` fails at the
  end.
- **wall time** — median and total per arm.

## Release gates

These are *release-announcement* criteria, not merge criteria. Per decision D-7
in the [v0.5.0 execution plan](plan-v0.5.md), the code lands without them and
the announcement waits for a run that clears them, on the `mcp` arm:

| Gate | Threshold |
| --- | --- |
| Scored tasks | at least 30 |
| Final pass rate | at least 80% |
| First-attempt success rate | at least 80% |
| Regression rate | at most 5% |

## Extending the manifest to a release run

1. Pick 30–50 tasks across bugfix, feature, refactor, and test-writing
   categories, weighted toward multi-file work where patch reliability actually
   bites.
2. For each, pin `repo` and `commit` to a state where `verify` fails and
   `regression_verify` passes. Confirm that with `--validate-only` plus a dry
   run using an agent command that does nothing: every task should report
   `started_green: false` and end unsolved.
3. Use the same model, prompt template, and round budget on both arms. The
   comparison is worthless if the arms differ in anything but the tool surface.
4. Publish the resulting `report.json` under `reports/` alongside the manifest
   commit so the numbers can be traced to the exact tasks that produced them.
