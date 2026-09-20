# Coding Tools MCP Operating Guide

[**English**](coding-tools.md) | [简体中文](../zh-CN/mcp-guides/coding-tools.md)

Component: `coding-tools`

## Mental model

Coding Tools is the repository-bound execution/edit/Git capability. Its workspace policy is a security and correctness boundary, not an inconvenience to bypass.

## Actual exposed capability evidence

Stage 9 discovery used real MCP initialize + tools/list. The live server exposed 18 tools:
`server_info`, `check_exec_environment`, `read_file`, `list_dir`, `list_files`, `search_text`, `apply_patch`, `apply_changes`, `exec_command`, `write_stdin`, `kill_command`, `read_output`, `git_status`, `git_diff`, `git_log`, `git_show`, `git_blame`, `view_image`.

The edit schemas include revision/idempotency support; command execution has explicit workdir, timeout and retained-output semantics.

## Best use cases

- repository reads/searches when the configured workspace is the target repository;
- bounded line-addressed or context-anchored edits;
- test/build/lint commands with explicit workdir;
- Git status/diff/log/show/blame inside the bound workspace;
- polling long-running commands by returned command id.

## Poor use cases

- writing outside the configured workspace;
- bypassing workspace policy with shell tricks;
- browser or Windows GUI interaction;
- semantic refactors where Serena can update/check references safely;
- host-wide service/process inspection better handled by Desktop Commander.

## Goal-oriented patterns

- Before repo work: verify workspace/binding with `git_status` or server/environment evidence.
- Known line numbers: prefer `apply_changes` with the revision returned by `read_file`.
- Context-anchored patch: prefer `apply_patch`; use dry-run when uncertainty is material.
- Tests/builds: pass explicit workdir; if still running, poll the returned command id instead of starting duplicates.
- Git verification: `git_status` -> `git_diff` -> targeted tests -> commit through the allowed repository workflow.

## Common mistakes

- assuming “not a Git repo” means the target repository is broken when Coding Tools is bound elsewhere;
- using a default interpreter/environment that imports another editable worktree;
- retrying a command side effect instead of polling post-state;
- omitting revisions on edits and losing concurrent-change protection.

## Failure diagnosis

1. Confirm the configured workspace and intended repository are the same.
2. Distinguish workspace-policy rejection from target-code failure.
3. Confirm command workdir and interpreter/environment.
4. For long commands, inspect command id/output before retrying.
5. If binding is wrong, use an authorized isolated worktree or the project-approved host fallback; do not bypass the boundary.

## Verification signals

- Git reports the expected branch/repository;
- edits return affected files/revisions and intended changed ranges;
- tests/builds exit with the expected code;
- final Git diff matches the owned stage boundary.

## Performance / cost

Prefer structured read/search/edit/Git tools over generic shell. Use line-addressed edits when positions are known and batch independent work where safe. Redirect very large command output to a file and page it rather than flooding context.

## Accumulated lessons

Workspace binding drift is a recurring harness failure. Treat it as binding evidence, not as permission to use broader tools silently.

## Better alternatives

Use Serena for semantic navigation/refactoring. Use Desktop Commander when the target is host-level files/processes or when Coding Tools is genuinely not bound to the repository. GUI/browser work belongs to Windows-MCP/Playwright.
