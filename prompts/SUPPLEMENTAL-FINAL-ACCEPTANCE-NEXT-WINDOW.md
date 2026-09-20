# WebGPT-as-Codex Loop Engineering — SUPPLEMENTAL-FINAL-ACCEPTANCE

STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2

Continue the WebGPT-as-Codex project using Computer Agent Skill + Loop Engineering + MCP-routed execution.

This is an automatic continuation window. Do not stop after reporting progress if owned work remains.

CURRENT_STAGE = SUPPLEMENTAL-FINAL-ACCEPTANCE
NEXT_STAGE = GLOBAL_LOOP_COMPLETE
AFTER_NEXT_STAGE = TERMINAL
SOURCE_HEAD = 988a11a3712c25c4813de67d438f963454280f21
PRODUCT_HEAD = 988a11a3712c25c4813de67d438f963454280f21

Program state on entry = ACTIVE.
This window is final reconciliation / release-readiness acceptance, not a new feature-development stage.
## 0. 本棒唯一目标

- Stage: SUPPLEMENTAL-FINAL-ACCEPTANCE
- 唯一主目标：把原已接受主链与 Stage13-19 supplemental chain 做最终 reconciliation，证明 one-click deploy、Agent-native deployment、OAuth/Gateway/recovery/concurrency/release packaging 的事实彼此一致，并执行 Program Completion Gate。
- 本棒明确不做：不 broad audit；不重做 Stage1-19；不新增大功能；不为了验收反复 restart/re-register production Connector/Funnel/OAuth。
- 前一棒：Stage19 已 CLOSED_LOCAL_VERIFIED + REAL_HOST_VERIFIED + REAL_CHATGPT_VERIFIED。
- 当前产品版本：0.1.0。
- Windows full reboot 仍是 MANUAL_REAL_REBOOT_ACCEPTANCE_PENDING，不等于 OAuth failure。
- 用户已明确确认真实 ChatGPT WebGPT-as-Codex connector 配置成功；把它当 protected known-good evidence。
## 1. 真实仓库 / Workspace Map

- Workspace: D:\AgentData\10_Workspaces\coding-tools-mcp-demo\
- Repository / product root: D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex\
- Branch: main
- PRODUCT_HEAD: 988a11a3712c25c4813de67d438f963454280f21
- 启动后第一件事重新运行 git status / branch / rev-parse HEAD / log -5；如果只比 PRODUCT_HEAD 多 prompt/handoff artifact commit，记录即可，不把它误判为产品代码变化。
- Source root: src/webgpt_as_codex/
- Tests root: tests/
- Docs/SoT root: docs/
- Product Skill: skills/webgpt-as-codex/
- Component manifests: components/
- Manager resources: manager/static/
- Prompt path: prompts/SUPPLEMENTAL-FINAL-ACCEPTANCE-NEXT-WINDOW.md
- 生成 prompt 时 PRODUCT_HEAD 对应的 repo worktree 是 clean。
- 禁止 git reset / git clean / force push / destructive deploy。
## 2. Computer Agent Skill Bootstrap

Workspace Skill root:
D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.skills\computer-agent\

启动后按顺序读取：
1. .skills/computer-agent/SKILL.md
2. .skills/computer-agent/routing.md
3. .skills/computer-agent/environment.local.md
4. .skills/computer-agent/workflows/loop-engineering.md
5. .skills/computer-agent/workflows/coding.md
6. .skills/computer-agent/workflows/cross-tool.md
7. .skills/computer-agent/workflows/handoff-template.md
8. .skills/computer-agent/workflows/browser.md
9. .skills/computer-agent/validation.md

不要因为 direct MCP schema 没暴露就跳过已登记的本机 MCP；先按 environment.local.md 做 listener/process -> initialize -> tools/list -> minimal probe。
## 3. MCP Locator Table

