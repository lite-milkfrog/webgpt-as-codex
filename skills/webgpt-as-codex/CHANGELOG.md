# Changelog

## 1.3.1 — 2026-09-22

- Hardened Playwright/Loop Engineering handoff against connector session churn: a later Welcome-only tab list no longer implies that a previously created ChatGPT page disappeared.
- Requires session-scoped handoff chains to stay inside one `mcp-session-id` / persistent context, or use the canonical `chatgpt-loop-handoff.mjs` helper instead of splitting `new -> type -> submit -> verify` across session-churning connector calls.
- Added shared-browser tab lease guidance and explicit recovery rules for already-filled-but-unsent prompts, exactly-once submit, and cleanup of only Agent-owned unused duplicate tabs.
- Bumped the handoff Stable Core to `LE-STABLE-2026-09-22.1` so future NEXT-WINDOW prompts inherit the stronger session-continuity and duplicate-tab contract.
- Added regression scenario R55 for the real “new succeeded, next connector call only shows Welcome” failure mode.

## 1.3.0 — 2026-09-21

- Unified the former Computer Agent core and WebGPT-as-Codex product profile into one canonical `webgpt-as-codex` Skill.
- Preserved the full Experience Ledger, MCP Guides, GUI/browser workflows and all original 53 regression scenarios; restored the legacy `serena-down`, `handoff` and `parallel-edit` contract aliases and added R54 for destructive-action authorization, for 57 scenarios total.
- Added the explicit WebGPT product contract, one canonical release/local Skill path and compatibility markers for local SoT / Validation / Handoff.
- The old `computer-agent` name is migration history only and is no longer a second release entry point.
- Release packaging now contains only the `webgpt-as-codex` Skill tree while preserving its scripts, workflows, evals and product contract.
- Hardened Windows-login recovery after a real reboot incident: prestart descendants no longer inherit launcher log handles, launcher diagnostics use generation-specific logs, bounded boot recovery waits for networking/Tailscale/OAuth convergence, and READY remains layered/fail-closed.
- Added an explicit destructive-action gate: generic continuation language never authorizes reboot/shutdown/sign-out/network interruption/Tailscale reset; those actions require same-turn, action-specific user approval.
- Serena global health no longer uses `get_current_config` as a safe probe because that call legitimately errors when no project is active; protocol + tools/list remain the project-independent health proof.

## 1.2.0 — 2026-09-20

