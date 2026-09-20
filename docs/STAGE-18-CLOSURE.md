# Stage 18 Closure — Chinese Mirror and Third-Party Notices

STATUS = CLOSED_LOCAL_VERIFIED  
CURRENT_STAGE = STAGE-18-CHINESE-MIRROR-AND-THIRD-PARTY-NOTICES  
NEXT_STAGE = STAGE-19-END-TO-END-DEPLOYMENT-ACCEPTANCE  
AFTER_NEXT_STAGE = SUPPLEMENTAL-FINAL-ACCEPTANCE  
PRODUCT_BASELINE = 310458dfe3cd97720963a08b69a1d82558588e59  
ENTRY_HEAD = f0c70baf2aaedc60e950bbac97a999ea11c80f1f

## Ownership boundary

Stage 18 changed repository documentation, public provenance metadata, release
resource declarations and their regression tests. It did **not** change Manager,
Gateway, OAuth, Tailscale, component lifecycle, concurrency, recovery or shared
Serena runtime behavior.

Shared Serena 9121 was reserved by another task and was never activated,
switched, restarted or stopped.

Stage 17 and its post-acceptance Hotfix remain accepted and were not reopened.

## Tool / routing evidence

- Coding Tools MCP: MCP initialize/tools/list succeeded; server
  `coding-tools-mcp 0.3.0`, workspace
  `D:\AgentData\10_Workspaces\coding-tools-mcp-demo`; it was the sole
  repository writer and owned repo reads/tests/build/Git.
- Remote Desktop Commander: direct connector to `JIAOLONG16proSeries` was
  online/pingable and used only for host/process transport and local MCP
  handshake support, not as a concurrent repository writer.
- Playwright MCP: initialize/tools/list succeeded on
  `http://127.0.0.1:8931/mcp`; reserved for the post-commit recursive handoff.
- Windows-MCP / Unified Gateway: listeners were reachable but not required for
  Stage 18 product work.
- Serena 9121: reachable but explicitly RESERVED / NOT_NEEDED; no project
  mutation occurred.

## Translation coverage result

Stage 18 established deterministic mirror rules:

- root reader entrypoints: sibling `*.zh-CN.md`;
- current live docs: `docs/zh-CN/<same basename>`;
- Product Skill/Guides:
  `skills/webgpt-as-codex/zh-CN/<same relative path>`;
- Manager: the existing Stage 17 `index.html` /
  `index.zh-CN.html` language shells continue to share
  `manager.js` / `manager.css`.

`docs/TRANSLATION-COVERAGE.json` is the regression authority. At closure it
classifies 155 current Stage18 text-format candidates/dispositions:

- 21 `MIRRORED_CURRENT`;
- 23 `MIRROR_TARGET`;
- 1 `LEGAL_ORIGINAL_PRESERVED`;
- 15 `LANGUAGE_NEUTRAL`;
- 36 `HISTORICAL_EVIDENCE_PRESERVED_WITH_INDEX`;
- 58 `NOT_HUMAN_READER_CONTENT`;
- 1 `BILINGUAL_INLINE`.

Historical closure/cost/prompt evidence was not cosmetically rewritten.
`docs/zh-CN/HISTORICAL-EVIDENCE-INDEX.md` gives the Chinese treatment while the
canonical evidence remains single-source.

The English and Chinese repository entrypoints/live docs/Product Skill/Guides
cross-link both directions. Protocol identifiers, commands, URLs, schema keys,
hashes and code blocks remain exact where semantics require.

## Legal boundary

The authoritative root `LICENSE` remained byte-for-byte unchanged:

- bytes: 11,558;
- SHA-256:
  `1eb85fc97224598dad1852b5d6483bbcf0aa8608790dcc657a5a2a761ae9c8c6`;
- diff against Stage17 Hotfix product baseline: none.

`LICENSE.zh-CN.md` is a complete reading translation with a prominent
non-binding/non-official notice and an explicit rule that the English original
controls every discrepancy. The original appendix application boilerplate is
kept in English inside the reading translation to avoid substituting translated
legal boilerplate into real license headers.

## Third-party provenance

The existing third-party notice was reconciled rather than replaced blindly.

`docs/THIRD-PARTY-PROVENANCE.json` is now machine-readable and maps all eight
component manifests to their exact upstream and repository-declared
license/license-note fields:

- MCPJungle;
- mcp-auth-proxy;
- Tailscale;
- Serena;
- Coding Tools MCP;
- Playwright MCP;
- Windows-MCP;
- Remote Desktop Commander.

The release dependency surface also records the declarations from
`pyproject.toml`:

- setuptools — build;
- requests — runtime;
- pytest — development/test;
- Ruff — development/lint.

Local metadata evidence observed requests 2.34.2 / Apache-2.0, pytest 9.1.1 /
MIT and Ruff 0.16.8 / MIT. setuptools was not installed in the development venv,
which was recorded as unavailable rather than invented as a local version.

`THIRD_PARTY_NOTICES.md` and `THIRD_PARTY_NOTICES.zh-CN.md` explain that the
listed metadata does not replace the exact upstream license/NOTICE shipped by a
redistributed artifact and does not relicense third-party software under the
project's Apache-2.0 license.

## Package / release boundary

