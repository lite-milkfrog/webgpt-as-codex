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
- after opening the new page, do not trust snapshot `[active]` alone: ChatGPT's hidden fallback textarea can carry autofocus and still be invisible to Playwright;
- first find a visible editable composer from live DOM geometry/style, focus it, then reacquire a fresh snapshot and use the focused active ref;
- browser_evaluate results may encode a JSON.stringify payload as a JSON string inside the MCP result; unwrap only bounded JSON string layers and still require the final value to be an object rather than weakening verification;
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
- service/MCP host processes may have no `USERPROFILE`/`APPDATA` even when HKCU `User Shell Folders` contains those tokens; prefer expanded `Shell Folders` or explicitly resolve known tokens from a registry-derived user home before writing;
- a launcher install is not verified until a host-context status probe shows an absolute real Desktop/Startup path with no unresolved `%...%` token.

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


## 2026-09-19 — Capability names are hints; tools/list is evidence

Origin:
- Stage 9 generic Add MCP productization and live Coding Tools/Serena discovery.

Protected lesson:
- do not infer MCP capability from server name, manifest role or a remembered tool set;
- validate initialize and inspect actual tools/list schema;
- preserve success/unavailable/failed/unattempted separately;
- derive routing recommendations from evidence, not labels.

## 2026-09-19 — Portable operating knowledge and machine state must split

Origin:
- Stage 9 needed reusable Guides without leaking local endpoints, bindings or health.

Protected lesson:
- portable Guide: mental model, exposed schema, usage patterns, verification, failures, performance and alternatives;
- machine-local inventory: endpoints, workspace/path bindings, listener/process state and transient availability;
- stable component ids attach the two layers without copying machine state into Git.

## 2026-09-19 — Onboarding must not become lifecycle ownership

Origin:
- newly applied components automatically become visible through the shared registry used by Manager/Doctor.

Protected lesson:
- visibility/discovery is not start/kill/restart authority;
- a new component enters Stage 8 lifecycle control only through an explicit fixed runtime adapter and ownership contract;
- Manager restart scope remains a fixed allowlist.

## 2026-09-19 — Binding and harness failures must stay classified

Origin:
- the Stage 9 Coding Tools connector was still bound away from the target repository, while the web Serena project activated but exposed no language server for semantic overview. Host/local MCP evidence remained usable.

Protected lesson:
- “not a Git repository” from a workspace-bound tool is binding evidence, not target-repository evidence;
- “no active language server” is not the same as Serena service unavailability;
- diagnose preferred-tool binding/session/schema first, then use the approved local/host fallback and record why;
- the user's rule to use local Serena when the web-connected Serena is unusable is a reusable fallback principle, not a one-off click recipe.

## 2026-09-19 — Shell syntax/quoting friction is harness evidence

Origin:
- Desktop Commander ran Windows PowerShell where `&&` was not accepted and a base64 Python write attempt failed from nested quoting.

Protected lesson:
- adapt commands to the actual shell instead of blaming the repository;
- prefer direct structured file-edit/write tools over complex nested quoting when repository-bound structured editing is unavailable;
- a failed write command is not a partial code mutation unless post-state proves otherwise.

## 2026-09-19 — Semantic readiness requires an actual semantic call

Origin:
- Stage 10 web Serena and direct local Serena MCP both reported `webgpt-as-codex` active and language-server status `ready`, but real `get_symbols_overview` returned `Active language servers: []`.

Protected lesson:
- config/session summaries are diagnostic evidence, not proof the intended capability works;
- verify the actual semantic operation before relying on Serena;
- distinguish reachable/configured, session-ready and semantic-call-capable states;
- after both web and approved local semantic paths reproduce the same backend failure, use the authorized repository/host fallback instead of looping on identical calls.

## 2026-09-19 — Exactly-once handoff requires a pre-submit boundary

Origin:
- earlier stages encountered hidden hydration composers, stale UI refs and tab ambiguity; a future transport error could also occur after ChatGPT receives the submit but before the MCP client receives success.

