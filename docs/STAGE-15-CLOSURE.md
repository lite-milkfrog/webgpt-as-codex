# Stage 15 Closure — Component Install / Upgrade / Lifecycle

CURRENT_STAGE = STAGE-15-COMPONENT-INSTALL-UPGRADE-LIFECYCLE
NEXT_STAGE = STAGE-16-CONCURRENCY-SESSION-ISOLATION-FALLBACK
AFTER_NEXT_STAGE = STAGE-17-MANAGER-UX-BILINGUAL-DESKTOP

Status: CLOSED_LOCAL_VERIFIED

## Owned concern

Make WebGPT-as-Codex the one-repository deployment authority for detecting, versioning, installing and upgrading declared MCP/system dependencies without duplicating or unexpectedly taking over the healthy MCP services already in use.

## Implemented

- Added repository-owned component lifecycle/deployment planner and CLI: `webgpt-codex deploy`.
- Added install metadata to all eight built-in component manifests, including explicit toolchain requirements and compatibility windows for every automatic adapter.
- Added latest-stable resolvers for:
  - PyPI;
  - npm;
  - GitHub Releases;
  - winget.
- GitHub Release provisioning requires the expected repository, expected Windows asset name and a release-provided SHA-256 digest before download/write.
- Added dependency/toolchain discovery for Git, Node, npm, uv and winget.
- Missing uv and Node/npm can be provisioned through allowlisted winget package IDs.
- Added install strategies:
  - `uv-tool`;
  - `npm-global`;
  - `winget`;
  - verified `github-release`;
  - `manual`.
- Extended verified artifact provisioning so a WebGPT-owned stopped binary can actually be replaced during an owned upgrade instead of being accidentally preserved as if it were an initial install.
- Separated `installed_version`, `latest_version`, installed compatibility and latest-candidate compatibility instead of collapsing them into one version field.
- Removed `@latest` invocations from installed-version probes. Package-manager metadata, owned receipts, a known machine binary or a real local version command may establish an installed version; otherwise it remains unknown.
- Latest candidates outside the manifest compatibility window fail closed. A newer compatible existing installation is preserved and never downgraded.
- A stopped older external installation still requires explicit `--adopt-external` before WebGPT may upgrade it and record install ownership.
- A successfully resolved latest release is cached machine-locally for at most 24 hours as verified fallback evidence. Cached evidence is explicitly non-fresh and cannot authorize install/upgrade; a fresh machine with no online evidence remains fail-closed.
- WebGPT installation ownership is persisted machine-locally. An install receipt does **not** automatically grant runtime start/stop authority; lifecycle ownership remains a separate security contract.
- Default deployment planning keeps the Remote Desktop Commander manual/pairing step visible instead of silently omitting it as an optional component.
- Service-context command discovery now reuses the repository's Windows user-home resolution instead of assuming `Path.home()` / `USERPROFILE` exists.

## Deployment state machine

The planner distinguishes at least:

- `preserve-healthy`;
- `preserve-healthy-system`;
- `preserve-newer`;
- `preserve-installed-current`;
- `preserve-external-upgrade-available`;
- `install-missing`;
- `upgrade-owned`;
- `upgrade-owned-requires-stop`;
- `upgrade-external-requires-adoption`;
- `diagnose-running-unhealthy`;
- `diagnose-listener-conflict`;
- `diagnose-installed-incompatible`;
- `diagnose-version-unknown`;
- `diagnose-version-incomparable`;
- `preserve-existing-latest-unavailable`;
- `preserve-current-latest-incompatible`;
- `install-blocked-latest-unavailable`;
- `install-blocked-incompatible-latest`;
- `manual-required`.

A healthy listener wins over PATH/package absence. A system service such as Tailscale may be healthy from process evidence without having an HTTP MCP listener. An existing external installation is not silently adopted merely because a newer release exists. Unknown upstream metadata and incompatible candidates are blocking evidence, not permission to mutate.

## Live dry-run evidence