- Promoted the previously machine-local Computer Agent into the canonical portable release Skill while preserving machine-specific overlays outside the release.
- Unified release and local Skill versioning at \`1.2.0\`; the portable file set is now sync/checkable instead of relying on manual copy discipline.
- Preserved the full historical Computer Agent workflow/eval set and absorbed the complete WebGPT-as-Codex Experience Ledger plus MCP Operating Guides; no prior experience module was removed.
- Added RDC four-layer health truth (\`installation -> local process -> control plane -> execution plane\`) and regression coverage that forbids treating \`online\` as execution proof.
- Kept the WebGPT-as-Codex product profile as a sibling compatibility/product specialization at the same Skill version instead of flattening away its product-specific Doctor/Gateway/OAuth/Release knowledge.
- Release packaging now carries both the unified Computer Agent core and the WebGPT-as-Codex product profile so a fresh installed artifact has the same portable operating knowledge as the local Skill.

## 1.1.17-local-candidate — 2026-09-20

- Absorbed a real mixed-version service failure where a loopback listener and health endpoint stayed green while a long-running Python Manager still held an old route table and read newer static files from disk.
- Added the rule that listener/process health is not runtime-generation proof: compare ownership, process identity, runtime generation and key capability/resource contracts before refreshing a stale owned service; ambiguous/unrelated listeners remain fail-closed and must not be killed.
- Separated user desktop URL opening from browser automation profiles. Desktop launchers now conceptually reuse the user's normal running browser profile, or the Windows default URL handler when no browser is running; Playwright isolated/shared contexts remain an automation concern rather than a desktop-launch concern.
- Added regression scenarios R50 and R51 for stale long-running runtimes and desktop-launcher browser-profile isolation.
- Recorded the 2026-09-20 host acceptance that the current machine's WebGPT desktop launcher reused the existing Edge Default profile without creating a new automation-only profile.

## 1.1.16-local-candidate — 2026-09-20

- Hardened side-effect recovery after a real isolated Serena shutdown race: process stop/restart timeout or non-zero is now treated as ambiguous until a bounded post-state observation window checks listener plus PID birth/image identity.
- Explicitly forbids issuing a second kill/restart merely because the first confirmation window expired; an already-exited/recovered process is accepted from post-state, while a still-live matching identity remains a classified failure for the next authorized recovery step.
- Added regression scenario R49 for delayed process-exit confirmation.

## 1.1.15-local-candidate — 2026-09-20

- Added an explicit MCP concurrency state model instead of treating “parallel requests” as equivalent to “parallel projects/sessions”.
- Verified from the installed Serena 1.7.0 source that the standard `SerenaAgent` has one process-wide active project and project switching shuts down the previous active project's language server; concurrent ChatGPT windows must therefore use fixed-project Serena instances/ports/slots or the read-only multi-project query path rather than racing `activate_project`.
- Clarified Coding Tools concurrency: independent command/process sessions may overlap, but one server remains bound to one configured workspace and the existing single-writer-per-worktree rule still applies.
- Clarified Remote/Desktop Commander and Windows-MCP concurrency: independent terminal/filesystem/process work may overlap, while real mouse/keyboard/foreground-focus GUI side effects share one physical desktop and must be serialized.
- Added regression scenario R48 for cross-window Serena/Coding Tools concurrency.
- Hardened the Skill validator so the manifest version is checked against the current SKILL frontmatter instead of a stale hard-coded version, and so historical `state/` handoff documents do not create false broken-link failures for project-relative references.

## 1.1.14-local-candidate — 2026-09-19

- Promoted WeChat / QQ verification to a hard **Screenshot-only business-state rule**.
- UI Tree/UIA is now explicitly non-authoritative for WeChat/QQ attachment, message, file-card, send-success, and control-existence checks.
- When Screenshot and UI Tree disagree, Screenshot wins; `UIA_FOUND=0` must not trigger a retry or false “not present” conclusion.
- Prefer the original/highest-resolution Windows-MCP Screenshot for verification. User-provided clear original screenshots are valid semantic-state evidence, while actual click coordinates still come from the current live capture/window geometry.
- Updated the canonical WeChat File Transfer Assistant workflow and the general Windows GUI calibration workflow to enforce this exception.

## 1.1.13-local-candidate — 2026-09-19

- Added the dedicated canonical WeChat File Transfer Assistant workflow.
- Added existing-session takeover: when WeChat is already logged in / already on 文件传输助手, do not restart or re-navigate the client.
- Reverified local Windows-MCP Streamable HTTP at `127.0.0.1:8001/mcp`; server reported `windows-mcp 4.0.4` and exposed the expected native GUI primitives.
- Validated the stable WeChat file-send path on `JARVIS-2.11.3.zip`: Windows FileDropList -> current chat `Ctrl+V` -> send -> user-confirmed file appearance.
- Corrected the earlier overreliance on Qt UI Tree and repeated coordinate guessing.


## 1.1.12-local-candidate — 2026-09-19

- Expanded `workflows/windows-gui-visual-calibration.md` from a coordinate note into a full Windows-MCP execution handbook based on the complete WeChat ZIP-upload incident.
- Added a micro-level canonical upload state machine: native file control -> current visual locate -> dialog discovery -> literal path input -> nested chooser handling -> pending-file evidence -> send -> post-send evidence.
- Added a macro-level GUI failure taxonomy covering `ACTION_FAILURE`, `OBSERVER_FAILURE`, `FOCUS_FAILURE`, `DIALOG_LAYER_CHANGED`, `INPUT_ERROR`, stale state and coordinate-space mismatch.
- Documented the real observer failure where a Qt `选择文件` window was already open but a detector that only searched `#32770` falsely concluded the click had failed.
- Documented the real path-escaping failure where program-string backslashes were inserted into the GUI and Windows correctly rejected the filename.
- Added native-GUI-first policy: do not create drag-source helper windows, OCR workarounds or CLI substitutes while an application-native upload/open control remains usable.
- Hardened completion evidence: primitive results such as `Single left clicked`, `Typed text` and `Pressed enter` never constitute business completion without post-state evidence.
- Added multi-layer dialog tracking and foreground-window transitions as first-class state evidence.
- Added regression scenarios R40-R44 for observer-vs-action failure, native-control-first behavior, nested file choosers/path escaping, UIA-invisible Qt post-state, and premature success reporting.
- Windows-MCP source code remains unchanged; this iteration only improves Computer Agent behavior and regression coverage.