| MCP | 当前已知本机 locator | 本棒用途 | 本棒不做 | fallback / recovery |
|---|---|---|---|---|
| Remote Desktop Commander | direct connector；无稳定本地 HTTP | host/process/log/read-only post-state；独立 repair plane | repo 双写、无必要 GUI mutation | direct 不暴露时按 environment.local.md 动态发现 stdio runtime |
| Coding Tools | trusted 127.0.0.1:8766；workspace = coding-tools-mcp-demo | repo truth/read/edit/tests/Git | workspace 外 host GUI | start-trusted.ps1 / local shell fallback |
| Serena | 127.0.0.1:9121 | 仅在需要 symbol/reference reconciliation 时使用 | 不切 shared 9121 到别的 project；不负责 tests/build | 只读 source/search；必要时 fixed-project isolated slot |
| Playwright | http://localhost:8931/mcp；Extension/shared Edge Default | 最终 ChatGPT automatic handoff | 不做代码/Git；不新建隔离空 profile | status.cmd -> start-extension.cmd -> initialize/tools/list |
| Windows-MCP | http://127.0.0.1:8001/mcp | 仅 DOM 外 Windows UI fallback | 网页 DOM 默认操作 | RDC / Playwright |
| Unified Gateway | localhost 9330 behind OAuth edge 9341/9340 | 只读 final status/evidence，若有必要 | 禁止为验收 churn production connector | independent repair plane |

下一 worker 第一条用户可见更新必须报告这些 MCP 的实际 availability、本棒用途和 fallback。
## Mandatory read order

1. D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex\AGENTS.md
2. docs/CURRENT-PROJECT-STATE.md
3. docs/STAGE-19-CLOSURE.md
4. docs/FINAL-OVERALL-ACCEPTANCE-CLOSURE.md
5. docs/PROJECT-COMPLETE-CLOSURE.md
6. docs/ROADMAP-2026-09-20.md
7. docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md
8. docs/ARCHITECTURE.md
9. docs/DEPLOYMENT.md
10. docs/CONCURRENCY-AND-FALLBACK.md
11. docs/DECISIONS-AND-RISKS.md
12. docs/STAGE-13-CLOSURE.md through docs/STAGE-18-CLOSURE.md
13. skills/webgpt-as-codex/SKILL.md
14. skills/webgpt-as-codex/loop-engineering.md
15. skills/webgpt-as-codex/handoff.md
16. skills/webgpt-as-codex/routing.md
17. skills/webgpt-as-codex/experience-ledger.md
18. relevant component manifests / tests only when a contradiction requires exact source proof.

The local repository SoT outranks chat memory and this prompt when current evidence differs.
## Stage objective

Perform final supplemental reconciliation and Program Completion Gate without disturbing the known-good production connector.

Specifically prove:
- Stage1-12 original accepted contract and Stage13-19 supplemental contract do not contradict each other;
- one-click Desktop/Start All truth is consistent with current runtime ownership and readiness rules;
- Agent-native deployment truth is documented and bounded by the interactive account/privilege boundaries;
- canonical HTTPS/OAuth identity/recovery semantics are stable and no false-green readiness remains;
- concurrency/fallback ownership rules remain coherent;
- installed wheel/release resources remain current;
- no unresolved security, secret, lifecycle, bilingual, packaging or handoff contradiction remains.
## Required outputs

- a concise final reconciliation matrix mapping original goals -> supplemental goals -> accepted evidence;
- final release-readiness / one-click-deploy truth;
- final Agent-native deployment truth and explicit interactive boundaries;
- explicit handling of MANUAL_REAL_REBOOT_ACCEPTANCE_PENDING without converting it into a false failure or silently claiming PASS;
- final full repository gates if any tracked file changes; otherwise at minimum verify the 205-PASS Stage19 baseline and run diff/status checks;
- update all affected live SoT English + Chinese mirrors if reconciliation changes wording/status;
- create docs/SUPPLEMENTAL-FINAL-ACCEPTANCE-CLOSURE.md;
- create the final Program Completion decision;
- if and only if the canonical Program Completion Gate is fully satisfied, transition CURRENT project state to GLOBAL_LOOP_COMPLETE and prepare the terminal handoff/receipt required by the current Stable Core.
## Do not redo

