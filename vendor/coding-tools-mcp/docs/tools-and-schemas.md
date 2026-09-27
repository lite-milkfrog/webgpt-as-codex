# Tools And Schemas

The normative behavior is [runtime-contract-v0.3.md](runtime-contract-v0.3.md).
Live JSON Schemas come from `tools/list`; CI compares their names, input
properties, annotations, and error codes with the contract.

## Fixed inventory

The registry holds exactly 19 tools. Two are gated, so a default `tools/list`
advertises 18:

- `server_info`: server, workspace, automatic project context, policy, runtime,
  auth, protocol, and fixed-catalog metadata.
- `check_exec_environment`: lightweight execution policy and Landlock status.
- `read_file`: stream a bounded UTF-8 range without loading the whole file.
- `list_dir`: list immediate or bounded-recursive directory entries.
- `list_files`: iterate files with glob, ignore, hidden-file, sort, and cap
  controls.
- `search_text`: literal or regex search; ripgrep stops after the result cap.
- `apply_patch`: stage and atomically commit add/update/delete/move envelopes.
- `apply_changes`: line-addressed create/write/edit/delete/move/copy against a
  known file revision.
- `exec_command`: run a bounded command and wait up to 10 seconds by default.
- `write_stdin`: poll or interact with a running command.
- `kill_command`: terminate one runtime-owned command.
- `read_output`: page retained stdout or stderr using absolute byte offsets.
- `git_status`: structured working-tree status.
- `git_diff`: bounded unified staged/unstaged diff.
- `git_log`: structured bounded commit history.
- `git_show`: bounded revision metadata/content/diff.
- `git_blame`: structured bounded line attribution.
- `request_permissions`: report elicitation status without silently granting.
- `view_image`: one MCP image content block plus structured metadata.

Two gates apply, and they are not tool profiles:

- `view_image` is a **capability** gate: an installation that cannot accept
  binary image content disables it, and a disabled `view_image` is an unknown
  tool.
- `request_permissions` is a **mode** gate: it is advertised only under
  `--permission-mode dangerous`, the only mode in which it can return
  `granted`. Elsewhere it can only return `ELICITATION_UNSUPPORTED`, so
  advertising it hands the model a call that is guaranteed to fail. The handler
  stays reachable by name in every mode, so removing it from the catalog does
  not break a client that calls it anyway.

The remaining 17 tools are always advertised, and `listChanged` is `false`.

Each tool declares its own `outputSchema` naming the fields it actually
returns — `command_id`, `exit_code`, `output_ref`, `revision`,
`operation_outcome`, and so on — rather than sharing one schema that declared
only `ok` and `error`. `additionalProperties` stays open: payloads carry
advisory fields (`warnings`, `next_action`) that are not part of the contract.

## Result envelope

Every successful tool call has:

```json
{
  "content": [{"type": "text", "text": "Agent-readable summary or bounded preview"}],
  "structuredContent": {"ok": true},
  "isError": false
}
```

`content` is not a JSON mirror. `structuredContent` is the complete machine
interface and retains existing fields where possible. Model-facing text is
bounded at 16 KiB; if it is shortened, the full structured value is still
present. Errors use the same envelope with readable recovery guidance and
`isError: true`.

`view_image` is the exception to text-only content: its base64 appears exactly
once in one `image` block. `structuredContent` contains path, media type, byte
count, dimensions, resize metadata, and warnings, but no base64 or data URL.

## Patch behavior

`apply_patch` accepts the standard envelope:

```text
*** Begin Patch
*** Add File: path/to/new.py
+content
*** Update File: path/to/existing.py
@@
 old
-before
+after
*** Move to: path/to/moved.py
*** Delete File: path/to/old.py
*** End Patch
```

