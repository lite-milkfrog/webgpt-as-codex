# Remote Desktop Commander Final Recovery-Plane Closure

STABLE_CORE_VERSION = LE-STABLE-2026-09-17.2

SOURCE_HEAD = 95a4e42004d20f13d09e9d5aec9829e66ec0b2e3

This closure belongs to `SUPPLEMENTAL-FINAL-ACCEPTANCE`. It does not reopen Stage 1-19 and does not create a new product stage.

## Entry truth

```text
RDC_VERSION = 0.2.51
RDC_INSTALLATION = VERIFIED
RDC_LOCAL_PROCESS = VERIFIED
RDC_CONTROL_PLANE = VERIFIED
RDC_TRANSPORT_BROADCAST_V1 = VERIFIED
RDC_EXECUTION_PLANE = VERIFIED
WEBGPT_PRIMARY_PLANE = VERIFIED
```

The active paired Windows device used by the real acceptance was `JIAOLONG16proSeries`. An older 0.2.50 offline device/session record is historical and is not the active health authority.

## Architecture

The final relationship is:

```text
WebGPT-as-Codex
= primary structured execution plane

Remote Desktop Commander
= independent complementary full-machine repair/control plane
```

RDC is not:
- a WebGPT Gateway child;
- an internal Unified Gateway MCP dependency;
- a WebGPT READY prerequisite;
- part of the WebGPT OAuth/Funnel lifecycle.

A desktop bootstrap may request RDC startup after WebGPT itself reaches READY, but RDC failure does not invalidate WebGPT READY.

## Incident

The recovered incident exposed a false-online state:

```text
control plane:
device visible
auth valid
status online

execution plane:
ping failed
get_config failed
no live connection
```

The protected invariant is:

```text
CONTROL_PLANE_ONLINE != EXECUTION_PLANE_LIVE
```

RDC health must therefore be evaluated at four distinct layers:

1. installation;
2. local process;
3. control plane;
4. execution plane.

Only a real command probe can promote RDC to usable execution-plane state.

## Root cause

The incident was local/vendor-runtime transport state, not a WebGPT Gateway failure.

Observed failure mechanism:

```text
RDC starts
-> session/auth available
-> realtime channel joins
-> presence succeeds
-> control plane reports online
-> broadcast transport capability update fails
-> presence remains tracked
-> old watchdog checks presence but does not reliably restore missing transport capability
-> device remains apparently online
-> live command transport is unavailable
```

An earlier stale persisted session/refresh state also contributed to unreliable reauthorization persistence. Recovery preserved backup evidence and did not place any token, refresh token, pairing secret or relay credential in Git.

## Repair

The local repair is intentionally not vendored into this repository. Public-safe operating truth is:

- fixed local RDC runtime at 0.2.51 rather than resolving `@latest` every startup;
- idempotent launcher behavior that preserves an existing agent;
- direct fixed-runtime startup with PID/log evidence and non-zero failure reporting;
- broadcast-capability self-heal when presence is already tracked but transport capability is still missing;
- clean session recovery/persistence after stale local session state;
- RDC remains independent from Gateway/OAuth/WebGPT READY lifecycle.

## Real execution-plane verification

The final acceptance used the ChatGPT-side RDC connector, not only local logs or process state.

```text
list_devices = PASS
ping = PASS -> pong
get_config = PASS
read-only host file probe = PASS
```

The active device reported RDC 0.2.51 and `transport_broadcast_v1=true`. The read-only host probe successfully inspected the local RDC launcher file metadata.

Therefore:

```text
RDC_EXECUTION_PLANE = VERIFIED
```

## Complementary recovery matrix

### WebGPT healthy / RDC unhealthy

WebGPT remains READY. Use structured Coding Tools / Windows-MCP / approved local control capability to inspect the RDC runtime and attempt only authorized recovery. RDC failure must not downgrade WebGPT READY.

### RDC healthy / WebGPT unhealthy

Use RDC filesystem/terminal/process/log capability to inspect Gateway, Coding Tools, OAuth edge, Tailscale/Funnel, Manager, Playwright/Windows-MCP relays and startup scripts. After WebGPT recovers, reacquire fresh connector/session/tool references instead of reusing stale refs.

### Both healthy

Route structured project/code work primarily through WebGPT. Route independent full-machine recovery through RDC. Browser DOM remains Playwright-owned. Native GUI work uses Windows-MCP or RDC subject to the shared machine GUI lease.

### Both unhealthy

