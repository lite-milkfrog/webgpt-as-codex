# Decisions and Risks

[**English**](DECISIONS-AND-RISKS.md) | [简体中文](zh-CN/DECISIONS-AND-RISKS.md)

## Stage 5 — OAuth/Tailscale edge

### Decision: one public MCP endpoint
Only the unified Gateway path is published for the self-hosted stack.
Individual core MCP backends remain loopback/private.

### Decision: preserve an OAuth compatibility adapter
The current verified mcp-auth-proxy flow needs correct forwarded HTTPS host/proto semantics and consent-session continuity.
The adapter is generic project code; no machine secret or public hostname is embedded.

### Decision: final OAuth acceptance must use real HTTPS
Local HTTP localization can distort Secure-cookie behavior.
The authoritative Stage 5 gate runs DCR, PKCE, login/consent, token, refresh and MCP calls through a temporary real Tailscale Funnel HTTPS endpoint.

### Risk: upstream OAuth behavior may change
The compatibility adapter is isolated behind a small boundary and must be revalidated when mcp-auth-proxy changes.
Doctor must report OAuth metadata/DCR/PKCE/refresh separately so a future upstream change is diagnosable.

### Risk: hosted Tailscale availability
Tailscale Funnel is an edge adapter, not a repository security boundary.
The core local stack remains useful without public Funnel availability.

## Cross-stage decision — recursive verified handoff

Automatic continuation is a project invariant, not a one-time permission.
Every stage closure must:
- commit first;
- generate the next prompt from that committed HEAD;
- carry CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE;
- include the recursive continuation invariant;
- validate + hash the prompt;
- Playwright-submit the exact prompt in one MCP session;
- verify sent-message SOURCE_HEAD + assistant run + /c/ conversation URL;
- require the receiving window to repeat the same protocol.

The chain terminates only after the planned final stage and Final Overall Acceptance are both closed.

## Cross-stage decision — self-evolving Skill and operating knowledge

Execution is not complete merely because the immediate task worked. Reusable friction must be diagnosed, verified and written back at the narrowest durable layer: general principles to the Skill, MCP-specific behavior to an Operating Guide, machine facts to local inventory/config, and one-off evidence only to the relevant stage/ledger.

Routing and operating knowledge remain distinct. Routing selects the narrowest appropriate capability. An MCP Guide is based on actual exposed schema/capability evidence and teaches correct goal-oriented usage, verification, common misuse and justified fallback. Tool names are never treated as proof of capability.

User guidance is reusable evidence when it exposes a stable operating principle. It does not become a brittle click recipe by default; record the mental model, goal, constraints, verification and failure signals.

### Decision: stage sizing protects closure
The current target is an approximately 20-minute soft stage budget with closure included. This is a planning heuristic derived from observed workflow continuity needs, not a claimed 25-minute platform cutoff. A shorter fully closed stage is preferable to a larger stage that ends before docs/commit/handoff verification.

Collect baseline data over the next 5-10 stages: implementation versus closure effort, files/tests changed, major tool switches/calls, retries/harness failures, docs effort, first-pass handoff success, almost-done incidents and emergency splits. Recalibrate from evidence.

### Risk: self-improvement can bloat or overfit the Skill
Do not append every incident to core rules. Merge duplicates, retire obsolete methods with provenance, move machine details out of portable docs and keep detailed MCP-specific behavior in Guides. Optimize for the fastest known safe/reliable/low-context path without weakening verification.

## Stage 6 — Manager control plane

### Decision: reference Manager is evidence, not source
The existing service on `127.0.0.1:9199` was inspected read-only. Its machine-specific service inventory, external addresses, local authentication state and recovery implementation were not copied into the repository.

### Decision: shallow polling, deep Doctor evidence
Manager polling is cached and limited to inexpensive discovery/listener evidence. Protocol initialize, tools/list, safe-call, OAuth and remote checks remain distinct and are supplied by the durable last-Doctor result. This preserves diagnostic fidelity without creating a continuous performance tax.

### Decision: action contracts precede action executors
Stage 6 exposes a fixed allowlist for Start All, Restart, Doctor, Repair and Update but ships with no real executor wired. Later owner stages inject the bounded implementations. This prevents Stage 6 from acquiring arbitrary shell authority or restarting healthy production-like services.