All operations are parsed and matched before writes. Files are prepared in
their destination directories, fsynced, baseline-checked, and installed with
atomic replacement. Multi-file failure restores prior files. Mode bits, BOM,
and newline style are preserved; moves inherit source mode. Lines are split on
`\n` only, so a line containing another Unicode line boundary (`\x0c`,
`\u2028`, `\x85`, …) is one line to both the file and the patch. A file's
final newline is an ordinary line the hunk can add or remove.

### Locating a hunk

A hunk has no line numbers; it finds itself by its context, so the context must
be unique within the file. Two things narrow the search when it is not:

- `@@ <scope>` — the text after `@@` names the enclosing block (`@@ def
  farewell`). Candidates are grouped by the scope anchor that most closely
  precedes them; if one group remains, it wins. A unified-diff position header
  (`@@ -1,4 +1,4 @@`) names line numbers this dialect does not use and reads as
  no scope.
- `*** End of File` — placed on its own line inside a hunk, it prefers the
  placement that reaches the end of the file.

A blank context line may be written as `""` or as a single space; both mean the
same empty line.

### Graded matching

Context is compared at three grades, in order, and the first grade that
produces candidates decides the outcome:

| Grade | Comparison | Reported as |
| --- | --- | --- |
| exact | byte-for-byte | `match_quality: "exact"` |
| trailing whitespace | `rstrip()` | `match_quality: "trailing_ws"` |
| indentation width | `strip()`, plus a uniform indent delta | `match_quality: "indent"` |

Every downgrade is labeled in `match_quality` and repeated as a warning; none
is silent. Ambiguity is checked at each grade — a fuzzy grade that matches two
places is `PATCH_CONTEXT_AMBIGUOUS`, never a guess. Context lines are
reinstated from the file rather than from the patch, so a tolerated whitespace
difference is preserved instead of being rewritten; added lines under the
`indent` grade are re-indented by the block's uniform delta, and a delta that
is not uniform disqualifies the grade rather than being approximated.

### Chaining and idempotency

Several `*** Update File` blocks naming one path in one envelope chain in
order: each sees the previous block's result. `apply_changes` is the
declarative counterpart and rejects same-path duplicates instead. Chained
blocks produce one final `affected_files` record for the resolved path; its
revision and line count name the committed bytes, and its `changed_ranges`
describe the net difference from the original baseline to those final bytes,
not a stale accumulation of intermediate block-local ranges.

A hunk whose result is already in the file is skipped rather than failing, so
replaying an envelope after a lost response returns success with
`already_applied: true` and an `unchanged` operation. An update that changes
nothing is committed as a baseline assertion, so it does not touch the file's
mtime. `*** Move to:` is still a write when it relocates the file, even if all
of that block's hunks were already present; such a result reports
`already_applied: false` and an operation of `move`.

That claim turns a miss into a success, so it takes locatable evidence: the
hunk's `new` block has to be found at the `exact` or `trailing_ws` grade, and
the hunk must carry either a context line — which sits inside `new` and so
anchors the block where the hunk belonged — or a multi-line addition. A hunk
with no context whose single added line is some common line (`pass`,
`return None`) is not evidence of anything, and fails with
`PATCH_CONTEXT_NOT_FOUND` and its repair data instead. The evidence must be
unique inside the hunk's `@@` scope and `*** End of File` constraint. A result
made only of blank lines is never evidence: every newline-terminated file has
a trailing empty element in the patcher's line model.

`idempotency_key` goes further: the runtime keeps one 64-entry
least-recently-used cache across both write tools, keyed by `(tool, key)`, and
replays the recorded result, flagged `idempotent_replay`, rather than doing the
work twice. Concurrent calls under the same `(tool, key)` are serialized, so
duplicates already in flight wait for and replay the first successful result.
An evicted key does the work again. A key names one request. It is recorded
with a fingerprint of the arguments that produced it, and reusing it for
anything else — a different patch, a different `dry_run` — is
`IDEMPOTENCY_KEY_REUSED` rather than a replay of work that was never done for
those arguments. Failures are never recorded, and neither is a dry run: it
changed nothing, so it must never answer a later real apply.