The current machine was evaluated repeatedly with `webgpt-codex deploy` in dry-run mode. No install, upgrade, restart or reconfiguration action was executed.

The first all-source live metadata run succeeded and established same-stage official latest evidence:

| Component | Current/latest evidence | Action |
|---|---|---|
| Coding Tools MCP | live listener/process; upstream latest 0.3.0 | `preserve-healthy` |
| mcp-auth-proxy | live listener/process; upstream latest 2.10.2 | `preserve-healthy` |
| MCPJungle | live listener/process; upstream latest 0.4.6 | `preserve-healthy` |
| Playwright MCP | live listener/process; npm latest 0.0.82 | `preserve-healthy` |
| Remote Desktop Commander | upstream latest 0.2.51 | `manual-required` |
| Serena | live listener/process; upstream latest 1.7.0 | `preserve-healthy` |
| Tailscale | installed 1.102.2; winget latest 1.102.4; live system process | `preserve-external-upgrade-available` |
| Windows-MCP | live listener/process; package latest evidence 0.8.5 | `preserve-healthy` |

The Playwright installed-version field is intentionally **not** claimed to be 0.0.82: the prior `npx @playwright/mcp@latest --version` probe measured the upstream candidate, not the local installation. After the Stage 15 correction, its local installed version remains unknown while the healthy existing listener is preserved.

The stricter final dry-run again proposed zero install/restart/stop actions. PyPI/npm/winget metadata remained fresh. An intermediate rerun saw GitHub `HTTPError` for both binary components; on the final rerun MCPJungle again resolved fresh 0.4.6 evidence while mcp-auth-proxy still returned `HTTPError`, so only mcp-auth-proxy remained `preserve-existing-latest-unavailable` / blocking. The same Stage has successful official GitHub API evidence for MCPJungle 0.4.6 and mcp-auth-proxy 2.10.2, including expected Windows release assets and SHA-256 digests.

Successful latest metadata may be retained machine-locally for at most 24 hours as verified fallback evidence. A cached value is labeled `latest_fresh=false` / `latest_provenance=verified-cache`; it may support diagnosis and compatibility display but **cannot** authorize install or upgrade.

The Windows-MCP runtime has separately reported a server/product version in another version domain. Stage 15 therefore does not infer upgrade/downgrade authority from that incompatible version string while the external service is healthy.

The current Coding Tools execution environment did not expose `uv` on PATH, but healthy Serena/Coding Tools listeners were preserved. This is intentional: “tool executable not found in this shell” is not proof that an already-running MCP is absent.

## Validation

- Stage 15 narrow tests: 26 PASS.
- Stage 13–15 targeted regression: 38 PASS.
- Full repository tests: 146 PASS.
- Ruff: PASS.
- Secret scan: PASS.
- `git diff --check`: PASS.
- Existing-machine deployment dry-run: REAL_HOST_VERIFIED for zero mutation / zero duplicate proposal / healthy-service preservation. The final strict run intentionally returned blocking for the still-unavailable mcp-auth-proxy GitHub latest lookup and is **not** mislabeled as a network PASS.
- Live official metadata evidence: REAL_HOST_VERIFIED for PyPI/npm/winget and for successful same-stage GitHub API resolution before the later HTTP errors.
- Verified latest cache fallback: UNIT_VERIFIED; the cache preserves component/version/source plus GitHub asset URL/digest evidence, expires after 24 hours, is marked non-fresh and cannot authorize install/upgrade.
- Computer Agent Skill regression validation after the concurrency lesson: `VALIDATION_OK`, 48 scenarios.

## Computer Agent experience absorption

Machine-local/project Skill version: `1.1.15-local-candidate`.

New reusable rule:
- MCP request concurrency is not equivalent to conversation/project state isolation.
- Serena's standard server has process-wide active-project state and must not be shared as a mutable multi-project slot.
- Coding Tools may overlap independent command/process work, but one configured workspace still obeys single-writer-per-worktree.
- Remote/Desktop Commander and Windows-MCP GUI side effects share one physical desktop resource.

