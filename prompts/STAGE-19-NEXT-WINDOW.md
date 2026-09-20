# WebGPT-as-Codex — STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE

Continue the WebGPT-as-Codex project using Computer Agent Skill + Loop Engineering + MCP-routed execution.

This is an automatic continuation window. Do not stop after reporting progress if owned work remains.

CURRENT_STAGE = STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE
NEXT_STAGE = SUPPLEMENTAL-FINAL-ACCEPTANCE
AFTER_NEXT_STAGE = GLOBAL_LOOP_COMPLETE
SOURCE_HEAD = 5f4eb7c48e0a3f7abad0c816a40c3525d20f9df7

## Mandatory read order
1. D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex\AGENTS.md
2. docs/CURRENT-PROJECT-STATE.md
3. latest previous-stage closure
4. docs/ARCHITECTURE.md
5. skills/webgpt-as-codex/SKILL.md
6. skills/webgpt-as-codex/loop-engineering.md
7. skills/webgpt-as-codex/handoff.md
8. skills/webgpt-as-codex/routing.md
9. relevant component manifests, MCP Guides/inventory when present, and tests

The local repository SoT outranks chat memory.

## Stage objective
Perform the final supplemental end-to-end deployment acceptance from the committed Stage18 product truth: prove clean/fresh build-install-runtime behavior and existing-machine preservation, exercise component lifecycle/version adapters, Gateway safe calls, OAuth 2.1 DCR/PKCE/authorization-code/refresh/401/authenticated MCP, configured Tailscale HTTPS/public /mcp, ChatGPT browser OAuth when the interactive surface exists, complementary fallback drills, multi-window concurrency/session isolation, Desktop Manager/launcher behavior, and full repository/package gates; fix only directly owned root-cause defects found by this acceptance, then hand off a committed evidence state to Supplemental Final Acceptance.

## Required outputs
- re-probe Git and MCP/tool reality from SOURCE_HEAD, preserving single-writer discipline and not force-switching a shared/reserved Serena 9121 context
- build a fresh wheel from committed source, install outside the checkout, verify CLI/version/resource resolution, all component manifests, Manager assets and Stage18 bilingual release/legal/provenance resources, and confirm repository-only/private machine state is not packaged
- exercise clean bootstrap/doctor/repair with isolated non-destructive roots plus existing-machine preservation: deterministic paths, idempotency, valid config/custom MCP preservation, duplicate-prevention, managed-vs-unmanaged ownership, rollback/atomic-state behavior and no destructive takeover of external services
- verify component installed-version detection, install/upgrade/already-current behavior, source/digest/runtime-identity boundaries and failure rollback on representative owned component classes
- verify Unified Gateway listener/schema with real MCP handshake and minimal safe calls; distinguish Gateway transport from downstream failure; verify malformed/unauthorized inputs fail closed without leaking credentials
- prove OAuth 2.1 DCR, PKCE, auth-code exchange, refresh-token, 401 recovery and authenticated MCP as far as the safe configured environment supports; store secrets only in machine-local authority and classify any true external-only gap as BLOCKED_ENV without stopping unrelated acceptance
- verify the configured Tailscale/Funnel HTTPS public /mcp path and authenticated/unauthenticated boundary when available without rotating account configuration; verify ChatGPT browser OAuth/connected state in the authenticated normal browser context when the surface is available
- run representative fallback drills and multi-window/session-isolation tests, including direct-missing -> local MCP reconnect, Playwright for DOM, Windows-MCP only for browser chrome/system dialogs, host tools for process/outside-workspace evidence, and no stale tab refs or double repo writers
- verify Desktop Manager/launcher opens in the normal browser profile/default handler, not an isolated Playwright profile, remains responsive, preserves bounded action contracts and creates no duplicate launcher/autostart artifacts
- if acceptance finds an owned defect, add the minimum regression evidence and root-cause fix, rerun the affected end-to-end path, then run full pytest, Ruff, secret scan, git diff check, wheel build and isolated installed-artifact smoke
- update all affected live English/Chinese SoT mirrors, deployment/concurrency/decision-risk/experience docs, write docs/STAGE-19-CLOSURE.md with LOCAL_IMPLEMENTATION/LOCAL_VERIFIED/REAL_HOST_OR_DEVICE_VERIFIED/BLOCKED_ENV distinctions, commit Stage19 product/docs first, then generate/validate/hash/commit and exactly-once Playwright-submit prompts/SUPPLEMENTAL-FINAL-ACCEPTANCE-NEXT-WINDOW.md from the real Stage19 closure HEAD

