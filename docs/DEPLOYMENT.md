# Deployment Contract

[**English**](DEPLOYMENT.md) | [简体中文](zh-CN/DEPLOYMENT.md)

## Entry point

An Agent or user starts from this repository only. The repository decides the deployment path from discovered machine state.

Deployment is discovery-first, idempotent and version-aware.

The verified Git source checkout is the canonical fresh-machine deployment artifact. WebGPT-as-Codex carries complete derivative source snapshots for WAC-maintained Coding Tools and Serena changes under `vendor/`; a thin Python wheel that omits those trees is not, by itself, a complete deployment source.

The Stage 15 repository CLI for the component lifecycle plan is:

```powershell
webgpt-codex deploy
```

This is a dry-run by default. It reports preserve/install/upgrade/diagnose/manual state without mutating services. `--apply` installs missing components and upgrades already WebGPT-installed stopped components. A stopped older external install still requires the additional explicit `--adopt-external` flag before upgrade/adoption; a live external service is never silently taken over.

## Phase 0 — language and repository truth

1. Select English or Chinese instructions.
2. Read `AGENTS.md`, this document, `docs/CURRENT-PROJECT-STATE.md`, `docs/ARCHITECTURE.md`, `skills/webgpt-as-codex/SKILL.md`, `session-bootstrap.md` and `routing.md`.
3. Never treat a prior machine's installed state as a fresh-machine prerequisite.
4. Resolve the repository URL supplied by the user and its current default branch. A generic request such as "deploy this project" means deploy that branch's current remote HEAD unless the user explicitly requests a tag/commit/release.
5. On a fresh machine, clone the current default branch. For an existing checkout, verify the remote and fetch before deployment. Fast-forward only when the checkout is clean and non-divergent; never discard unknown local work with `reset --hard` or `clean` merely to reach latest.
6. If the existing checkout is dirty/diverged, preserve it and use a fresh clone in a separate safe directory when possible.
7. Immediately before source installation, fetch again and record `SOURCE_REPOSITORY`, `SOURCE_BRANCH` and `SOURCE_HEAD`; the deployment source HEAD must equal the fetched `origin/<default-branch>` HEAD.
8. Keep that verified checkout available for the WAC runtime and use a source-preserving/editable install. Do not delete it after creating a wheel, because bundled derivative MCP sources resolve from its `vendor/` tree. Run lifecycle/deploy commands from the checkout root; if an executor changes cwd, set `WEBGPT_CODEX_SOURCE_ROOT` to the verified checkout root.
9. Before substantive WAC machine work, complete the per-session Skill bootstrap. Complex work selects a Workflow first and loads only the active Stage's leaf Skills.

## Phase 1 — environment gate

Detect at minimum:
- Windows support level;
- Python >= repository minimum;
- Git;
- Node/npm when required by selected MCPs;
- uv when required by selected MCPs;
- winget;
- Tailscale installation/version/login/online/MagicDNS/Funnel capability;
- WebGPT state-root writability;
- reserved ports/conflicts;
- WebGPT-owned MCPJungle and mcp-auth-proxy binaries.

Do not claim Edge readiness until the environment report says it is ready.

## Phase 2 — system dependency bootstrap

For an absent prerequisite, use an allowlisted official source. Existing healthy prerequisites are preserved.

Tailscale:
- absent + winget available -> approved `Tailscale.Tailscale` install path;
- installed but old -> controlled upgrade path;
- installed but logged out/offline -> request the account login step;
- online -> preserve;
- Funnel/HTTPS unavailable -> block public-edge success and surface the exact next action.

## Phase 3 — WebGPT private runtime provisioning

WebGPT owns the Gateway/Edge runtime dependency installation.

Missing approved artifacts are downloaded from official upstream releases, SHA-256 verified and placed under the machine-local WebGPT state root.

