# Current Project State

[**English**](CURRENT-PROJECT-STATE.md) | [简体中文](zh-CN/CURRENT-PROJECT-STATE.md)

CURRENT_STAGE = GLOBAL_LOOP_COMPLETE
NEXT_STAGE = TERMINAL
AFTER_NEXT_STAGE = TERMINAL
AFTER_NEXT_STAGE = TERMINAL

Stage 1: CLOSED_LOCAL_VERIFIED
Stage 2: CLOSED_LOCAL_VERIFIED
Stage 3: CLOSED_LOCAL_VERIFIED
Stage 4: CLOSED_LOCAL_VERIFIED
Stage 5: CLOSED_LOCAL_VERIFIED
Stage 6: CLOSED_LOCAL_VERIFIED
Stage 7: CLOSED_LOCAL_VERIFIED
Stage 8: CLOSED_LOCAL_VERIFIED
Stage 9: CLOSED_LOCAL_VERIFIED
Stage 10: CLOSED_LOCAL_VERIFIED
Stage 11: CLOSED_LOCAL_VERIFIED
Stage 12: CLOSED_LOCAL_VERIFIED
Final Overall Acceptance: CLOSED_LOCAL_VERIFIED
Project Complete: CLOSED_LOCAL_VERIFIED

Supplemental chain (user requirements added after the accepted TERMINAL state):
- Stage 13: CLOSED_LOCAL_VERIFIED
- Stage 14: CLOSED_LOCAL_VERIFIED
- Stage 15: CLOSED_LOCAL_VERIFIED
- Stage 16: CLOSED_LOCAL_VERIFIED
- Stage 17: CLOSED_LOCAL_VERIFIED
- Stage 18: CLOSED_LOCAL_VERIFIED
- Stage 19: CLOSED_LOCAL_VERIFIED; REAL_HOST_VERIFIED + REAL_CHATGPT_VERIFIED
- Supplemental Final Acceptance: CLOSED_LOCAL_VERIFIED + REAL_HOST_VERIFIED

The supplemental chain does not invalidate the accepted Stage 1-12 evidence. It owns only the later one-repository deployment, production unified Gateway, fresh-machine dependency/bootstrap, complementary Remote Desktop Commander recovery, multi-window concurrency, bilingual Manager/desktop experience and complete Chinese mirror requirements.

Stage 13 live implementation evidence so far:
- fresh-machine environment reporting now distinguishes Windows/Python/winget/Tailscale installed/version/login/online/MagicDNS/Funnel state plus WebGPT private runtime-binary readiness;
- current host verified Tailscale 1.102.2, online state, MagicDNS and configured Funnel evidence, with `ready_for_edge=true`;
- bootstrap can optionally install an absent Tailscale through the allowlisted winget package while preserving an existing installation;
- WebGPT private runtime provisioning now has approved official release URLs and SHA-256 verification for MCPJungle and mcp-auth-proxy, preserving existing binaries by default;
- production Edge/runtime and route-sync work is present as Stage 13/14 work-in-progress and is not yet closed;
- installed Serena source confirms its standard agent has process-wide active-project state, and switching projects shuts down the previously active project; this explains observed cross-window project collisions and is owned by Stage 16;
- live Coding Tools evidence shows more than one server-managed command can be active with overlapping execution windows, while one server remains bound to one configured workspace; parallel writers therefore still require worktree/workspace isolation.

Stage 13 closure: `docs/STAGE-13-CLOSURE.md`.

Stage 14 proof:
- WebGPT's private MCPJungle route sync is idempotent: same name/transport/URL is preserved, missing routes are registered, changed routes are replaced only inside the WebGPT Gateway registry;
- current live Gateway aggregated Coding Tools, Serena, Playwright and Windows-MCP through localhost endpoints and returned MCP initialize 200 plus `tools/list=87`;
- production OAuth Edge is now a repository-owned Runtime Supervisor target while external MCP backends remain outside WebGPT kill/restart authority;
- OAuth credential is generated/reused only in the machine-local WebGPT secrets root;
- a real production Tailscale `:10003` run passed public OAuth metadata, unauthenticated MCP 401, DCR + PKCE + token, authenticated MCP safe call, controlled Edge restart, refresh-token continuity and a second authenticated MCP call with the same 87-tool surface;
- the real Edge restart did not restart Serena, Coding Tools, Playwright or Windows-MCP;
- full repository gate: 120 PASS, Ruff PASS, secret scan PASS, `git diff --check` PASS.

Stage 14 closure: `docs/STAGE-14-CLOSURE.md`.

