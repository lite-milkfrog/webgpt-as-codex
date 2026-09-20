# WebGPT-as-Codex — STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES

Continue the WebGPT-as-Codex project using Computer Agent Skill + Loop Engineering + MCP-routed execution.

This is an automatic continuation window. Do not stop after reporting progress if owned work remains.

CURRENT_STAGE = STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES
NEXT_STAGE = STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE
AFTER_NEXT_STAGE = SUPPLEMENTAL-FINAL-ACCEPTANCE
SOURCE_HEAD = 310458dfe3cd97720963a08b69a1d82558588e59

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
Complete the repository-wide Chinese mirror and public third-party provenance without changing closed runtime behavior: audit every tracked human-readable English asset, establish complete Chinese mirror treatment, preserve the original Apache-2.0 LICENSE while adding a clearly non-binding Chinese reading translation, reconcile dedicated third-party notices/provenance, and ensure release/package-facing bilingual resources remain verifiable.

## Required outputs
- tracked-file language coverage audit with an explicit classification for every human-readable candidate
- complete Chinese mirror treatment for current human-readable project/release/Skill documentation while preserving protocol identifiers, commands, URLs, schema keys and hashes exactly
- original LICENSE preserved byte-for-byte plus a clearly labeled non-binding Chinese reading translation
- dedicated third-party notices/provenance reconciled from repository manifests and upstream metadata, with Chinese counterpart where human-readable
- translation coverage manifest usable as a regression gate rather than an informal checklist
- package/release resource updates required for the bilingual experience, without copying machine-local state or secrets
- targeted translation/provenance tests plus full repository gates
- updated live SoT, decision/risk records, experience ledger and Stage18 closure
- fresh Stage19 prompt generated only after the Stage18 product/docs closure commit and automatically handed off through Playwright

## Do not redo
- Stages 1-17 implementation and accepted closures
- Stage17 post-acceptance Manager runtime/profile Hotfix unless Stage18 produces direct contradictory evidence
- Gateway/OAuth/Tailscale/component lifecycle/concurrency behavior owned by Stages 13-17
- shared Serena 9121 state; this docs/release stage does not require project switching
- real MCP runtime restart/reconfiguration merely to translate documentation

## Known risks / evidence
- THIRD_PARTY_NOTICES.md already exists and must be audited/reconciled rather than blindly replaced
- LICENSE is the legal Apache-2.0 original and must remain authoritative; any Chinese translation must explicitly state that it is for reading convenience only
- the repository currently has about 70 tracked human-readable-format candidates, but not every JSON/TOML/JS/protocol artifact should be translated; the coverage manifest must classify rather than mutate machine/protocol semantics
- historical closure/evidence files are canonical evidence and must not be silently rewritten just to make the repository look uniformly bilingual
- Computer Agent 1.1.17 added R50/R51 after the real Stage17 Hotfix; Stage18 must preserve the runtime-generation and desktop-profile separation rules
- Serena shared port 9121 is being used by another task; do not activate/switch/restart it for Stage18

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
- this window closes STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES, then hands off STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE;
- the STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE window must, after its own verified closure, generate and submit a fresh prompt for its NEXT_STAGE;
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

STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2

## Stage18 Zero-Guess workspace map