- Do not redo Stage1-19 implementation.
- Do not broad-audit every file simply because this is final acceptance.
- Do not restart/re-register/rotate the successfully configured production ChatGPT Connector/Funnel/OAuth for confidence.
- Do not force Windows reboot solely to obtain a green checkbox.
- Do not switch shared Serena 9121 between projects.
- Do not replace healthy external MCPs or infer lifecycle ownership from routing ownership.
- Do not regenerate OAuth credential, delete OAuth DB, modify browser cookies/session, or change Tailscale node identity.
- Do not change public identity unless a real contradiction proves migration is required.
## 5. CONFIRMED facts on entry

- Stage19 product/docs closure commit = 988a11a3712c25c4813de67d438f963454280f21.
- Stage19 final repository gate = 205 PASS; Ruff PASS; SECRET_SCAN_PASS; git diff --check PASS.
- A fresh wheel built from the committed Stage19 HEAD installed outside the repo and verified 8 component manifests, 4 Manager resources, all 9 release resources, authoritative LICENSE hash and CLI 0.1.0.
- Real host OAuth path recovered to managed 9341 compatibility edge -> 9340 OAuth proxy -> 9330 Gateway.
- Public MCP unauthenticated gate returned 401; OAuth metadata/DCR/PKCE/token/authenticated MCP/refresh passed.
- Authenticated MCP tool surface stayed 87 across controlled Edge restart.
- User confirmed real ChatGPT connector configuration succeeded after the recovery.
- After that success the current window deliberately stopped disruptive production acceptance.
- Windows full reboot was not performed after connector success.
## 6. BLOCKED_ENV / LIMITATION

MANUAL_REAL_REBOOT_ACCEPTANCE_PENDING:
- do not pretend a whole-machine reboot was verified;
- do not force it just for closure;
- treat it as manual post-release acceptance unless current canonical goals explicitly require it as a non-waivable Program Completion Gate.
- If it is non-waivable, final state must be PAUSED_EXTERNAL_BLOCKER rather than GLOBAL_LOOP_COMPLETE; explain the exact canonical requirement.
- If current canonical goals permit manual post-release acceptance, document that distinction and continue the completion gate.

No other Stage19-owned OAuth/HTTPS/readiness blocker is known at handoff.
## MCP routing contract

- Prefer structured capability; diagnose before fallback.
- Repo writes/tests/Git have one writer.
- Remote Desktop Commander is the independent repair-plane path, not a second repo writer.
- Playwright is mandatory for the automatic next-window transport when the loop continues.
- Direct schema not exposed != local service absent.
- Browser/login state is separate from MCP service state.
- A live port != protocol healthy != correct generation != complete product readiness.
- Do not use a broken runtime-plane WebGPT connection as the only tool to repair/restart WebGPT.
- After runtime restart, reacquire MCP/browser session refs; never reuse stale refs across restart.
## Failure protocol

1. 查后态；
2. classify input/schema/session/auth/binding/target/runtime/harness/external failure；
3. same-tool recovery first；
4. local structured fallback；
5. cross-tool fallback only at real capability boundary；
6. preserve known-good production state；
7. only PAUSED_EXTERNAL_BLOCKER when all authorized recovery paths are exhausted and a mandatory external condition truly remains.

Ordinary test/doc/tool failures remain ACTIVE_RECOVERY.
Never ask the user merely because investigation is inconvenient.
Never bypass an explicit permission/safety gate.
## Self-evolving execution contract

Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse.

Carry forward Stage19 lessons:
- child-process liveness cannot satisfy wrapper/product readiness;
- compatible child reuse requires strict identity + issuer evidence;
- self-restart needs an independent repair plane;
- once a real external connector is confirmed good, acceptance should freeze disruptive churn.

