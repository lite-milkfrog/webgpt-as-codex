# Experience Ledger Contract

For every defensive rule keep:
- origin/failure that created it;
- current failure mechanism;
- verification evidence;
- current location of the lesson;
- status: active, relocated, or retired-with-evidence.

Protected examples:
- OAuth authorized but client did not resume;
- PKCE/state/redirect/issuer mismatch;
- browser extension/login-state behavior;
- Playwright host validation;
- stale UI snapshots/high-DPI coordinates;
- HOME/USERPROFILE service-context failure;
- process alive versus MCP healthy;
- handoff submit verification;
- local memory for long tasks;
- Windows console encoding causing the harness, not the target, to fail.

Never delete a lesson only because current code looks simpler.

## 2026-09-19 — Real HTTPS is authoritative for OAuth acceptance

Origin:
- Stage 5 OAuth + Tailscale edge integration.
- A localized HTTP probe of an HTTPS external OAuth flow produced invalid authorization-session failures because Secure-cookie/origin behavior differed from the real client path.

Protected lesson:
- do not treat localhost HTTP localization as authoritative for an OAuth flow whose advertised external URL is HTTPS;
- preserve X-Forwarded-Proto and X-Forwarded-Host at the compatibility boundary;
- validate DCR, PKCE, consent, token, refresh and MCP access through the real HTTPS edge;
- an OAuth compatibility adapter may preserve session/consent continuity, but must not bypass authentication;
- test passwords and OAuth databases remain machine-local.

## 2026-09-19 — Temporary integration instances must not mutate shared agent state

Origin:
- Stage 4 temporary Serena initially used activate_project through a shared Serena configuration and changed the main Serena active project.

Protected lesson:
- start temporary Serena with --project / --project-from-cwd;
- do not use a temporary integration test to mutate a shared Serena active project;
- verify active project before repo-relative writes;
- after any suspicious project switch, verify both target and unrelated repository git status before continuing.

## 2026-09-19 — Playwright Extension handoff must stay in one MCP session

Origin:
- Stage 5 automatic handoff hardening.
- A new Playwright MCP session re-entered through the extension Welcome page; a tab index visible in a previous MCP session was not selectable in the next one.

Protected lesson:
- new ChatGPT tab, snapshot, composer target, submit and verification belong to one Playwright MCP session;
- never carry Playwright element refs or tab indexes across MCP sessions;
- verify handoff from ChatGPT DOM state, not from a click or URL assumption;
- sent-message proof is the user-message DOM containing SOURCE_HEAD;
- new-run proof is an assistant-message DOM node plus a /c/ conversation URL.

## 2026-09-19 — MCP SSE responses may be fragmented across data lines

Origin:
- First live Stage 5 -> Stage 6 Playwright handoff attempt.
- The executor reached browser_snapshot before any prompt submission, then failed because the decoder assumed one complete JSON object per SSE data line.

Protected lesson:
- parse an SSE event as a whole, not only its first data line;
- tolerate data payload fragmentation/line wrapping before JSON decode;
- share one MCP decoder across Doctor, Gateway tests and Playwright handoff;
- a handoff that fails before composer typing has not submitted anything and is safe to repair/retry after a new prompt HEAD is generated.

## 2026-09-19 — Coding Tools workspace binding is authoritative

Origin:
- Stage 6 found Coding Tools attached to `coding-tools-mcp-demo` instead of the target repository.
- Repo-relative access therefore did not address WebGPT-as-Codex.

Protected lesson:
- verify the reported Coding Tools workspace before repository operations;
- honor the configured workspace boundary;
- when rebinding is unavailable, use a dedicated Git worktree located inside the configured workspace and fast-forward the canonical tree only after validation;
- workspace mismatch is harness state, not evidence that target files are absent.

## 2026-09-19 — Manager polling must not become deep-health polling

Origin:
- Stage 6 needed component status while preserving the process/listener/protocol/safe-call/OAuth/remote distinction.

Protected lesson:
- use a bounded status cache and inexpensive listener discovery in the Manager;
- consume deep Doctor evidence rather than running MCP safe calls on every browser refresh;
- unknown, failed and healthy are separate states;
- never render raw manifests or private/loopback service addresses.

## 2026-09-19 — Control actions are owner-stage capabilities

Origin:
- Stage 6 owns Manager contracts, while Doctor/Repair and runtime launch/restart belong to later stages.

Protected lesson:
- expose only a fixed action allowlist;
- no arbitrary command or argument surface belongs in the Manager API;
- confirmation is required for mutating contracts;
- real executors are injected by the stage that owns their safety and rollback semantics.

## 2026-09-19 — Deep health checks must respect prerequisites

Origin:
- Stage 7 live Doctor found a real process/listener split: the OAuth proxy process existed while its expected listener was down, and MCPJungle was installed but not running.

Protected lesson:
- process alive, listener alive, MCP protocol healthy and safe-call healthy are independent evidence;
- do not report protocol/safe-call unknowns as extra failures when listener prerequisite is absent;
- do not report remote unknown as degradation when no public endpoint is configured or remote checking is explicitly disabled;
- a red live Doctor can be correct without authorizing Stage 7 to start the service.

## 2026-09-19 — Version output is evidence only when unambiguous

Origin:
- the first Stage 7 MCPJungle version parser matched dotted address-like banner text as `127.0.0`.

Protected lesson:
- accept explicit version-labelled values or exact semver lines;
- otherwise fall back to verified manifest evidence instead of guessing;
- skip network-capable version commands such as `@latest` during Doctor.

