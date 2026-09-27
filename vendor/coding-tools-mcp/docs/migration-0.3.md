# Migrating to coding-tools-mcp 0.3.0

0.3.0 adds MCP `2026-07-28` and removes every session from the server. A
handshake-era client still connects the way it always did — the wire shape of
`2025-11-25` and `2025-06-18` is unchanged — but the tool catalog, the HTTP
transport, and a few `server_info` fields did change, and this page lists all of
it. The contract itself is
[runtime-contract-v0.3.md](runtime-contract-v0.3.md).

If all you need is the fix for the OpenAI connector that could not finish a tool
scan ([issue #39](https://github.com/xyTom/coding-tools-mcp/issues/39)), it
shipped first as **0.2.3**, a hotfix off 0.2.2 with nothing else in it. Upgrade
to 0.2.3 to get that fix alone; upgrade to 0.3.0 for the protocol work.

## Breaking changes

### The two cwd tools are gone; the catalog is 18 tools

`get_default_cwd` and `set_default_cwd` are removed. There is no session to hold
a working directory, so there is nothing to set or read: a relative `path`
always resolves against the workspace root.

- Pass a workspace-relative `path` to the file and Git tools.
- Pass `exec_command`'s `workdir` (also workspace-relative) to run somewhere
  else. It defaults to the workspace root.
- `read_file`'s `next_action` continuation now repeats the workspace-relative
  path it was given. A client that fed the continuation back unchanged keeps
  working; one that re-based it against a session cwd must stop doing that.

### HTTP has no sessions

- No response carries `Mcp-Session-Id` any more, and a client that still sends
  one — because it kept the header from an older server — is served normally
  rather than refused with `-32001 Unknown MCP session`.
- `DELETE /mcp` returns `405` with `Allow: POST`. There is nothing to
  terminate. `DELETE` is gone from the `Allow` header, from
  `Access-Control-Allow-Methods`, and from the server card's
  `transport.methods`.
- The 128-session ceiling and its `503`, the idle-session expiry, and the check
  that a request's `MCP-Protocol-Version` matched its session are all gone with
  the sessions.

Clients that already treated the session header as optional — the spec always
made it a MAY — need no change at all.

### The handshake is no longer an admission gate

`tools/list`, `tools/call`, and every other implemented method are served
whether or not `initialize` came first. `-32002 Server not initialized` is never
returned; a method this server does not implement answers `-32601` before the
handshake exactly as it does after it. `initialize` is idempotent: each one
negotiates on its own and answers with what it negotiated, so a repeat naming a
different supported version is answered with that version instead of `-32600
Server is already initialized with a different protocol version`.

### `notifications/cancelled` no longer stops a command

The notification is still accepted and still answered with nothing, but it no
longer terminates the command that the cancelled request started. That mapping
was keyed by the client's own JSON-RPC id, and two clients that both use `id: 1`
— which is normal — could cancel each other's commands.

Terminate a command with `kill_command`, which names the command by its
`command_id`. The responsiveness this costs is a known limitation, tracked in
[issue #48](https://github.com/xyTom/coding-tools-mcp/issues/48).

### Command handles are named `command_id`

Carried over from [#34](https://github.com/xyTom/coding-tools-mcp/pull/34) and
released here for the first time:

| 0.2.x | 0.3.0 |
| --- | --- |
| `kill_session` | `kill_command` |
| `session_id` argument of `write_stdin` / `kill_session` | `command_id` |
| `session:<id>:stdout` / `session:<id>:stderr` output refs | `command:<command_id>:stdout` / `command:<command_id>:stderr` |

The old names are not accepted. A command is owned by the workspace rather than
by whoever started it, so any authenticated client of that workspace can
continue, read, or kill one with its `command_id`, and no transport event ends
it.

### `server_info` field changes

| 0.2.x | 0.3.0 |
| --- | --- |
| `protocol_version`: the one version this session negotiated | `supported_protocol_versions`: every version this server speaks, newest first |
| `default_cwd` | removed |
| — | `output_retention`: the static per-stream budget (`buffer_bytes_per_stream`, `head_bytes_per_stream`) |

How often that budget was actually hit is a property of the process, not an
answer to whichever client asked, so the eviction and omission counters are
reported in the telemetry `session_end` event rather than by `server_info`. See
[telemetry.md](telemetry.md).

### Server card protocol versions

`/.well-known/mcp.json` and `/.well-known/mcp/server-card.json` report
`supportedProtocolVersions` — a list, newest first — in place of the single
`protocolVersion`. Neither is session-scoped any more.

```json
{"supportedProtocolVersions": ["2026-07-28", "2025-11-25", "2025-06-18"]}
```

## Behavior changes

**`initialize` downgrades instead of failing.** A `protocolVersion` this server
does not speak is answered with an `InitializeResult` naming the newest version
it does (`2025-11-25`), which is what the handshake spec requires, rather than
with `-32602`. Asking to handshake with `2026-07-28` downgrades the same way:
that protocol states its version per request and is never negotiated.

**A missing `MCP-Protocol-Version` header is read as `2025-11-25`.** The older
spec suggests assuming `2025-03-26` for a request without the header, but this
server has never spoken `2025-03-26`, and answering as if it did would name a
version no client could then use. The header value travels with the request as
context and nothing echoes it, records it, or acts on it; no method behaves
differently for it. Send the header and this does not arise.

**Legacy results gained nothing.** The fields `2026-07-28` adds — `resultType`,
`_meta.io.modelcontextprotocol/serverInfo`, `ttlMs`, `cacheScope` — appear only
in answers to requests that asked in that era. A handshake-era client's
responses are byte-for-byte what they were.

## What a `2026-07-28` client gets

Nothing to migrate here — this era is new — but two notes for clients that
support both:

- The probe works. `server/discover` reports `supportedVersions:
  ["2026-07-28"]`, the `tools` capability, and the workspace instructions, so a
  client that discovers never has to handshake. A probe sent *without* the
  modern `_meta` is a handshake-era request for a method that era does not have
  and is answered `-32601`; that is the reply that sends such a client to
  `initialize`, which works.
- Over HTTP, a modern request must mirror its body in `MCP-Protocol-Version`
  and `Mcp-Method`, plus `Mcp-Name` for the methods that name a subject
  (`tools/call`, `resources/read`, `prompts/get`). A mismatch, a missing
  mirror header, or one sent twice is `400` with `-32020`. Handshake-era
  requests are asked for none of this.
- Falling back to the handshake means dropping the header as well. Do **not**
  send `MCP-Protocol-Version: 2026-07-28` on an `initialize`, or on any other
  body that carries no modern `_meta`: the header states which era the request
  is in, so one that disagrees with the body is a mirror violation and is
  refused with `-32020` before the handshake is read. Send the handshake
  version, or no header at all.

## Compliance statement

0.3.0 claims **full support for `2026-07-28`**, with `tools` as the only
advertised capability. Nothing about that support is partial: every method this
server implements is served in that era, with the required `_meta` validation,
mirror headers, error codes, and result shaping.

The one gap worth naming is quality of implementation rather than compliance. A
cancelled request is answered exactly as the spec says, but the work it started
is not stopped any sooner: on stdio the loop is serial, so a response is already
written before a cancellation could be read, and over HTTP the modern
cancellation signal is a closed response stream, which this server does not
detect. Nothing client-observable is violated — the mitigation is the 30-second
foreground window of `exec_command` and terminating with `kill_command` — but
the SHOULD to stop working promptly is not met. Tracked in
[issue #48](https://github.com/xyTom/coding-tools-mcp/issues/48).

## Operator warning: one workspace is one trust domain

Removing sessions made explicit what was already true of commands and files:
**every client that authenticates to a workspace shares that workspace.** One
server process, one runtime, one set of resources.

- Commands are shared. Any client can `read_output`, `write_stdin` to, or
  `kill_command` any command in the workspace, whoever started it.
- Output cursors are consumed globally. Two clients polling the same
  `command_id` split the output between them rather than each seeing all of it.
- Patch state is shared. Concurrent `apply_patch` calls are serialized against
  one another, so an edit cannot be lost, but the loser is answered with a
  conflict.
- The quotas are per workspace, not per client: active commands, retained
  output entries, and output bytes come from one pool, so a busy client can
  exhaust what another was going to use.

Give mutually distrusting clients separate server processes with separate
workspaces. Per-client quotas and identity are tracked in
[issue #46](https://github.com/xyTom/coding-tools-mcp/issues/46); see also
[SECURITY.md](../SECURITY.md) and [limitations.md](limitations.md).

## Non-breaking fixes worth knowing

- Two clients patching the same file no longer lose an update. The patch lock
  now spans every client of the workspace, so the second write is answered with
  a conflict instead of silently overwriting the first.
- A repeated `initialize` on one persistent stdio process is answered rather
  than refused, which is what unblocked the connector in issue #39. This
  shipped first in 0.2.3.
