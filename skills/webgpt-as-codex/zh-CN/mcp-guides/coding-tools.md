# Coding Tools MCP Operating Guide — 简体中文

[English](../../mcp-guides/coding-tools.md) | **简体中文**

Component: `coding-tools`

## Mental model
Coding Tools 是 repository-bound execution/edit/Git capability。workspace policy 是 security/correctness boundary，不是需要绕过的麻烦。

## Real capability evidence
Stage9 真实 initialize + tools/list 暴露 18 tools：
`server_info`, `check_exec_environment`, `read_file`, `list_dir`, `list_files`, `search_text`, `apply_patch`, `apply_changes`, `exec_command`, `write_stdin`, `kill_command`, `read_output`, `git_status`, `git_diff`, `git_log`, `git_show`, `git_blame`, `view_image`。

edit schema 支持 revision/idempotency；command 有 explicit workdir/timeout/retained-output。

## Best use
repo read/search、bounded line/context edit、test/build/lint、Git status/diff/log/show/blame、poll long-running command id。

## Poor use
workspace 外写入、shell 绕 workspace policy、browser/Windows GUI、适合 Serena 的 semantic refactor、适合 Desktop Commander 的 host-wide process/file。

## Goal patterns
- repo work 前用 Git/server evidence 验证 workspace binding；
- known line -> `apply_changes` + read revision；
- context patch -> `apply_patch`，不确定时 dry-run；
- test/build 显式 workdir，running command 用 id poll，不 duplicate start；
- Git verification：status -> diff -> targeted tests -> allowed commit。

## Mistakes
把 “not a Git repo” 误判为 target repo broken；用错误 interpreter import 另一 worktree；side effect command 直接 retry 而不是 poll；edit 不带 revision 丢 concurrent protection。

## Diagnosis
先确认 configured workspace 与 intended repo；区分 workspace policy rejection/target failure；查 workdir/interpreter；running command 查 id/output；binding 错时用 authorized isolated worktree 或 approved host fallback，不绕 boundary。

## Verification
Git 指向预期 branch/repo；edit 返回 affected file/revision/range；test/build exit 正确；final diff 与 stage scope 匹配。

## Performance
优先 structured read/search/edit/Git；known position 用 line edit；安全时 batch independent work；大 command output 重定向/page，避免 context flooding。

## Lesson
workspace binding drift 是 recurring harness failure，应作为 binding evidence，不是默许 broader fallback。

## Alternative
semantic navigation/refactor -> Serena；host file/process -> Desktop Commander；browser/native UI -> Playwright/Windows-MCP。
