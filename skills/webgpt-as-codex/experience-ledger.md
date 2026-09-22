## 2026-09-20 — Release and local Agent Skill must share one portable core

Origin:
- the machine-local Computer Agent continued evolving after the public WebGPT-as-Codex Product Skill had already stabilized;
- both accumulated valuable but different operating knowledge, creating a risk that publishing either tree alone would silently discard the other half.

Protected lesson:
- keep one canonical portable Computer Agent release core and sync it to the machine-local Computer Agent;
- machine-specific environment/inventory/state remains an overlay and never becomes public release truth;
- keep the WebGPT-as-Codex product specialization as a sibling profile at the same Skill version rather than flattening away product-specific Doctor/Gateway/OAuth/Release knowledge;
- the Experience Ledger, reusable MCP Guides, evals and workflows are release assets, not disposable local notes;
- any portable rule/experience/eval/workflow change must close with release/local sync validation in the same iteration.

## 2026-09-20 — RDC online does not prove a live execution plane

Origin:
- Supplemental Final Acceptance Remote Desktop Commander recovery-plane incident.
- The device remained visible, authenticated and online while connector-side `ping` and `get_config` reported no live connection.

Protected lesson:
- model RDC installation, local process, control plane and execution plane separately;
- require a real execution probe before routing depends on RDC;
- if presence is tracked but broadcast transport capability registration failed, retry that capability registration rather than treating presence as sufficient;
- fixed validated runtime startup avoids `@latest` drift during recovery;
- keep session/auth secrets machine-local and never copy them into Git evidence;
- a healthy WebGPT plane may repair unhealthy RDC and healthy RDC may repair unhealthy WebGPT, but recovery has one active mutation owner and never recurses through an unhealthy plane.

## 2026-09-20 — Installed, latest and compatible are different facts

Origin:
- Stage 15 component lifecycle hardening and real existing-machine dry-runs.

Protected lesson:
- never use `package@latest --version` as proof of what is installed locally;
- model installed version, upstream latest and compatibility independently;
- newer compatible installs are preserve/no-downgrade;
- latest outside the verified compatibility window blocks mutation;
- upstream metadata failure remains unknown/blocking instead of becoming “already latest”;
- external install upgrade requires explicit adoption before WebGPT records install ownership.

## 2026-09-20 — Deployment discovery must outrank PATH/package absence

Origin:
- Stage 15 real deploy dry-run in a service-like Coding Tools environment.
- Serena/Coding Tools were live and healthy while uv/the corresponding package executable was not visible in that shell.

Protected lesson:
- do not infer “MCP absent” from PATH/package-manager evidence alone;
- listener/protocol/process truth can prove an existing service that must be preserved;
- fresh-machine installation and existing-machine preservation are different branches of the same deployment state machine;
- never create a duplicate instance merely to make package discovery look tidy.

## 2026-09-20 — Latest version and lifecycle authority are separate decisions

Origin:
- Stage 15 latest-stable resolution across PyPI/npm/GitHub Releases/winget.
- current Tailscale was healthy at 1.102.2 while winget reported 1.102.4.

Protected lesson:
- latest stable is useful deployment evidence, not automatic permission to mutate an actively used external service;
- WebGPT-installed ownership is durable machine-local evidence, but runtime stop/restart authority stays separate;
- GitHub binary upgrades require expected upstream/asset identity plus release SHA-256;
- version strings from different package/server/product domains are not automatically comparable.

## 2026-09-20 — Latest metadata cache is bounded evidence, not truth substitution

Origin:
- Stage 15 first resolved official GitHub release metadata successfully, then reproduced transient GitHub HTTP errors during a later strict dry-run.

Protected lesson:
- registry/API availability and target component health are separate states;
- never reinstall/restart a healthy component because latest metadata is temporarily unavailable;
- persist successful latest metadata only machine-locally and only with a bounded freshness window;
- GitHub cache entries must retain validated repository asset URL/name/SHA-256 evidence;
- cached metadata must be labeled non-fresh and may inform diagnosis/compatibility display but must never authorize install/upgrade;
- a fresh machine without current online evidence remains fail-closed.

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

## 2026-09-20 — Unified Gateway route sync must preserve identical registrations

Origin:
- Supplemental Stage 14 productionization.
- The first route-sync draft used MCPJungle `register --force` on every Edge start.