### Success and failure fields

Success returns, per affected file: `revision` (a SHA-256 over the resulting
UTF-8 bytes — the same token `read_file` publishes and `apply_changes`
requires), `total_lines`, `changed_ranges` (1-based, inclusive, with locating
context trimmed off both ends; a pure deletion reports `end_line ==
start_line - 1`), and `match_quality`.

`PATCH_CONTEXT_NOT_FOUND` and `PATCH_CONTEXT_AMBIGUOUS` carry `hunk_index`,
`match_count`, `scope`, and numbered file text: `nearby_text` around the
nearest near-miss for a miss, and `candidate_lines` plus per-candidate excerpts
for an ambiguity.

`apply_patch` has no `revision` argument. Its context lines are its optimistic
concurrency check, and a second mechanism on one tool would produce two
conflicting failure modes.

## Model-ready examples

Every relative path resolves against the workspace root; there is no
session-scoped working directory. Use explicit paths for multi-call workflows:

```json
{"cmd":"pytest -q","workdir":".","yield_time_ms":30000}
```

If the result is still running, copy its `command_id` exactly:

```json
{"command_id":"abc","chars":"","yield_time_ms":10000}
```

Terminate that command when needed:

```json
{"command_id":"abc","signal":"KILL"}
```

Page a truncated stream using the returned reference:

```json
{"output_ref":"command:abc:stdout","offset":0,"limit":4096}
```

`exec_command.workdir` and each file/Git tool's `path` argument are how a call
targets a subdirectory; both are still confined to the workspace.

## Command and output behavior

`exec_command` and `write_stdin` default `yield_time_ms` to `10000`. Short
commands ordinarily return `status: "exited"` in one call. A still-running
command returns a `command_id` and a machine-readable `next_action` for
`write_stdin` with empty `chars`.

Yield time and process lifetime are separate budgets. `yield_time_ms` only
bounds how long the call waits; `exec_command.timeout_ms` bounds how long the
process may live and defaults to `300000` (maximum `600000`). A build or test
run that has not finished when the call returns keeps running until the
lifetime expires, at which point the runtime kills its process group and the
command reports `status: "timeout"`.

Only truncated terminal output returns a `read_output` next action by default.
`output_ref` values are `command:<id>:stdout` or `command:<id>:stderr`; offsets
are stream-specific absolute byte positions. Runtime limits bound active
commands, retained completed commands, per-command output, total output, and
retention time.

Each stream retains the earliest output (a frozen head segment, one eighth of
the per-stream budget) plus the most recent output (a rolling tail). When a
command produces more output than the budget, bytes between the head and the
tail are evicted permanently; `read_output` reports the loss via
`evicted_gap_bytes` and `omitted_bytes`. For output expected to exceed the
budget, redirect it to a file (`cmd > out.log 2>&1`) and page it with
`read_file` or `search_text` instead of relying on retained output.

Use `tty: true` only when a program requires a terminal. POSIX receives a real
PTY (`isatty()` is true). This build returns `TTY_UNSUPPORTED` on Windows rather
than labeling pipes as a TTY.

## Permission modes

- `safe`: blocks network-looking commands, shell expansion, inline scripts,
  destructive commands, outside-workspace arguments, and secret/loader env.
- `trusted`: enables normal local-development network, expansion, and inline
  snippets while retaining secret and destructive-command checks.
- `dangerous`: disables command permission gates and Landlock; use only inside
  an isolated container or VM.

These modes change only one catalog entry: `request_permissions` is advertised
in `dangerous` mode and hidden (but still callable by name) in `safe` and
`trusted`. Direct path tools retain workspace confinement in every mode.

`--dangerously-fake-readonly-annotations` advertises every tool as read-only in
`tools/list` for clients that gate on annotations. It does not change the tool list
either, and it does not stop mutation or execution. `server_info` and the server
card keep reporting the real annotations. See
[permission-modes.md](permission-modes.md).