### Risk: stale Doctor evidence
Protocol/OAuth/remote fields may be unknown or stale until Stage 7 writes a fresh Doctor result. The UI must display unknown separately from failed and must never infer protocol health from a listener.

### Risk: workspace binding drift
The shared Coding Tools service was bound to a different repository during Stage 6. Repository writes were therefore moved into a dedicated Git worktree inside the Coding Tools workspace rather than bypassing its path boundary. Future windows must verify workspace binding before writes.

## Stage 7 — Bootstrap / Doctor / Repair

### Decision: bootstrap discovers before it mutates
Bootstrap preserves an already healthy listener and never treats “installed” as permission to restart it. Stage 7 apply is limited to creating/verifying machine-local state directories and persisting the plan. Runtime start/restart remains Stage 8 ownership.

### Decision: health evidence is prerequisite-aware
Process, listener, protocol, safe-call, OAuth and remote are stored independently. Protocol is attempted only after a listener is present; safe-call only after protocol succeeds; OAuth metadata only when its local listener is present; remote only when a valid credential-free public HTTPS endpoint is configured. Unattempted deeper checks remain unknown rather than becoming cascaded failures.

### Decision: Doctor is read-only with respect to OAuth authority
The normal Doctor checks OAuth metadata locally and may probe the configured real HTTPS edge for protected-resource metadata plus the expected unauthenticated 401 challenge. It does not create clients/tokens or mutate OAuth state. Full DCR/PKCE/consent/token/refresh acceptance remains an explicit real-HTTPS integration gate.

### Decision: bounded Repair has no shell surface
Repair accepts only named repository-defined actions. Apply requires explicit confirmation. Manager configuration repairs back up the original machine-local file before replacement/edit. Runtime failures produce targeted hints instead of generic command execution.

### Risk: version probes can lie if arbitrary banner text is parsed
Doctor accepts explicit version-labelled or exact-semver command output and otherwise falls back to verified manifest evidence. This prevents dotted addresses or banner decoration from being reported as versions.

### Risk: live Doctor can correctly be red while the Stage is green
A machine may intentionally have Gateway/OAuth runtime listeners stopped. Stage 7 closure means the diagnostic/bootstrap/repair contracts are verified, not that Stage 7 silently starts later-stage runtimes. Stage 8 owns bringing repository-managed services up.

### Risk: test environment can import the wrong editable worktree
The shared virtual environment points at the canonical repository. Stage 7 tests in the Coding Tools worktree therefore used an explicit worktree `PYTHONPATH`. A missing pytest/module import in the harness is not target-code evidence.

## Stage 8 — Runtime supervisor / launcher / autostart

### Decision: lifecycle ownership requires repository evidence, not process discovery
Finding a matching listener/process is sufficient to preserve a healthy service but not sufficient to stop or restart it. Stage 8 requires a fixed runtime adapter plus a machine-local PID receipt validated against the live process birth token and executable image. PID reuse/stale receipts therefore fail closed.

### Decision: Start All is discovery-first and may be partially ready
Start All preserves healthy listeners and process-only system services before considering starts. It starts only repository-owned missing adapters and reports required-but-unmanaged missing components separately from action success. This prevents a successful MCPJungle start from being mislabeled as proof that the whole OAuth/edge stack is ready.

### Decision: do not promote Stage 5 E2E credentials into autostart authority
The machine contains an mcp-auth-proxy binary and Stage 5 E2E OAuth data, but no separate credential-safe production runtime contract. Stage 8 therefore leaves the stopped proxy unmanaged rather than embedding/reusing a test password, OAuth DB or private key. A later owner may add an explicit credential-reference/config contract with its own security evidence.

### Decision: Manager Restart is narrower than component discovery
The Manager accepts only a named component from a repository-fixed restart allowlist; Stage 8 currently allows MCPJungle. It does not accept arbitrary shell, PID, executable, URL or argv input. Healthy unmanaged components such as Serena cannot be restarted through this action.

