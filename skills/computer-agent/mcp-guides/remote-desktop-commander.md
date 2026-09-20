# Remote Desktop Commander Operating Guide

[**English**](remote-desktop-commander.md) | [简体中文](../zh-CN/mcp-guides/remote-desktop-commander.md)

Component: `remote-desktop-commander`

## Mental model

Remote Desktop Commander (RDC) is an independent full-machine repair/control plane. It complements WebGPT-as-Codex rather than sitting inside the Unified Gateway. It is appropriate for host filesystem, process, terminal and bounded GUI recovery work when the structured WebGPT path is unavailable or when host-wide visibility is required.

RDC is not a WebGPT Gateway child, not part of OAuth/Funnel, and not a WebGPT READY prerequisite.

## Health model

Never collapse RDC health into one boolean. Verify four layers:

1. installation/runtime exists;
2. local agent process is alive;
3. control plane sees the intended device and authentication/session state;
4. execution plane can actually receive and execute commands.

A device marked `online` proves only control-plane presence. It does not prove a live command transport.

## Real acceptance evidence

Supplemental Final Acceptance recovered and verified a fixed local 0.2.51 runtime. The active device record was online/authenticated and advertised broadcast transport capability. Real connector-side probes succeeded:

- `list_devices`;
- `ping` -> `pong`;
- `get_config`;
- read-only host file metadata probe.

That evidence supports `RDC_EXECUTION_PLANE = VERIFIED`.

## Best use cases

- host filesystem/process/log inspection outside a repository-bound Coding Tools workspace;
- independent repair of WebGPT Gateway/OAuth/Manager/startup state when WebGPT itself is unavailable;
- bounded terminal/process recovery after classifying the failed layer;
- native GUI repair only while holding the shared machine GUI lease.

## Poor use cases

- repository edits/build/test/Git when Coding Tools is healthy and correctly bound;
- browser DOM work better handled by Playwright;
- treating an `online` device badge as health proof;
- recursive repair loops where WebGPT asks broken RDC to repair WebGPT or RDC asks broken WebGPT to repair RDC.

## Recovery matrix

- WebGPT healthy / RDC unhealthy: keep WebGPT READY; use structured Gateway-routed host capabilities to inspect and repair RDC where authorized.
- RDC healthy / WebGPT unhealthy: use RDC to inspect filesystem/process/log/startup state and perform only allowlisted recovery; reacquire fresh connector/tool refs after WebGPT returns.
- both healthy: route structured project/code work through WebGPT and independent full-machine recovery through RDC.
- both unhealthy: use local startup/reboot/human-local recovery. Do not pretend a dead remote plane can self-repair.

## Common mistakes

- checking only device visibility/auth/status;
- re-pairing or deleting device/session state before a real execution probe proves it necessary;
- starting from `@latest` on every boot and introducing version drift;
- recording tokens, refresh tokens, pairing secrets or relay credentials in Git/docs;
- letting RDC and Windows-MCP mutate the same physical GUI concurrently.

## Failure diagnosis

1. Confirm the installed/fixed runtime and local process.
2. Confirm the active device/control-plane state.
3. Run one real execution probe such as `ping` or `get_config`.
4. If control plane is online but execution fails, inspect local realtime/broadcast capability registration and session persistence before destructive re-pairing.
5. Select exactly one healthy recovery owner and verify post-state after one mutation attempt.

## Verification signals

- intended active device is online/authenticated;
- broadcast command transport capability is present when required by the connector;
- `ping` succeeds;
- `get_config` or an equivalent read-only remote host call succeeds;
- recovery does not downgrade WebGPT READY or mutate unrelated Gateway/OAuth credentials.

## GUI concurrency

Filesystem/process/terminal reads can overlap when independently safe. Mouse, keyboard, focus, clipboard, foreground-window and native-dialog mutations share physical desktop state with Windows-MCP and must be serialized through the machine GUI lease.

## Security

Never persist auth tokens, refresh tokens, pairing secrets, relay credentials or account secrets in repository files or public operating guides. Local runtime/session state stays outside Git.

## Accumulated lesson

Control-plane presence is not execution-plane liveness. The historical fake-online incident is now a protected routing rule: a real remote command must succeed before RDC is considered usable.
