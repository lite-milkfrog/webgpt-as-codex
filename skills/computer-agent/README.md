# Computer Agent Skill

Local-first, GPT-Web-ready multi-MCP routing skill.

## Structure

- `SKILL.md` — compact entry and invariant rules
- `routing.md` — tool selection and fallback
- `permissions.md` — P0–P3 authorization model
- `environment.local.md` — current machine specifics, no secrets
- `workflows/` — coding/browser/desktop/files/cross-tool procedures，以及 Loop Engineering / Zero-Guess handoff template

## 1.1.2 additions

- Adaptive recovery ladder：先查后态，再分类失败，同工具换策略后才跨 MCP。
- Loop Engineering：每个语义阶段一个 conversation，阶段结束更新 SoT/进度/commit，并自动交下一棒。
- Zero-Guess Handoff：下一 prompt 必须明确工具、文件、精确路径、读取方式、使用方式、fallback、tests/gates、exit criteria 和 handoff。
- Single-writer rule：同一 Git worktree 默认只允许一个 active writer。
- Playwright overlay/intercept recovery：网页 click 被遮挡时先在 Playwright 内恢复，不直接跳 Windows-MCP。
- `validation.md` — completion checklist
- `maintenance.md` — A/B testing and pruning
- `gpt-web-port.md` — migration plan for persistent Remote MCPs
- `evals/scenarios.json` — routing/permission test cases
- `scripts/validate_skill.py` — deterministic structure validator

## Design rule

This Skill must stay smaller than the combined MCP manuals. It contains decisions and invariants, not vendor documentation.

## Local validation

```powershell
python .skills/computer-agent/scripts/validate_skill.py
```

Passing the validator means the bundle is structurally coherent. It does not mean every MCP is currently connected or that GPT Web registration is complete.
