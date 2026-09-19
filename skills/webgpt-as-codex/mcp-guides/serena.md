# Serena MCP Operating Guide

Component: `serena`

## Mental model

Serena is the semantic code-navigation/refactoring capability. Use it when the question is about symbols, references, declarations, implementations, diagnostics or reference-aware changes. It is not the default shell, Git client, browser automation tool or host-process manager.

## Actual exposed capability evidence

Stage 9 discovery used real MCP initialize + tools/list. The live server exposed 29 tools, including:
`get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, `find_implementations`, `find_declaration`, `get_diagnostics_for_file`, `rename_symbol`, `safe_delete_symbol`, `replace_symbol_body`, `insert_before_symbol`, `insert_after_symbol`, `search_for_pattern`, project activation/configuration and project-memory operations.

The schema distinguishes symbol-level operations from text/file operations. Symbol mutations require a symbol name path plus relative path; reference-aware rename/delete operations should be preferred when the intent matches them.

## Best use cases

- locate a class/function/method or understand a file symbol tree;
- find callers/references before changing a public symbol;
- inspect declarations/implementations and diagnostics;
- perform reference-aware rename or safe deletion;
- replace or insert complete symbol bodies after retrieving the relevant symbol.

## Poor use cases

- running repository test/build/Git commands;
- browser/UI automation;
- generic machine file/process management;
- editing a few unrelated text lines when a direct file patch is cheaper and clearer.

## Goal-oriented patterns

- Unknown code area: `get_symbols_overview` -> narrow `find_symbol` -> retrieve only needed bodies.
- Impact analysis: `find_symbol` -> `find_referencing_symbols` before changing externally referenced symbols.
- Rename: use `rename_symbol` instead of manual search/replace.
- Delete: use `safe_delete_symbol`; do not delete first and hunt references later.
- Ambiguous name/location: use `search_for_pattern` to find candidate files, then return to symbol tools.

## Common mistakes

- calling semantic tools before confirming the active project;
- treating a Serena session/config failure as proof the server is unavailable;
- reading whole files when symbol-level retrieval is sufficient;
- using symbol replacement for a tiny line edit inside a large symbol;
- using Serena shell capability as a substitute for a repository-bound execution tool.

## Failure diagnosis

1. Confirm the MCP is reachable and tools/list still exposes the expected semantic tools.
2. Check active-project/config state, but do not stop there: a configuration summary that says the language server is `ready` is not proof that a semantic tool can actually acquire an active backend.
3. Exercise one intended semantic operation such as symbol overview and distinguish “no active language server” from server unavailability.
4. Check whether the requested operation is symbol-capable for the file/language.
5. If the web-connected Serena session is unusable but the local Serena service is healthy, use the local Serena path rather than abandoning semantic navigation.

## Verification signals

- active project is the intended repository;
- symbol lookup returns the intended relative path/name path;
- reference-aware mutations report success without unresolved references;
- diagnostics/reference queries agree with the intended edit boundary.

## Performance / cost

Batch independent semantic queries when possible. Prefer overview -> targeted symbol bodies over whole-file reads. Do not re-read a symbol only to “confirm” a Serena mutation that already returned success unless independent validation is required for the wider change.

## Accumulated lessons

A tool/session failure is not tool unavailability. Project binding, language-server state and orchestration/session failures must be diagnosed before fallback.

## Better alternatives

Use Coding Tools for repository execution/Git and narrow file edits when it is correctly bound. Use Desktop Commander for host files/processes. Use Playwright for browser DOM and Windows-MCP for native Windows GUI.