### Decision: Windows Startup folder is the bounded autostart mechanism
The project uses a transparent user Startup-folder `.cmd` launcher rather than hidden registry persistence, scheduled tasks or credential-bearing scripts. Install/status/uninstall verify exact managed content (newline-insensitive for Windows text normalization) and refuse to overwrite/delete user-owned files. Windows shell-folder lookup must also work in service/MCP contexts where `USERPROFILE` and `APPDATA` are missing, so it prefers expanded `Shell Folders` registry values and rejects unresolved relative token paths in favor of a known user-home fallback.

### Risk: graceful shutdown is component-dependent
The supervisor first attempts a bounded graceful signal and then applies a bounded forced fallback. Live MCPJungle evidence on Windows required the forced fallback after the graceful window. This is recorded as runtime behavior, not hidden by reporting restart as intrinsically graceful.

### Risk: process evidence is not protocol evidence
Process-only preservation is used only to decide “do not start/kill this unmanaged system service.” It does not promote Tailscale or any MCP to protocol/OAuth/remote health; Doctor continues to own those deeper evidence levels.


## Stage 9 — Generic Add MCP / Operating Guides

### Decision: capability discovery precedes routing

Generic onboarding must use real MCP initialize + tools/list evidence. Server names, manifest roles and tool names are hints only. A routing recommendation may be created only from actual schema evidence and remains reviewable rather than silently rewriting Skill routing.

### Decision: unavailable, failed and unattempted remain distinct

An unreachable listener/session is `unavailable`; malformed reached protocol/schema evidence is `failed`; an intentionally skipped/non-applicable probe is `unattempted`. These states are preserved in the Operating Guide and local onboarding receipt instead of being collapsed into a single false value.

### Decision: dry-run is the default; mutation is explicit and machine-local

`add-mcp` performs discovery and Guide/routing planning without persistence by default. `--apply` is required to create a custom component. Applied custom manifests, machine-readable Guides and routing/inventory receipts stay in the external state directory. Repeated application of the same manifest is idempotent; the same id with different content fails closed; custom components cannot shadow repository component ids.

### Decision: Operating Guides are portable knowledge, not inventory

A Guide contains reusable mental model, actual exposed tool/schema facts, usage patterns, mistakes, diagnostics, verification, performance/cost notes, accumulated lessons and alternatives. Endpoints, local paths, workspace bindings, PID/process state, transient health and secrets stay machine-local. Public component manifests may attach a portable Guide by stable component id.

### Decision: onboarding visibility does not grant lifecycle authority

The existing registry makes applied components visible to Manager and Doctor. Stage 9 does not add runtime adapters, arbitrary command surfaces or Manager restart entries. Stage 8 ownership remains authoritative.

### Risk: exposed tool schemas can themselves mention credentials

A schema may legitimately describe fields named token/password without containing a secret. Secret scanning therefore rejects credential-bearing literal values while allowing schema structure that merely describes such fields. Persisted Guides are validated again before write.

### Live evidence

Stage 9 real discovery observed current local Coding Tools initialize/tools/list success with 18 tools and local Serena success with 29 tools. This is stage evidence, not portable availability truth. The earlier Stage 8 Serena-down observation is therefore health drift rather than a contradiction of Stage 8 ownership behavior.

## Stage 10 — Loop Engineering dogfood

### Decision: closure budget is explicit and evidence-driven
The approximately 20-minute stage target remains a heuristic. Stage 10 makes closure reserve explicit and recalibrates only after at least three verified, non-split, first-pass-handoff records. Total effort is bounded to a 15-25 minute planning range and closure share to 25-55% so a small sample cannot create extreme sizing rules.

### Decision: chat context is not execution state
A stage keeps machine-local durable closure state outside Git. Phase is monotonic within one closure attempt; commit-time contradictory evidence may explicitly reopen the minimum affected boundary, invalidating stale prompt/handoff state while preserving stage pointers, evidence history and reopen provenance. Repository SoT remains authoritative for stage definition and closure.

### Decision: prompt plans are durable, SOURCE_HEAD is late-bound
The next-stage plan may be committed before closure, but SOURCE_HEAD is injected only after the current stage commit. Prompt validation checks CURRENT/NEXT/AFTER_NEXT/SOURCE_HEAD before hashing and browser submission.