Use approximately a 20-minute soft stage budget INCLUDING closure/handoff. This is a workflow heuristic, not a claimed platform timeout.
If final reconciliation expands unexpectedly, save SoT + close a bounded sub-scope + hand off before context/execution exhaustion.
## 7. Exact execution steps

### Step A — Entry truth
- Primary: Coding Tools/local shell.
- Recheck git status/branch/HEAD/log and confirm PRODUCT_HEAD relationship.
- Read mandatory SoT/closures in order.
- Exit: current canonical completion criteria are explicit.

### Step B — Reconciliation matrix
- Primary: docs/source evidence.
- Compare original accepted final closure + supplemental goals + Stage13-19 closures.
- Classify each item VERIFIED / MANUAL_POST_RELEASE / CONTRADICTION.
- Do not assign PASS from implication alone.

### Step C — Minimal contradiction handling
- If no contradiction: no product code changes.
- If contradiction exists: reopen only the smallest owner scope, add regression evidence, run targeted then full gates.
- Production Connector/Funnel/OAuth mutation requires a concrete defect, not curiosity.
### Step D — Release/Agent-native truth
- Confirm one-click launcher/Start All behavior, ownership boundaries, bootstrap/Doctor/Repair design, wheel/resource boundary and interactive login/privilege boundaries from accepted evidence.
- Do not simulate a destructive fresh-machine reinstall on the user's live machine.
- Use isolated state/env only if additional proof is actually necessary.

### Step E — Program Completion Gate
- Decide whether MANUAL_REAL_REBOOT_ACCEPTANCE_PENDING is allowed as post-release/manual evidence or is a non-waivable blocker according to canonical goals.
- Check unresolved security/deployment/concurrency/bilingual/release contradiction = zero.
- Record exact program state: GLOBAL_LOOP_COMPLETE or PAUSED_EXTERNAL_BLOCKER.

### Step F — Docs / closure / Git
- Update affected EN/ZH live SoT before prompt/handoff artifacts.
- Create docs/SUPPLEMENTAL-FINAL-ACCEPTANCE-CLOSURE.md.
- Run required final gates.
- Commit product/docs closure.
## Tests / Gates

Entry baseline:
- PRODUCT_HEAD 988a11a3712c25c4813de67d438f963454280f21
- full pytest 205 PASS
- Ruff PASS
- SECRET_SCAN_PASS
- git diff --check PASS
- final committed-head wheel installed-artifact PASS
- real ChatGPT connector user-confirmed successful

If no product code changes:
- git status/diff consistency;
- documentation/translation coverage tests as applicable;
- final full pytest is preferred before completion if within the stage budget.

If product code changes:
- targeted regression for owner scope;
- full pytest;
- Ruff;
- secret scan;
- git diff --check;
- rebuild/install fresh wheel if release/runtime resources changed.
## 9. 文档与进度更新

For every live document below mark UPDATED_WITH_NEW_EVIDENCE / CHECKED_NO_CHANGE_REQUIRED / NOT_APPLICABLE_THIS_STAGE:
- docs/CURRENT-PROJECT-STATE.md + zh-CN mirror
- docs/ROADMAP-2026-09-20.md + zh-CN mirror
- docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md + zh-CN mirror
- docs/ARCHITECTURE.md + zh-CN mirror
- docs/DEPLOYMENT.md + zh-CN mirror
- docs/CONCURRENCY-AND-FALLBACK.md + zh-CN mirror
- docs/DECISIONS-AND-RISKS.md + zh-CN mirror
- skills/webgpt-as-codex/SKILL.md + zh-CN mirror
- skills/webgpt-as-codex/experience-ledger.md
- docs/TRANSLATION-COVERAGE.json when new human/evidence artifacts require classification

Historical closure files stay canonical; do not rewrite earlier history.
## 10. Git / Commit discipline