Protected lesson:
- query the private Gateway registry before mutation;
- same route identity + transport + URL is a preserve operation, not an update;
- force replacement is justified only when a same-name route actually changed;
- route ownership does not imply lifecycle ownership of the upstream MCP;
- verify the aggregated MCP surface after synchronization rather than inferring success from a registry CLI exit code.

## 2026-09-20 — Production OAuth Edge requires restart continuity, not only first-login success

Origin:
- Supplemental Stage 14 real production Edge acceptance.

Protected lesson:
- production OAuth credentials and OAuth database are explicit machine-local runtime state, separate from integration-test credentials;
- real HTTPS remains the authority for metadata, DCR/PKCE/token and authenticated MCP behavior;
- acceptance includes an unauthenticated 401 gate;
- restart the owned Edge through the Runtime Supervisor, then prove an existing refresh token still works and the unified MCP tool surface remains stable;
- do not restart routed external MCP backends merely because the Edge restarts.

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

## 2026-09-19 — Browser tab lists can repeat the same tab inventory

Origin:
- the first Stage 12 post-commit handoff failed before typing or submission even though one blank ChatGPT tab had been created;
- current Playwright `browser_tabs` output repeated the same indexed rows under both `### Result` and `### Open tabs`, so the handoff parser counted one physical tab twice and falsely reported ambiguity.

Protected lesson:
- tab identity is the indexed browser tab, not the number of textual row occurrences in a tool response;
- normalize exact duplicate tab rows before set-difference/unique-blank reasoning;
- keep true conflicting duplicate indexes ambiguous rather than guessing;
- a pre-submit false ambiguity is recoverable after fixing the evidence parser because no external send side effect occurred.

## 2026-09-19 — Final acceptance must separate build-harness failure from release failure

Origin:
- Final Overall Acceptance first attempted a no-build-isolation wheel build with the repository development venv.
- That caller venv did not contain setuptools, so the build backend could not load even though the repository tests were green.
- Re-running the same source build with normal isolated build dependencies succeeded, and the resulting wheel passed installed-layout verification.

Protected lesson:
- a missing caller-side build backend is harness evidence until the source can be rebuilt through the declared build-system contract;
- do not weaken or skip installed-artifact verification after a harness failure;
- final acceptance should verify the installed resource root, public manifests, static UI and representative control surfaces from outside the source checkout;
- when an acceptance probe itself fails from a parsing assumption, verify the returned product data before classifying it as a target defect.

## 2026-09-20 — Process mutation timeout needs a bounded observation window

Origin:
- Stage 16 launched an isolated fixed-project Serena server on a non-shared loopback port and verified MCP initialize plus `tools/list`.
- the existing Windows bounded-stop helper reported a shutdown timeout while the isolated Serena process disappeared shortly afterwards;
- repeating an immediate stop/kill would have created an unnecessary second side effect.

Protected lesson:
- timeout/non-zero after stop/restart/kill is an ambiguous mutation result, not proof that the mutation failed;
- query listener and PID birth/image identity repeatedly for a bounded observation window before considering another destructive action;
- if the original process is already gone or the target is healthy, close from post-state and do not retry;
- only a still-live matching identity plus current lifecycle authority can justify the next mutation attempt;
- preserve shared services while probing isolated workers: Stage 16 never switched or restarted the user's shared Serena 9121 instance.

## 2026-09-20 — Bilingual Manager parity should share behavior, not duplicate it

Origin:
- Stage 17 inherited package/test WIP that referenced a Chinese Manager asset which did not yet exist;
- duplicating the old self-contained English page would have created two independent JavaScript action implementations and a long-term parity risk.

Protected lesson:
- use language-specific HTML shells only for readable copy while sharing one JavaScript/API/action contract and one stylesheet when no build framework is required;
- test parity at the functional surface (routes, controls, sections, mutation count, API endpoints and DOM accessibility), not only by asserting that both files exist;
- package/install validation must exercise every shared static dependency from outside the source checkout.

## 2026-09-20 — A live listener can still be a stale runtime generation

Origin:
- Stage 17 post-acceptance desktop testing found the production 9200 Manager process predated the Stage 17 implementation while continuing to read the newer HTML file from disk.
- the result was a mixed generation: `/` returned the new HTML shell but the old route table returned 404 for `/en`, `/zh`, `/manager.css`, `/manager.js` and `/api/local-config`.