### Decision: handoff preparation is retryable; submission is exactly-once
Hidden hydration, stale refs and tab-selection ambiguity are pre-submit failures and may be recovered with fresh evidence. Once the external send action is attempted, no second send is allowed. Lost/ambiguous tool responses are resolved by querying sent-message, /c/ URL and assistant-run post-state; unresolved ambiguity fails closed.

### Risk: stage-cost evidence can become fake precision
Do not infer a platform timeout from a few stages or invent duration data. Use measured/observed effort when available, preserve unknowns, and recalibrate only from verified baseline records. Detailed machine/session facts stay outside portable evidence.

### Live dogfood evidence
Stage 10 again found Coding Tools bound to a different workspace. Serena web and local MCP configuration both reported the target project and a ready language-server state, while the actual semantic `get_symbols_overview` call returned no active language servers. This proves configuration summaries are not semantic-capability proof and justified repository/host fallback without changing the portable routing role.

## Stage 11 — Security / reliability hardening

### Decision: Manager Update is repository-approved, offline-by-default authority
The Stage 11 Update executor is not a downloader or shell. Manager may select only a fixed updateable component id. The repository must predeclare the release version, same-upstream release URL, artifact name, SHA-256 and bounded machine-binary destination. Execution consumes only an already staged machine-local artifact, verifies the digest before and after replacement, refuses a running/owned runtime, creates a backup when replacing an existing binary, and is idempotent when the verified destination is already current. With no repository-approved update entry, Update reports `no-approved-update` and performs no mutation.

### Decision: machine-local configuration is untrusted input
Custom MCP manifests are revalidated on every registry load. They cannot shadow built-in ids, inject version/lifecycle command fields, or gain a safe-call tool without repository review. Malformed custom entries are isolated rather than breaking built-in registry availability. External tools/list descriptions and schema strings are recursively sanitized and bounded before machine-local Guide persistence.

### Decision: durable state writes fail closed
Bootstrap, Doctor, Repair, Runtime PID/state, Loop state and Playwright handoff receipts use temporary-file + fsync + atomic replace. Multi-file onboarding apply stages all outputs before replacement and rolls back already replaced files if a later replacement fails within the process. Partial state is not accepted as valid durable truth.

### Risk: local control surfaces are vulnerable to browser-origin confusion without Host/Origin checks
Loopback binding alone does not prove a browser request originated from the local Manager page. Stage 11 therefore validates loopback Host/port and, when present, same-origin HTTP Origin in addition to the control header. Unsupported action payload fields fail before executor invocation, and executor exceptions return sanitized failure classes rather than exception text.

### Risk: connector/tool exposure can drift independently of target health
During Stage 11 the web Coding Tools functions disappeared after earlier successful repository binding. The repository HEAD and working tree remained reachable and all gates were completed through Desktop Commander. Treat tool exposure/session drift as harness evidence until target post-state contradicts it.

## Stage 12 — README / release / final-acceptance preparation

### Decision: release verification must exercise an installed artifact
A source checkout can hide packaging defects because repository-root resources are still present. Stage 12 therefore treats wheel build + isolated install + representative CLI/resource probes as a required release-facing gate in addition to unit tests.

### Decision: installed runtime resources are explicit and minimal
The release wheel includes only public component manifests and the Manager static UI as non-Python runtime data. Installed code resolves those resources from a dedicated `share/webgpt-as-codex` tree when a source checkout is absent. Stage documentation, prompt plans, Skill source, machine-local state and handoff receipts are not wheel runtime data.

### Risk resolved: source-layout assumptions can create a false-green release
The Stage 12 baseline wheel installed successfully and exposed the console entry point, but `load_components()` returned zero built-ins and the Manager static page path did not exist because `repo_root()` pointed into the installed environment. The minimum release boundary was reopened, resource packaging/path resolution was corrected, and an isolated rebuilt wheel then loaded all eight built-in component manifests and the Manager UI.

## Stage 17 — bilingual Manager / desktop UX

### Decision: language parity shares one functional implementation
English and Chinese Manager pages are language shells over the same packaged JavaScript/CSS and the same loopback API contracts. This avoids duplicated action logic and makes parity testable from shared element/action surfaces. No framework/build-chain dependency was added for the static Manager.

