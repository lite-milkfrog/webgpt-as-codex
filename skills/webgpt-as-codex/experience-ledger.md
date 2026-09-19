# Experience Ledger Contract

For every defensive rule keep:
- origin/failure that created it;
- current failure mechanism;
- verification evidence;
- current location of the lesson;
- status: active, relocated, or retired-with-evidence.

Protected examples:
- OAuth authorized but client did not resume;
- PKCE/state/redirect/issuer mismatch;
- browser extension/login-state behavior;
- Playwright host validation;
- stale UI snapshots/high-DPI coordinates;
- HOME/USERPROFILE service-context failure;
- process alive versus MCP healthy;
- handoff submit verification;
- local memory for long tasks;
- Windows console encoding causing the harness, not the target, to fail.

Never delete a lesson only because current code looks simpler.

## 2026-09-19 — Real HTTPS is authoritative for OAuth acceptance

Origin:
- Stage 5 OAuth + Tailscale edge integration.
- A localized HTTP probe of an HTTPS external OAuth flow produced invalid authorization-session failures because Secure-cookie/origin behavior differed from the real client path.

Protected lesson:
- do not treat localhost HTTP localization as authoritative for an OAuth flow whose advertised external URL is HTTPS;
- preserve X-Forwarded-Proto and X-Forwarded-Host at the compatibility boundary;
- validate DCR, PKCE, consent, token, refresh and MCP access through the real HTTPS edge;
- an OAuth compatibility adapter may preserve session/consent continuity, but must not bypass authentication;
- test passwords and OAuth databases remain machine-local.

## 2026-09-19 — Temporary integration instances must not mutate shared agent state

Origin:
- Stage 4 temporary Serena initially used activate_project through a shared Serena configuration and changed the main Serena active project.

Protected lesson:
- start temporary Serena with --project / --project-from-cwd;
- do not use a temporary integration test to mutate a shared Serena active project;
- verify active project before repo-relative writes;
- after any suspicious project switch, verify both target and unrelated repository git status before continuing.

## 2026-09-19 — Playwright Extension handoff must stay in one MCP session

Origin:
- Stage 5 automatic handoff hardening.
- A new Playwright MCP session re-entered through the extension Welcome page; a tab index visible in a previous MCP session was not selectable in the next one.

Protected lesson:
- new ChatGPT tab, snapshot, composer target, submit and verification belong to one Playwright MCP session;
- never carry Playwright element refs or tab indexes across MCP sessions;
- verify handoff from ChatGPT DOM state, not from a click or URL assumption;
- sent-message proof is the user-message DOM containing SOURCE_HEAD;
- new-run proof is an assistant-message DOM node plus a /c/ conversation URL.

## 2026-09-19 — MCP SSE responses may be fragmented across data lines

Origin:
- First live Stage 5 -> Stage 6 Playwright handoff attempt.
- The executor reached browser_snapshot before any prompt submission, then failed because the decoder assumed one complete JSON object per SSE data line.

Protected lesson:
- parse an SSE event as a whole, not only its first data line;
- tolerate data payload fragmentation/line wrapping before JSON decode;
- share one MCP decoder across Doctor, Gateway tests and Playwright handoff;
- a handoff that fails before composer typing has not submitted anything and is safe to repair/retry after a new prompt HEAD is generated.

## 2026-09-19 — Coding Tools workspace binding is authoritative

Origin:
- Stage 6 found Coding Tools attached to `coding-tools-mcp-demo` instead of the target repository.
- Repo-relative access therefore did not address WebGPT-as-Codex.

Protected lesson:
- verify the reported Coding Tools workspace before repository operations;
- honor the configured workspace boundary;
- when rebinding is unavailable, use a dedicated Git worktree located inside the configured workspace and fast-forward the canonical tree only after validation;
- workspace mismatch is harness state, not evidence that target files are absent.

## 2026-09-19 — Manager polling must not become deep-health polling

Origin:
- Stage 6 needed component status while preserving the process/listener/protocol/safe-call/OAuth/remote distinction.

Protected lesson:
- use a bounded status cache and inexpensive listener discovery in the Manager;
- consume deep Doctor evidence rather than running MCP safe calls on every browser refresh;
- unknown, failed and healthy are separate states;
- never render raw manifests or private/loopback service addresses.

## 2026-09-19 — Control actions are owner-stage capabilities

Origin:
- Stage 6 owns Manager contracts, while Doctor/Repair and runtime launch/restart belong to later stages.

Protected lesson:
- expose only a fixed action allowlist;
- no arbitrary command or argument surface belongs in the Manager API;
- confirmation is required for mutating contracts;
- real executors are injected by the stage that owns their safety and rollback semantics.