- Repository/worktree: `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex`
- Coding Tools workspace root: `D:\AgentData\10_Workspaces\coding-tools-mcp-demo`
- Coding Tools repo-relative worktree: `webgpt-as-codex`
- Branch: `main`
- PRODUCT_HEAD: `310458dfe3cd97720963a08b69a1d82558588e59`
- Upstream comparison: `origin/main`; at Hotfix closure PRODUCT_HEAD was ahead 14 / behind 0.
- Current actual HEAD: re-run `git rev-parse HEAD` on entry. If it is only one handoff-artifact commit newer than PRODUCT_HEAD, record that difference and keep PRODUCT_HEAD as the product-code/docs baseline.
- Source root: `src/webgpt_as_codex/`
- Tests root: `tests/`
- Docs/SoT root: `docs/`
- Product Skill root: `skills/webgpt-as-codex/`
- Computer Agent Skill root: `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.skills\computer-agent\`
- Current Stage prompt: `prompts/STAGE-18-NEXT-WINDOW.md`
- Next Stage prompt: `prompts/STAGE-19-NEXT-WINDOW.md`
- Package/release authority: `pyproject.toml`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `README.md`, `manager/static/`, `components/*.json`.
- Expected dirty state at Stage18 start: clean product tree except the already-committed handoff prompt commit if present. Re-read, do not assume.
- Do not use `git reset`, `git clean`, force push, or broad destructive cleanup. Do not push unless the user separately asks.
- Single writer: Coding Tools owns repository edits/tests/Git. Remote Desktop Commander may inspect host state but must not concurrently edit repo files.
- Tool-local metadata: record Git pre-state before any IDE/semantic activation; new untracked tool cache/.serena created by this worker is local metadata only and must not enter the commit.

## Correct mandatory read order

The generated Stable Core's historical repository path is overridden here by the real current workspace. Read in this order:
1. `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\webgpt-as-codex\AGENTS.md`
2. `docs/CURRENT-PROJECT-STATE.md`
3. `docs/STAGE-17-POST-ACCEPTANCE-HOTFIX-CLOSURE.md`
4. `docs/STAGE-17-CLOSURE.md` only for the accepted Stage17 baseline boundary
5. `docs/ROADMAP-2026-09-20.md`
6. `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`
7. `docs/ARCHITECTURE.md`
8. `docs/DECISIONS-AND-RISKS.md`
9. `docs/DEPLOYMENT.md`
10. `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `pyproject.toml`
11. `skills/webgpt-as-codex/SKILL.md`, `loop-engineering.md`, `handoff.md`, `routing.md`, `validation.md`
12. Computer Agent files listed below.

## Computer Agent Skill bootstrap

Reload, do not inherit from chat memory:
- `.skills/computer-agent/SKILL.md`
- `.skills/computer-agent/routing.md`
- `.skills/computer-agent/environment.local.md`
- `.skills/computer-agent/workflows/coding.md`
- `.skills/computer-agent/workflows/cross-tool.md`
- `.skills/computer-agent/workflows/loop-engineering.md`
- `.skills/computer-agent/workflows/handoff-template.md`
- before final handoff: `.skills/computer-agent/workflows/browser.md`
- before completion: `.skills/computer-agent/validation.md`

Computer Agent current version from the previous stage is `1.1.17-local-candidate`. The previous Hotfix added:
- R50: a listener/health endpoint is not proof that a long-running runtime loaded the current code generation;
- R51: user desktop URL opening must not create or reuse automation-only browser profiles.
Exact changed rule files: `.skills/computer-agent/SKILL.md`, `workflows/cross-tool.md`, `workflows/browser.md`, `maintenance.md`, `environment.local.md`, `evals/scenarios.json`, `manifest.json`, `CHANGELOG.md`.
Reload these before execution. Preserve the shared Serena rule below.

## MCP locator and execution map

| MCP | Current known state | Locator | Stage18 use | Recovery/fallback |
|---|---|---|---|---|
| Coding Tools | local backend previously verified AVAILABLE, 18 tools | `http://127.0.0.1:8766/mcp`; state/start: `D:\AgentData\20_State\coding-tools-mcp\start-trusted.ps1` | primary repo read/audit/edit/tests/build/Git/docs | if direct schema absent, use local Streamable HTTP `initialize -> tools/list -> server_info`; if down, use the registered trusted launcher, then reconnect |
| Remote Desktop Commander | direct connector verified AVAILABLE on `JIAOLONG16proSeries` | direct `Remote_Desktop_Commander` namespace; no stable localhost HTTP should be invented | host/process/outside-workspace evidence only | if direct absent, follow Computer Agent dynamic package discovery; do not make it a second repo writer |
| Playwright MCP | local backend verified AVAILABLE, 26 tools; shared Edge extension context | `http://localhost:8931/mcp`; deployment `D:\AgentData\10_Workspaces\coding-tools-mcp-demo\.tools\playwright-mcp\`; start `start-extension.cmd` | final ChatGPT handoff only, unless an actual browser acceptance need appears | same MCP session for tabs/fill/submit/verify; if down, restart extension mode and re-handshake; Windows-MCP is handoff-only last fallback |
| Windows-MCP | local backend previously verified AVAILABLE, 14 tools | `http://127.0.0.1:8001/mcp`; config under `%USERPROFILE%\.windows-mcp\` | NOT_NEEDED for normal Stage18 repo work; native GUI only if a true OS/browser-chrome step appears | do not use for webpage DOM or repo editing |
| Serena | listener 9121 exists but is RESERVED by another task | `http://127.0.0.1:9121/mcp` | NOT_NEEDED: Stage18 is documentation/release/provenance work | DO NOT call `activate_project`, switch, restart or stop shared 9121. Use Coding Tools search/read for this stage. If later semantic need becomes mandatory, use an isolated fixed-project Serena slot rather than touching 9121 |
| Unified Gateway | previously verified 9330/87 tools | `http://127.0.0.1:9330/mcp` | NOT_NEEDED for translation work | preserve; do not mutate routes merely for Stage18 |

Direct schema NOT_EXPOSED is not service failure. For stage-critical local MCPs, verify `initialize -> tools/list -> minimal read-only probe` before declaring unavailable.

## Confirmed facts

- Hotfix product/docs closure commit is `310458dfe3cd97720963a08b69a1d82558588e59`.
- Stage17 and its post-acceptance Hotfix are CLOSED_LOCAL_VERIFIED; do not reopen them without contradictory evidence.
- Hotfix final gates: targeted 31 PASS; full repository 184 PASS; Ruff PASS; secret scan PASS; diff check PASS.
- Real desktop two-pass launch preserved the same core MCP/Gateway/Manager PIDs and reused the existing Edge `Default` profile.
- Computer Agent validator passed with 51 scenarios.
- The tracked human-readable-format inventory was about 70 candidates at handoff generation.
- `THIRD_PARTY_NOTICES.md` already exists and currently lists MCPJungle, mcp-auth-proxy, Tailscale, Serena, Coding Tools MCP, Playwright MCP, Windows-MCP and Remote Desktop Commander.
- `LICENSE` is the original Apache License 2.0 text and is authoritative.
- Existing tracked Chinese content is currently limited primarily to `manager/static/index.zh-CN.html`; Stage18 owns the repository-wide mirror treatment.

## Stage18 execution plan

### Step A — baseline and tracked-file language audit
Primary: Coding Tools.
- Re-read HEAD/status/ahead-behind and verify PRODUCT_HEAD ancestry.
- Run `git ls-files` and classify every human-readable candidate. At minimum inspect root README/AGENTS/LICENSE/NOTICE, all current docs, current Product Skill/Guides, human-readable component metadata/descriptions, packaging/release metadata and Manager shells.
- Do not translate code identifiers, commands, URLs, schema keys, hashes, protocol constants or machine-generated evidence merely because the file format is text.
- Historical closure/evidence files are canonical evidence: classify them explicitly. Do not silently rewrite historical English originals.
Expected evidence: a complete auditable source list and classification model before bulk translation.

### Step B — establish the Chinese mirror contract and coverage manifest
Primary: Coding Tools.
- Choose one consistent repository mirror convention based on current structure; avoid scattered ad-hoc suffixes.
- Create/update a machine-readable translation coverage manifest plus a human-readable explanation. Every audited candidate must have a status such as MIRRORED_CURRENT, BILINGUAL_INLINE, LANGUAGE_NEUTRAL, LEGAL_ORIGINAL_PRESERVED, HISTORICAL_EVIDENCE_PRESERVED_WITH_INDEX/MIRROR, or NOT_HUMAN_READER_CONTENT with reason.
- Add tests that fail when a required current human-readable source loses mirror coverage.
- Exact mirror paths must be deterministic and documented.

### Step C — complete current human-readable Chinese experience
Primary: Coding Tools.
- Translate current user/developer-facing repository entrypoints and live SoT/Skill/Guide documents that Stage18 classifies as mirror-required.
- Preserve terminology, commands, identifiers, URLs, file paths and code blocks exactly where semantics require.
- Cross-link English and Chinese entrypoints so a fresh Agent/user can choose language without guessing.
- Do not rewrite closed historical English evidence merely for cosmetic uniformity; provide the Stage18-declared mirror/index treatment instead.

### Step D — legal LICENSE and third-party provenance
Primary: Coding Tools.
- Preserve `LICENSE` byte-for-byte as the authoritative legal Apache-2.0 original.
- Add a Chinese reading translation with an explicit notice that it is non-binding and the English/original LICENSE controls on any discrepancy.
- Audit existing `THIRD_PARTY_NOTICES.md` against `components/*.json`, pyproject/runtime dependency declarations and current source/provenance metadata.
- Correct omissions or stale provenance; do not invent licenses or copy upstream license text unless repository evidence supports it.
- Add a Chinese counterpart/reading mirror for the notices where appropriate.
- Keep product README concise; provenance belongs in the dedicated notice files/metadata.

### Step E — package/release bilingual resource verification
Primary: Coding Tools.
- Update `pyproject.toml` or release-resource rules only if needed for the Stage18 bilingual contract.
- If package contents change, run an isolated wheel build/install smoke outside the source checkout and verify the intended bilingual release resources are present and readable.
- Never package machine-local state, prompts/receipts, credentials, browser profiles or private paths.

### Step F — tests and gates
Baseline is the Hotfix closure: 184 full tests PASS.
Required before Stage18 closure:
- new/targeted Stage18 translation/provenance tests;
- existing relevant packaging/Stage12/Stage17 resource tests;
- full `.venv\Scripts\python.exe -m pytest -q`;
- `.venv\Scripts\python.exe -m ruff check .`;
- `.venv\Scripts\python.exe scripts\secret_scan.py`;
- `git diff --check`;
- if packaging/resource lists changed: build wheel, install into an isolated environment, verify bilingual/notice/license resources from outside source checkout.
RED introduced by Stage18 is owned and must be fixed. A pre-existing external environment limitation must be classified, evidenced and cannot be disguised as PASS.

### Step G — docs-before-prompt closure
Before generating Stage19 prompt, inspect/update each live doc and record one of UPDATED_WITH_NEW_EVIDENCE / CHECKED_NO_CHANGE_REQUIRED / NOT_APPLICABLE_THIS_STAGE:
- `docs/CURRENT-PROJECT-STATE.md`
- `docs/ROADMAP-2026-09-20.md`
- `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS-AND-RISKS.md`
- `docs/DEPLOYMENT.md`
- `README.md` and its Chinese entrypoint/mirror
- translation coverage manifest/docs created by Stage18
- `THIRD_PARTY_NOTICES.md` and Chinese counterpart
- Product Skill/Guide bilingual treatment
- `skills/webgpt-as-codex/experience-ledger.md`
- new `docs/STAGE-18-CLOSURE.md`
Do not rewrite historical closure documents unless Stage18 explicitly creates separate mirror artifacts without altering the originals.

Stage18 progress must distinguish LOCAL_IMPLEMENTATION / LOCAL_VERIFIED / REAL_HOST_OR_DEVICE_VERIFIED. This stage does not get to claim host verification merely because repository translations exist.

## Failure recovery

Default state for ordinary failures is ACTIVE_RECOVERY:
`post-state -> classify -> same-tool adaptation -> structured fallback -> cross-tool fallback -> BLOCKED only if mandatory external condition remains`.

- Coding Tools revision mismatch: reread current revision/diff, then reapply context-anchored edit; never blind overwrite.
- Long test/build timeout: inspect command/process/output post-state before rerun.
- Serena: do not touch shared 9121 in this stage; use Coding Tools because semantic navigation is not required for translation/provenance ownership.
- Playwright final handoff timeout: inspect tabs/composer/user message/conversation URL first; never refill or resubmit until post-state proves the prompt was not sent.
- Windows-MCP instability: Stage18 normally does not need it. Do not convert repo work to coordinate GUI.
- Permission/security gate: never bypass through a broader MCP.
- If a reusable new failure is discovered, run Experience Absorption: `RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE`.

## Git / commit discipline

- Coding Tools is the repository write owner.
- Use path-scoped status/diff; no `git add .` if unrelated noise exists.
- Product/docs Stage18 closure commit comes before the Stage19 prompt artifact commit.
- Stage19 prompt `PRODUCT_HEAD`/SOURCE_HEAD must refer to the Stage18 product/docs closure commit, not to its later handoff-prompt commit.
- No push unless separately authorized.
- No reset/clean/force push.

## Exit criteria

Stage18 can close only when all are true:
- every tracked human-readable candidate is represented in the translation coverage audit with an explicit disposition;
- all current mirror-required human-readable entrypoints/docs/Skill/Guides have a complete Chinese treatment under the documented convention;
- authoritative original `LICENSE` is unchanged and the Chinese reading translation clearly states non-binding status;
- third-party notices/provenance are reconciled against repository evidence and have the required Chinese treatment;
- package/release resource behavior is updated and verified if Stage18 changed it;
- targeted and full gates pass;
- live docs + Stage18 closure are current;
- product/docs closure commit exists and Git post-state is verified;
- current handoff template/SoT are reloaded after that commit;
- `prompts/STAGE-19-NEXT-WINDOW.md` is freshly generated from the real Stage18 closure HEAD, validated and committed as a handoff artifact;
- Playwright submits that exact Stage19 prompt once and verifies a sent user message, a `/c/` conversation URL and a new assistant run/response.

## Next-stage definition

CURRENT_STAGE = STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES
NEXT_STAGE = STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE
AFTER_NEXT_STAGE = SUPPLEMENTAL-FINAL-ACCEPTANCE

Stage19 unique goal: prove the complete deployment contract end-to-end on clean/fresh-state and existing-machine preservation paths, including duplicate prevention, version/install adapters, Gateway safe calls, OAuth DCR/PKCE/refresh/401/authenticated MCP, Tailscale HTTPS, ChatGPT browser OAuth acceptance when available, fallback drills, multi-window concurrency, wheel/install/Desktop Manager and full repository gates.

Stage19 prompt path: `prompts/STAGE-19-NEXT-WINDOW.md`.

## Playwright automatic handoff rules

At Stage18 closure:
1. finish all live docs and product closure commit first;
2. reload `.skills/computer-agent/workflows/handoff-template.md`, browser workflow and final SoT;
3. local Playwright endpoint is `http://localhost:8931/mcp`; if direct schema is absent, `initialize -> tools/list`;
4. use one `mcp-session-id` for tabs/new/select/snapshot/fill/submit/verify;
5. reuse authenticated Edge shared context; do not create an isolated browser profile;
6. read the exact repo prompt file, fill only the real visible active composer;
7. verify length and first/middle/last content; if needed use the same whitespace-normalized SHA-256 on both sides;
8. submit exactly once;
9. after any timeout/error, check sent-message/URL/composer/generating post-state before any new action;
10. verify the sent message includes Stage19 `SOURCE_HEAD`, the URL is `/c/...`, and a new assistant run/response begins;
11. if Playwright authenticated context cannot be recovered but an already logged-in browser exists, Windows-MCP may be used only as the documented handoff transport fallback;
12. if all transports fail, write `STAGE_COMPLETE_HANDOFF_PENDING / PAUSED_HANDOFF_TRANSPORT`; do not reopen Stage18 product work.

## First user-visible update required from the Stage18 worker

The first update must state:
- current Stage18 name;
- actual probed availability for Coding Tools, Remote Desktop Commander, Playwright and any other tool it truly needs;
- that shared Serena 9121 is reserved/not needed and will not be switched;
- each tool's Stage18 role and fallback;
- the first concrete audit actions.
Then execute. Do not stop after planning.

## Full Recursive Handoff Invariant — MUST PROPAGATE VERBATIM IN MEANING

1. Handoff is a recursive chain: this worker must not only complete CURRENT_STAGE -> NEXT_STAGE, it must explicitly require the NEXT_STAGE worker to continue NEXT_STAGE -> AFTER_NEXT_STAGE.
2. Every handoff prompt must state CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE.
3. Continue across batch/stage boundaries. Finishing one Stage or Batch is not a Global Loop Stop Condition.
4. Every next prompt must be self-contained with repo/worktree/branch/HEAD/upstream/source/tests/SoT/Skill/MCP locators/gates/dirty state/BLOCKED_ENV/failure recovery.
5. PRODUCT_STAGE_COMPLETE and HANDOFF_COMPLETE are independent. If product work is complete but transport fails, record STAGE_COMPLETE_HANDOFF_PENDING and recover only the handoff layer.
6. After timeout/non-zero/connection loss on a side-effecting handoff action, inspect real post-state before any retry; duplicate sending is forbidden.
7. For strong long-prompt validation, use identical whitespace normalization + SHA-256 on both local prompt and browser composer. UTF-8 byte count is not JavaScript character count.
8. Rediscover MCP state every window. For local Playwright reconnect, keep the entire multi-step handoff inside one mcp-session-id and never reuse stale tab indexes/refs across sessions.
9. Continue Experience Absorption as RECOVER -> DISTILL -> GENERALIZE -> PATCH -> EVAL -> VALIDATE -> PROPAGATE.
10. Program state must distinguish ACTIVE / PAUSED_EXTERNAL_BLOCKER / USER_STOPPED / GLOBAL_LOOP_COMPLETE. User stop and an unrecoverable safety/external blocker are unfinished states; only the canonical Program Completion Gate can authorize GLOBAL_LOOP_COMPLETE.
11. The NEXT_STAGE worker, when generating its own next prompt, must again carry this full recursive invariant forward.
12. If the generated next prompt lacks this complete invariant, the Zero-Guess / Recursive Handoff gate fails and automatic submission is forbidden.

## Start now

Use this execution sequence:
`Skill bootstrap -> MCP availability/map -> Git/SoT baseline -> tracked-file language audit -> mirror/coverage design -> Chinese mirror implementation -> LICENSE/notices provenance -> package/release resource verification -> targeted gates -> full gates -> ALL live-doc checks/updates -> Stage18 product closure commit -> reload Stable Core + final SoT -> fresh Stage19 prompt -> handoff artifact commit -> Playwright handoff`.

Do not stop at a progress report while owned work remains. Do not silently change closed runtime behavior. Do not swallow Stage19.
