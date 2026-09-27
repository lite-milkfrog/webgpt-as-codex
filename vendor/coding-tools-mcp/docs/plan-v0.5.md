# v0.5.0 execution plan

**Status:** plan approved for execution; no feature code written yet.
**Baseline commit:** `b079994` (`pyproject.toml` version `0.3.0`; `coding_tools_mcp/` unchanged since `ed85e41`).
**Every file:line reference in this document was re-verified against `b079994`.**
Line numbers drift; each reference carries anchor text, and the anchor text is
authoritative. Confirm with `grep -n` before acting.

This plan supersedes the circulating handoff/review material for v0.5.0. Where
that material disagreed with the code at `b079994`, this document records the
correction (section 2) and plans against the code, not the memo.

---

## 1. Goal and scope

User feedback and telemetry converged on one diagnosis: the model was not
forgetting — the server handed out handles and state it silently invalidated,
and its error surface could not say "this call can never succeed." 0.3.0 fixed
the handle/state half (see [CHANGELOG.md](../CHANGELOG.md) and
[migration-0.3.md](migration-0.3.md)). v0.5.0 finishes the remaining half:

1. **Patch recovery protocol** — `apply_patch` produced ~29% of all detailed
   errors (970 of 3,352 in the 2026-07-26..30 telemetry window); its failure
   modes are deterministic and fixable locally in `patching.py` /
   `tool_results.py`.
2. **A structured editing tool (`apply_changes`)** — a second write primitive so
   a stuck model has a fallback, with an explicit optimistic-concurrency
   (`revision`) contract.
3. **Truthful measurement** — the current telemetry counts failed builds as
   successes and its loop metric measures the wrong thing; v0.5.0 cannot be
   proven to work without fixing this first.
4. **Loop prevention** — a circuit breaker for verbatim retries of
   deterministic errors, and removal of the guaranteed-failure
   `request_permissions` advertisement.

Telemetry baseline for acceptance gates (window 2026-07-26..30, ~32,300 calls):
overall attempt failure rate ~7.5%; per-tool failure rates `write_stdin` 84.3%,
`read_output` 58.2%, `request_permissions` 59.9%, `apply_patch` 14.4%,
`exec_command` 4.1%; ~26% of sessions never closed. Four families covered ~84%
of detailed errors: patch context/format (28.9%), stale process handles
(27.1%, addressed in 0.3.0), permissions/elicitation (17.2%), path/boundary
(10.5%).