Current approved bootstrap baselines are repository metadata, not claims that they remain the latest forever. Deployment resolves current stable upstream metadata, compares it with the verified compatibility policy, and tests before promotion.

Existing binaries are preserved by default.

## Phase 4 — MCP inventory and deployment

For each declared MCP:
1. detect installation;
2. detect running process/listener;
3. detect installed version when safe;
4. query upstream latest stable version through the component adapter;
5. run MCP initialize + tools/list when reachable;
6. run only the manifest-declared safe call;
7. classify as preserve / install / upgrade / diagnose / incompatible;
8. mutate only after component-specific authority is established.

Repository-bundled derivatives are first-class deployment sources, not emergency patches. When a component declares `bundled_derivative=true` and the `bundled-uv-tool` strategy, the source under the repository's declared `vendor/` path is the release source for that WebGPT component version. Do not substitute an unmodified registry package merely because PyPI/npm has the same nominal version.

Current bundled derivative sources:
- `vendor/coding-tools-mcp/`: complete Coding Tools MCP source snapshot based on upstream `bedb632e1afd2e9ec9b268a50fe0b04695c22c64`, including WebGPT's Windows/process/desktop fixes, upstream Apache-2.0 LICENSE/NOTICE, modification notices and exact derivative-diff evidence.
- `vendor/serena-agent/`: complete Serena v1.7.0 source snapshot (upstream tag commit `949a27ef1e5fda1a6e7b561e777bcece345c6ffd`, the last MIT-licensed Serena release), including the verified `find_implementations` exact-name-and-kind fallback and exact derivative-diff evidence.

Before accepting a bundled install, verify that the declared source directory exists, contains its `pyproject.toml` and license/provenance files, installation succeeds through the repository lifecycle adapter, and the installed runtime passes its normal MCP readiness/safe-call contract.

Never deploy a duplicate healthy instance merely because a package executable is absent from PATH.

### Required standalone Skills Manager

`skills-control-plane` is a required WAC component, but its source of truth is the standalone `https://github.com/lite-milkfrog/skills-manager` repository rather than a vendored copy inside WAC.

The relationship is intentional: Skills Manager owns structured Skill discovery/resolution plus Workflow/Run/gate/evidence semantics; WAC owns the integration declaration, lifecycle supervision, unified Gateway exposure and remote OAuth/HTTPS edge. Local Skills remain normal files in their own roots. Skills Manager indexes and resolves them instead of replacing them.