### Decision: explicit local secret control is separate from status
The normal local-config/status surfaces expose only whether an OAuth password is configured. Reveal/set/regenerate remain explicit confirmed loopback mutations. Regenerate always creates a fresh value; reveal plaintext is returned only to the requesting local response and is excluded from activity records, docs and tracked evidence.

### Decision: Manager migration visibility does not create authority
Adding/removing a custom MCP candidate only mutates the validated machine-local registry. The response explicitly reports `route_applied=false` and `lifecycle_authority=false`. Built-in component deletion is blocked. Stage 14 route ownership and Stage 8/16 lifecycle/recovery ownership therefore remain authoritative.

### Risk resolved: exact-content launcher ownership can strand a managed older version
Adding the Chinese default line changed the expected managed launcher bytes, so the previously installed Stage8 launcher initially appeared unmanaged. Stage 17 recognizes only the complete known historical WebGPT launcher structure (marker + Python executable + fixed module/flags) as upgradeable. This permits a safe in-place managed upgrade across workspace-path changes while still refusing arbitrary marker-bearing or user-owned files.

### Risk: local mutation timeout can tempt duplicate side effects
Manager local mutations are serialized and the UI disables mutation controls while a request is pending. Process shutdown evidence continues to follow Stage16 R49: timeout/non-zero is ambiguous until listener plus PID identity are observed for a bounded window. Stage17 applied that rule to its disposable host probe rather than inventing a second stop.

## Final Overall Acceptance

### Decision: final acceptance requires both source-tree and installed-artifact evidence
The final gate does not treat a green import, listener, build command or source-tree test suite as sufficient release evidence. Acceptance requires the complete repository gates plus a freshly built wheel installed outside the source checkout, with metadata, console entry point, public runtime resources and representative loopback Manager surfaces exercised from that installed layout.

### Decision: transient MCP/session drift is not a release blocker without target contradiction
The final window observed Serena connector unavailability and an initial Coding Tools workspace mismatch. The target repository remained independently verifiable, and Coding Tools was used only after a Git worktree inside its authorized workspace reported the expected repository HEAD. These are harness/binding observations, not reasons to weaken the product gates or reopen closed ownership.

### Result: no unresolved release, security or ownership blocker
The accepted release preserves the documented boundaries for OAuth/edge, runtime lifecycle ownership, generic Add MCP visibility versus authority, durable Loop Engineering, exactly-once handoff and Stage 11 trust/mutation hardening. The installed artifact loads all eight public component manifests and Manager UI, and the Manager still exposes only the fixed action contract set. No contradictory final evidence requires reopening Stages 0-12.

### Residual risk: external service health can drift after acceptance
Serena, Coding Tools, Playwright, Windows-MCP, Tailscale and other external/runtime services can change independently of repository correctness. PROJECT-COMPLETE and TERMINAL must not reinterpret later listener/session drift as retroactive acceptance failure unless it produces repository-owned contradictory evidence.

## Supplemental chain — one-repository deployment / Gateway / concurrency

### Decision: the repository is the single deployment authority

Users and Agents start from WebGPT-as-Codex. Third-party source trees do not need to be vendored wholesale; component manifests plus installer/provision/version/health adapters are the reproducibility boundary. Existing healthy installations are detected and preserved, while missing components are installed from approved official sources.

### Decision: latest-stable intent needs a compatibility gate

Deployment should target the latest stable upstream release, but `latest` is not treated as proof of compatibility. The component adapter records upstream/latest evidence, validates source/provenance, installs or stages the candidate, runs the component's compatibility health contract and only then promotes it to verified/current state. Already-newer compatible installations are not downgraded.

### Decision: route ownership is separate from lifecycle ownership

WebGPT may register an existing localhost MCP into MCPJungle without changing that MCP's own launch configuration. Stop/restart authority requires separate WebGPT ownership evidence. This enables gradual migration without breaking currently used services.

### Decision: Remote Desktop Commander and Unified Gateway are complementary

Neither replaces the other. The Unified Gateway is the structured MCP path; Remote Desktop Commander is an independent host rescue/control path. Agent routing may use one to recover the other only after classifying the failure layer and only through bounded recovery authority.

### Decision: one Serena MCP process is not a multi-project parallel slot

