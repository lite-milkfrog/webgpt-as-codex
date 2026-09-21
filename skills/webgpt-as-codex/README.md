# WebGPT-as-Codex Skill

The single canonical Skill shipped with WebGPT-as-Codex.

It combines the former Computer Agent routing/workflow core with the WebGPT-as-Codex product contract: MCP routing, permissions, recovery, browser/desktop automation, Loop Engineering, Gateway/OAuth operations, Doctor/Repair, and verified cross-conversation handoff.

## Structure

- `SKILL.md` — canonical entry, invariants and execution rules
- `product-contract.md` — WebGPT Gateway/OAuth/Manager/bootstrap/runtime rules
- `routing.md` — MCP selection, concurrency and fallback
- `permissions.md` — P0-P3 authorization model
- `workflows/` — coding, browser, desktop, file, GUI and handoff workflows
- `mcp-guides/` — reusable MCP operating knowledge
- `experience-ledger.md` — preserved operational lessons
- `evals/scenarios.json` — regression scenarios
- `scripts/validate_skill.py` — deterministic structural validator

Machine-specific endpoints, paths and transient health live only in the local `.skills/webgpt-as-codex/` overlay and are not committed to the public Skill.

## Local validation

```powershell
python .skills/webgpt-as-codex/scripts/validate_skill.py
```

A passing validator proves bundle coherence; live MCP/OAuth/remote readiness still requires real health checks.
