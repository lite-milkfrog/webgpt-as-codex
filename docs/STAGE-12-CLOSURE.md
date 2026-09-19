# Stage 12 Closure — README / Release / Final-Acceptance Preparation

Result: CLOSED_LOCAL_VERIFIED

CURRENT_STAGE = FINAL-OVERALL-ACCEPTANCE
NEXT_STAGE = PROJECT-COMPLETE
AFTER_NEXT_STAGE = TERMINAL

SOURCE_HEAD = 6a72d5f4c5b77c33f25e55c75fc00353cd9cd92f

## Release findings and implementation

- audited README, package metadata, Skill metadata and release-facing architecture against verified Stage 0-11 behavior;
- removed the stale README claim that Manager Update was still deferred and documented the current fixed Stage 11 Update authority;
- aligned the machine-readable Skill manifest with `SKILL.md` at version `0.6.0`;
- built and installed the baseline wheel in an isolated venv instead of trusting source-tree tests;
- baseline install exposed a real release blocker: the console entry point worked, but `load_components()` returned zero built-ins and Manager `index.html` was absent because runtime resources were repository-root siblings not included in the wheel;
- reopened only the Stage 12 packaging boundary, added explicit public data-file packaging, and introduced `resource_root()` so source checkout and installed layouts resolve the same public resources;
- updated Registry, Manager and onboarding built-in lookup to use that resource boundary without changing Stage 0-11 behavior;
- added Stage 12 regression coverage for package metadata, installed-resource fallback and Skill version alignment;
- removed the empty literal `%SystemDrive%` directory tree left by an earlier service-context probe; it was never Git-tracked or part of the wheel.

## Release artifact evidence

Final wheel: `webgpt_as_codex-0.1.0-py3-none-any.whl`.

Isolated final install:
- console `--version`: PASS (`0.1.0`);
- console `--help`: PASS;
- installed public resource root: PASS;
- built-in component manifests: 8/8 loaded;
- Manager static UI: present;
- wheel listing contains runtime Python, public component manifests, Manager static UI and standard distribution metadata; no stage closures, handoff receipts, local state databases or private machine artifacts are packaged.

## Validation

Focused Stage 12/Registry/Manager/Stage 9 boundary suite: 29 PASS.

Full repository: 107 PASS.

Static and safety gates:
- Ruff PASS;
- secret scan PASS;
- `git diff --check` PASS.

Final wheel build/install/resource smoke: PASS.

## Failure and tool evidence

- Coding Tools was bound to a workspace containing the repository as the nested `webgpt-as-codex` path. An initial `git_status(.)` failure was binding/path evidence, not a repository failure.
- Coding Tools `git_log(path=...)` did not honor the nested repository path in this session; repository status/commands continued through the same bound Coding Tools command surface with explicit workdir.
- the first wheel command accidentally passed `webgpt-as-codex` as a requirement name rather than `.\webgpt-as-codex`; the corrected path built successfully. This was command-argument harness evidence.
- the baseline installed-resource failure was target/release evidence and therefore was fixed rather than bypassed.
- the first full gate found one Ruff-only import ordering issue in the new Stage 12 test; it was corrected and the complete gate reran green.

## Ownership boundary

Stage 12 did not redesign OAuth/Tailscale, runtime supervision, Add MCP, Loop Engineering, handoff semantics or Stage 11 security contracts. The only implementation boundary reopened was the release packaging/resource lookup required for an installed artifact to preserve already-verified behavior.

## Post-commit recursive handoff

After this closure is committed:
1. read the real Stage 12 committed HEAD;
2. instantiate `FINAL-OVERALL-ACCEPTANCE` from `prompts/FINAL-OVERALL-ACCEPTANCE-PLAN.json`;
3. validate CURRENT/NEXT/AFTER_NEXT/SOURCE_HEAD;
4. hash the exact prompt;
5. use the already authenticated Playwright MCP browser context;
6. submit exactly once;
7. verify sent user message + `/c/` URL + new assistant run;
8. persist the prompt SHA-256 / handoff receipt machine-locally.

Final Overall Acceptance inherits the recursive obligation into PROJECT-COMPLETE.