Installed Serena source confirms one `SerenaAgent` has one process-wide `_active_project`; activating a different project shuts down the previous active project. Its read-only ProjectServer explicitly protects this process-wide state with an active-project lock. A shared mutable Serena server therefore cannot safely represent different projects for concurrent ChatGPT conversations. Stage 16 owns fixed-project instance pooling/project-slot routing rather than papering over this conflict.

### Decision: Coding Tools parallelism is bounded by workspace/write ownership, not by a one-call global model

Live evidence showed multiple server-managed commands can have overlapping execution intervals. The server is nevertheless configured with one workspace. Independent read/process work may overlap, while concurrent writers must use separate worktrees/workspaces or a one-writer lease. This distinction becomes explicit in Stage 16.

### Risk: automatic deployment can duplicate a healthy service

PATH/package absence is not sufficient evidence that an MCP is absent. Discovery must check listener/protocol/process/known install evidence before install. If a healthy service is already reachable, bootstrap preserves it instead of creating a second instance.

### Risk: a new machine may have no Tailscale or no account session

Tailscale is now an explicit environment gate. Installation may be automated from the allowlisted official package; account login/approval remains an interactive boundary when required. Public-edge success is blocked until online/MagicDNS/Funnel evidence exists.

### Risk: fresh-machine binary bootstrap becomes an unbounded downloader

WebGPT-owned MCPJungle/mcp-auth-proxy bootstrap uses repository-approved official release origins and SHA-256 verification. Existing binaries are preserved by default. Stage 15 may add latest-stable resolution, but source-origin and compatibility validation remain mandatory.

## Stage 17 post-acceptance hotfix — runtime generation / desktop browser continuity

### Decision: listener health is not runtime-generation proof

A long-running Python Manager may continue serving a live listener and shallow health endpoint while retaining an older route table and reading newer static files from disk. Manager preservation therefore requires lifecycle identity plus runtime-generation/resource-contract evidence. A stale process is refreshed only when it is repository-owned or matches the strict legacy WebGPT Manager identity. An unrelated/ambiguous process on 9200 is never terminated.

### Decision: ownership follows the real listener, not only the venv launch wrapper

On Windows a venv `pythonw.exe` launch may create a child base-Python process that becomes the actual listener. The machine-local receipt rebinds to the listener PID/birth/image while retaining the launcher PID identity only for bounded cleanup. This avoids treating a living parent wrapper as the service identity.

### Decision: desktop browser continuity is separate from Playwright profile lifecycle

The one-click desktop Manager opener is ordinary user browsing, not a Playwright automation session. If Edge is already running, WebGPT reuses the last-used normal profile; otherwise it uses the Windows default URL handler. The desktop launcher must not create a temporary user-data directory, InPrivate session or automation-only blank profile.

### Live acceptance

The real stale 9200 Manager was safely replaced after strict identity/contract proof. `/`, `/en`, `/zh`, `/manager.css`, `/manager.js` and `/api/local-config` then returned the current Stage 17 contract. Two consecutive Desktop launches preserved the same core MCP/Gateway/Manager listeners and the same existing Edge `Default` top-level process, while Windows-MCP observed the complete Manager control tree.

## Stage 16 — concurrency / session isolation / complementary recovery

### Decision: concurrency authority is explicit per shared state

Request-level concurrency is not treated as project/session isolation. Serena fixed-project slots are separate processes/ports with machine-local project/owner/process identity receipts; the user's shared 9121 instance is excluded. Coding Tools readers do not need a writer lease, while writers are serialized per worktree and a requested path outside the configured workspace is rejected. Native GUI side effects across Remote Desktop Commander and Windows-MCP use one machine GUI lease.

### Decision: one recovery attempt has one mutation owner

Gateway and Remote Desktop Commander remain complementary control paths, but a recovery request carries an attempt id, visited paths and bounded hop budget. Only one path may claim mutation authority for a component in that attempt. Lack of lifecycle authority is diagnose-only. This keeps route ownership, install ownership and runtime mutation authority distinct.

### Risk: process shutdown acknowledgement can lag the real exit