Stage 15 proof:
- all eight built-in components now carry explicit install/latest-source metadata; automatic adapters additionally carry explicit toolchain requirements and compatibility windows;
- `webgpt-codex deploy` resolves latest stable evidence through PyPI, npm, GitHub Releases or winget and keeps installed/latest/verified-compatible/install/lifecycle authority separate;
- GitHub Release artifacts require expected repository/asset identity plus release-provided SHA-256 before provisioning;
- healthy existing listeners are preserved even when the executable/package is absent from the current shell PATH;
- `@latest` is never used as an installed-version probe; unknown local versions remain unknown rather than being replaced by upstream metadata;
- an upstream version outside the manifest compatibility window fails closed; a newer compatible local install is preserved and never downgraded;
- system-process components such as Tailscale are not misclassified merely because they have no MCP HTTP listener;
- WebGPT install ownership is persisted machine-locally and does not automatically grant runtime kill/restart authority; stopped external installs require explicit `--adopt-external` before controlled upgrade/adoption;
- current-machine dry-runs made no mutation and proposed no duplicate install. Live PyPI/npm/winget metadata resolved successfully; same-stage GitHub API evidence resolved MCPJungle 0.4.6 and mcp-auth-proxy 2.10.2. An intermediate strict rerun saw both GitHub lookups fail; on the final rerun MCPJungle recovered fresh 0.4.6 evidence while mcp-auth-proxy still returned `HTTPError`, so only that row remained blocking/unavailable;
- successful latest-release metadata is cached machine-locally for at most 24 hours as verified fallback evidence. Cache reuse is explicitly marked `latest_fresh=false` / `latest_provenance=verified-cache` and cannot authorize install/upgrade; a cacheless failure remains unavailable/blocking;
- full repository gate: 146 PASS, Ruff PASS, secret scan PASS, `git diff --check` PASS.

Stage 15 closure: `docs/STAGE-15-CLOSURE.md`.

Stage 16 proof:
- repository-owned `concurrency.py` provides machine-local fixed-project Serena slots on isolated loopback ports; shared port 9121 is explicitly excluded from pool ownership and mutation;
- slot receipts bind project, owner, port, PID birth token, image name and launch fingerprint, with idempotent acquire/release, stable free-slot reuse, stale-receipt cleanup and occupied-port fail-closed behavior;
- the current CLI-installed Serena used for isolated workers self-reported 1.28.1. Its installed source still has one process-wide `_active_project`, shuts down the prior active project on switch, and uses an active-project lock/context in the ProjectServer path. Separately, the user's already-running shared direct Serena still reports 1.7.0 with active project `Jarvis-dev`; Stage 16 never switched or restarted that shared instance;
- real isolated Serena instances on non-9121 ports completed MCP initialize and `tools/list=29`; the probes were cleaned up without restarting or switching the shared 9121 instance;
- Coding Tools concurrency is now an executable policy boundary: reads/bounded independent processes do not take a writer lease, one configured workspace rejects out-of-binding paths, one worktree has one machine-local writer lease, and a different worktree may have a distinct writer;
- Remote Desktop Commander / Windows-MCP native GUI side effects share a machine-local lease with owner, heartbeat/expiry, idempotent release and stale reclaim;
- complementary recovery now carries attempt identity, visited paths, hop budget and one mutation owner per component/attempt. No lifecycle authority is diagnose-only; ambiguous timeout/non-zero mutation checks bounded post-state before any new mutation;
- Stage14-16 targeted regression: 52 PASS; full repository: 167 PASS; Ruff, repository secret scan and `git diff --check`: PASS;
- current production listeners remained on their baseline PIDs after Stage 16 probing: Gateway 9330 = 77084, Windows-MCP 8001 = 50508, Playwright 8931 = 53880, shared Serena 9121 = 38924. Shared Serena also remained on active project `Jarvis-dev`; temporary Serena 9477/9478 listeners were absent at final post-state;
- Computer Agent Skill advanced to `1.1.16-local-candidate`; validator reports `VALIDATION_OK`, 49 scenarios, including R48 concurrency isolation and R49 bounded process post-state observation.

Stage 16 closure: `docs/STAGE-16-CLOSURE.md`.