## 1.1.11-local-candidate — 2026-09-19

- Added `workflows/windows-gui-visual-calibration.md` to capture the real Windows/WeChat high-DPI GUI failure mode.
- Distinguished Windows DPI scaling from Windows-MCP Screenshot downscaling. The runtime is already Per-Monitor DPI Aware, but returned screenshots may still require `Screenshot Coordinate Scale` + `Screenshot Region` conversion before `Click/Move`.
- Added a hard rule that user-uploaded/remote-desktop screenshot pixels are not direct Windows-MCP click coordinates.
- Added post-state evidence requirements for GUI actions: successful input injection is not proof that the intended control was hit.
- Added window-preservation policy: bring the target app to front, but do not close the user's pre-existing windows for convenience; prefer minimize/background/move/Snap.
- Added regression scenarios R38 (screenshot/image coordinate conversion) and R39 (preserve pre-existing windows).
- No Windows-MCP source code was modified in this iteration; tool-level `coordinate_space/capture_id` changes remain a future design candidate pending explicit approval.

## 1.1.10-local-candidate — 2026-09-18

- Added a Windows shell-dialect rule for Coding Tools `exec_command`: do not assume PowerShell; use cmd-native syntax when the route is cmd, or explicitly invoke `powershell -NoProfile -Command` for `$null` / object-pipeline syntax.
- Added mandatory post-state/Git inspection after shell syntax/redirection failures so accidental literal files such as `$null` are detected and only precisely attributable tool noise is removed; `git clean` remains forbidden as a recovery shortcut.
- Added regression scenario `R37` for the real B06-02 failure mode where PowerShell redirection syntax was interpreted by cmd and created a literal `$null` file.
- Corrected three historical JARVIS environment references to workspace-relative paths so the structural validator can resolve them from the Skill workspace root.

## 1.1.9-local-candidate — 2026-09-17

- Added `ACTIVE_RECOVERY` as the default state for ordinary MCP/browser/test/build/tool failures; workers may pause only after exhausting authorized local recovery and fallback paths and finishing other stage-local work.
- Added a hard docs-before-prompt barrier: all affected live SoT/evidence/risk/environment/session/progress documents are checked/updated before the product closure commit and before any next-stage prompt is generated.
- Hardened Zero-Guess handoff to require explicit workspace Skill root, current Stage prompt path, next prompt path, SoT/source/tests roots, and to distinguish Coding Tools workspace from the JARVIS worktree.
- Bumped Stable Core to `LE-STABLE-2026-09-17.2` so subsequent prompts must be re-instantiated from the new template instead of copying older prompts.
- Added regression coverage for “do not stop on recoverable failure” and “docs must be current before next prompt”.
- Verified and documented no-click Edge Extension bootstrap: when the token-backed Playwright client is already connected but only the extension `Welcome` tab is listed, opening a fresh `https://chatgpt.com/` tab inside the same MCP session inherits the signed-in Edge state; manual `Allow & select` of an old tab is not required for Loop handoff.

