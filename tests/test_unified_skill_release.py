from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPUTER_AGENT = ROOT / "skills" / "computer-agent"
WAC_SKILL = ROOT / "skills" / "webgpt-as-codex"
_SYNC_SPEC = importlib.util.spec_from_file_location(
    "sync_computer_agent_skill", ROOT / "scripts" / "sync_computer_agent_skill.py"
)
assert _SYNC_SPEC is not None and _SYNC_SPEC.loader is not None
_SYNC = importlib.util.module_from_spec(_SYNC_SPEC)
_SYNC_SPEC.loader.exec_module(_SYNC)
compare_portable = _SYNC.compare_portable
sync_portable = _SYNC.sync_portable


def test_unified_skill_versions_are_aligned() -> None:
    computer_manifest = json.loads(
        (COMPUTER_AGENT / "manifest.json").read_text(encoding="utf-8")
    )
    wac_manifest = json.loads(
        (WAC_SKILL / "manifest.json").read_text(encoding="utf-8")
    )
    assert computer_manifest["version"] == "1.2.0"
    assert wac_manifest["version"] == "1.2.0"
    assert "version: 1.2.0" in (COMPUTER_AGENT / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "version: 1.2.0" in (WAC_SKILL / "SKILL.md").read_text(
        encoding="utf-8"
    )


def test_experience_ledger_is_losslessly_shared() -> None:
    canonical = (COMPUTER_AGENT / "experience-ledger.md").read_bytes()
    product = (WAC_SKILL / "experience-ledger.md").read_bytes()
    assert canonical == product
    text = canonical.decode("utf-8")
    assert "RDC online does not prove a live execution plane" in text
    assert "Release and local Agent Skill must share one portable core" in text


def test_computer_agent_keeps_full_regression_set() -> None:
    scenarios = json.loads(
        (COMPUTER_AGENT / "evals" / "scenarios.json").read_text(encoding="utf-8")
    )
    ids = {row["id"] for row in scenarios}
    assert len(scenarios) >= 53
    assert {"R01", "R52", "R53"} <= ids


def test_canonical_skill_excludes_machine_local_overlay() -> None:
    assert not (COMPUTER_AGENT / "environment.local.md").exists()
    assert not (COMPUTER_AGENT / "MCP-SKILLS-INVENTORY.md").exists()
    assert not (COMPUTER_AGENT / "MCP-SKILLS-INVENTORY.json").exists()
    assert not (COMPUTER_AGENT / "state").exists()


def test_sync_preserves_target_overlay(tmp_path: Path) -> None:
    target = tmp_path / "computer-agent"
    target.mkdir()
    overlay = target / "environment.local.md"
    overlay.write_text("machine-local", encoding="utf-8")

    copied = sync_portable(target)

    assert copied
    assert overlay.read_text(encoding="utf-8") == "machine-local"
    assert compare_portable(target) == []


def test_wheel_declares_both_skill_profiles() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = project["tool"]["setuptools"]["data-files"]
    assert "share/webgpt-as-codex/skills/computer-agent" in data_files
    assert "share/webgpt-as-codex/skills/webgpt-as-codex" in data_files
