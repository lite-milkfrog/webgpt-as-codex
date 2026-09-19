# Stage 17 Closure — Manager UX / Bilingual / Desktop

STAGE = STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP
STATUS = CLOSED_LOCAL_VERIFIED
STAGE_PROGRESS = 100%
SUPPLEMENTAL_PROGRESS = 5/8 closure nodes = 62.5%
EVIDENCE_LEVEL = LOCAL_IMPLEMENTATION + LOCAL_VERIFIED + REAL_HOST_VERIFIED

## Baseline / ownership

- Prior accepted product HEAD: `5c323f45903d7a912def28ccaaf09dd4b5a3292a`.
- Stage17 startup HEAD: `f10d0ff8c380e75c7ac5e6e92be73b20be39b8e2`; the extra commit was the Stage17 handoff artifact, not product code.
- Branch: `main`; startup upstream delta: ahead 12 / behind 0.
- Startup dirty set was exactly the five preserved Stage17/18 WIP files documented by Stage16: `pyproject.toml`, `src/webgpt_as_codex/launcher.py`, `src/webgpt_as_codex/manager.py`, `src/webgpt_as_codex/registry.py`, `tests/test_stage12.py`.
- `manager/static/index.zh-CN.html` was confirmed missing at startup even though package/test WIP already referenced it. No reset, clean, stash, drop or force operation was used.
- Shared Serena 9121 stayed on the user's existing `Jarvis-dev` project and was never switched or restarted. Coding Tools remained the only repository writer.

## WIP reconciliation

1. `pyproject.toml`
   - preserved the bilingual resource intent;
   - completed the package boundary with `index.html`, `index.zh-CN.html`, `manager.css` and `manager.js`.
2. `launcher.py`
   - preserved the WIP Chinese default;
   - added safe upgrade recognition for the complete historical WebGPT-managed launcher structure so the real Stage8 Desktop/Startup files could be refreshed despite an older workspace Python path;
   - marker-only or otherwise unmanaged files remain protected.
3. `manager.py`
   - preserved the WIP local-config/environment/component/OAuth surfaces;
   - completed Host/Origin/control-header/payload/body-size boundaries for the new local mutations;
   - added one non-blocking mutation lock and secret-safe in-memory recent activity;
   - made local-config public-safe, separating status from explicit secret reveal;
   - protected built-ins and kept custom candidates registry-only;
   - completed bilingual/static asset serving with a strict self-only CSP.
4. `registry.py`
   - preserved `delete_custom_component` and verified idempotent custom deletion.
5. `tests/test_stage12.py`
   - preserved the Chinese package expectation and completed it for shared JS/CSS.
6. Missing asset contradiction
   - created the real tracked `manager/static/index.zh-CN.html`;
   - English/Chinese pages now share one functional JavaScript/CSS implementation to prevent control drift.

## Manager security / local configuration contract

- Normal `/api/local-config` exposes product version, deployment readiness, environment readiness, Gateway/local/public MCP URLs, configured OAuth state and registry/migration/version visibility.
- Raw executable paths, secret-file paths, Tailscale private DNS identity and secret material are not emitted by that surface.
- OAuth:
  - Set is explicit, confirmed and does not echo the supplied value.
  - Reveal returns plaintext only in that explicit local response.
  - Regenerate now creates a new random value rather than reusing `ensure` behavior.
  - Activity evidence contains action/status only and never the revealed/set/regenerated plaintext.
- Local environment/component/OAuth mutations serialize on one non-blocking server lock so concurrent button submissions cannot create duplicate side effects.
- Unknown fields, invalid component ids, oversized bodies, bad Origin and missing control header fail closed.
- Built-in deletion returns `builtin-component-protected`.
- Custom create/delete is idempotent and explicitly reports `route_applied=false` / `lifecycle_authority=false`; Stage14 routing and Stage8/16 lifecycle/recovery remain separate authorities.
- Exceptions return generic operation codes plus failure class only, not exception text.

## Bilingual / UX / accessibility contract

- `/` follows `WEBGPT_CODEX_UI_LANG`; the real managed desktop launcher sets `zh-CN`.
- `/zh` and `/en` remain explicit routes.
- Both languages expose the same:
  - overview and deployment/version/Gateway/OAuth/HTTPS readiness;
  - local/public MCP URL copy/open;
  - fixed runtime actions;
  - environment/Tailscale action;
  - OAuth set/reveal/regenerate;
  - migration-candidate add/remove;
  - component inventory;
  - recent activity.
- Mutation controls disable while a mutation is pending and show a real pending spinner/status rather than decorative continuous animation.
- Native controls/labels, visible `:focus-visible`, `aria-live` status regions and `prefers-reduced-motion` are present.

## Real host / browser evidence

### Desktop current deployment