## Do not redo
- Stages 1-18, original FINAL-OVERALL-ACCEPTANCE, original PROJECT-COMPLETE or the Stage17 post-acceptance hotfix unless Stage19 produces direct contradictory evidence at the minimum affected owner boundary
- Stage18 Chinese mirror/legal/provenance work except keeping live mirror-required docs synchronized when Stage19 changes those live docs
- broad feature development or refactors unrelated to a defect directly exposed by end-to-end acceptance
- reset/clean/force-push/push, destructive deletion of real user state, secret/token copying into Git, or takeover/reconfiguration of external/Tailscale/Serena services merely to make acceptance green
- Supplemental Final Acceptance itself; Stage19 must finish, commit and hand off that separate final reconciliation window

## Known risks / evidence
- Direct ChatGPT connector schemas can disappear while the local MCP service remains healthy; direct absence is not proof of service failure. Known verified locators: Coding Tools 127.0.0.1:8766/mcp, Playwright 127.0.0.1:8931/mcp, Windows-MCP 127.0.0.1:8001, Unified Gateway 127.0.0.1:9330, Serena 127.0.0.1:9121. Re-probe rather than assume.
- Shared Serena may be reserved by another worker. If reserved, do not activate/switch/restart it; Coding Tools search/read is the fallback.
- Existing-machine acceptance is safety-sensitive: snapshot non-secret state, prefer isolated/dry-run/read-only paths, and prove preservation instead of destructively recreating the user's environment.
- OAuth/Tailscale/browser acceptance contains external state. Distinguish server correctness, public transport, authenticated browser/account state and optional interactive availability; do not conflate one unavailable layer with total failure.
- Browser and handoff actions are side-effecting. Keep one Playwright mcp-session-id for tabs/new/select/snapshot/fill/submit/verify, use the real visible composer, hash-check long prompts when needed, submit exactly once and inspect post-state before any retry.
- The Stage19 source truth is product/docs commit 5f4eb7c48e0a3f7abad0c816a40c3525d20f9df7; the later Stage19 handoff-prompt commit is metadata only and must not replace PRODUCT_HEAD.

## MCP routing contract
- Serena: semantic code navigation only after confirming the active project is webgpt-as-codex.
- Coding Tools: repo writes/tests/git only when the workspace is actually bound to this repository.
- Playwright MCP: browser/Web App automation and the final next-window handoff.
- Windows-MCP: native Windows GUI fallback.
- Desktop Commander / shell: host files/processes when structured project tools do not fit.
- Prefer structured tools; diagnose preferred-tool failure before fallback.
- Routing decides WHICH capability; actual schema/Operating Guide knowledge decides HOW to use it.
- One failed call is not proof an MCP is unavailable: inspect binding, session, auth, schema, harness and real post-state first.
- Never let a temporary test instance change the shared Serena active project.

## Failure protocol
1. distinguish harness failure from target failure;
2. inspect real logs/state;
3. retry only after a root-cause hypothesis;
4. use a bounded temporary instance when production-like services must remain untouched;
5. record reusable lessons in the Experience Ledger;
6. do not broaden into closed stages without contradictory evidence.
7. explore reasonable tools/schema/environment/log/history evidence before asking the user unless the missing fact/choice is genuinely user-exclusive.

## Self-evolving execution contract
- Do not merely execute. Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse.
- Observe the full chain: SoT loading, planning, stage sizing, routing, MCP use, implementation, validation, docs, Git, prompt generation, Playwright submit and receiving-run verification.
- Treat repeated friction, premature fallback, user reminders, missing docs and almost-finished handoffs as candidate process defects.
- Classify lessons narrowly: general -> Skill; MCP-specific -> Operating Guide; machine-specific -> local inventory/config; one-off -> stage evidence.
- User guidance that reveals a reusable operating principle is valid experience input.
- Use an approximately 20-minute soft stage budget INCLUDING closure/handoff. This is a heuristic, not a platform timeout.
- If implementation expansion threatens tests/docs/commit/verified handoff, split into a bounded sub-stage while preserving CURRENT/NEXT/AFTER_NEXT and one-owner scope.
- Collect stage-cost evidence so this heuristic can self-correct instead of hardcoding an unsupported duration limit.