- Single repo writer.
- No reset/clean/force-push.
- No secret/private host identity in Git.
- Product/docs closure commit and handoff artifact commit remain separate.
- Any final prompt must point PRODUCT_HEAD/SOURCE_HEAD at the actual product/docs closure commit, not the later prompt-only commit.
- Do not push unless a separately authorized task owns remote publication.
- Clean tool-local metadata created by this worker only when pre-state proves it was new/untracked and disposable.
## 11. Exit criteria

SUPPLEMENTAL-FINAL-ACCEPTANCE may close only when:
- reconciliation matrix has no unresolved contradiction;
- one-click and Agent-native deployment truth are explicitly stated;
- manual reboot status is truthfully classified;
- security/lifecycle/concurrency/public identity/release boundaries agree;
- required gates are green;
- affected EN/ZH SoT is updated;
- Supplemental Final Acceptance closure is written and committed;
- canonical Program Completion Gate has produced a justified program state.

Do not label GLOBAL_LOOP_COMPLETE merely because all implementation stages are closed.
## Closure contract

Before closing this stage:
1. finish reconciliation;
2. run required gates;
3. update all affected docs;
4. write Supplemental Final Acceptance closure;
5. commit product/docs;
6. re-read current Stable Core + SoT + real HEAD;
7. only if loop still continues, generate a fresh next prompt from that committed HEAD;
8. validate required markers and SOURCE_HEAD;
9. hash exact prompt bytes;
10. Playwright-submit exactly once in the authenticated shared Edge context;
11. verify sent user message + /c/ URL + next assistant run;
12. write machine-local receipt.

If Program Completion Gate returns GLOBAL_LOOP_COMPLETE, follow the current Stable Core terminal/receipt rule rather than inventing another development stage.
## Recursive continuation invariant

This handoff rule is recursive and MUST be inherited by every subsequent window:
- this window closes SUPPLEMENTAL-FINAL-ACCEPTANCE;
- if canonical state is not yet GLOBAL_LOOP_COMPLETE, it must generate and submit a fresh prompt for the actual remaining owner scope;
- every prompt is regenerated from that stage's newly committed product/docs HEAD;
- every continuing handoff uses Playwright MCP and is successful only after sent-message + new-assistant-run verification;
- USER_STOPPED and PAUSED_EXTERNAL_BLOCKER are not completion;
- recursive continuation ends only after the planned final stage and Final Overall Acceptance are both CLOSED_LOCAL_VERIFIED.

Do not stop at an intermediate stage boundary merely to report progress.
## Automatic handoff contract

Automatic continuation is authorized when the loop still has work.
Use Playwright MCP with the already authenticated Edge Extension/shared context:
1. read workflows/browser.md + environment.local.md;
2. use http://localhost:8931/mcp when direct schema is absent;
3. keep one MCP session for tabs/fill/submit/verify;
4. create/select a blank ChatGPT conversation and wait for the real active composer; hidden hydration fallback textarea is not a valid target;
5. load the exact validated prompt from repo;
6. verify draft length plus normalized SHA-256 / beginning / middle / end;
7. attempt submit exactly once;
8. after submit attempt, never resend until post-state proves it did not submit;
9. verify user message, /c/ conversation URL and that a new assistant run/response begins;
10. write machine-local receipt.

A filled textbox, click, URL change or prompt file alone is NOT successful handoff.
## Safety

- Never commit OAuth password, token, cookie, private key, OAuth DB, pairing material, private public-URL identity or browser session data.
- Do not alter the known-good production Connector/Funnel/OAuth unless a concrete contradiction requires the smallest owner fix.
- Do not conflate routing ownership with lifecycle ownership.
- Do not treat missing direct schema as service failure.
- Do not let two windows mutate the same worktree/component simultaneously.
- Do not fake Windows reboot evidence.

## 15. 现在开始

Start with:
1. Computer Agent Skill bootstrap;
2. actual MCP availability report;
3. Git/SoT truth;
4. final reconciliation matrix;
5. Program Completion Gate;
6. docs/closure/tests/commit;
7. recursive handoff only if canonical state still requires another window.

Do not stop after reporting progress while authorized owned work remains.
