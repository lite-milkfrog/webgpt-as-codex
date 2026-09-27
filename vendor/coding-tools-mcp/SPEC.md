# Coding Tools MCP Spec

This repository implements the `coding-tools-mcp-v0.3` runtime contract defined
in [docs/runtime-contract-v0.3.md](docs/runtime-contract-v0.3.md).

## Product boundary

The server exposes low-level coding primitives over MCP: inspect a workspace,
apply structured patches, run and interact with commands, and inspect Git. It is
not an agent wrapper and does not expose accounts, memory, cloud tasks, web
search, model routing, plugins, image generation, or subagent orchestration.

## Tool model

There is one stable catalog. The runtime has no tool profiles, no `edit_file`,
no dynamic `tools/list_changed`, and no required `open_workspace` call.
`apply_patch` and `apply_changes` are the direct file-write tools. `safe`,
`trusted`, and `dangerous` primarily govern command policy; they also govern
whether `request_permissions` is useful enough to advertise.

The registry contains 19 tools; the default `safe` and `trusted` catalogs
advertise 18:

- runtime/context: `server_info`, `check_exec_environment`
- workspace inspection: `read_file`, `list_dir`, `list_files`, `search_text`
- mutation: `apply_patch`, `apply_changes`
- processes: `exec_command`, `write_stdin`, `read_output`, `kill_command`
- Git: `git_status`, `git_diff`, `git_log`, `git_show`, `git_blame`
- image: `view_image`

`view_image` can be disabled as an installation capability.
`request_permissions` is advertised only in `dangerous` mode, where it can
return `granted`; its handler remains callable by name in every mode. The
remaining 17 tools are always advertised, and `listChanged` is `false`.

## Protocol

- Two eras are served at once: `2026-07-28`, which carries its version, client
  capabilities, and identity in each request's `params._meta`, and the
  handshake era `2025-11-25` with `2025-06-18` explicitly supported. A request
  belongs to the modern era if and only if its `_meta` names that version.
- Streamable HTTP uses `/mcp`; stdio uses newline-delimited JSON-RPC.
- There are no sessions in either era. One `Runtime` owns the workspace and
  serves every client of it; HTTP issues no `Mcp-Session-Id` and `DELETE /mcp`
  returns `405`.
- JSON-RPC batches are rejected, unimplemented logging is not advertised, and
  `notifications/cancelled` is accepted without terminating the command the
  cancelled request started — a command is stopped with `kill_command`.
- `content` is agent-readable text normally sized by each tool's per-call
  limits, with a documented emergency safety ceiling for pathological entries.
  `structuredContent` is the complete stable machine result. `_meta` is
  optional UI space only.
- Root project instructions are loaded automatically and returned in the
  `instructions` of `initialize` and of `server/discover`.

## Correctness guarantees

Patch operations are staged before writing, use same-directory fsynced temporary
files and atomic replacement, preserve mode/BOM/newlines, detect stale
baselines, and roll back multi-file failures. Filesystem rollback failure is
reported explicitly rather than hidden.

Commands use a 10-second default yield, real POSIX PTYs, bounded active and
retained-command stores, per-command and runtime output budgets, TTL cleanup,
and explicit `next_action` objects for polling or truncated output. Command
handles are `command_id` values, owned by the workspace rather than by a
client: any authenticated client of the workspace can continue, read, or kill
a command with one, and no transport event ends it.

## Security boundary

Direct tools reject absolute paths, traversal, NULs, and symlink escapes.
`exec_command` also applies permission policy and Linux Landlock when available,
but remains a coding runtime rather than a complete container sandbox. Remote
deployment must use bearer or OAuth authentication. OAuth supports protected
resource metadata, PKCE S256, exact redirect binding, and RFC 7591 dynamic client
registration. Authentication admits a client to a workspace and does not
partition it: one workspace is one trust domain, shared by every client of it.

## Compatibility

Version 0.3 adds `2026-07-28` and removes every session. The handshake era is
unchanged on the wire; the cwd tools, the HTTP session, and several
`server_info` fields are not. See
[docs/migration-0.3.md](docs/migration-0.3.md).

Version 0.2 changes model-facing result text from a JSON mirror to summaries.
Clients that parsed `content[0].text` as JSON must read `structuredContent`.
Image base64 now appears once, in the MCP image block. Tool profiles and the
`view_image.output` selector are removed.