Stage 17 proof:
- the five preserved Stage17/18 WIP files were reconciled without reset/stash/overwrite; the previously missing `manager/static/index.zh-CN.html` is now a real tracked product resource;
- English and Chinese Manager pages share one `manager.js` / `manager.css` functional contract, while `/`, `/zh` and `/en` retain explicit language routing. The desktop launcher defaults `WEBGPT_CODEX_UI_LANG=zh-CN`;
- Manager local-config output now exposes product/deployment/environment/component/Gateway/OAuth/HTTPS/migration state through public-safe summaries. Executable paths, secret-file paths and Tailscale private DNS details are not emitted;
- OAuth password set/reveal/regenerate is loopback/control-header/confirm gated. Regenerate now creates a new value rather than reusing the existing secret. Plaintext is returned only by the explicit local reveal response and never recorded in activity/log evidence;
- local environment/component/OAuth mutations share one non-blocking Manager mutation lock; unknown payload fields/body overflow fail closed; built-in component deletion is blocked; custom create/delete stays idempotent and never grants route/lifecycle authority;
- the Manager exposes secret-safe recent activity, mutation pending/disabled feedback, MCP URL copy/open controls, visible focus, labels/live regions and reduced-motion handling. Motion is limited to real pending state;
- the previously installed Stage8 desktop/autostart launchers were recognized only through the exact historical WebGPT launcher structure, upgraded in place to the Chinese default and left `managed=true`; arbitrary marker-bearing files remain unmanaged/refused;
- Playwright reconnected to the existing 8931 Extension MCP with one session and verified a disposable Manager on port 9217: both Chinese and English views rendered the same seven sections, 10 mutation controls, two live regions, six labels, two URL rows and eight component cards. No mutation control was clicked;
- the temporary Manager stop first returned non-zero. R49 was followed: listener plus PID parent/image/command identity were re-observed before the verified temp-only process tree was force-stopped. Port 9217 and its temporary PIDs were absent afterward;
- production listeners remained unchanged after Stage17 host/browser work: Gateway 9330 = 77084, Windows-MCP 8001 = 50508, Coding Tools 8766 = 54448, Playwright 8931 = 53880, shared Serena 9121 = 38924. Shared Serena was never switched or restarted;
- Stage8/Manager/Stage11/12/14/15/16/17 regression gate reached 100 PASS before final full closure; the final full repository gate reached 176 PASS. Ruff, repository secret scan and `git diff --check` passed;
- a normal isolated PEP517 wheel build succeeded after the development venv's optional `python -m build` harness was found unavailable. The wheel installed outside the source checkout and loaded English HTML, Chinese HTML, shared CSS and shared JS from the installed resource tree;
- Stage17 = 100%. Supplemental chain progress = 5/8 closure nodes = 62.5%. Status: `LOCAL_IMPLEMENTATION + LOCAL_VERIFIED + REAL_HOST_VERIFIED`.

Stage 17 closure: `docs/STAGE-17-CLOSURE.md`.

Stage 17 post-acceptance hotfix: CLOSED_LOCAL_VERIFIED.

Post-acceptance Hotfix proof:
- reproduced the real mixed-version Manager on port 9200: root HTML came from the new Stage 17 static tree while `/en`, `/zh`, `/manager.css`, `/manager.js` and `/api/local-config` were missing from the old long-running route table;
- Runtime Supervisor now records a Manager runtime generation, probes the Stage 17 resource/API contract and refreshes a stale process only after WebGPT ownership/process identity is proven;
- a strict legacy WebGPT Manager process may be safely adopted for one stale refresh; an unrelated or ambiguous 9200 listener is never killed;
- Windows venv launcher indirection is accounted for by rebinding the machine-local receipt to the actual listening Python PID while preserving launcher identity for bounded cleanup;
- the desktop opener now reuses the already-running normal Microsoft Edge profile when available and otherwise falls back to the Windows default URL handler; it does not create a temp/isolated/InPrivate automation profile;
- real Desktop launcher acceptance returned Chinese root HTML plus HTTP 200 for CSS/JS/local-config, preserved the same Manager/Gateway/core-MCP PIDs across a second launch, and preserved the existing Edge `Default` top-level process without creating a new profile window;
- Windows-MCP live desktop evidence showed the full Manager control tree in the foreground rather than the prior unstyled/bare page;
- targeted Hotfix/Stage8/Stage17 gate: 31 PASS; full repository: 184 PASS; Ruff, repository secret scan and `git diff --check`: PASS;
- Computer Agent Skill advanced to `1.1.17-local-candidate`; validator reports `VALIDATION_OK`, 51 scenarios, adding R50/R51 for mixed-version long-running services and desktop-browser-profile separation.

Hotfix closure: `docs/STAGE-17-POST-ACCEPTANCE-HOTFIX-CLOSURE.md`.

