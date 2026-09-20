# Serena MCP Operating Guide — 简体中文

[English](../../mcp-guides/serena.md) | **简体中文**

Component: `serena`

## Mental model
Serena 是 semantic code navigation/refactoring capability，适合 symbol/reference/declaration/implementation/diagnostic/reference-aware change；不是默认 shell/Git/browser/host manager。

## Real capability evidence
Stage9 真实 initialize + tools/list 暴露 29 tools，包括：
`get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, `find_implementations`, `find_declaration`, `get_diagnostics_for_file`, `rename_symbol`, `safe_delete_symbol`, `replace_symbol_body`, `insert_before_symbol`, `insert_after_symbol`, `search_for_pattern`，以及 project activation/config/memory tools。

schema 区分 symbol 与 file/text operation。rename/delete 意图匹配时应优先 reference-aware tool。

## Best use
定位 class/function/method、file symbol tree、find callers/references、declaration/implementation/diagnostic、reference-aware rename/delete、完整 symbol body replace/insert。

## Poor use
test/build/Git、browser/UI、generic host file/process、仅改几个文本行且 direct patch 更便宜。

## Goal patterns
- unknown area：overview -> narrow find_symbol -> 只取需要 body；
- impact：find_symbol -> find_referencing_symbols；
- rename：`rename_symbol`，不用 manual replace；
- delete：`safe_delete_symbol`，不要先删再找引用；
- ambiguous：`search_for_pattern` 找 candidate，然后回 symbol tool。

## Mistakes
没确认 active project 就 semantic call；把 session/config failure 当 server unavailable；能 symbol-level retrieval 却 whole-file read；tiny line edit 用 whole symbol replacement；拿 Serena shell 替 repo-bound execution。

## Diagnosis
1. 确认 reachable + tools/list 仍有 semantic tools；
2. 查 active project/config，但 `ready` summary 不足以证明 backend；
3. 真实 exercise intended semantic op（如 overview），区分 “no active language server” 与 server unavailable；
4. 检查 file/language 是否支持 symbol op；
5. web session 不可用但 local Serena 健康时，走 local Serena，不直接放弃 semantic navigation。

## Verification
active project 正确；symbol path/name path 正确；reference-aware mutation 无 unresolved reference；diagnostic/reference 与 boundary 一致。

## Performance
可安全 batch independent semantic query；优先 overview -> targeted body；mutation 已返回成功时不要仅为“再确认”重复读 symbol，除非 wider validation 需要。

## Lesson
tool/session failure != tool unavailability；project binding、language-server、orchestration/session 必须先诊断。

## Alternative
repo execution/Git/narrow edit -> Coding Tools；host -> Desktop Commander；browser -> Playwright；native Windows GUI -> Windows-MCP。