## Safety
- Never copy secrets, OAuth DBs, passwords, tokens, cookies, private keys or machine-specific private state into Git.
- Do not reset/clean/force-push unrelated repositories.
- Keep existing working MCP/Funnel endpoints unchanged unless this stage explicitly owns them.
- One file has one writer; use worktrees for parallel writers.

## Closure contract
Before closing this stage:
1. finish owned implementation;
2. run narrow tests, then required full gates;
3. verify post-state and Git diff;
4. update all affected docs and decision/risk/experience records;
5. write the stage closure;
6. commit the stage;
7. generate the next prompt from the new verified HEAD;
8. validate prompt required markers + SOURCE_HEAD;
9. hash the exact prompt;
10. Playwright-submit the exact prompt in the already authenticated browser context;
11. verify sent user message + /c/ conversation + new assistant run;
12. write prompt SHA-256 / handoff receipt locally.

## Recursive continuation invariant
This handoff rule is recursive and MUST be inherited by every subsequent window:
- this window closes STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE, then hands off SUPPLEMENTAL-FINAL-ACCEPTANCE;
- the SUPPLEMENTAL-FINAL-ACCEPTANCE window must, after its own verified closure, generate and submit a fresh prompt for its NEXT_STAGE;
- that following window must do the same for its own NEXT_STAGE, preserving CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE;
- every prompt is regenerated from that stage's newly committed HEAD and validated before submission;
- every handoff uses Playwright MCP and is successful only after sent-message + new-assistant-run verification;
- do not stop at a stage boundary merely to report progress;
- recursive continuation ends only after the planned final stage and Final Overall Acceptance are both CLOSED_LOCAL_VERIFIED.

## Automatic handoff contract
Automatic continuation is authorized.
After closure, use Playwright MCP with the logged-in ChatGPT browser state:
1. keep one MCP session and reuse the already authenticated browser context; do not create a fresh isolated profile merely to get a new conversation;
2. open a new ChatGPT tab/page, enumerate the tabs and explicitly select that new ChatGPT tab in the same MCP session; do not assume the extension focused it;
3. reacquire fresh DOM evidence from the selected tab and wait for the real active composer; an initial hidden hydration fallback textarea is not a valid target;
4. enter the exact validated prompt file and submit once;
5. verify the prompt appears as a sent user message containing SOURCE_HEAD;
6. verify the URL is /c/... and a new assistant run/response begins;
7. only then mark the handoff successful.
A populated textbox, click, navigation, or prompt file alone is NOT proof of handoff.

Continue Loop Engineering recursively until the full project and final overall acceptance are complete.

## Stage19 concrete workspace / final-chain contract

- Actual repository/worktree: `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex`
- Coding Tools workspace root: `D:\AgentData\10_Workspaces\coding-tools-mcp-demo`
- PRODUCT_HEAD = `5f4eb7c48e0a3f7abad0c816a40c3525d20f9df7`
- Stage18 closure: `docs/STAGE-18-CLOSURE.md`
- Current live SoT must begin with:
  - CURRENT_STAGE = `STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE`
  - NEXT_STAGE = `SUPPLEMENTAL-FINAL-ACCEPTANCE`
  - AFTER_NEXT_STAGE = `GLOBAL_LOOP_COMPLETE`