**Not in scope for v0.5.0:** runtime permission elicitation / an authorization
flow for `write_paths` (startup argument only), Windows ConPTY, per-client
identity and quotas ([issue #46](https://github.com/xyTom/coding-tools-mcp/issues/46)),
prompt-cancellation responsiveness ([issue #48](https://github.com/xyTom/coding-tools-mcp/issues/48)).

---

## 2. Verified state at `b079994` and corrections to the handoff material

### 2.1 Confirmed still open

| ID | Problem | Verified anchor |
| --- | --- | --- |
| B2 | No repeat-failure circuit breaker; a verbatim retry of a deterministic error is unlimited. | no implementation exists |
| B3 | `request_permissions` is always advertised (`ToolSpec` marked `read_only=True`, anchor `"request_permissions": ToolSpec(` at `server.py:684`), yet unconditionally returns `ELICITATION_UNSUPPORTED` outside `dangerous` mode (`def request_permissions` at `server.py:3397`, error at `:3419`). | confirmed |
| C2 | The `@@ <scope>` header text is parsed and discarded (`if lines[i].startswith("@@")` at `patching.py:319`), so a Codex-dialect scope anchor cannot disambiguate. Reproduced live: `@@ def farewell` + a non-unique body line fails `PATCH_CONTEXT_AMBIGUOUS`. | confirmed |
| C4 | Exact line equality only (`find_subsequence_all` at `patching.py:426`); one trailing space in a context line is `PATCH_CONTEXT_NOT_FOUND`. Reproduced live. | confirmed |
| C6 | Success returns only `Patch applied to N file(s) (+a -r)` plus a status summary (`_render_patch` at `tool_results.py:172`); no post-edit evidence. | confirmed |
| C7 | No already-applied detection, no idempotency key for mutating calls. | no implementation exists |
| C8 | `apply_patch` is the only write primitive; `apply_changes` does not exist anywhere in the repo. | confirmed |
| D1 | Non-zero exits are recorded as successful tool calls (`"ok": True` hardcoded at `processes.py:280`; the server records `ok=bool(payload.get("ok"))`). | confirmed |
| D2 | `consecutive_failures` is one global slot (`self._failure_streak` at `telemetry.py:311`) reset by any success of any tool (`if ok: self._failure_streak = None` at `telemetry.py:400-401`), keyed by tool name only. | confirmed |
| D4 | One generic output schema for every tool, declaring only `ok` and `error` (`def tool_output_schema` at `server.py:4438`, attached to every catalog entry at `:4545`). | confirmed |
| E1 | `timeout_ms` defaults to 30000 (`server.py:2361`, schema default at `:4644`) and the watchdog kills the process group at that same deadline even after the call yields (`refresh_status` at `processes.py:296-298`, `start_command_watchdog` at `:411`). The schema maximum is already 600000, so the problem is the default plus the conflation of yield time with process lifetime, not a hard cap. | confirmed, refined |
| E2 | `git_diff` runs only `git diff` and `git diff --cached` (`server.py:3153-3156`, `--cached` at `:3177`); untracked files are invisible, so a file created via `*** Add File` cannot be verified. The non-git fallback (`_fallback_diff` at `:3186`) covers only paths previously touched by `apply_patch` (`patch_baselines`). | confirmed |
| F1 | SWE-bench predictions are schema-valid placeholders ([swe-bench.md](swe-bench.md)); dogfood/benchmark runs mostly submit pre-made patches. | confirmed |
| F2 | [limitations.md](limitations.md) does not disclose exact-match patching, the uniqueness requirement, the absence of fuzzy matching, or retained-output expiry (`COMPLETED_COMMAND_TTL_SECONDS = 300` at `server.py:199`). | confirmed |

### 2.2 Confirmed fixed in 0.3.0 — do not redo

A1 (workspace-owned commands), A3 (`COMMAND_NOT_FOUND` with recovery path), A4
(`default_cwd` removed, 18-tool catalog), B1 (error text carries category,
retryability, and "Do not repeat this call unchanged." — `tool_results.py:51-65`),
C3 (blank context line written as `""` accepted — `parse_update_hunk` at
`patching.py:406-411`). Partially addressed: A2 (`server_info.output_retention`
published at `server.py:1588`; the TTL itself remains), C1 (one-line example in
the `apply_patch` description at `server.py:609-612`; still no uniqueness or
`@@` semantics), C5 (`retry_hint` renders at `tool_results.py:68-70`, and —
further along than the handoff stated — `hunk_index` and `match_count` are
already in the error details at `patching.py:356-374`; missing only the nearby
file text and candidate positions).

### 2.3 Corrections — where the handoff/review material is out of date

1. **The appendix repro script's expected output is wrong.** Run as written at
   `b079994` it passes **4/5**, not 3/5: its case 3 places `def greet(name):`
   as an ordinary context line (which is unique in the fixture), so it never
   exercises the discarded `@@` scope. C2 itself is real — moving the scope
   text onto the `@@` line (`@@ def farewell`) reproduces
   `PATCH_CONTEXT_AMBIGUOUS`. When the script is restored under `scripts/`,
   case 3 must be corrected to put the anchor on the `@@` line; only then is
   "all five OK" a valid Track A exit criterion.
2. **Same-path chaining in `apply_patch` is implemented today**, not merely
   un-promised. The planner keys staged files by display path and chains a
   second update on the prior staged content (`prior = staged.get(source.display)`
   and `content = prior.content if prior is not None` at `server.py:2277-2281`);
   update-after-delete is explicitly rejected (`"Cannot update a deleted file."`
   at `:2279`). The committer receives one `StagedFile` per path, so
   `_assert_unique_paths` (`patching.py:172-176`) never fires for chained
   envelopes. What is true: zero test envelopes name the same path twice and
   [runtime-contract-v0.3.md](runtime-contract-v0.3.md) is silent on chaining.
   This flips the framing of the handoff's decision 2: forbidding chaining is
   now a **behavior change** to working code, while promising it costs only
   tests and a contract sentence. See decision D-2.
3. **The `had_trailing_newline` / `splitlines` diagnoses are obsolete.**
   `apply_update_hunks` uses a `split("\n")` bijection where the final empty
   element *is* the trailing newline (comment block at `patching.py:340-345`),
   and `parse_patch` does the same (`:277-281`); tests cover form-feed context
   lines and EOF blank-line shapes (`tests/compliance/test_runtime_helpers.py:1680-1731`).
   Do not budget work for these. The one residual: `*** End of File` is parsed
   and ignored (`patching.py:404-405`) rather than acting as an EOF anchor;
   fold that into C2's locator work (see A-1).
4. **The tool catalog is 18, not 20.** `TOOL_REGISTRY` holds 18 specs
   (`server.py:570-697`); `view_image` is gated by `enable_view_image`
   (default `True`), so 18 are advertised by default.
5. **B3 cannot be fixed by per-client capability detection as circulated.** The
   server never reads client capabilities at `initialize`, and since 0.3.0 HTTP
   is stateless with no `Mcp-Session-Id`, so there is no per-client place to
   hang a differentiated `tools/list`. The existing `gated_by` mechanism
   (`ToolSpec.gated_by` at `server.py:555-556`, applied at `:1284-1288`) gates
   on a runtime property; gate `request_permissions` on the permission mode
   instead (advertised only when `dangerously_skip_all_permissions` is true,
   the sole configuration in which it can ever return `granted`).
6. **Landlock claims verified as circulated:** the workspace root receives the
   full handled access mask (`workspace_access = handled` at `server.py:4136`,
   granted at `:4141`), write roots add only the runtime dir
   (`landlock_write_roots` at `:1455-1456`), and Landlock has no deny rules —
   so "writable workspace except these files" is inexpressible and
   structured-only enforcement means a read-only workspace plus an allowlist.
   `write_generated_or_ignored` exists only in the `request_permissions` input
   schema (`server.py:4745`); delete it rather than implement it.

---

## 3. Work breakdown

Four tracks. Track A goes first: it addresses the largest verified error family
with changes local to `patching.py`, `tool_results.py`, and tool descriptions.
Track D can run in parallel with A. Track C must land before any release
measurement. Track B builds on Track A's C6 output (shared revision mechanism).

### Track A — finish the `apply_patch` recovery protocol (do first)

**A-0. Restore the regression guard.** Add `scripts/repro_patch_failures.py`
from the handoff appendix with case 3 corrected per §2.3(1) (scope text on the
`@@` line). Exit status = number of failing cases; wire into CI. Extend with a
same-path-chaining envelope (locks in current behavior per decision D-2) and an
`*** End of File` case.

**A-1. C2 — make `@@ <scope>` participate in hunk location.** In `parse_patch`,
retain the header text after `@@` per hunk instead of dropping it
(`patching.py:319-325`). In `apply_update_hunks`, when context matches multiple
locations, use the scope line to select the candidate whose preceding lines
contain (exact, then whitespace-insensitive) the scope text; a unified-diff
numeric header (`@@ -1,4 +1,4 @@`) is treated as no scope, preserving today's
accepted shape. Give `*** End of File` real semantics at the same time: prefer
the match that ends at EOF when present. Exit criteria: corrected repro case 3
passes; `PATCH_CONTEXT_AMBIGUOUS` count in the repro fixtures drops to zero;
existing compliance vectors (`tests/compliance/runtime_semantics/semantic_vectors.json`)
unchanged.

**A-2. C4 — graded matching.** In `find_subsequence_all` callers: try exact,
then retry ignoring trailing whitespace, then retry ignoring
leading-indentation width (rstrip / uniform-dedent comparison), then fail.
Every downgrade is labeled truthfully in the result (`"match_quality":
"exact" | "trailing_ws" | "indent"` plus a warning string). Ambiguity checks
run per grade — a fuzzy grade that matches two places is still
`PATCH_CONTEXT_AMBIGUOUS`, not a guess. Exit criterion: repro case 5 (trailing
space) passes with a labeled downgrade.

**A-3. C6 — post-edit evidence on success.** Extend the `apply_patch` payload
and `_render_patch` (`tool_results.py:172`) with, per affected file: changed
line ranges in the *new* file, `total_lines` after the edit, and a SHA-256
content hash of the resulting bytes. The hash field must use the same
name/derivation as `apply_changes`' `revision` (Track B) — this is the shared
mechanism, so it is a prerequisite for Track B.

**A-4. C5 — repair data on failure.** On `PATCH_CONTEXT_NOT_FOUND` /
`PATCH_CONTEXT_AMBIGUOUS`, add to `details`: the current file text around the
best near-miss (with line numbers, bounded to a few hundred bytes), and
candidate match positions for the ambiguous case. `hunk_index` and
`match_count` already exist (`patching.py:356-374`); keep them.

**A-5. C1 — description and disclosure.** Extend the `apply_patch` tool
description (`server.py:609-612`) with: context must be unique within the file
(or use `@@ <scope>`), `@@` carries scope semantics, a blank context line may
be `""` or a single space, and matching is graded with truthful labels. Keep it
under the length that clients truncate; the full format reference lives in
[tools-and-schemas.md](tools-and-schemas.md).

**A-6. C7 — idempotency.** Two halves: (a) already-applied detection — before
failing a hunk whose *old* text is absent, check whether the *new* text is
already present at the expected location and, if the entire operation set is
already applied, return success flagged `"already_applied": true` instead of
`PATCH_CONTEXT_NOT_FOUND`; (b) an optional `idempotency_key` argument on
mutating tools — the runtime keeps a small LRU of `(key → result)` and replays
the recorded result on repeat, making lost-response retry safe. (b) is shared
with `apply_changes`; implement once.

### Track B — `apply_changes` structured editing tool

New tool, additive (no breaking change to `apply_patch`). Design decisions
already settled by verification (see also §5 for the ones still open):

- **`revision` is computed incrementally inside `read_file`'s existing
  streaming pass.** `read_file` already iterates every line unconditionally
  (never breaks — it needs `total_lines`; `server.py:1757-1768`) with
  `errors="strict"` and `newline=""`, so per-line `digest.update(line.encode("utf-8"))`
  reproduces the file's exact bytes (BOM round-trips as `\ufeff`), adds no
  fourth file access (today: `stat()` at `:1745`, binary sniff at `:1746-1748`,
  streaming read at `:1757`), is O(1) memory, and **eliminates
  `MAX_REVISION_BYTES`, `revision: null`, and any "pass null to confirm" path
  entirely.** The `revision=` value also appears in the model-visible rendered
  text — a `tool_results.py` change.
- **`StagedFile` gains an explicit `action: "write" | "delete" | "verify"`
  enum**, replacing `content=None`-means-delete (`patching.py:79-84`). `copy`
  needs verify-without-write of a source baseline. No new committer; the
  committer's API changes — budget it as such, not as zero.
- **Path validation lives in the planner, before staging** — every `path` and
  `destination` through `reject_write_symlink` / `resolve_for_write`, exactly
  as `apply_patch` does at `server.py:2242-2249`.
- **Empty `changes` array** fails identically to `apply_patch`'s
  `PATCH_FAILED "No files were modified."` (`server.py:2320-2321`).
- **Keep both `insert_before` and `insert_after`** and state the boundary
  values (0 and `total_lines + 1` respectively) in the schema descriptions.
  Whole-line semantics throughout; no intra-line spans.
- **1 MiB is the binding size constraint** (`MAX_HTTP_REQUEST_BYTES` at
  `server.py:195`, enforced at `:4989`). Keep change/edit counts only as guards
  against pathological input; document the byte limit and advise roughly ≤20
  files per call.
- **Same-path duplicates within one call are rejected** (declarative
  semantics; chaining is `apply_patch`'s imperative territory — decision D-2).
- Concurrency: reuse the single `patch_lock` (`server.py:1337`) and the
  pre-commit baseline recheck. The cross-process honesty statement is Track D.

### Track C — circuit breaker and truthful telemetry (before any measurement)

- **D1** — split command outcome recording: replace the hardcoded `"ok": True`
  (`processes.py:280`) with an outcome enum
  `exited_0 | exited_nonzero | timeout | signal | spawn_error` carried through
  `emit_tool_trace`. Transport-level `ok` (the tool call executed) stays as-is;
  telemetry gains the operation-level outcome so failed builds stop counting
  as successes.
- **D2** — key failure streaks by `(tool, error_code)` in a small map, cleared
  only by a success of the same tool (`telemetry.py:400-408`). This reverses
  the 0.3.0 regression where any success of any tool cleared the one global
  slot.
- **B2** — circuit breaker keyed on `(tool, error_code, argument fingerprint)`
  (a stable hash of normalized arguments): after the second identical
  deterministic (`retryable=false`) failure, refuse the verbatim retry with a
  distinct terminal error naming what must change. Scope it runtime-wide
  (there is no task identity in the protocol today); the argument fingerprint
  keeps two clients' different work from colliding.
- **B3** — gate `request_permissions` advertisement on permission mode via
  `gated_by` (§2.3(5)). Outside `dangerous` mode the tool disappears from
  `tools/list`; the handler stays for direct callers. Delete the
  `write_generated_or_ignored` enum value (`server.py:4745`). Breaking-change
  note in the migration doc.
- **D4** — per-tool output schemas: declare the fields each tool actually
  returns (`command_id`, `status`, `exit_code`, `output_ref`, `truncated`,
  `next_action`, patch evidence fields, …) instead of the single generic
  schema (`server.py:4438`, `:4545`). Guarded by the existing schema-drift
  test.
- Dashboard: separate tool-call failures, policy denials, logical operation
  failures, eventual recovery rate, and task verification failures. Do not
  read the current dashboard until D1 and D2 land.

### Track D — low-risk, pure upside (parallel with Track A)

- **E1** — separate yield time from process lifetime: keep `yield_time_ms`
  semantics; give the process lifetime its own default (recommend 300s; see
  decision D-6) independent of the initial yield, so a backgrounded build
  survives the first return. `timeout_ms` keeps its meaning as total lifetime;
  only the default and its coupling to the watchdog change
  (`processes.py:296-298`, `:411`).
- **E2** — include untracked files in `git_diff` (e.g.
  `git diff --no-index /dev/null <file>` per untracked path from
  `git ls-files --others --exclude-standard`, appended under the same
  truncation budget), so `*** Add File` results are verifiable.
- **Disclosure** — expose `workspace_mutation_policy` in `server_info`; warn on
  non-Linux in `check_exec_environment` (`server.py:1669-1687` currently warns
  only on Landlock absence, dangerous mode, and faked annotations); update
  project instructions to "prefer `apply_changes` / `apply_patch`".
- **Contract honesty** — state in the runtime contract that `patch_lock`
  (`server.py:1337`) protects concurrency *within one process only*, and that
  cross-process safety (two servers on one workspace) rests entirely on the
  pre-commit baseline recheck. Word it around processes, not sessions — 0.3.0
  advertises multi-client single-server sharing, which invites the wrong
  inference.
- **F2** — disclose in [limitations.md](limitations.md): exact-match patching
  and its graded-matching successor, the uniqueness requirement, and retained
  output expiry (`COMPLETED_COMMAND_TTL_SECONDS`, `server_info.output_retention`).

### Behind a flag, not default in v0.5.0

- `--workspace-mutation=structured-only`, defaulting to `unrestricted`.
  Enforcement via Landlock means read-only workspace + allowlist (§2.3(6));
  the `__pycache__`-class obstacle is operational (enumerate and pre-create
  under every package directory, redo on every added package), not technical.
  Ship the mechanism dark; default-on would break pytest, npm, cargo, gradle,
  and git in one release on the heels of 0.3.0's seven breaking changes.
- `write_paths` as a startup argument (a project property, not a per-request
  one), layered with directories derived from `.gitignore`. No runtime
  authorization flow in v0.5.0 — none exists today (`server.py:3397`) and
  building one is out of scope.

---

## 4. Sequencing and PR slicing

Each PR is independently releasable and ordered so measurement is trustworthy
before the headline feature ships.

| # | Contents | Depends on |
| --- | --- | --- |
| PR-1 | A-0 repro script (corrected) + A-1 (C2, `*** End of File`) + A-2 (C4), `patching.py` + tests | — |
| PR-2 | A-3 (C6 evidence) + A-4 (C5 repair data) + A-5 (C1 description), `patching.py` / `tool_results.py` / `server.py` descriptions | PR-1 |
| PR-3 | A-6 (C7 idempotency: already-applied + `idempotency_key`) | PR-2 |
| PR-4 | D1 + D2 + D4 (telemetry truth + per-tool output schemas) | — |
| PR-5 | B2 circuit breaker + B3 mode-gated `request_permissions` | PR-4 (D2 keying) |
| PR-6 | E1 + E2 + Track D disclosure/contract/F2 docs | — |
| PR-7 | `apply_changes`: `read_file` incremental `revision` + committer `action` enum + planner + tool surface (may split in two: mechanism, then tool) | PR-2 (shared hash), PR-3 (shared idempotency) |
| PR-8 | Flagged: `--workspace-mutation=structured-only` + `write_paths` startup arg, off by default; delete `write_generated_or_ignored` if not already gone via PR-5 | PR-7 |
| PR-9 | F1 evaluation harness: 30–50 real tasks, same model/prompt, native tools vs this server; scored on final test pass rate, first-patch success, rounds to green, regressions, wall time | PR-4 (metrics) |

Standing rule 3 does not apply (no `infra/cloudflare` or workflow changes).
Every PR runs the narrowest relevant checks first (`tests/compliance` patching
and schema-drift suites), then the full suite.

---

## 5. Decisions that need an owner

Best practice does not settle these; each carries a recommendation.

**D-1. Is `revision` required or optional on `apply_changes`?**
Recommendation: **required.** Optional reintroduces the hidden-stale-state bug
class that 0.3.0 removed `default_cwd` to kill; required guarantees the server
never overwrites bytes the model has not seen. The escape hatch for
generated/huge files is a startup argument, not a wire-level bypass. Cost:
more verbose than comparable tools. Do **not** add `revision` to `apply_patch`
— its context lines already are its optimistic check, and a second mechanism
would produce two conflicting failure modes on one tool.

**D-2. Same-path chaining in `apply_patch`: promise, forbid, or leave silent?**
Corrected framing (§2.3(2)): chaining is implemented and works today, so
forbidding it is a behavior change, while promising it costs a contract
sentence plus tests. Recommendation: **promise it** (document + lock in with a
repro/test envelope), and **reject same-path duplicates in `apply_changes`**,
whose semantics are declarative. Only a real downstream consumer depending on
rejection — knowledge that lives with maintainers, not the repo — flips this.

**D-3. `--workspace-mutation=structured-only` default.**
Recommendation: **off, behind a flag** (see §3, flagged work). Sell
kernel-enforced structured-only as an available strong mode, not a default
stacked onto a release that follows seven breaking changes.

**D-4. `write` versus `replace_all` at file level in `apply_changes`.**
Recommendation: **file-level `write` action** — the alternative is already
being patched around with "cannot be mixed with other edits". Low priority;
either shape works.

**D-5. How `request_permissions` disappears (B3).**
Recommendation: **mode-gated via `gated_by`** (§2.3(5)); per-client capability
gating is architecturally unavailable in the stateless-HTTP design.
Removing a tool from `tools/list` outside `dangerous` mode is breaking for any
client that hardcodes the catalog; document it in the migration notes. The
alternative — keep advertising but mark it non-read-only with a
description warning — is strictly worse (it is what produces the 59.9%
failure rate today) but is the fallback if a consumer requires a stable
catalog.

**D-6. New default process lifetime for `exec_command` (E1).**
The schema already permits 600s; only the default (30s) and the
watchdog-coupling change. Recommendation: **300s lifetime default with the
initial yield unchanged at 10s**, matching the 2-CPU/4-GB sandbox reality of
install/build/test steps. 120s is defensible if operators complain about
zombie budget; make it one constant.

**D-7. Owner and budget for the F1 real-task evaluation.**
The only artifact that can falsify "spent all day and it still isn't right"
requires model access, task curation, and repeated runs — a resourcing
decision, not an engineering one. Recommendation: gate the v0.5.0 *release
announcement* (not the code merge) on at least the first 30-task run.

---

## 6. Acceptance gates

Measured on the telemetry pipeline **after PR-4 (D1/D2) lands**; the current
dashboard counts failed builds as successes and must not be used as baseline
or evidence.

| Metric | Baseline (0.2.2 window) | v0.5.0 target |
| --- | --- | --- |
| `write_stdin` failure rate | 84.3% | < 10% |
| `read_output` failure rate | 58.2% | < 10% |
| `request_permissions` failure rate | 59.9% | n/a — not advertised |
| `apply_patch` failure rate | 14.4% | < 5% |
| First-attempt patch success rate | not measured | establish, then > 80% |
| Same deterministic error repeated 3+ times | occurs | 0 (breaker-guaranteed) |
| Sessions never closed | 26% | < 5% |
| Overall failure rate | 7.32% | < 3% |
| Repro script (`scripts/repro_patch_failures.py`, corrected) | 4/5 at `b079994` | 5/5, plus chaining and EOF cases |

Plus the F1 evaluation per D-7: native tools versus this server on 30–50 real
tasks, scored on final test pass rate, first-patch success rate, rounds to
green, regressions introduced, and wall time.

---

## 7. Notes for implementers

- Re-verify every line number in this document against your working tree
  before acting; anchor text is authoritative.
- The patch dialect is V4A; the codebase uses that name in comments
  (`patching.py:407`), useful when researching `@@` scope semantics.
- Per [AGENTS.md](AGENTS.md), this plan links to
  [CHANGELOG.md](../CHANGELOG.md), [migration-0.3.md](migration-0.3.md),
  [limitations.md](limitations.md), [runtime-contract-v0.3.md](runtime-contract-v0.3.md),
  and [swe-bench.md](swe-bench.md) instead of restating them; keep it that way.
- No code changes have been made for any item in section 3; everything is
  diagnosis with a verified location.