Updated Skill paths:
- `.skills/computer-agent/SKILL.md`;
- `.skills/computer-agent/routing.md`;
- `.skills/computer-agent/environment.local.md`;
- `.skills/computer-agent/workflows/coding.md`;
- `.skills/computer-agent/manifest.json`;
- `.skills/computer-agent/evals/scenarios.json`;
- `.skills/computer-agent/CHANGELOG.md`;
- `.skills/computer-agent/scripts/validate_skill.py`.

Regression scenario: `R48`.

The Skill root is a workspace-local shared asset and is not part of the WebGPT-as-Codex Git repository, so these Skill edits are validated machine-local state rather than files in this Stage 15 product commit.

## Inherited WIP boundary

These files were already dirty before Stage 15 ownership and remain excluded from the Stage 15 closure commit:

- `pyproject.toml`;
- `src/webgpt_as_codex/launcher.py`;
- `src/webgpt_as_codex/manager.py`;
- `src/webgpt_as_codex/registry.py`;
- `tests/test_stage12.py`.

They belong to later Manager/bilingual work and were not used as permission to broaden Stage 15.

Commit `d08603a` contains a pre-closure Stage-15 continuation prompt artifact. Because it was created before the docs-before-prompt barrier and before the Stage 15 product closure HEAD existed, it is historical/stale handoff evidence and must not be submitted as the Stage 16 prompt.

## Live document barrier

- `docs/CURRENT-PROJECT-STATE.md`: UPDATED_WITH_NEW_EVIDENCE
- `docs/ROADMAP-2026-09-20.md`: UPDATED_WITH_NEW_EVIDENCE
- `docs/ARCHITECTURE.md`: UPDATED_WITH_NEW_EVIDENCE
- `docs/DEPLOYMENT.md`: UPDATED_WITH_NEW_EVIDENCE
- `docs/DECISIONS-AND-RISKS.md`: UPDATED_WITH_NEW_EVIDENCE
- `docs/SUPPLEMENTAL-PRODUCT-GOALS-2026-09-20.md`: CHECKED_NO_CHANGE_REQUIRED — Stage 15 implements the already-recorded deployment lifecycle goal without changing its wording.
- `docs/CONCURRENCY-AND-FALLBACK.md`: CHECKED_NO_CHANGE_REQUIRED — remains the Stage 16 owner boundary.
- `skills/webgpt-as-codex/experience-ledger.md`: UPDATED_WITH_NEW_EVIDENCE
- relevant `components/*.json`: UPDATED_WITH_NEW_EVIDENCE
- `README.md`: CHECKED_NO_CHANGE_REQUIRED — release-facing walkthrough remains a later Stage 18/19 concern.
- `THIRD_PARTY_NOTICES.md`: CHECKED_NO_CHANGE_REQUIRED — component provenance remains represented there and in manifests.
- historical Stage 1–14 closures: NOT_APPLICABLE_THIS_STAGE / unchanged.

## Progress

- Stage 15: 100% — LOCAL_IMPLEMENTATION + LOCAL_VERIFIED + REAL_HOST_VERIFIED for current-machine preservation/live metadata behavior.
- Supplemental roadmap: 3 of 8 closure/final-acceptance gates complete = 37.5% by stage-count, not an effort estimate.
- Real fresh-machine installation remains Stage 19 acceptance; Stage 15 proves the lifecycle planning/install adapters and current-machine preserve behavior.

## Next owner

Stage 16 owns multi-window/session isolation and complementary rescue:
- fixed-project Serena instance/project-slot pooling without switching the user's existing shared Serena session;
- Coding Tools workspace/worktree concurrency boundary;
- machine-level GUI lease for Remote Desktop Commander / Windows-MCP;
- Unified Gateway <-> Remote Desktop Commander recovery routing;
- recovery-loop prevention and exact mutation ownership;
- concurrency/fallback tests.

Stage 16 must not use the user's currently shared Serena instance as an implementation dependency; inspect source through Coding Tools and create isolated test instances only when needed.
