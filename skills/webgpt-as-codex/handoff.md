# Handoff

A handoff prompt is generated from verified local state after the current stage commit.
It is never a copy of the previous prompt with only a renamed stage.

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

## Automatic continuation
When authorized:
1. use Playwright MCP with the logged-in ChatGPT browser state;
2. open a new ChatGPT conversation;
3. enter the exact validated prompt file;
4. submit once;
5. verify the prompt appears as a sent user message;
6. verify a new assistant run/response begins;
7. write a handoff receipt with prompt path, SHA-256, source HEAD and verification evidence.

A filled textbox, click, navigation, prompt file, or URL change alone is not proof of successful handoff.