Protected lesson:
- process/listener/healthz evidence proves liveness, not that a long-running interpreter loaded the current code generation;
- pair lifecycle ownership and PID birth/image identity with a current runtime-generation marker and key capability/resource contract;
- strict legacy-product identity can justify one bounded stale refresh, but a same-port unrelated/ambiguous listener remains protected;
- Windows venv launchers may introduce a parent launcher plus a different real listener PID, so the ownership receipt must follow the listening process while retaining bounded parent-cleanup identity.

## 2026-09-20 — User desktop browser opening is not browser automation

Origin:
- the user reported that the one-click Manager launcher opened an empty Edge experience without the expected logged-in state.
- real host acceptance showed one normal Edge profile (`Default`) already in use.

Protected lesson:
- keep a user-facing desktop URL opener independent from Playwright standalone/isolated profile creation;
- if the normal browser is already running, explicitly reuse its current normal profile; if not, use the operating system's normal URL-handler path;
- never default a desktop Manager launcher to temp user-data-dir, InPrivate or automation-only profiles;
- verify the real host path by comparing browser top-level process/profile state before and after launch, not merely by asserting that an `open()` call returned success.

## 2026-09-20 — Managed launcher upgrades need stronger ownership than a marker and weaker identity than exact bytes

Origin:
- adding the Chinese default environment line caused the real previously managed Stage8 launcher to fail exact-content ownership checks;
- the old launcher also pointed at an earlier workspace Python path, so comparing against a newly generated historical string was insufficient.

Protected lesson:
- exact current bytes are the strongest current ownership proof, but known previous managed versions may be recognized by a complete historical command structure;
- require the WebGPT marker, a Python/pythonw executable shape, exact module entry point and fixed historical flags with no additional commands;
- do not treat the marker alone as ownership and never overwrite arbitrary/user-owned launcher content;
- verify the real Desktop/Startup post-state after upgrade without launching or closing unrelated user windows.

## 2026-09-20 — Explicit local secret reveal must stay outside normal status and activity

Origin:
- Stage 17 needed local OAuth password set/reveal/regenerate controls while the Manager already had a public-safe status contract;
- the inherited generate WIP called an ensure helper and therefore reused an existing value instead of actually regenerating it.

Protected lesson:
- status should expose configured/not-configured state, never the plaintext secret or secret path;
- Reveal may return plaintext only in the explicit loopback/confirmed response and must not be copied into the activity log;
- Set and Regenerate should return post-state booleans/restart requirements rather than echoing the value;
- tests must prove Regenerate changes a disposable value and prove neither old nor new value appears in activity evidence.

## 2026-09-20 — Repository-wide translation needs classification, not extension-based bulk rewriting

Origin:
- Stage 18 repository-wide Chinese mirror work;
- the tracked tree contains human documentation, historical closure evidence,
  protocol/config JSON, source/tests/scripts and shared bilingual Manager code
  in the same text-like formats.

Protected lesson:
- audit every text-format candidate, but classify before translating;
- current reader-facing sources need deterministic mirrors, while protocol
  identifiers, schema keys, commands, URLs and hashes remain exact;
- historical closure/prompt/evidence should keep one canonical original and use
  an explicit translated index/treatment rather than silently rewriting history;
- turn the classification into a machine-readable regression gate so future
  additions cannot disappear from the language audit.

## 2026-09-20 — Legal translations must not become a second license authority

Origin:
- Stage 18 required Chinese access to the Apache-2.0 license while preserving
  the existing legal file.

Protected lesson:
- preserve the authoritative license bytes and record a stable digest;
- put a reading translation in a separate file with an unmistakable
  non-binding/non-official disclaimer;
- state that the original language controls every discrepancy;
- package both only when the installed artifact needs public legal context.

## 2026-09-20 — Third-party provenance is wider than the external-service inventory

Origin:
- the pre-Stage18 `THIRD_PARTY_NOTICES.md` covered the eight integrated MCP /
  transport components but did not enumerate the Python build/runtime/dev
  dependencies declared in `pyproject.toml`.

Protected lesson:
- reconcile notices from every repository dependency authority relevant to the
  release, not only the component registry;
- keep manifest/package declarations machine-readable and test them against the
  notice/provenance record;
- never invent or paste an upstream license from memory when repository/upstream
  metadata can identify the provenance boundary; the redistributed upstream
  artifact's own license/NOTICE remains authoritative.