From the verified WAC checkout, install or update it with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_skills_manager.ps1 -Update
```

The installer is intentionally non-destructive:
- absent checkout -> clone the standalone repository's `main`;
- existing clean checkout + update -> fetch and fast-forward only to `origin/main`;
- dirty checkout -> refuse automatic overwrite;
- after source setup -> editable install, production Workflow import, and WAC integration wrapper installation.

The production import must include the repository-backed WAC workflows when present, including Loop Engineering and Parallel Agent Orchestration. WAC deployment separately runs its canonical Skill sync/validation path. Acceptance should prove that the live Skills MCP can resolve the canonical `webgpt-as-codex` Skill and return the imported WAC Workflow definitions; a cloned repository alone is not sufficient integration evidence.

Deployment acceptance must record the standalone repository URL, branch and actual HEAD, and prove that its HEAD equals the freshly fetched remote default-branch HEAD. The resulting 8943 MCP must pass initialize/tools/list/read-only acceptance, and the WAC external-ensure binding must point to the standalone `skills-manager` checkout rather than the historical `skill-control-plane` development workspace.

Supported automatic installation channels are intentionally explicit:
- WAC-maintained Python derivative MCPs: repository-bundled complete source + `uv tool install`;
- Python MCP packages: `uv tool`;
- Node MCP packages: global npm package;
- Windows system prerequisites: allowlisted winget IDs;
- WebGPT private binary dependencies: official GitHub Release asset + expected asset identity + SHA-256 digest;
- hosted/account-pairing integrations such as Remote Desktop Commander: manual/authenticated action surfaced in the deployment report.

Every automatic adapter also declares:
- the toolchain it actually needs (for example `uv`, `node` + `npm`, or `winget`);
- a compatibility window for versions WebGPT is allowed to install.

Installed version, upstream latest and verified compatibility are separate fields. If the latest resolver is unavailable, the deployment report remains unknown/blocking rather than claiming the installed copy is current. If latest is outside the compatibility window, install/upgrade is blocked. If the existing installed version is newer but compatible, it is preserved and never downgraded.

For `bundled-uv-tool` components, “latest” means the version declared by the verified bundled source in this repository, not the public package registry. Replacing it with PyPI latest would destroy WAC's derivative reproducibility contract.

A successful latest lookup is cached machine-locally for no more than 24 hours. During a transient registry/API failure, only a still-fresh previously verified entry may be reused. For GitHub binary releases that entry must still contain the expected repository asset URL/name and SHA-256 evidence. With no valid cache, latest remains unknown/blocking.

If uv or Node/npm is missing on a genuinely fresh machine, the deployment adapter may install the required toolchain through the approved winget package. If the target MCP is already healthy, missing PATH/toolchain evidence does not authorize a duplicate installation.

Version comparison is only used inside a compatible version domain. A package version and an independently reported server/product version are not assumed comparable merely because both contain dotted numbers.

Do not use commands such as `npx package@latest --version` to infer the installed version: that measures/fetches upstream latest and can fabricate a false local version. Package-manager metadata, owned receipts, a known machine binary or a real local version command may establish installed-version evidence; otherwise it stays unknown.

## Phase 5 — unified local Gateway

Start/preserve MCPJungle.
Register healthy enabled Streamable HTTP MCPs as upstream routes in WebGPT's private Gateway database.

Route registration must not rewrite an upstream MCP's own configuration.

The initial migration may use:
- routing ownership = WebGPT;
- lifecycle ownership = external/preserved.

Later WebGPT-installed components may acquire WebGPT lifecycle ownership after validation.

## Phase 6 — OAuth and HTTPS Edge

Start the WebGPT production Edge:
- private Gateway;
- OAuth proxy;
- compatibility adapter;
- Tailscale Funnel HTTPS.

OAuth credentials live only under the machine-local WebGPT state/secrets area.

The Web Manager exposes status and explicit local credential controls without embedding secrets in static assets or repository files.

## Phase 7 — deep verification

Required health layers:
1. process;
2. listener;
3. MCP initialize;
4. tools/list;
5. safe tool call;
6. OAuth metadata;
7. DCR + PKCE;
8. token exchange;
9. protected unauthenticated 401 gate;
10. refresh token;
11. authenticated MCP call;
12. public HTTPS reachability.

A green lower layer does not imply a green higher layer.

## Phase 8 — desktop/control plane

Install or refresh the transparent one-click `WebGPT-as-Codex.cmd` launcher. The repository-managed Desktop launcher defaults the Manager to Chinese with `WEBGPT_CODEX_UI_LANG=zh-CN`; `/en` remains an explicit English route and `/zh` an explicit Chinese route.
Open the loopback Web Manager. The two language pages share one functional JavaScript/CSS contract rather than separate control logic.
The Manager must show:
- environment readiness;
- product/deployment readiness;
- MCP inventory/version state;
- Gateway routes;
- local/public MCP addresses;
- OAuth state and local credential controls;
- Tailscale/HTTPS state;
- backend health;
- migration/lifecycle ownership;
- recent action feedback/recovery actions.

The Manager local-config/status surfaces expose configured/readiness state only, not plaintext OAuth secrets, executable/secret-file paths or private Tailscale DNS identity. Password reveal/set/regenerate are explicit loopback-only confirmed operations. Regenerate must change the stored value, and recent activity must not contain it.

Custom migration-candidate add/remove changes registry visibility only. It does not apply a Gateway route, start/restart a runtime or grant lifecycle authority. Built-in component deletion is rejected.

Managed launcher refresh may recognize the complete known previous WebGPT launcher structure so an older repository-managed file can be upgraded in place. A marker by itself is insufficient: unmanaged/user-owned files remain protected from overwrite or deletion.

The browser UI never owns runtime lifetime.

Manager liveness and Manager generation are separate facts. A live 9200 listener/healthz does not prove that the process loaded the current Python route table or current packaged/source UI contract. Repository-owned Manager reuse therefore requires ownership/process identity plus current runtime-generation/resource capability evidence. A strictly identified legacy WebGPT Manager may be refreshed when its current contract is stale; an unrelated or ambiguous listener is preserved and reported rather than killed.

The Desktop launcher is a user browser entry point, not a Playwright runtime. When the user's normal Microsoft Edge session is already running, the launcher reuses its last-used normal profile; otherwise it dispatches through the Windows default URL handler. It never intentionally creates a temporary user-data directory, isolated automation profile or InPrivate session for Manager opening.

Machine-only one-click additions must not be embedded in the release launcher. Two fixed machine-local extension points are supported: `%LOCALAPPDATA%\WebGPT-as-Codex\local-prestart.cmd` may run before Start All from both Desktop and Windows-login launchers to recover already-approved external MCP backends, while `%LOCALAPPDATA%\WebGPT-as-Codex\local-launcher-overlay.cmd` remains a manual-Desktop-only post-READY extension. The prestart hook must be credential-free, may only invoke verified local backend launchers, and must never claim or rewrite the canonical WebGPT public HTTPS 443 route. Its stdout/stderr is isolated from the WebGPT launcher log so long-lived backend grandchildren cannot inherit and lock the launcher log handle on Windows. Only the prestart completion/failure summary is written afterward. Its exit status remains diagnostic only: the subsequent layered readiness checks decide success. Both hooks are absent from fresh installs unless deployment discovers a justified machine-local need.

The managed Desktop install additionally writes `%LOCALAPPDATA%\WebGPT-as-Codex\rdc-recover-webgpt.ps1`. This is not a new public endpoint or lifecycle owner: it is a local recovery bridge intended for execution through an already-healthy RDC/local shell. It validates loopback Manager health and performs a real MCP `initialize` against Coding Tools (`127.0.0.1:8766/mcp`). If either check is down, it invokes only the managed `WebGPT-as-Codex-Autostart.cmd`, refuses an unmanaged replacement, and reports success only after both loopback probes recover. No credentials or machine-specific public URL are written into the bridge.

Windows-login Autostart uses a bounded boot-recovery mode: it gives external backends plus Windows networking/Tailscale/Funnel/OAuth Edge up to 300 seconds to converge, retrying a not-yet-`fully_ready` state rather than only retrying missing unmanaged backends. The manual Desktop launcher uses a 180-second bounded wait. Both fail closed after their budget; neither may print READY unless the launcher command returns success with layered readiness satisfied. Launcher diagnostics use generation-specific files (`autostart-v2.log` / `desktop-launcher-v2.log`) so already-running legacy processes that inherited an old log handle cannot block a repaired launcher.

## Phase 9 — final manual actions

For a fresh deployment, only interactive account/browser authorization remains:

1. Remote Desktop Commander: install/sign in/pair through the ChatGPT-side integration.
2. WebGPT Unified Gateway: add the single public MCP URL to ChatGPT and complete the real OAuth browser flow.
3. If a fresh Tailscale account requires sign-in/permission approval, complete that account action when prompted.

On the currently accepted host, RDC pairing is no longer pending: the recovered fixed 0.2.51 runtime passed connector-side `list_devices`, `ping`, `get_config` and a read-only host probe. Future deployment/Doctor logic must still treat an `online` device record as control-plane evidence only; execution-plane acceptance requires a real command probe.

## Phase 10 — acceptance

A deployment is not complete until:
- no duplicate managed MCP instance was created;
- existing healthy external services were preserved;
- required versions are current/compatible;
- local Gateway routing is proven;
- public HTTPS/OAuth is proven;
- the ChatGPT OAuth flow is proven;
- desktop launcher and Manager work;
- fallback paths are exercised;
- concurrency policy is documented and tested.

## Stage 19 production identity / recovery rule

Production WebGPT uses one canonical `https://<stable-tailnet-dns>/mcp` identity on HTTPS 443. Ordinary Manager, Gateway, OAuth Edge, WebGPT and Windows restarts must not intentionally change that identity, issuer or OAuth credential.

