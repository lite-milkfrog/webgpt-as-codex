# Migrating to coding-tools-mcp 0.5.0

0.5.0 is a reliability release. Nothing about the transport or the handshake
changes, and no tool is renamed or removed from the runtime — but the default
advertised catalog still contains 18 tools. The registry gains
`apply_changes`, `request_permissions` becomes mode-gated rather than being
removed, and three existing tools return more than they used to. The contract
itself is [runtime-contract-v0.3.md](runtime-contract-v0.3.md); this page lists
only what a client or an operator has to notice.

The engineering rationale behind each item is in the
[v0.5.0 execution plan](plan-v0.5.md).

## Breaking changes

### `request_permissions` is advertised only in `dangerous` mode

`request_permissions` no longer appears in `tools/list` in `safe` or `trusted`
mode, because it cannot do anything there: it answers
`ELICITATION_UNSUPPORTED` in every case, which is where roughly 60% of its
observed calls went. The registry now holds 19 tools; `safe` and `trusted`
advertise 18 of them and `dangerous` advertises all 19.

The advertised count in `safe` mode is still 18, but it is a different 18:
`request_permissions` left and `apply_changes` arrived.

- A client that hardcodes the catalog, or asserts a fixed tool count, must
  read `tools/list` instead.
- A client that calls `request_permissions` directly still gets the same
  `ELICITATION_UNSUPPORTED` answer. The tool remains callable when hidden, so
  no existing call becomes an `Unknown tool` error.
- To keep it advertised, run with `--permission-mode dangerous`. Do that only
  inside an isolated container or VM.

The `write_generated_or_ignored` permission kind is gone from the
`request_permissions` schema. It was only ever an enum value; no code path
requested it and none granted it.

### `read_file` model text now starts with a banner

Every `read_file` result — not just a truncated one — now begins with a line
like:

```
[Showing lines 1-40 of 40 revision=9f2c…]
```

The revision is the token `apply_changes` requires, and most clients forward
only this text to the model, so a revision that lived solely in
`structuredContent` would be unreachable by the caller that needs it. The
truncation wording and the continuation hint are unchanged.

A client that compared `read_file` text to file bytes must strip the first line
or read `structuredContent.content` instead, which is unchanged.

### `exec_command` default process lifetime is 300s

`timeout_ms` defaults to 300000 instead of 30000. It always meant total process
lifetime, but the old default was shorter than an install or a build, so a
command backgrounded by the yield was killed shortly after the call returned.
The initial yield (`yield_time_ms`) is unchanged at 10000, and the schema
maximum is unchanged at 600000.

Set `timeout_ms` explicitly if you relied on the old default to bound runaway
commands.

## New behavior you may want to adopt

### `apply_changes`

A new tool for line-addressed editing: you name an action (`create`, `write`,
`edit`, `delete`, `move`, `copy`) and a path. Existing files also use the
`revision` `read_file` reported. Nothing has to match textually, and a file
that changed since you read it is refused with `REVISION_MISMATCH` rather than
silently overwritten.

`write` remains an upsert: it requires `revision` when its path exists and may
omit it when creating a missing path. `create` rejects `revision` and asserts
absence; `edit`, `delete`, `move`, and `copy` require it. A path may appear once
per call; chaining several edits onto one file is `apply_patch`'s territory.
See the contract for the full semantics, including the line-content rules
(`""` is zero lines; a trailing newline adds a blank line) and the
`insert_after` / `insert_before` boundaries.

### `apply_patch` recovery

- `@@ <scope>` headers and `*** End of File` now participate in locating a
  hunk instead of being ignored.
- Matching is graded: exact, then ignoring trailing whitespace, then ignoring
  indentation width. The grade actually used is reported in `match_quality`,
  so a downgrade is visible rather than silent.
- Success returns `changed_ranges`, a per-file `revision`, and `total_lines`.
  These are evidence; `apply_patch` still takes no `revision` argument, because
  its context lines are already its optimistic check.
- Failure returns the hunk index, nearby numbered text, and candidate match
  positions, so the next attempt can be aimed rather than guessed.