Real isolated Serena probes showed that a Windows process stop confirmation can time out while the process exits shortly afterwards. A timeout/non-zero response is therefore an ambiguous mutation result, not proof that a second kill/restart is required. Stage 16 uses a bounded post-state observation window over listener and PID birth/image identity; an already-exited/recovered post-state ends the attempt without a duplicate mutation. This reusable rule is also captured by Computer Agent 1.1.16 / R49.

### Risk: local lease files become stale after a crashed owner

Serena slot ownership, Coding Tools writer ownership and GUI ownership are machine-local leases/receipts rather than Git state. They carry expiry/identity evidence and allow bounded stale reclaim; active unexpired ownership is never stolen merely because another ChatGPT window wants the resource.

## Stage 15 — component install / upgrade / lifecycle

### Decision: latest stable is resolved at deployment time but is not blind mutation authority

Component manifests declare the package/upstream and the allowed resolver. PyPI/npm/winget metadata may establish the current stable package version; GitHub binary installation additionally requires a release-provided SHA-256 digest and the expected asset identity. The planner may report that an external service is behind without replacing it while that service is healthy and actively used.

Automatic adapters also declare a compatibility window. Installed version, upstream latest and compatibility are separate evidence fields. Latest outside the window blocks install/upgrade; newer compatible installed versions are preserved; unavailable upstream metadata remains unavailable rather than becoming an implicit “up-to-date” result.

### Decision: availability evidence outranks shell PATH absence

The current machine intentionally has healthy Serena and Coding Tools services even though the Coding Tools execution environment does not expose uv or those executables on PATH. A live healthy service is therefore preserved and no duplicate install is attempted. PATH/package discovery is used for installation/version evidence, not as the sole existence truth.

### Decision: install ownership and runtime lifecycle ownership stay separate

When WebGPT performs an installation it writes a machine-local ownership receipt. That receipt records the installed component/version/strategy and still leaves `runtime_lifecycle_authority=false`. Kill/restart authority continues to require the stricter runtime ownership contract.

### Decision: system services have a process-only healthy state

Tailscale does not expose an MCP listener and must not be classified as unhealthy solely because `listener_up=null`. A live system process can be preserved while OAuth/Funnel/remote readiness remains a separate deeper health question.

### Risk: version domains can look comparable while meaning different things

The current Windows-MCP package source reports 0.8.5 while a live server has separately exposed a different product/server version family. Numeric string comparison across those domains could trigger a false downgrade/upgrade. Stage 15 therefore preserves a healthy external instance and only compares versions when the adapter establishes a compatible version source.

### Risk: upstream latest metadata can become temporarily unavailable

Stage 15 resolved the official GitHub latest-release API successfully for MCPJungle 0.4.6 and mcp-auth-proxy 2.10.2, including expected Windows asset digests. An intermediate strict deployment dry-run received GitHub HTTP errors for both lookups; on the final rerun MCPJungle again resolved fresh 0.4.6 evidence while mcp-auth-proxy still returned `HTTPError`. The lifecycle planner preserved both running services and refused to invent fresh latest evidence for the unavailable lookup.

The bounded resilience rule is now: a successful latest query may create a machine-local verified cache entry usable for at most 24 hours **as evidence only**. Cache reuse must revalidate component identity and GitHub asset URL/digest shape, is surfaced as `latest_fresh=false` / `latest_provenance=verified-cache`, and cannot authorize install/upgrade. A cache miss/expired entry remains blocking, so historical repository text cannot be silently promoted into a fresh latest result.

### Risk: pre-closure prompts can become stale artifacts

Commit `d08603a` prepared a Stage-15 continuation prompt before Stage 15 implementation/docs closure. It remains historical evidence only. The docs-before-prompt barrier requires the Stage 16 prompt to be regenerated from the real Stage 15 closure commit HEAD rather than submitted from that earlier artifact.

## Stage 14 — Production Unified Gateway / Edge

### Decision: route synchronization is idempotent and private to WebGPT

The Edge queries the WebGPT MCPJungle registry before mutation. A healthy backend whose existing route already has the same Streamable HTTP transport and URL is preserved. A missing route is registered; a same-name route whose URL changed is force-replaced only inside WebGPT's private Gateway database. Upstream MCP configuration is never rewritten by route synchronization.

### Decision: the production Edge wrapper, not third-party backends, is the owned runtime