## 2026-09-20 — Child-process liveness must not satisfy wrapper readiness

Origin:
- Stage 19 real recovery after an OAuth Edge restart left the child OAuth proxy on 9340 alive while the repository compatibility edge on 9341 was absent;
- discovery looked only at the component manifest endpoint and incorrectly reported Start All `fully_ready=true`.

Protected lesson:
- define readiness at the product/runtime boundary, not whichever child port happens to answer;
- for repository-managed wrappers, Start All must consult the managed RuntimeSpec/contract before declaring ready;
- a surviving child can be reused only after strict identity/issuer validation;
- `port alive != correct generation != complete runtime contract`.

## 2026-09-20 — Self-restart needs an independent repair plane

Origin:
- the production OAuth E2E restarted the same WebGPT Edge carrying the current ChatGPT tool session;
- the runtime recovered, but the control session could disappear during the restart.

Protected lesson:
- never require a runtime-plane connector to be the only mechanism that restarts itself;
- use an independent local Agent/RDC repair plane for restart + post-state evidence;
- reacquire MCP/browser session references after restart;
- once the user confirms a real external connector is configured successfully, freeze disruptive acceptance and prefer read-only verification unless a real defect requires mutation.

## 2026-09-22 — Connector session churn can hide still-live ChatGPT pages

Origin:
- During a real Loop Engineering handoff, `browser_tabs new` successfully opened `https://chatgpt.com/`, but the next connector call listed only the Extension Welcome page.
- Directly connecting to the local Playwright Streamable HTTP endpoint and keeping one `mcp-session-id` across `initialize -> tabs list -> tabs new -> tabs list` proved the ChatGPT page remained alive.
- A persistent Playwright context later exposed multiple ChatGPT pages created by recovery attempts; Windows-MCP showed that one page already contained the full handoff prompt but had not yet been submitted.

Protected lesson:
- browser page lifetime and connector/MCP-session visibility are different state dimensions; a new connector session can lose page observability without closing the real page;
- after `new` succeeds, a later Welcome-only view is `OBSERVER_SESSION_CHURN` until proven otherwise, not permission to open more tabs;
- session-scoped handoff must use one persistent `mcp-session-id`, the canonical handoff helper, or one persistent-context call for target discovery, fill, exactly-once submit and verification;
- before retrying, enumerate existing pages and inspect composer/URL post-state; if a full unsent prompt already exists, reuse that page and do not duplicate the prompt;
- after successful handoff, clean up only blank/duplicate tabs that are provably owned by the current Agent; preserve the user's pre-existing tabs and the accepted conversation.

## 2026-09-22 — Handoff rules need a programmatic transaction owner

Origin:
- The 1.3.1 Skill was actually loaded and already documented same-session Playwright, observer-session churn and duplicate-tab rules, but recovery still used direct connector calls outside the canonical helper. The rules therefore did not prevent a second mutation path from opening candidate tabs.
- The user later clarified that they had manually closed the handoff tab. A missing tab is therefore not evidence that submit failed, and a recovery system that only trusts live tab presence can accidentally resend work that already crossed the side-effect boundary.
- The existing helper's generic submitted predicate accepted any `/c/` page with at least one user message and an empty composer; resume mode could therefore mistake an unrelated conversation for the target handoff without proving exact prompt identity.

Protected lesson:
- a behavioral instruction is not enough for an exactly-once side effect; handoff needs one programmatic mutation owner and a durable transaction identity;
- bind the transaction to the full whitespace-normalized prompt SHA-256 and compare the exact last-user-message hash before treating a conversation as the target;
- before creating a new page, recover an exact-hash submitted message or unsent draft if one already exists; ambiguous duplicates fail closed;
- write a machine-local `SUBMIT_ATTEMPTED` receipt immediately before invoking any real submit primitive, then upgrade it to `SUBMITTED` only after exact submit is proven and to `HANDOFF_OK` only after takeover is observed; this write-ahead boundary covers a crash/connection-loss window between the side effect and its post-state confirmation;
- once `SUBMITTED` exists, user tab closure, connector failure or missing live browser state cannot authorize another submit; recovery is read-only verification against the receipt's conversation URL;
- direct connector/Windows GUI may diagnose a helper failure, but cannot become a parallel mutation owner for the same transaction.