- Current Computer Agent Stable Core is under:
  `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.skills\computer-agent\`
  and Stage19 must read `SKILL.md`, `routing.md`, `environment.local.md`,
  `workflows/loop-engineering.md`, `workflows/coding.md`,
  `workflows/cross-tool.md`, `workflows/handoff-template.md`,
  `workflows/browser.md`, and `validation.md`.

The Supplemental Final Acceptance window is the last planned supplemental work stage. Its job is reconciliation, not new feature development. It may record `GLOBAL_LOOP_COMPLETE` only if the canonical Program Completion Gate is actually satisfied: all supplemental stages are closed; no unresolved deployment/security/concurrency contradiction remains; required final evidence is green; live SoT shows no remaining planned stage; Git truth is committed/clean except documented machine-local evidence; no mandatory external acceptance remains blocked; and the original Final Overall Acceptance remains closed and consistent with the supplemental chain. If that gate fails, reopen only the smallest contradictory owner scope.

## Full Recursive Handoff Invariant — MUST PROPAGATE VERBATIM IN MEANING

1. Handoff is a recursive chain: this worker must not only complete CURRENT_STAGE -> NEXT_STAGE, it must explicitly require the NEXT_STAGE worker to continue NEXT_STAGE -> AFTER_NEXT_STAGE.
2. Every handoff prompt must state CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE.
3. Continue across batch/stage boundaries. Finishing one Stage or Batch is not a Global Loop Stop Condition.
4. Every next prompt must be self-contained with repo/worktree/branch/HEAD/upstream/source/tests/SoT/Skill/MCP locators/gates/dirty state/BLOCKED_ENV/failure recovery.
5. PRODUCT_STAGE_COMPLETE and HANDOFF_COMPLETE are independent. If product work is complete but transport fails, record `STAGE_COMPLETE_HANDOFF_PENDING` and recover only the handoff layer.
6. After timeout/non-zero/connection loss on a side-effecting handoff action, inspect real post-state before any retry; duplicate sending is forbidden.
7. For strong long-prompt validation, use identical whitespace normalization + SHA-256 on both local prompt and browser composer. UTF-8 byte count is not JavaScript character count.
8. Rediscover MCP state every window. For local Playwright reconnect, keep the entire multi-step handoff inside one `mcp-session-id` and never reuse stale tab indexes/refs across sessions.
9. Continue Experience Absorption as `RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE`.
10. Program state must distinguish `ACTIVE / PAUSED_EXTERNAL_BLOCKER / USER_STOPPED / GLOBAL_LOOP_COMPLETE`. User stop and an unrecoverable safety/external blocker are unfinished states; only the canonical Program Completion Gate can authorize GLOBAL_LOOP_COMPLETE.
11. The NEXT_STAGE worker must carry this full recursive invariant forward. The final Supplemental worker may terminate without another implementation window only when it has actually satisfied the canonical Program Completion Gate and records `GLOBAL_LOOP_COMPLETE`.
12. If a generated next prompt lacks this complete invariant, the Zero-Guess / Recursive Handoff gate fails and automatic submission is forbidden.

## Strengthened Playwright exactly-once handoff rules

At Stage19 closure:
1. finish all owned implementation, evidence, live-doc updates and the Stage19 product/docs closure commit first;
2. reload the current Computer Agent handoff template, browser workflow, validation rules and final SoT;
3. generate `prompts/SUPPLEMENTAL-FINAL-ACCEPTANCE-NEXT-WINDOW.md` from the real Stage19 product/docs closure HEAD, not from the later prompt-only commit;
4. validate the exact prompt with `webgpt_as_codex.handoff.validate_handoff_prompt` and hash its exact UTF-8 bytes;
5. use the actual Playwright locator from `environment.local.md`; previously verified local endpoint was `http://127.0.0.1:8931/mcp`, but re-probe;
6. if direct Playwright schema is absent, perform standard MCP `initialize -> tools/list`;
7. keep tabs/new/select/snapshot/fill/submit/verify in one `mcp-session-id`;
8. reuse the authenticated normal Edge/shared context and explicitly select the new ChatGPT tab;
9. target only a real visible editable composer and reacquire a fresh snapshot/ref after focusing it;
10. verify first/middle/last prompt content and, for strong validation, compare identical whitespace-normalized SHA-256 on local prompt and browser composer;
11. submit exactly once;
12. after any timeout/error, inspect URL, composer, sent user message and assistant generating/response state before any retry;
13. once submit was attempted, duplicate sending is forbidden unless post-state proves no submission occurred;
14. handoff is complete only when the sent message contains the Supplemental prompt SOURCE_HEAD, the URL is `/c/...`, and a new assistant run/response begins;
15. write a machine-local handoff receipt with prompt path, prompt SHA-256, source HEAD, conversation URL and verification evidence;
16. if all transports fail after Stage19 product work is closed, record `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT` and recover only the handoff layer later.

Do not stop at a progress report while Stage19 owned work remains. Do not swallow Supplemental Final Acceptance. Do not claim `GLOBAL_LOOP_COMPLETE` from Stage19.