Stage 18 proof:
- a deterministic repository-wide mirror contract now covers root entrypoints, current live docs and Product Skill/Guides while preserving protocol identifiers, commands, URLs, schema keys and hashes;
- `docs/TRANSLATION-COVERAGE.json` classifies 155 Stage18 text-format candidates/dispositions: 21 mirrored current sources, 23 mirror targets, 1 preserved legal original, 15 language-neutral artifacts, 36 preserved historical-evidence artifacts, 58 non-reader executable artifacts and 1 bilingual-inline contract;
- historical closure/cost/prompt evidence was not rewritten; Chinese readers use `docs/zh-CN/HISTORICAL-EVIDENCE-INDEX.md`;
- root `LICENSE` remains 11,558 bytes with SHA-256 `1eb85fc97224598dad1852b5d6483bbcf0aa8608790dcc657a5a2a761ae9c8c6`; `LICENSE.zh-CN.md` is explicitly non-binding and defers to the English original;
- third-party provenance now reconciles all eight `components/*.json` entries plus setuptools/requests/pytest/Ruff from `pyproject.toml`; bilingual notices and machine-readable `docs/THIRD-PARTY-PROVENANCE.json` are public-safe;
- the wheel now carries a bounded 9-file bilingual release/legal/provenance resource group in addition to the existing component manifests and bilingual Manager static UI;
- targeted Stage18/12/17/Hotfix gate: 27 PASS; full repository: 191 PASS; Ruff, secret scan and `git diff --check`: PASS;
- a fresh PEP517 wheel installed outside the source checkout and verified 8 component manifests, 4 Manager static resources, all 9 Stage18 release resources, the original license hash, `load_components()==8` and CLI version 0.1.0;
- shared Serena 9121 was not switched/restarted; Stage18 changes no closed runtime behavior and claims `LOCAL_IMPLEMENTATION + LOCAL_VERIFIED`, not new real-host/device acceptance.

Stage 18 closure: `docs/STAGE-18-CLOSURE.md`.