`Start All` must distinguish the 9340 OAuth child from the complete 9341 OAuth Edge. A raw 9340 listener can never by itself satisfy Edge readiness. The managed Edge is ready only when the 9341 compatibility contract, current issuer, repository generation, real Tailscale Funnel HTTPS 443 target (`127.0.0.1:9341`), and public 401/OAuth metadata all agree. If another process rewrites 443 after startup, the Edge must drop out of READY rather than continuing with a false-green local state.

If a matching 9340 OAuth child survives while the 9341 wrapper is absent, WebGPT may reuse that child only after verifying the canonical issuer. This permits restart recovery without forcing a credential rotation or connector recreation. Unknown/incompatible listeners fail closed.

Stage 19 real-host acceptance proved local 9341 metadata 200, public `/mcp` 401, current OAuth metadata, DCR + PKCE, authenticated MCP, refresh continuity and the same 87-tool surface across an Edge restart. After the user confirmed the ChatGPT connector was configured successfully, the production Connector/Funnel/OAuth state was frozen against further disruptive acceptance in this stage.

A full Windows reboot was deliberately not forced after that successful real connector setup. Treat it as a manual real-reboot acceptance item; the startup/recovery contract is implemented and tested, but preserving the newly established production connector takes priority over destructive proof-by-reboot.