## 2026-09-19 — Editable environments can import the wrong worktree

Origin:
- Coding Tools was correctly constrained to its configured workspace, so Stage 7 used an isolated Git worktree there; the shared virtual environment still pointed its editable package at the canonical tree.

Protected lesson:
- distinguish missing test dependencies from target failures;
- when validating an isolated worktree with a shared venv, make the target source root explicit (for example through `PYTHONPATH`);
- do not install into or rewrite a shared environment merely to hide a harness-binding mismatch.

## 2026-09-19 — ChatGPT composer hydration can expose a hidden fallback first

Origin:
- Stage 7 -> Stage 8 automatic handoff opened a new authenticated ChatGPT tab in the existing Playwright context.
- the first snapshot exposed a hidden fallback textarea before the real composer hydrated; choosing the first textbox ref caused browser_type to wait on an invisible element and time out before any message was sent.

Protected lesson:
- preserve the already authenticated browser context and the same Playwright MCP session;
- after browser_tabs new, enumerate/resolve and explicitly select the new blank ChatGPT tab in that same session; do not assume the extension automatically focused it;
- after opening the new page, poll fresh snapshots for the real active composer instead of selecting the first textbox;
- never reuse stale refs or compensate with blind coordinates;
- verify sent SOURCE_HEAD + assistant run + /c/ URL before declaring handoff success.

## 2026-09-19 — Closure budget belongs inside the Stage

Origin:
- repeated long-window experience showed that implementation can be mostly complete while docs, commit or recursive handoff remain as fragile last steps.
- the user's observed longest runs were around 25 minutes, but there is no verified platform cutoff or stable task-size unit.

Protected lesson:
- use approximately 20 minutes as a soft stage budget including closure/handoff, not as a hard timeout;
- shorter fully closed stages are better than maximizing implementation volume;
- split the owner concern when continuation would threaten validation/docs/commit/handoff;
- collect stage-cost evidence over the next 5-10 stages and recalibrate instead of hardcoding an unsupported limit.

## 2026-09-19 — One tool failure is not tool unavailability

Origin:
- real MCP work has encountered session, workspace-binding, authentication, hydration and harness failures that were initially indistinguishable from tool failure.

Protected lesson:
- inspect actual tool schema/capability, workspace/session/auth state, logs and failure category before fallback;
- distinguish misuse or harness state from capability absence;
- prefer independent exploration before asking the user;
- when user guidance reveals the correct mental model, classify and preserve the reusable principle rather than only the historical click sequence.

## 2026-09-19 — Runtime discovery is not lifecycle ownership

Origin:
- Stage 8 live Start All saw healthy Serena, Coding Tools, Playwright and Windows-MCP listeners that were not launched by the repository.
- Tailscale and Remote Desktop Commander also required process evidence because they do not fit the same listener contract.

Protected lesson:
- use listener/process evidence to preserve a healthy external service, never as authority to kill it;
- stop/restart requires repository-owned PID receipt plus live birth-token/image identity;
- a stale/dead/reused PID receipt is removed without signaling that PID;
- a no-listener system transport needs process evidence for startup preservation but remains distinct from protocol/OAuth health.

## 2026-09-19 — Windows process identity needs a real host probe

Origin:
- Stage 8 unit tests passed while the first real PID-identity probe failed because `ctypes.wintypes` was not imported explicitly on the host Python.

Protected lesson:
- lifecycle safety primitives need at least one real host probe in addition to mocked unit tests;
- explicitly import Windows ctypes types before using FILETIME/process APIs;
- do not start a managed process until the ownership primitive itself has been exercised on the target OS.

## 2026-09-19 — Managed launcher ownership must tolerate newline normalization

Origin:
- the first reversible launcher test wrote CRLF but Python text reading normalized it to LF, causing an exact-content ownership check to misclassify the project-created file as unmanaged.

Protected lesson:
- ownership checks for Windows text launchers may normalize line endings while still requiring the entire expected content and a project marker;
- never weaken that into marker-only deletion/overwrite authority;
- reversible install/uninstall must fail closed when the target file is user-owned or modified.

## 2026-09-19 — Integration-test credentials are not production runtime authority

Origin:
- Stage 8 found the mcp-auth-proxy binary and Stage 5 E2E OAuth state, including machine-local secret material, but no separate production/autostart credential contract.

Protected lesson:
- existence of a secret is not authorization to reuse it for a new lifecycle purpose;
- Start All must truthfully report a required unmanaged component instead of silently promoting E2E state into persistent runtime state;
- credentials remain machine-local and lifecycle adapters consume only explicitly owned credential references/configuration.

## 2026-09-19 — Stage 8 harness and closure-cost evidence

Origin:
- Serena instruction/config calls timed out at the orchestration layer; Coding Tools remained bound to `coding-tools-mcp-demo`; its default Python lacked pytest; the shared venv editable install pointed at the canonical tree.

Protected lesson:
- diagnose the preferred-tool/session failure before fallback;
- honor Coding Tools workspace policy with an isolated worktree rather than bypassing it;
- validate that worktree with the known venv plus explicit worktree `PYTHONPATH` when the default interpreter lacks test dependencies;
- closure evidence includes live Windows PID probing, two-pass idempotent Start All, targeted restart, Manager HTTP boundaries, full tests/lint/secret scan, docs/commit and verified handoff—not only implementation.
