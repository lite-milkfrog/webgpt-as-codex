# Telemetry

coding-tools-mcp collects anonymous usage telemetry to answer two product
questions: how many installs are active, and which tools succeed, fail, or run
slowly in the wild. Telemetry is enabled by default and can be disabled at any
time; disabling it changes nothing else about the server.

## How to disable

Any one of the following turns telemetry off completely:

```bash
export CODING_TOOLS_MCP_TELEMETRY=off   # also accepts 0 / false / no
export DO_NOT_TRACK=1                    # the cross-tool convention
```

Telemetry is also disabled automatically whenever `CI` is set, and the test
suite forces it off in `tests/__init__.py`, so CI and test runs never pollute
usage data. Deleting `~/.coding-tools-mcp/id` resets the anonymous install
identity.

To see exactly what would be sent without sending it:

```bash
export CODING_TOOLS_MCP_TELEMETRY=debug  # prints events to stderr instead
```

## What is collected

Events are sent to PostHog (`us.i.posthog.com`) over HTTPS using the standard
library only. The payload is a closed schema — counters, enums, durations, and
version strings assembled by one function (`coding_tools_mcp/telemetry.py`).
It is structurally incapable of carrying paths, arguments, or file contents.

Every event carries: package version, OS platform and architecture, Python
`major.minor`, transport (`stdio`/`http`), permission mode, a random
per-session id, and the anonymous install id. No client identity and no
protocol version is carried by every event: one server process answers every
client of its workspace, so a value recorded once would only ever describe
whichever client connected first.

| Event | When | Additional properties |
| --- | --- | --- |
| `session_start` | the first request or notification of the session, `ping` excepted | — |
| `handshake` | every MCP `initialize` | negotiated protocol version, the client's `clientInfo` name and version |
| `tool_error` | a tool call fails (max 20 per session) | tool name, error code, duration ms, consecutive-failure count, and for a 2026-07-28 request the `clientInfo` name and version it carried |
| `tool_summary` | session ends, one per tool used | `calls`, `ok`, `errors`, `operation_failures`, per-error-code `err_*` counts, per-outcome `outcome_*` counts, duration buckets, truncation count |
| `session_end` | session ends | session duration, total calls, distinct tools, dropped error-event count, handshake-era and 2026-07-28 request counts, `server/discover` probe count, retained-output eviction and omitted-read counters |

A typical session produces 5–15 events totalling a few kilobytes.

In `tool_summary`, `ok` means successful operations, not merely calls that
dispatched successfully: it is `calls - errors - operation_failures`.
`operation_failures` on `exec_command` counts successfully dispatched commands
whose terminal outcome was `exited_nonzero`, `timeout`, or `signal`; a
`spawn_error` remains a tool error and is not counted twice. A background
command's terminal outcome stays attributed to the `exec_command` that launched
it even when `write_stdin`, `read_output`, or `kill_command` is the first call
to observe that outcome. Those observer calls remain successful unless the
calls themselves fail. Each `outcome_*` property counts the named operation
outcome. A terminal command outcome is counted only on its first observation,
however many later polls report it again.

## What a session is

A session is one server process, not one client: every client of a workspace
is served by the same runtime, and neither protocol era leaves a session
behind on the server.

- The session is activated by the first request or notification that passes
  envelope validation, whichever era it belongs to, and before the method
  runs — so a first call that fails still reports its `tool_error`. A client
  that never sends `initialize` is measured like any other.
- `ping` never activates a session. An HTTP health probe against an idle
  server produces no events at all.
- `consecutive_failures` on `tool_error` is keyed by `(tool, error_code)` and
  counts that pair's runtime-wide streak across every client of the process.
  A successful operation by the same tool clears its error-code streaks;
  another tool's success and a failed operation clear nothing. It is not a
  single client's failure streak, and must not be read as one.
- The 20-error budget per session is likewise a whole-process budget, shared
  by every client; `session_end` reports how many error events were dropped
  once it ran out.
- A long-running HTTP server emits `session_start` once when it first serves
  a client and `tool_summary`/`session_end` once when it shuts down, however
  many clients it served in between.

`client_name` and `client_version` are sanitized self-reported labels, not
identity. `clientInfo` is whatever a client says it is, so each field is
narrowed to letters, digits, spaces, and `. _ -` — dropping the characters that
make up an address or a path, so that neither can travel verbatim — and then
truncated to 40 characters. Only `name` and `version` are read; a handshake-era
`tool_error` carries no identity at all, because the request that failed did
not name one.

## First-appearance server log

Independently of telemetry — including when telemetry is off — the server
writes one line to stderr the first time a process sees each protocol choice,
so an operator can tell from the log which era their clients actually speak:

```text
coding-tools-mcp: legacy client handshake (2025-11-25)
coding-tools-mcp: modern client request (tools/list)
coding-tools-mcp: server/discover probe
```

Each line appears at most once per process and only ever on stderr; over
stdio, stdout is the MCP wire.

## What is never collected

File paths, file contents, tool arguments, command lines, environment
variables, patch bodies, diffs, repository or branch names, workspace
locations, hostnames, usernames, and IP-derived identity. The install id is a
random UUID generated locally — never derived from hardware, hostname, or any
workspace property — so it cannot be reversed into an identity.

`tests/test_telemetry.py` enforces the boundary: a probe session touches files
with distinctive path substrings and the test asserts none of them appear
anywhere in the serialized payload, and that a disabled session never reaches
the sender at all.

## Delivery guarantees

Events queue in memory on a bounded queue serviced by a daemon thread with a
3-second send timeout; failures are swallowed and overflow is dropped. Nothing
is written to stdout (over stdio that is the MCP wire), nothing telemetry-
related is stored on disk beyond the install id file, and a dead or slow
telemetry endpoint is invisible to tool calls.
