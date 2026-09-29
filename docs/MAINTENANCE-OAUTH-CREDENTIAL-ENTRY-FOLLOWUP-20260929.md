# OAuth Password Input over Remote MCP — Maintenance Follow-up

DATE = 2026-09-29
STATUS = TRIAGED_SERVER_FORM_PRESENT
OWNER = WebGPT-as-Codex maintenance + consuming-client boundary
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

The reported symptom concerns surface 2, but live reproduction has now separated server-form availability from consuming-client reachability.

## Live reproduction — 2026-09-29

No real OAuth password was read, printed, submitted, persisted or placed into evidence.

Using the running loopback OAuth Edge only:

- OAuth Authorization Server Metadata advertises:
  - authorization endpoint path `/.idp/auth`;
  - token endpoint path `/.idp/token`;
  - dynamic registration endpoint path `/.idp/register`.
- a disposable Dynamic Client Registration request returned HTTP 201;
- a disposable PKCE authorization request followed this redirect chain:
  - `/.idp/auth`;
  - `/.idp/auth/<ephemeral-request-id>`;
  - `/.auth/login`.
- `GET /.auth/login` returned HTTP 200 with:
  - one form, `POST /.auth/login`;
  - one `input type=password name=password id=password`;
  - one submit control labelled `Login`.

Therefore the WAC/mcp-auth-proxy authorization server **does provide a real password-entry page**. The user's “no place to enter the OAuth password” symptom cannot be explained by absence of a WAC password field.

The consuming JARVIS client was then inspected. Its current remote-MCP OAuth flow:

- requires a manually supplied OAuth Client ID before authorization starts;
- reads protected-resource and authorization-server metadata;
- does not consume the advertised `registration_endpoint`;
- rejects blank Client ID before it opens the browser authorization URL.

For self-hosted DCR-capable MCPs this can prevent the user from ever reaching WAC's real password page. That gap is now owned by the JARVIS J213-07R2 remediation track.

## Security constraints

- Never write a real OAuth password into repository files, logs, test snapshots, MCP transcripts, SoT, screenshots, or durable receipts.
- Use a disposable test credential or synthetic secret for reproduction.
- Secret-bearing DOM/input values must not be included in debug output.
- If the authentication surface is controlled by the host platform and intentionally blocks programmatic secret entry, document that boundary rather than bypassing it.

## Reproduction plan

1. Start from a healthy WAC Gateway/OAuth/Manager state. **DONE**
2. Use a disposable DCR + PKCE test connection without exposing secrets. **DONE**
3. Reach the actual password challenge without printing the credential. **DONE**
4. Determine which interaction plane owns the field. **DONE: normal server-owned web DOM**
5. If a WAC automation defect is still reported after the consuming client can reach the page, test:
   - normal web DOM / Playwright;
   - browser chrome or platform connector UI;
   - native/system dialog;
   - external host boundary.
6. Test focus, keyboard input, paste policy, Enter/button submit and post-submit state with a disposable credential only if WAC interaction ownership remains in question.
7. Classify any remaining failure as WAC defect, browser/automation limitation, consuming-client defect, connector boundary, or observer failure.
8. Implement the narrowest safe repair only in the repository that owns the reproduced defect.
9. Add regression coverage for the owned layer and re-run its security gates.

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

TRIAGED_SERVER_FORM_PRESENT.

WAC server-form absence is disproven. Do not add or duplicate a second password field in JARVIS: the authorization password belongs on the server-owned browser page and must never be collected or synchronized by JARVIS.

The JARVIS self-hosted-MCP reachability gap remains open under J213-07R2 until blank-Client-ID + advertised-DCR successfully reaches the browser authorization page and the callback/token/tool-list path is verified. A separate WAC automation defect should only be reopened if the page is reachable but the supported authorized browser-control path still cannot focus/type/submit a disposable credential.