Use local desktop bootstrap, local startup/reboot or human-local recovery. A dead remote endpoint is never treated as capable of repairing itself.

## Loop prevention

Recovery is attempt-scoped and non-recursive:

```text
probe
-> classify
-> choose one healthy recovery owner
-> mutate at most once within authority
-> verify post-state
```

An unhealthy plane is never selected as the active recovery executor. A WebGPT -> RDC -> WebGPT repair loop is invalid.

## GUI concurrency

Filesystem/process/terminal work can overlap when independently safe. Mouse, keyboard, foreground focus, clipboard, native dialogs and other physical-desktop mutations are shared state across RDC and Windows-MCP and require the Stage 16 machine GUI lease/serialization rule.

## Reboot truth

This closure did not force a new destructive Windows reboot.

```text
REBOOT_RECOVERY_DESIGN = IMPLEMENTED
PROCESS_RESTART_SESSION_RESTORE = VERIFIED
LOCAL_RDC_STARTUP_IDEMPOTENCE = VERIFIED
FULL_WINDOWS_REBOOT_ACCEPTANCE = NOT_RE-RUN_IN_THIS_CLOSURE
```

Any final Supplemental claim about a physical reboot must use separate real reboot evidence; this document does not manufacture one.

## Repository scope

No Gateway runtime, OAuth/Funnel implementation, Coding Tools, Serena, Playwright or Windows-MCP product code was reopened for this RDC incident. The repository change is limited to public-safe architecture/recovery/routing documentation and the Product Skill operating guide.

The fixed vendor runtime, local session state and local logs remain outside Git.

## Documentation reconciliation

```text
docs/ARCHITECTURE.md = UPDATED_WITH_NEW_EVIDENCE
docs/zh-CN/ARCHITECTURE.md = UPDATED_WITH_NEW_EVIDENCE
docs/CONCURRENCY-AND-FALLBACK.md = UPDATED_WITH_NEW_EVIDENCE
docs/zh-CN/CONCURRENCY-AND-FALLBACK.md = UPDATED_WITH_NEW_EVIDENCE
docs/DECISIONS-AND-RISKS.md = UPDATED_WITH_NEW_EVIDENCE
docs/zh-CN/DECISIONS-AND-RISKS.md = UPDATED_WITH_NEW_EVIDENCE
docs/DEPLOYMENT.md = UPDATED_WITH_NEW_EVIDENCE
docs/zh-CN/DEPLOYMENT.md = UPDATED_WITH_NEW_EVIDENCE
docs/CURRENT-PROJECT-STATE.md = UPDATED_WITH_NEW_EVIDENCE
docs/zh-CN/CURRENT-PROJECT-STATE.md = UPDATED_WITH_NEW_EVIDENCE
skills/webgpt-as-codex/routing.md = UPDATED_WITH_NEW_EVIDENCE
skills/webgpt-as-codex/zh-CN/routing.md = UPDATED_WITH_NEW_EVIDENCE
skills/webgpt-as-codex/experience-ledger.md = UPDATED_WITH_NEW_EVIDENCE
skills/webgpt-as-codex/mcp-guides/remote-desktop-commander.md = ADDED
skills/webgpt-as-codex/zh-CN/mcp-guides/remote-desktop-commander.md = ADDED
```

## Validation

Repository validation for this isolated RDC closure worktree:

```text
targeted Stage16/18/19 regression = 38 PASS
full repository regression = 205 PASS
Ruff = PASS
repository secret scan = SECRET_SCAN_PASS
git diff --check = PASS
Computer Agent validator = VALIDATION_OK
Computer Agent scenarios = 52
Computer Agent inventory JSON = parse PASS
```

The first full-suite attempt was intentionally rejected as harness evidence because the shared editable virtual environment imported the dirty main worktree runtime while the tests came from this isolated worktree. After forcing `PYTHONPATH=src`, import truth resolved to this worktree and the full 205-test suite passed. No target failure was inferred from the mixed-worktree harness.

The real RDC execution-plane acceptance above is inherited from the verified recovery handoff and is not re-simulated by repository unit tests.

## Handoff

This closure returns to `SUPPLEMENTAL-FINAL-ACCEPTANCE` for reconciliation with the independent Desktop Launcher repair evidence.

Do not create another product stage. If the Desktop Launcher/final reconciliation and all remaining owned work are green, the enclosing Supplemental Final Acceptance may proceed to `GLOBAL_LOOP_COMPLETE`.