Protected lesson:
- tab/composer/ref recovery is allowed only while the prompt is still an unsent draft;
- type with submission disabled first;
- attempt the real send once;
- after that attempt, recover only by querying sent-message, conversation URL and assistant-run post-state;
- unresolved state is an ambiguous submission failure, never permission to press Enter again.

## 2026-09-19 — Closure reserve must be owned before implementation expands

Origin:
- Stage 8/9 repeatedly showed that implementation can finish while tests/docs/commit/handoff remain expensive tail work; Stage 10 itself reached the original ~20-minute soft target around implementation completion.

Protected lesson:
- stage duration is implementation plus closure, not implementation alone;
- reserve closure budget at planning time;
- projected implementation that consumes the reserve triggers a bounded split before tail work is endangered;
- when expansion has already happened, freeze scope and close rather than add more work;
- recalibrate from verified stage-cost evidence instead of claiming a fixed platform cutoff.

## 2026-09-19 — Extension-current can hide an already-created blank ChatGPT tab

Origin:
- Stage 10 first post-commit handoff failed before typing/submission.
- The Playwright extension Welcome page remained current while one blank ChatGPT tab already existed from the attempted new-tab action. A fresh MCP session could no longer prove that tab by before/after index difference.

Protected lesson:
- tab creation, extension focus and ChatGPT page focus are separate facts;
- set-difference is preferred evidence for the newly created tab;
- after one fresh tab-list retry, pre-submit recovery may reuse an existing target only when exactly one blank ChatGPT tab exists;
- multiple blank candidates remain ambiguous and must fail rather than guessing;
- this recovery is legal only before composer typing/submission; after submit is attempted, exactly-once post-state rules take over.

## 2026-09-19 — Loopback control needs browser-origin validation too

Origin:
- Stage 11 Manager hardening found that loopback bind + a custom control header did not independently constrain browser Host/Origin semantics.

Protected lesson:
- loopback binding is necessary but not sufficient for a browser-facing local control plane;
- validate loopback Host/port and same-origin Origin when present before reading action authority;
- fixed action names also need fixed payload schemas so extra URL/path/command fields cannot be smuggled through an otherwise safe executor;
- raw executor exception text is private-state leakage risk and should not cross the HTTP boundary.

## 2026-09-19 — Machine-local extension state is untrusted authority

Origin:
- Stage 11 reviewed Stage 9 custom MCP manifests and multi-file onboarding persistence.

Protected lesson:
- a machine-local custom manifest may extend visibility but must not shadow a repository component or inject executable/lifecycle authority;
- revalidate custom state on every load instead of trusting that only the official onboarding path could have written it;
- sanitize and bound remote schema/description text before persisting it into reusable local knowledge;
- logical multi-file applies should stage first and roll back partial replacements rather than leaving mixed-generation state.

## 2026-09-19 — Tool exposure drift is separate from repository health

Origin:
- Stage 11 began with Coding Tools successfully bound to WebGPT-as-Codex, then the connector functions disappeared from the active tool session while the local repository and tests remained healthy.

Protected lesson:
- treat connector/function disappearance as session or tool-exposure evidence first;
- verify the target repository independently before declaring the preferred MCP unavailable or the project broken;
- continue through the approved host fallback when the target post-state is independently verifiable, and record the tool switch as stage-cost evidence.

## 2026-09-19 — Source checkout success is not release-package proof

Origin:
- Stage 12 built and installed the baseline wheel in an isolated environment.
- The console entry point worked, but installed resource discovery returned zero built-in components and the Manager static page was absent because runtime code assumed repository-root sibling files.

Protected lesson:
- release gates must exercise the built/installed artifact, not only the source tree;
- explicitly declare non-Python runtime resources and test their installed lookup path;
- prefer a narrow source-or-installed resource resolver over copying machine-local state into the package;
- a successful wheel build, import or `--help` is not sufficient evidence that runtime resources were packaged.