Repository: local checkout; use the active project/workspace binding rather than committing a machine-specific absolute path.
Stage 4 proof: unified Gateway, 4 core MCP backends, 87 tools, safe calls PASS.
Stage 5 proof: real Tailscale HTTPS edge, DCR + PKCE + token + 401 gate + restart + refresh + authenticated MCP call PASS.
Stage 6 proof: repository-owned loopback Manager, registry-backed component status, six-level health schema, Gateway/OAuth/Tailscale/Public-MCP/Doctor surfaces, fixed action contracts, secret/private-URL redaction, 30 tests PASS and Ruff/secret scan PASS.
Stage 7 proof: idempotent discovery-first bootstrap, deep prerequisite-aware Doctor with sanitized machine-local persistence, bounded/confirmable Repair with backups and no arbitrary-command surface, Manager Doctor/Repair executors only, handoff explicit-tab selection + active-composer hydration hardening, 41 tests PASS, Ruff PASS and secret scan PASS.
Stage 7 live evidence: healthy Serena/Coding Tools/Playwright/Windows-MCP listeners passed MCP initialize + tools/list + declared safe call. Current MCPJungle and default OAuth listeners were truthfully reported down and were not started because runtime lifecycle belongs to Stage 8.
Stage 8 proof: repository-owned runtime supervisor with PID birth/image ownership checks, stale/reused-PID rejection, discovery-first idempotent Start All, targeted Manager Restart, independent Manager/browser lifetime, reversible credential-free desktop launcher/autostart, 57 tests PASS, Ruff PASS and secret scan PASS.
Stage 8 live evidence: first Start All started only MCPJungle while preserving healthy Serena/Coding Tools/Playwright/Windows-MCP; the second run preserved the same owned MCPJungle without duplication. Process-only evidence preserved Tailscale and Remote Desktop Commander. Targeted MCPJungle restart changed PID after bounded shutdown; Manager rejected restart scope for Serena. Launcher exited while the Manager remained reachable. `mcp-auth-proxy` remains explicitly unmanaged/not started because the machine has Stage 5 E2E credential state but no separate production/autostart credential contract.
Stage 9 proof: discovery-first generic Add MCP with manifest/secret validation, real initialize + tools/list capability evidence, four-state success/unavailable/failed/unattempted semantics, machine-readable Operating Guide schema, routing recommendation, dry-run/default + explicit machine-local apply, idempotence/conflict protection, registry/Manager/Doctor visibility without lifecycle authority, public-safe Serena/Coding Tools Guide attachments, bounded real-HTTP fake MCP coverage, 70 repository tests PASS, Ruff PASS and secret scan PASS.
Stage 9 live evidence: local Coding Tools initialize/tools/list succeeded with 18 exposed tools and local Serena succeeded with 29 tools. This supersedes only transient availability evidence from the end of Stage 8; it does not change Stage 8 ownership boundaries. Coding Tools remained unbound from this repository in the web connector and web Serena exposed no active language server for symbol overview, so the stage correctly diagnosed binding/session capability before using host/local fallback.
Stage 10 proof: executable durable Loop Engineering closure state, public-safe stage-cost evidence, evidence-driven closure reserve and bounded split decisions, durable late-bound handoff plans, stronger four-pointer prompt validation, exactly-once Playwright submission semantics, 32 Stage 10/handoff tests PASS, 91 full repository tests PASS, Ruff PASS, secret scan PASS and git diff check PASS.
Stage 10 dogfood evidence: Coding Tools was still bound away from this repository. Both web and direct local Serena reported the target project, but real semantic symbol overview reproduced an Active language servers: [] backend failure despite the local config summary saying ready. Stage 10 therefore classified the failure correctly and used approved repository/host fallback. The run reached the soft budget and froze scope during closure rather than adding more implementation.
Stage 10 first post-commit handoff failed before typing/submission because the extension remained current while one already-created blank ChatGPT tab existed. The minimum handoff boundary was reopened to recover only a unique blank tab after new-tab diff + one refresh fail; the stale 74a1dab prompt was invalidated and never sent.
Stage 11 proof: fixed repository-owned Manager Update executor with repository-approved component/version/source/digest contracts; Host/Origin and action-payload fail-closed Manager boundaries; hardened custom MCP trust and schema persistence; atomic machine-local state writes with bounded multi-file rollback; runtime identity checks before binary update; 104 full repository tests PASS, Ruff PASS, secret scan PASS and git diff check PASS.
Stage 11 execution evidence: the web Coding Tools functions disappeared mid-window after earlier successful binding, so the failure was classified as tool-session exposure drift and the same repository was validated through Desktop Commander fallback. No target failure was inferred from the connector disappearance.
Stage 12 proof: README/release-facing documentation was reconciled to the verified Stage 0-11 behavior; the stale statement that Update remained deferred was removed; Skill metadata was aligned at 0.6.0; a real baseline wheel install exposed a release-only resource defect where built-in manifests and Manager static UI were absent; the minimum packaging boundary was corrected by explicit public runtime data files plus source-or-installed resource resolution; a rebuilt isolated wheel loaded all 8 built-in manifests and Manager UI; post-commit handoff evidence also hardened duplicate tab-inventory parsing; 108 repository tests PASS, Ruff PASS, secret scan PASS and git diff check PASS.
Stage 12 release boundary: the wheel contains Python runtime code, public component manifests and Manager static UI only. Stage docs/prompts/Skill source remain repository artifacts, while machine-local state, staged update files, handoff receipts, credentials, PIDs/process evidence and browser/account state remain outside release artifacts.
Final Overall Acceptance proof: Stage 0 baseline/original goals plus Stages 1-12 were reconciled without an unresolved ownership, security or release contradiction. A fresh wheel built from the accepted Stage 12 HEAD installed in a separate environment, reported version 0.1.0, exposed the console entry point, loaded all 8 built-in component manifests from the installed share tree, served the Manager static UI, returned HTTP 200 from /healthz, /api/actions and /, and retained only the five fixed Manager action contracts. Final full tests remained 108 PASS with Ruff, secret scan and git diff check PASS; the tracked-file inventory remained public-safe.
Final canonical-launcher dogfood later observed Serena's external listener down. Start All reported it as required/unmanaged missing and did not restart it; this is current external-service health drift, not repository lifecycle ownership. The same dogfood exposed a service-context shell-folder expansion defect, which was corrected and re-probed to resolve the real user Desktop/Startup paths even when `USERPROFILE`/`APPDATA` are absent.
Final Windows post-state: the managed desktop launcher is installed on the real user Desktop. Autostart passed a real install -> status -> uninstall -> absent -> reinstall -> present round trip and is left installed/managed in the real user Startup folder. The erroneous literal `%USERPROFILE%` tree created by the first probe was removed and confirmed absent.
First Stage 9 handoff attempt failed before typing/submission because ChatGPT's hidden autofocus fallback textarea also appeared active in the accessibility snapshot. No user message was sent. The minimum handoff helper boundary was reopened to focus a DOM-visible editable composer before consuming a fresh active snapshot ref.