- A patch whose changes are already present reports `already_applied` instead
  of failing, provided the hunk's result is locatable: an exact or
  trailing-whitespace match of a block that carries a context line, or a
  multi-line addition. A context-free single line found somewhere in the file
  is a coincidence and still fails. Evidence must also be non-blank, unique,
  and inside the hunk's `@@` scope and EOF constraints.
- `apply_patch` and `apply_changes` accept an optional `idempotency_key`. A
  replay of the same key with the same arguments returns the recorded result
  instead of doing the work twice; reusing the key for different arguments is
  `IDEMPOTENCY_KEY_REUSED`, and a `dry_run` result is never recorded.
  Concurrent duplicates under the same tool and key wait for the first call
  and replay its successful result.
- Several `*** Update File` blocks naming one path in one envelope chain in
  order. This already worked; it is now promised and tested. Their result has
  one final per-path evidence record whose changed ranges describe the net
  difference from the original baseline to the final staged bytes, not an
  accumulation of intermediate block-local ranges. If that net result is the
  original bytes, the baseline is verified without rewriting the file.

### `git_diff` includes untracked files

`git_diff` now reports untracked files by default so a file created by
`apply_patch` is visible in the diff. Pass `include_untracked: false` for the
old behavior.

## New startup arguments

### `--workspace-mutation` and `--write-path`

`--workspace-mutation=structured-only` makes the workspace read-only for
`exec_command` under Landlock, leaving `apply_patch` and `apply_changes` as the
only way to change files. It is **off by default** (`unrestricted`) and
experimental: it breaks any command that writes into the tree — pytest caches,
npm, cargo, gradle, git — unless every such directory is listed with a
repeatable `--write-path`.

Both are also settable as `CODING_TOOLS_MCP_WORKSPACE_MUTATION` and an
`os.pathsep`-separated `CODING_TOOLS_MCP_WRITE_PATHS`. The effective policy,
including whether it is actually enforced, is reported in `server_info` as
`workspace_mutation_policy`. See
[permission-modes.md](permission-modes.md).
Full enforcement requires Landlock ABI 3 or newer because ABIs 1–2 cannot deny
truncate. Reporting the policy does not create missing in-workspace
`--write-path` directories; they are created immediately before Landlock is
installed for `exec_command`.

## Behavior changes that need no action

- **Repeat-failure circuit breaker.** The third byte-identical call that would
  produce the same deterministic error is refused with `REPEATED_CALL_BLOCKED`
  instead of failing the same way again. Changing an argument gives that call a
  fresh budget. A successful non-dry-run `apply_patch` or `apply_changes` clears
  the breaker only when it wrote, moved, copied, or deleted something;
  `already_applied` results do not clear it. The first terminal observation of
  each command from `exec_command`, `write_stdin`, `read_output`, or
  `kill_command` also clears it whenever that command could write: in
  unrestricted mode, through a structured-only write path, when
  structured-only is not actually enforced, or when Landlock setup failed open
  for that launch. Re-polling the same completed command does not clear it
  again. A failure that began before one of these resets is not counted as a
  strike in the new post-reset generation.
  `IDEMPOTENCY_KEY_REUSED` does not count because its recovery is a new key.
- **Telemetry counts operations truthfully.** A command that exits nonzero,
  times out, or dies on a signal is no longer recorded as a successful tool
  call, and its terminal outcome is counted once however many times the command
  is polled afterwards. Consecutive failures are tracked per (tool, error code)
  rather than in one global slot any tool's success could reset. Anyone
  comparing a 0.5.0 dashboard to an earlier one is comparing different
  definitions.
- **Per-tool output schemas.** `tools/list` now carries a specific
  `outputSchema` per tool instead of one generic envelope.
- **`check_exec_environment` warns on non-Linux.** Landlock is Linux-only, so
  there is no filesystem confinement elsewhere; that is now stated rather than
  left to be inferred.
- **`patch_lock` is documented as in-process.** It serializes patches within
  one server process. Two servers on one workspace are protected only by the
  pre-commit baseline recheck.