Runtime Supervisor owns the Python Edge wrapper plus the child OAuth process it launches. Serena, Coding Tools, Playwright and Windows-MCP remain external/preserved until a later explicit lifecycle stage gives WebGPT ownership evidence. Manager restart scope therefore expands only to the fixed WebGPT Edge id, not to routed MCPs.

### Decision: production OAuth credentials are separate machine-local runtime state

The Stage 5 integration-test password/database are not reused as runtime authority. The production Edge owns a separate machine-local credential and OAuth data directory. Source, docs, manifests and static UI never contain the credential.

### Live acceptance

The current machine's WebGPT production Edge on the dedicated Funnel port passed:
- public protected-resource metadata;
- unauthenticated MCP 401;
- dynamic client registration;
- PKCE authorization-code token exchange;
- authenticated unified Gateway MCP with 87 routed tools and a safe Coding Tools call;
- Runtime Supervisor restart;
- refresh token after restart;
- authenticated MCP again with the same 87-tool surface.

### Risk: repeated Gateway registration can destroy useful registry continuity

Using `register --force` on every Edge start could churn MCPJungle registry records and any identity-associated state. The implementation therefore queries current registry state and uses force only when a same-name route actually changed.

## Stage 18 — Chinese mirror / third-party provenance

### Decision: translation coverage is an executable repository contract

Stage 18 uses deterministic mirror paths rather than ad-hoc translated copies:
root entrypoints use sibling `*.zh-CN.md` files, live documentation uses
`docs/zh-CN/`, and Product Skill/Guide mirrors use
`skills/webgpt-as-codex/zh-CN/`. The existing Manager keeps its Stage 17
`index.html` / `index.zh-CN.html` language-shell model over shared
JavaScript/CSS.

`docs/TRANSLATION-COVERAGE.json` classifies every current tracked/untracked
text-format candidate instead of treating "not translated" as "not audited".
Protocol identifiers, commands, URLs, schema keys, hashes, source code and
machine-readable authority remain exact.

### Decision: canonical historical evidence is indexed, not rewritten

Stage closure records, stage-cost evidence, accumulated incident provenance and
handoff prompt artifacts are canonical evidence. Rewriting those historical
files merely to make the tree visually bilingual could create a second timeline
with subtly different commands, hashes, counts or conclusions. They remain
unchanged and receive an explicit
`HISTORICAL_EVIDENCE_PRESERVED_WITH_INDEX` disposition plus
`docs/zh-CN/HISTORICAL-EVIDENCE-INDEX.md`.

### Decision: the legal original and reading translation have different authority

The root `LICENSE` remains the authoritative Apache License 2.0 text and is
guarded by its Stage 18 SHA-256
`1eb85fc97224598dad1852b5d6483bbcf0aa8608790dcc657a5a2a761ae9c8c6`.
`LICENSE.zh-CN.md` is explicitly non-binding, non-official reading material;
the English original controls any discrepancy.

### Decision: third-party provenance includes package/build dependencies

The existing notice already named the eight integrated external components, but
that is not the whole repository dependency surface. Stage 18 reconciles those
entries against `components/*.json` and also records the `pyproject.toml`
build/runtime/development dependencies (setuptools, requests, pytest and Ruff)
in `docs/THIRD-PARTY-PROVENANCE.json` and bilingual notice files. Upstream
license text is not copied or invented; the exact license/NOTICE shipped by an
upstream artifact remains authoritative for its redistribution obligations.

### Decision: installed artifacts carry a bounded bilingual release record

The wheel continues to exclude stage closures, prompts, the complete Skill
source and machine-local evidence. Stage 18 adds only the bilingual README,
legal/notices, provenance and translation-coverage resources under
`share/webgpt-as-codex/release`, so an installed artifact retains its public
license/provenance context without packaging private or machine-specific state.

### Risk: source and mirror can drift after Stage 18

Cross-links alone do not prevent drift. The Stage 18 regression gate therefore
requires an explicit disposition for every candidate, verifies every
`MIRRORED_CURRENT` target exists, preserves the legal hash, reconciles
component provenance against manifests, covers declared Python dependencies and
checks the release-resource list. A later source change must update its mirror
or intentionally revise the coverage contract.