Cross-stage supplemental contract is active immediately:
- the Computer Agent / WebGPT-as-Codex Skill self-evolves from real execution evidence across the whole chain, not only MCP usage;
- repeated friction follows Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse;
- routing decides WHICH capability to use, while MCP Operating Guides teach HOW to use the selected capability correctly from actual exposed tools/schema and verification evidence;
- one preferred-tool failure is not proof that the tool is unavailable; diagnose misuse, binding, session, auth, schema and harness state before justified fallback;
- user guidance that reveals a reusable operating principle is experience input and is classified into Skill, MCP Guide, machine-local inventory/config or one-off evidence;
- Stage sizing currently uses an approximately 20-minute soft execution budget including closure/handoff, not a claimed platform timeout. Shorter fully closed stages are preferred over unfinished closure, and bounded sub-stages are allowed when closure is at risk;
- future verified stages/runs continue collecting stage-cost evidence (implementation/closure effort, retries, tool switches, tests/docs, handoff first-pass success and almost-done incidents) so the heuristic can self-correct without inventing a platform timeout.

Remaining planned roadmap:
- `SUPPLEMENTAL-FINAL-ACCEPTANCE`
- `GLOBAL_LOOP_COMPLETE`

See `docs/ROADMAP-2026-09-20.md`, `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`, `docs/DEPLOYMENT.md` and `docs/CONCURRENCY-AND-FALLBACK.md`.

Supplemental ownership:
- Stage 9 productizes MCP Guide template/onboarding, capability discovery, inventory/routing attachment and guide validation/feedback.
- Stage 10 productizes self-evolving Loop Engineering, stage sizing/closure budget, context/execution-window resilience, recursive Playwright continuation and handoff failure recovery. Bounded follow-up stages are allowed if evidence justifies them.

Recursive handoff invariant:
The original Final Overall Acceptance and Project Complete remain CLOSED_LOCAL_VERIFIED. The supplemental chain inherits the same exact closure/handoff rules if a new window is required. The current user has explicitly authorized continuous Loop Engineering until the supplemental roadmap is fully closed; do not terminate at an intermediate supplemental stage merely because a prior TERMINAL sentinel once existed.

Stage 19 proof:
- canonical public MCP identity is HTTPS 443 with no explicit legacy port; the live Funnel maps canonical HTTPS to the repository OAuth compatibility edge on loopback 9341;
- a real recovery incident proved that raw OAuth child liveness on 9340 is not Edge readiness: Start All had incorrectly preserved an unmanaged 9340 listener while 9341 was absent. Runtime supervision now treats repository-owned OAuth Edge readiness as the 9341 contract and no longer reports that state fully ready;
- the Edge can safely reuse an already-running OAuth proxy only when the listener is the expected local port and its advertised issuer matches the current canonical public base. The compatibility edge then restores 9341 without rotating the OAuth password or changing public identity;
- Windows launcher-to-listener PID rebinding now applies to the OAuth Edge as well as Manager, so the receipt follows the real 9341 listener and generation/contract readiness no longer false-reds after venv launcher indirection;
- real host recovery restored 9341 metadata 200, public /mcp 401 and canonical OAuth metadata 200 while keeping the same public URL/issuer;
- controlled production OAuth E2E passed public metadata, protected 401, DCR + PKCE token, authenticated MCP with 87 tools, Edge restart, refresh-token continuity and authenticated MCP after restart with the same 87-tool surface;
- the user then reconfigured the ChatGPT connector successfully; after that success the production connector/Funnel/OAuth state was frozen against further disruptive acceptance in this stage;
- full repository gate: 205 PASS; Ruff PASS; SECRET_SCAN_PASS; git diff --check PASS;
- a fresh wheel installed into a new external venv and verified 8 component manifests, 4 Manager resources, all 9 release resources, the authoritative LICENSE hash and CLI version 0.1.0.

Stage 19 closure: docs/STAGE-19-CLOSURE.md.

Supplemental RDC recovery-plane proof:
- Remote Desktop Commander remains an independent complementary full-machine repair/control plane, not a Gateway child, WebGPT READY prerequisite, OAuth/Funnel component or Gateway lifecycle dependency;
- current recovered RDC runtime is fixed at 0.2.51 instead of resolving `@latest` on each startup;
- health is now explicitly four-layered: installation, local process, control plane and execution plane;
- the historical incident demonstrated that device visible/authenticated/online can coexist with an unusable live command transport, so control-plane `online` is never sufficient health proof;
- local recovery hardened startup/session handling and retries missing broadcast transport capability after presence is already tracked;
- real connector-side acceptance passed `list_devices`, `ping` -> `pong`, `get_config` and a read-only host file probe, with `transport_broadcast_v1` present;
- therefore `RDC_INSTALLATION`, `RDC_LOCAL_PROCESS`, `RDC_CONTROL_PLANE`, `RDC_TRANSPORT_BROADCAST_V1` and `RDC_EXECUTION_PLANE` are VERIFIED for this acceptance snapshot;
- the fallback matrix is non-recursive: healthy WebGPT may repair unhealthy RDC; healthy RDC may repair unhealthy WebGPT; an unhealthy plane is never selected as the active recovery executor; both-down requires local startup/reboot/human-local recovery;
- RDC and Windows-MCP share physical desktop GUI state, so mouse/keyboard/focus/clipboard/native-dialog mutations remain serialized through the machine GUI lease;
- this RDC closure did not force a new physical Windows reboot. Process restart/session restore and idempotent local startup are verified; any full-reboot claim must come from separate real reboot evidence.

