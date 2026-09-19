# Stable Handoff Contract

Every generated handoff prompt must be instantiated from verified local state, never by renaming the previous prompt.

Required facts:
- CURRENT_STAGE
- NEXT_STAGE
- AFTER_NEXT_STAGE
- SOURCE_HEAD
- mandatory local read order
- single stage objective
- required outputs
- explicit do-not-redo boundary
- known risks/evidence
- MCP routing contract
- failure protocol
- safety contract
- closure contract
- automatic Playwright handoff contract

Submission is allowed only after programmatic validation passes.
A handoff is successful only after Playwright verifies both the sent user message and a new assistant run/response.
