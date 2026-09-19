# Stage 9 Closure — Generic Add MCP / MCP Operating Guides

Result: CLOSED_LOCAL_VERIFIED

CURRENT_STAGE = STAGE-10-LOOP-ENGINEERING-DOGFOOD
NEXT_STAGE = STAGE-11-SECURITY-RELIABILITY-HARDENING
AFTER_NEXT_STAGE = STAGE-12-README-RELEASE-FINAL-ACCEPTANCE

## Implemented

- reusable machine-readable MCP Operating Guide schema covering mental model, best/poor use cases, actual exposed tools/input schemas, goal patterns, mistakes, failure diagnosis, verification, performance/cost, accumulated lessons and alternatives;
- discovery-first generic onboarding based on real MCP initialize + tools/list rather than component/server/tool names;
- explicit capability states: success, unavailable, failed and unattempted;
- manifest validation plus recursive credential-bearing literal rejection;
- default dry-run planning and explicit `--apply` mutation semantics;
- machine-local persistence of custom manifest, machine-readable Guide and routing/inventory receipt;
- same-manifest idempotence, conflicting same-id rejection and public-registry shadowing rejection;
- routing recommendation derived from actual tools/list evidence;
- registry/Manager/Doctor visibility for newly applied components without changing Stage 8 runtime ownership;
- public-safe Operating Guide attachments for Serena and Coding Tools;
- Skill/routing/add-mcp/architecture/decision/experience documentation updated with Stage 9 rules.

## Portable versus machine-local boundary

Portable repository knowledge:
- Guide contract/template;
- Serena/Coding Tools reusable operating Guides;
- stable component-id -> Guide attachment;
- routing and failure-diagnosis principles.

Machine-local only:
- custom MCP endpoint/config;
- machine-readable onboarding Guide generated from that live endpoint;
- availability/binding/path/health state;
- onboarding inventory receipt.

No secret, private URL, OAuth state, cookie, token, PID/process receipt or user-specific binding is promoted into Git.

## Lifecycle boundary

Stage 9 does not create a runtime adapter and does not change `MANAGER_RESTARTABLE`.

A newly onboarded MCP can become visible to:
- component registry;
- Manager shallow status;
- Doctor health reporting.

That visibility is not authority to start, stop, kill or restart the service. Stage 8 PID/ownership rules remain authoritative.

## Validation

Stage 9 narrow suite:
- 13 PASS.

Full repository:
- 70 PASS.

Static validation:
- Ruff PASS.
- Secret scan PASS.

Coverage includes:
- Operating Guide schema/required sections;
- public Guide attachment;
- real loopback fake-MCP HTTP initialize -> tools/list path;
- actual tool/schema preservation;
- unavailable service classification;
- malformed tools/list classification;
- nested credential-literal rejection;
- secret-bearing Guide rejection;
- dry-run non-persistence;
- explicit apply;
- same-manifest idempotence;
- conflicting duplicate rejection;
- public component shadowing rejection;
- routing/inventory attachment;
- registry/Manager/Doctor visibility;
- no Manager restart authority for newly onboarded components.

## Live MCP evidence

Real Stage 9 dry-run discovery:
- Coding Tools MCP: initialize/tools/list success, 18 exposed tools;
- Serena MCP: initialize/tools/list success, 29 exposed tools.

This confirms the capability-discovery path works against representative real MCPs. These counts are stage evidence rather than permanent capability assumptions.

The end-of-Stage-8 Serena listener-down observation was transient availability drift. Stage 9 did not silently restart Serena to manufacture a green result.

## Tool/harness lessons

- Coding Tools web connector remained bound away from this repository; its `git_status` therefore returned “not a Git repository”. The stage treated this as workspace-binding evidence and did not bypass the boundary.
- Web Serena could activate the repository but had no active language server for symbol overview. That was classified separately from service unavailability. The local Serena service remained usable for real MCP capability discovery.
- PowerShell on this host did not accept the attempted `&&` chaining form; switching to PowerShell-compatible sequencing fixed the harness issue.
- A nested base64/Python write attempt failed from shell quoting before changing the file. Direct structured Desktop Commander file writes were then used instead.
- These lessons were recorded in the Experience Ledger and relevant MCP Guides rather than preserved as brittle click/command anecdotes.

## Stage sizing evidence

This stage required:
- mandatory SoT reload;
- preferred-tool binding diagnosis;
- new onboarding implementation;
- focused safety/idempotence refinement;
- 13-test Stage 9 suite including a real loopback fake MCP;
- two representative live MCP discoveries;
- three new Guide artifacts plus Skill/routing/add-mcp updates;
- architecture/decision/experience/current-state updates;
- full test/lint/secret gates;
- closure, commit and verified recursive handoff.

The implementation itself remained bounded; closure and operating-knowledge documentation were a substantial fraction of stage cost. This is evidence for Stage 10's stage-sizing/dogfood work.

## Recursive continuation invariant

After this closure is committed:
1. read the real committed Stage 9 HEAD;
2. generate a fresh Stage 10 prompt from that HEAD;
3. validate required markers and SOURCE_HEAD;
4. hash the exact prompt;
5. use the already authenticated Playwright MCP browser context;
6. open/select a new ChatGPT tab;
7. focus the real visible composer and reacquire fresh DOM evidence;
8. submit the exact prompt once;
9. verify sent user message contains SOURCE_HEAD;
10. verify /c/ conversation plus a new assistant run;
11. persist the local handoff receipt.

Stage 10 inherits the same recursive requirement for Stage 11 and later stages through Final Overall Acceptance.