RDC recovery-plane closure: docs/RDC-FINAL-RECOVERY-PLANE-CLOSURE.md.

## Supplemental Final Acceptance proof

- desktop/reboot recovery repair is integrated: Start All waits boundedly for Edge prerequisites after reboot, fail-closes when they remain unavailable, and Doctor exposes prerequisite context instead of reporting a false-ready Edge;
- real host `Start All` ran twice with `ok=true`, `fully_ready=true`, `required_unmanaged_missing=[]`, preserving Manager PID 37400, OAuth Edge PID 42036 and Gateway PID 34744 rather than duplicating healthy services;
- real Doctor returned `status=pass`, zero required failures/warnings, eight components, public HTTPS protected-resource 200 and unauthenticated MCP 401 with OAuth challenge;
- Desktop launcher and Windows-login autostart are both installed/managed with `upgradeable=false`; manual launch dispatches the Manager through the Windows default URL handler and reports `browser_open_requested=true` / `browser_open_dispatched=true`; foreground activation is best-effort only;
- the manual desktop launcher contains a fixed post-READY machine-local overlay extension point. Current-host CloudBase remains only in that local overlay and MCPJungle machine state; it is explicitly NOT release content and autostart does not invoke it;
- RDC final recovery plane is VERIFIED per `docs/RDC-FINAL-RECOVERY-PLANE-CLOSURE.md`; WebGPT and RDC remain complementary independent recovery planes;
- Agent Skill 1.2.0 is unified: `skills/computer-agent/` is the canonical portable core, `skills/webgpt-as-codex/` is the product specialization, and the machine-local `.skills/computer-agent/` uses the same portable core plus local environment/inventory/state overlays;
- local Skill sync is `PORTABLE_SKILL_SYNC_OK`; validator is `VALIDATION_OK`, 26 required files / 53 scenarios; Experience Ledger is preserved losslessly between canonical Computer Agent and WAC product profile;
- fresh installed wheel verified package 0.1.0, Computer Agent 1.2.0, WAC Skill 1.2.0, 53 scenarios, matching Experience Ledger, RDC Guide and Chinese WAC profile;
- final pre-closure repository regression: targeted 52 PASS; full repository 225 PASS; Ruff PASS; SECRET_SCAN_PASS; `git diff --check` PASS.
- terminal fresh wheel SHA-256: `3082f5e1d8db3a5e3dc1565ee4574917b7c5806fb146e840a9e2add6c2b5cd17` (339894 bytes); external venv install reverified 8 components, 4 Manager resources, 9 release resources, Skill 1.2.0/1.2.0, 53 scenarios and ledger match;

Supplemental Final Acceptance closure: `docs/SUPPLEMENTAL-FINAL-ACCEPTANCE-CLOSURE.md`.

PROGRAM_STATE = GLOBAL_LOOP_COMPLETE


## Post-complete maintenance reconciliation — 2026-09-21

`PROGRAM_STATE` remains `GLOBAL_LOOP_COMPLETE`. This maintenance pass does not reopen the closed Stage 1-19 program; it supersedes current deployment/Skill/startup facts that changed after Supplemental Final Acceptance.

Current accepted truth:
- the product and the only canonical Agent Skill are both **WebGPT-as-Codex**;
- canonical release Skill: `skills/webgpt-as-codex/`, version `1.3.0`;
- machine-local workspace Skill: `.skills/webgpt-as-codex/` using the same portable core plus local environment/inventory/state overlays;
- user shared Skill source and Codex/Claude junctions now use `webgpt-as-codex`; the old active `computer-agent` 1.0.0-local-candidate source/junctions are retired and backed up outside active Skill roots;
- the former Computer Agent Experience Ledger, MCP Guides, GUI/Playwright workflows, Loop Engineering rules and all original 53 regression scenarios are preserved inside the single WAC Skill; three legacy contract aliases (`serena-down`, `handoff`, `parallel-edit`) are also restored, for 56 scenarios total;
- release packaging now declares only `share/webgpt-as-codex/skills/webgpt-as-codex/**`; there is no second Computer Agent release entry point;
- canonical Skill sync command is `scripts/sync_webgpt_skill.py`; the obsolete root `scripts/sync_computer_agent_skill.py` has been retired.