`pyproject.toml` now installs one bounded public resource group at
`share/webgpt-as-codex/release`:

1. `README.md`
2. `README.zh-CN.md`
3. `LICENSE`
4. `LICENSE.zh-CN.md`
5. `THIRD_PARTY_NOTICES.md`
6. `THIRD_PARTY_NOTICES.zh-CN.md`
7. `docs/TRANSLATION-COVERAGE.json`
8. `docs/TRANSLATION-COVERAGE.md`
9. `docs/THIRD-PARTY-PROVENANCE.json`

Stage closures, prompts, the complete Skill source, machine-local state,
credentials, browser profiles, process/PID evidence and handoff receipts remain
outside the wheel.

A fresh PEP517 wheel was built from the Stage18 tree and installed outside the
source checkout in an isolated venv. Installed-artifact verification passed:

- `resource_root()` resolved the installed share tree;
- 8 built-in component manifests loaded;
- English/Chinese Manager HTML + shared CSS/JS were present;
- all 9 Stage18 release resources were present;
- installed `LICENSE` SHA-256 matched the authoritative baseline;
- `load_components()==8`;
- installed CLI reported `0.1.0`.

Build output:
- wheel: `webgpt_as_codex-0.1.0-py3-none-any.whl`;
- build SHA-256 observed:
  `2e0537b75f5cf0b00de92c5a05f3c503b641f4ac6ed0b4fc9d582f3d6fa4b140`;
- installed-artifact marker: `STAGE18_INSTALLED_ARTIFACT_PASS`.

The wheel hash is evidence for this local build only; it is not a release pin.

## Validation

Targeted Stage18 + Stage12 + Stage17 + Stage17 Hotfix:
- 27 PASS;
- targeted Ruff: PASS;
- `git diff --check`: PASS.

Full repository:
- 191 PASS in 21.75s;
- Ruff: PASS;
- `scripts/secret_scan.py`: `SECRET_SCAN_PASS`;
- `git diff --check`: PASS.

The Hotfix baseline was 184 PASS. The increase to 191 is the seven new Stage18
regression tests; no prior accepted tests were removed.

## Live-doc closure matrix

- `docs/CURRENT-PROJECT-STATE.md` — UPDATED_WITH_NEW_EVIDENCE.
- `docs/ROADMAP-2026-09-20.md` — UPDATED_WITH_NEW_EVIDENCE.
- `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md` —
  UPDATED_WITH_NEW_EVIDENCE (language entrypoint/mirror; product goal unchanged).
- `docs/ARCHITECTURE.md` — UPDATED_WITH_NEW_EVIDENCE.
- `docs/DECISIONS-AND-RISKS.md` — UPDATED_WITH_NEW_EVIDENCE.
- `docs/DEPLOYMENT.md` — UPDATED_WITH_NEW_EVIDENCE (language entrypoint/mirror;
  deployment runtime contract unchanged).
- `README.md` / `README.zh-CN.md` — UPDATED_WITH_NEW_EVIDENCE.
- `docs/TRANSLATION-COVERAGE.*` — CREATED_AND_VERIFIED.
- `docs/THIRD-PARTY-PROVENANCE.json` — CREATED_AND_VERIFIED.
- `THIRD_PARTY_NOTICES.md` / `THIRD_PARTY_NOTICES.zh-CN.md` —
  UPDATED_WITH_NEW_EVIDENCE.
- Product Skill/Guide bilingual treatment — UPDATED_WITH_NEW_EVIDENCE.
- `skills/webgpt-as-codex/experience-ledger.md` —
  UPDATED_WITH_NEW_EVIDENCE.
- historical closure/evidence files — CHECKED_NO_CHANGE_REQUIRED; originals
  preserved and indexed rather than rewritten.

## Experience absorption

Three Stage18 lessons were appended to the canonical Experience Ledger:

1. repository-wide translation must classify text candidates instead of bulk
   translating by extension;
2. legal reading translations must never become a second license authority;
3. third-party provenance must cover all release dependency authorities, not
   only external-service/component inventory.

These are Product Skill/release lessons. No new evidence required changing
Computer Agent 1.1.17 R50/R51 or the shared Serena operating rules.

## Verification level

Stage18 = `LOCAL_IMPLEMENTATION + LOCAL_VERIFIED`.

No `REAL_HOST_OR_DEVICE_VERIFIED` claim is made merely because repository
translations and an isolated installed artifact passed. Stage18 did not own a
new runtime/GUI/device behavior requiring host acceptance.

## Git / handoff boundary

The product/docs closure commit must contain this file and all Stage18 owned
changes before any Stage19 prompt is generated.

After that commit:
1. read the actual product/docs closure HEAD;
2. reload the current handoff template, browser workflow and final SoT;
3. generate a fresh `prompts/STAGE-19-NEXT-WINDOW.md` whose
   `SOURCE_HEAD` / `PRODUCT_HEAD` refer to that product/docs closure commit;
4. validate the complete recursive invariant and exact prompt;
5. commit the prompt as a separate handoff artifact;
6. submit the exact prompt once through the already-authenticated Playwright
   context and verify sent-message + `/c/` + new assistant-run evidence.

Program state remains `ACTIVE` after this Stage18 closure. The chain continues
to Stage19 and then Supplemental Final Acceptance.
