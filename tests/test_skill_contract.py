import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "webgpt-as-codex"


def test_skill_has_required_invariants() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    required = ["CURRENT_STAGE", "NEXT_STAGE", "AFTER_NEXT_STAGE", "local SoT", "Validation", "Handoff"]
    for marker in required:
        assert marker in text


def test_skill_manifest_is_public_safe() -> None:
    data = json.loads((SKILL / "manifest.json").read_text(encoding="utf-8"))
    assert "no_secrets_in_git" in data["invariants"]


def test_skill_evals_cover_handoff_and_fallback() -> None:
    data = json.loads((SKILL / "evals" / "scenarios.json").read_text(encoding="utf-8"))
    ids = {item["id"] for item in data}
    assert {"serena-down", "handoff", "parallel-edit"} <= ids