- Before refresh, the actual Desktop and Startup files were the previous WebGPT-managed five-line launchers and were initially reported `managed=false`.
- Stage17 structural legacy matching reported them `upgradeable=true`.
- `desktop-launcher install` and `autostart install` returned `status=updated`; both then reported `managed=true`, `upgradeable=false`.
- Remote Desktop Commander read both host files after refresh and confirmed the expected `WEBGPT_CODEX_UI_LANG=zh-CN` line plus the normal WebGPT launcher command.
- No unrelated desktop shortcut, browser window or external MCP was opened, closed or rewritten.

### Disposable Manager

- Port 9217 was confirmed unused before the probe.
- A disposable Manager with a separate machine-local state directory served HTTP 200 for `/`, `/en`, `/zh`, `/manager.css`, `/manager.js` and `/api/local-config`.
- Playwright MCP 8931 completed `initialize -> tools/list` and exposed the real browser tool schema.
- One Playwright MCP session opened the disposable Manager and verified:
  - Chinese root: seven functional sections, 10 mutation controls, two live regions, six labels, two URL rows and eight component cards.
  - English `/en`: the same counts and equivalent functional sections.
  - No mutation control was clicked during DOM acceptance.
- The first normal temp-process tree stop returned non-zero. Stage16 R49 was applied: 9217 listener plus PID parent/image/command identity were re-read before a temp-only forced tree stop. The second bounded post-state check confirmed the temp listener and all three identified temporary processes were gone.
- Production listener PIDs after the probe were unchanged from the Stage16 baseline:
  - Gateway 9330 = 77084
  - Windows-MCP 8001 = 50508
  - Coding Tools 8766 = 54448
  - Playwright 8931 = 53880
  - shared Serena 9121 = 38924

## Package evidence

- The development venv does not provide a usable `python -m build` entry point; this was classified as a caller-side build harness limitation, not a source defect.
- Normal isolated PEP517 `pip wheel` succeeded for `webgpt_as_codex-0.1.0-py3-none-any.whl`.
- The wheel installed into a new environment outside the source checkout.
- Installed-layout smoke imported version `0.1.0` and read all four packaged Manager resources:
  - English HTML
  - Chinese HTML
  - shared CSS
  - shared JavaScript
- The installed resources retained the bilingual `manager-v2` UI contract, reduced-motion CSS and local Manager API wiring.

## Verification gates

Opening baseline:
- Stage11 + Stage12 + Stage16: 37 PASS.
- Full repository: 167 PASS.
- Ruff: PASS.
- repository secret scan: PASS.

Final targeted:
- Stage8 + Manager + Stage11 + Stage12 + Stage14 + Stage15 + Stage16 + Stage17: 100 PASS.
- Computer Agent validator: `VALIDATION_OK`, files=20, scenarios=49.

Final post-doc closure:
- Stage8 + Manager + Stage11 + Stage12 + Stage14 + Stage15 + Stage16 + Stage17: 100 PASS.
- full repository pytest: 176 PASS.
- Ruff: PASS.
- repository secret scan: PASS.
- `git diff --check`: PASS.
- isolated PEP517 wheel build: PASS.
- installed bilingual Manager resource smoke: PASS.
- disposable real-host HTTP + Playwright DOM acceptance: PASS.

## Live-doc barrier

| Live document | Stage17 result |
|---|---|
| `docs/CURRENT-PROJECT-STATE.md` | UPDATED_WITH_NEW_EVIDENCE |
| `docs/ARCHITECTURE.md` | UPDATED_WITH_NEW_EVIDENCE |
| `docs/DECISIONS-AND-RISKS.md` | UPDATED_WITH_NEW_EVIDENCE |
| `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md` | UPDATED_WITH_NEW_EVIDENCE |
| `docs/ROADMAP-2026-09-20.md` | UPDATED_WITH_NEW_EVIDENCE |
| `docs/DEPLOYMENT.md` | UPDATED_WITH_NEW_EVIDENCE |
| `README.md` | UPDATED_WITH_NEW_EVIDENCE |
| `skills/webgpt-as-codex/SKILL.md` | UPDATED_WITH_NEW_EVIDENCE |
| `skills/webgpt-as-codex/experience-ledger.md` | UPDATED_WITH_NEW_EVIDENCE |
| `docs/CONCURRENCY-AND-FALLBACK.md` | CHECKED_NO_CHANGE_REQUIRED — Stage16 ownership/isolation/recovery contract was preserved |
| `.skills/computer-agent/maintenance.md` and workflows | CHECKED_NO_CHANGE_REQUIRED — Stage17 exercised existing R49 rather than exposing a new generic rule |
| `.skills/computer-agent/evals/scenarios.json` | CHECKED_NO_CHANGE_REQUIRED — R48/R49 remain the relevant regressions |

## Remaining program

Program state remains `ACTIVE`; this is not `GLOBAL_LOOP_COMPLETE`.

- CURRENT_STAGE = `STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES`
- NEXT_STAGE = `STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE`
- AFTER_NEXT_STAGE = `SUPPLEMENTAL-FINAL-ACCEPTANCE`

Stage18 owns the repository/release-facing Chinese mirror and third-party notices/provenance audit. It must not reimplement the Stage17 Manager control plane.