## 1.1.5-local-candidate — 2026-09-17

- Added a machine-local MCP locator map in `environment.local.md` with non-secret install roots, localhost endpoints/listeners, and reconnect rules for Coding Tools, Serena, Desktop Commander, Windows-MCP, and Playwright.
- Added standard Streamable HTTP MCP helper `scripts/mcp-http-client.mjs`, including empty notification-body handling and session-id preservation.
- Added reusable `scripts/chatgpt-loop-handoff.mjs` for ChatGPT stage handoff through local Playwright MCP with fresh-tab creation, long-prompt post-state/hash verification, Enter submit, DOM-activation fallback, duplicate-submit protection, and takeover verification.
- Hardened Playwright rules: `NOT_EXPOSED` no longer implies `NOT_RUNNING`; direct-schema absence must trigger local locator/status/schema checks before cross-tool fallback.
- Documented session-scoped tab/ref behavior: `tabs list/select/type/submit/verify` must stay in one MCP session.
- Documented ProseMirror long-fill timeout behavior and whitespace-normalized SHA-256 verification before any retry.
- Hardened Zero-Guess handoff template to require an MCP Locator Table and exact local reconnect procedure for stage-critical MCPs.
- Added regression scenarios R25-R27 for local-MCP rediscovery, session-scoped tab indexes, and long-prompt/overlay-safe ChatGPT handoff.

## 1.1.4-local-candidate — 2026-09-17

- Fixed Coding Tools same-file line-edit guidance: all line operations in one `apply_changes` request use the original `read_file` revision/line numbers; they do not shift after earlier edits in that request.
- Added context-anchored `apply_patch` / edit-reread-edit recovery guidance for structural edits.
- Added regression scenario R24 for this line-addressing failure mode.

## 1.1.3-local-candidate — 2026-09-17

- Added Experience Absorption Loop: recover current task first, then distill reusable failure patterns into Skill/project rules.
- Added requirement to create a regression eval for reusable new failure modes before treating the Skill iteration as complete.
- Added propagation rule so Loop Engineering handoffs carry the new Skill version, changed rule paths and scenario IDs into the next stage.
- Added guardrails against overfitting one-off failures or using Skill self-iteration to expand permissions/scope.

## 1.1.2-local-candidate — 2026-09-17

- Added Loop Engineering workflow for one semantic stage per ChatGPT conversation.
- Added Zero-Guess handoff template requiring explicit tools, paths, read methods, usage, fallback, gates and exit criteria in every next-stage prompt.
- Added adaptive recovery ladder: post-state check -> failure classification -> same-tool adaptation -> cross-tool fallback.
- Added Playwright overlay/intercept recovery before Windows-MCP fallback.
- Added single-writer-per-worktree rule and parallel-worktree guidance.
- Added scoped authorization semantics for user-requested ChatGPT-to-ChatGPT loop handoffs.
- Added 6 regression scenarios covering loop handoff, Zero-Guess prompts, duplicate-submit prevention, same-tool recovery, writer isolation and Windows-MCP instability.
- Updated validator to require loop/handoff files, capabilities and regression scenarios.

## 1.0.0-local-candidate — 2026-09-17

- Initial local-first Computer Agent Skill.
- Added direct routing for Serena, Coding Tools, Desktop Commander, Playwright and Windows-MCP.
- Added P0–P3 permission model.
- Added high-DPI/stale-coordinate rules for Windows-MCP.
- Added Playwright-first web automation policy.
- Added coding, browser, desktop, file and cross-tool workflows.
- Added GPT Web migration plan without hardcoded URLs.
- Added 14 routing/permission evaluation scenarios.
- Added structural validator and machine-readable manifest.