## 2026-09-21 reboot-recovery hotfix

A real Windows reboot incident exposed a launcher-log handle inheritance bug: a machine-local prestart script could spawn long-lived external MCP grandchildren while its stdout/stderr was redirected into the same launcher log later reopened by WebGPT. On Windows those descendants could retain the handle, causing the next launcher redirection to fail with a sharing violation before Gateway/Edge startup.

The repaired contract is:
- prestart stdout/stderr is isolated from the WebGPT launcher log;
- only a post-return prestart outcome line is written to the launcher log;
- launcher diagnostics use generation-specific `desktop-launcher-v2.log` / `autostart-v2.log`;
- Windows-login Autostart gets a bounded 300-second boot-recovery window for external backends, networking, Tailscale, Funnel and OAuth Edge convergence;
- the manual Desktop launcher gets a bounded 180-second recovery window;
- a not-yet-`fully_ready` boot state is retryable inside the bound, but success remains fail-closed after the budget;
- Serena global Doctor health does not call `get_current_config`, because that call requires an active project and may correctly return an application-level error while the MCP server itself is healthy.

A controlled real-host recovery simulation stopped only WebGPT-owned Manager/Gateway/OAuth components while preserving external MCPs. The installed Windows Startup launcher restored 9200/9330/9340/9341, returned `fully_ready=true`, preserved the external MCP PIDs, and public protected-resource / unauthenticated MCP checks remained 200 / 401 + OAuth challenge.

### Destructive-action authorization gate

Reboot, shutdown, sign-out, sleep/hibernate, network-adapter interruption, Tailscale logout/reset, or any action likely to sever the current remote-control path requires explicit same-turn approval for that exact action. Generic instructions such as "continue", "finish the remaining work", "auto-close", or "keep going until done" never constitute that approval. When a host needs local human interaction to restore networking after reboot, a remote Agent must not initiate the reboot without explicit approval plus a confirmed local recovery path.