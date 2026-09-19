# Handoff

A handoff prompt is generated from verified local state after the current stage commit.
It is never a copy of the previous prompt with only a renamed stage.

The repository may commit a durable next-stage handoff plan containing CURRENT/NEXT/AFTER_NEXT, objective, outputs, boundaries and risks, but the plan must not freeze SOURCE_HEAD. After commit, prompt generation injects the real HEAD, validates all four pointers and hashes the exact bytes.

## Stability gate
Every prompt must contain:
- CURRENT_STAGE
- NEXT_STAGE
- AFTER_NEXT_STAGE
- SOURCE_HEAD from the committed stage
- mandatory local read order
- one stage objective
- required outputs
- explicit do-not-redo boundary
- known risks/evidence
- MCP routing contract
- failure protocol
- safety contract
- closure contract
- recursive continuation invariant
- automatic Playwright handoff contract

Use `webgpt_as_codex.handoff.validate_handoff_prompt` before submission.
Store the prompt SHA-256 in the local handoff receipt.

## Before handoff
1. finish stage implementation and validation;
2. update all affected docs, decision/risk log and Experience Ledger;
3. write the stage closure;
4. commit the stage;
5. read the real committed HEAD;
6. generate the next prompt from that HEAD;
7. validate required markers and SOURCE_HEAD;
8. verify the prompt file exists locally.

## Recursive continuation invariant
When automatic continuation is authorized, every window inherits the same obligation:
1. finish and commit its CURRENT_STAGE;
2. compute the real new HEAD;
3. instantiate a fresh prompt for NEXT_STAGE, carrying the next window's own NEXT_STAGE and AFTER_NEXT_STAGE;
4. validate and hash that prompt;
5. Playwright-submit it to a new ChatGPT conversation;
6. verify sent user message + new assistant run;
7. make that next window repeat the exact protocol.

Do not terminate at an intermediate stage boundary.
The recursion terminates only after the planned final stage and Final Overall Acceptance are CLOSED_LOCAL_VERIFIED.

## Automatic continuation
When authorized:
1. use Playwright MCP with the already authenticated ChatGPT browser context; prefer a new tab/page in that context, not a fresh isolated browser profile;
2. keep one MCP session for the entire handoff; extension tab indexes/refs are not stable across MCP sessions;
3. open a new ChatGPT conversation, then enumerate/select that new ChatGPT tab in the same MCP session instead of assuming the extension made it current/focused;
   If a pre-submit recovery starts after that tab was already created and a fresh MCP session cannot prove it by index set-difference, refresh once; only when exactly one blank ChatGPT tab exists may that unique blank be reused and explicitly selected. Multiple blank candidates remain ambiguous and must fail rather than guess.
4. use live DOM geometry/style to focus a visible editable composer on the selected page, then reacquire a fresh snapshot and use that focused active ref; initial hydration may expose a hidden autofocus fallback textarea that can also appear `[active]`, so snapshot-active alone is not proof of visibility;
5. type the exact validated prompt as a draft with submission disabled; hidden hydration, stale refs and tab-selection ambiguity may be recovered only before submission and only with fresh DOM/tab evidence;
6. attempt the real submit exactly once;
7. after submit is attempted, never press Enter/click Send again even if the MCP response is lost; query post-state for the sent user message containing SOURCE_HEAD, /c/ URL and assistant-run evidence;
8. if post-state cannot disambiguate the result, fail as ambiguous submission rather than risking a duplicate message;
9. write a machine-local handoff receipt with prompt path, SHA-256, source HEAD, conversation URL, first-pass result, recovery classes and verification evidence.

A filled textbox, click, navigation, prompt file, or URL change alone is not proof of successful handoff.
A prompt typed into a hidden hydration fallback is also not progress; reacquire live DOM visibility evidence, focus the visible editable composer and then select its fresh active ref rather than using stale refs or coordinate clicks.
