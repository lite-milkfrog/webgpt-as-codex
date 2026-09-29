# OAuth Password Input over Remote MCP — Maintenance Follow-up

DATE = 2026-09-29
STATUS = OPEN_NEEDS_REPRO
OWNER = WebGPT-as-Codex maintenance
PROGRAM_STATE = POST-COMPLETE-MAINTENANCE

## Reported symptom

A remote-control / MCP connection flow protected by OAuth may present a password-authentication step that the remote interaction path cannot reliably focus, type into, paste into, or submit.

This is a new post-complete maintenance report. It does not invalidate the previously verified OAuth issuance, refresh-token continuity, Manager password-management controls, or protected MCP 401/DCR/PKCE evidence.

## Scope distinction

Do not conflate two different surfaces:

1. Manager-local OAuth password management:
   - set;
   - reveal;
   - regenerate;
   - local loopback/control-header/confirm security boundaries.

2. Remote OAuth authentication interaction:
   - an OAuth/browser/connector challenge rendered while connecting a remote MCP;
   - ability of the authorized remote-control path to focus the secret field and complete the authentication form.

The reported defect concerns surface 2 until reproduction proves otherwise.

## Security constraints

- Never write a real OAuth password into repository files, logs, test snapshots, MCP transcripts, SoT, screenshots, or durable receipts.
- Use a disposable test credential or synthetic secret for reproduction.
- Secret-bearing DOM/input values must not be included in debug output.
- If the authentication surface is controlled by the host platform and intentionally blocks programmatic secret entry, document that boundary rather than bypassing it.

## Reproduction plan

1. Start from a healthy WAC Gateway/OAuth/Manager state.
2. Use an authorized OAuth-protected MCP test connection.
3. Reach the actual password challenge without printing the credential.
4. Determine which interaction plane owns the field:
   - normal web DOM / Playwright;
   - browser chrome or platform connector UI;
   - native/system dialog;
   - external host boundary.
5. Test focus, keyboard input, paste policy, Enter/button submit and post-submit state.
6. Classify failure as product defect, browser/automation limitation, connector boundary, or observer failure.
7. Implement the narrowest safe repair if WAC owns the defect.
8. Add regression coverage for the owned layer.
9. Re-run OAuth/Gateway/Manager regression plus secret scan.

## Acceptance criteria

The follow-up closes only when all applicable items are evidenced:

- the password field can be focused through the supported authorized path;
- a disposable secret can be entered without being echoed into logs/evidence;
- submission succeeds exactly once and the OAuth flow advances;
- keyboard and paste behavior are documented;
- failed/blocked platform-owned secret entry has an explicit safe human-in-the-loop fallback;
- no plaintext password persists in repository or machine-local diagnostic evidence;
- related OAuth/Gateway/Manager tests remain green;
- repository secret scan passes.

## Current disposition

OPEN_NEEDS_REPRO.

Do not claim this issue fixed merely because Manager can reveal/regenerate the local OAuth password or because DCR/PKCE token exchange succeeds through a non-interactive test harness. The acceptance target is the real remote authentication interaction path reported by the user.