Startup / OAuth correction accepted in this maintenance pass:
- Windows Startup now has one active WebGPT entry: `WebGPT-as-Codex-Autostart.cmd`;
- `%LOCALAPPDATA%\WebGPT-as-Codex\local-prestart.cmd` is the machine-local pre-Start-All hook for already-approved external MCP backend launchers; it contains no secrets and must never claim public HTTPS 443;
- legacy duplicate Local Remote MCP / standalone Serena startup entries were disabled after the WAC launcher was proven upgradeable and working;
- legacy `remote-mcp-unified` Manager processes on port 9199 were stopped; WebGPT Manager remains the control surface on 9200;
- OAuth Edge readiness now requires the real Tailscale Funnel 443 target to be `http://127.0.0.1:9341`, in addition to local 9341/9340 identity/generation/issuer contracts;
- the running OAuth Edge periodically detects if Funnel 443 is changed away from the managed 9341 edge and fails out of READY instead of remaining false-green;
- the launcher supports a bounded wait for required unmanaged backends during Windows-login recovery.

Real-host startup evidence from this maintenance pass:
- direct execution of the installed Windows Autostart path completed twice with exit code 0;
- first run reached `fully_ready=true`, `required_unmanaged_missing=[]` and refreshed the intentionally stale OAuth Edge generation introduced by this code change;
- second run again reached `fully_ready=true`, `required_unmanaged_missing=[]` and preserved the same healthy Manager/Gateway/OAuth Edge instead of duplicating them;
- live Funnel after the startup run kept canonical HTTPS 443 -> `http://127.0.0.1:9341`, while the independent compatibility endpoints remained on their assigned non-443 ports;
- a physical Windows reboot has still not been forced in this maintenance pass; any claim of full cold-reboot acceptance still requires a separate real reboot observation.

Agent-native deployment:
- `prompts/ONE-CLICK-AGENT-DEPLOY.md` is the current repository prompt for handing the repository to a Windows-capable AI agent;
- it covers environment discovery, preserve-vs-install decisions, MCP/Gateway/OAuth/Tailscale setup, single-Skill migration, desktop/autostart setup, layered acceptance and the final human-only account/OAuth consent boundary.

Release/readme reconciliation:
- English and Chinese README entrypoints now lead with the product outcome, one-endpoint architecture and Agent-native deployment path instead of Stage history;
- `pyproject.toml` summary now describes the one OAuth-protected MCP gateway / durable local agent outcome;
- `docs/DEPLOYMENT.md` documents the machine-local prestart hook and the stronger real-Funnel READY contract;
- `docs/TRANSLATION-COVERAGE.*` now treats `skills/webgpt-as-codex/` as the only current operational Skill tree.


### 2026-09-21 maintenance final acceptance

- full repository regression after the consolidation: **228 PASS**;
- Ruff: **PASS**;
- repository secret scan: **SECRET_SCAN_PASS**;
- `git diff --check`: **PASS**;
- canonical/source Skill validator: **VALIDATION_OK**, 27 required files / **56 scenarios**;
- workspace-local and user shared Skill copies were resynchronized and both validate at WebGPT-as-Codex Skill `1.3.0` / 56 scenarios;
- current Desktop launcher and Windows Autostart were upgraded through the managed previous-generation matcher and now report `installed=true / managed=true / upgradeable=false`;
- post-upgrade Autostart real-host execution completed with `fully_ready=true`, `required_unmanaged_missing=[]`; the final observed OAuth Edge was `preserved-owned` and canonical Tailscale Funnel HTTPS 443 still targeted `http://127.0.0.1:9341`;
- final PEP517 wheel was built from the fixed source state, installed into a new external venv and reverified: package `0.1.0`, Skill `webgpt-as-codex` `1.3.0`, 56 scenarios, 9 workflows, product contract present, 8 component manifests, 4 Manager static resources, 9 release resources, and **no installed `computer-agent` Skill tree**;
- final wheel SHA-256: `548ac770149ddadb1bde04081ffc5b79845589babbd2e804c60c63dd5e21e789`;
- final wheel size: `302996` bytes;
- full physical Windows cold reboot remains intentionally unforced. Startup recovery is implemented and repeatedly real-host exercised through the installed Windows Autostart path, but a separate reboot observation is still required for a literal cold-reboot acceptance claim.
