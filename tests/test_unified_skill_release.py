from __future__ import annotations

import importlib.util
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
WAC_SKILL = SKILLS / "webgpt-as-codex"
_SYNC_SPEC = importlib.util.spec_from_file_location(
    "sync_webgpt_skill", ROOT / "scripts" / "sync_webgpt_skill.py"
)
assert _SYNC_SPEC is not None and _SYNC_SPEC.loader is not None
_SYNC = importlib.util.module_from_spec(_SYNC_SPEC)
_SYNC_SPEC.loader.exec_module(_SYNC)
compare_portable = _SYNC.compare_portable
sync_portable = _SYNC.sync_portable


def test_single_canonical_skill_tree() -> None:
    names = {path.name for path in SKILLS.iterdir() if path.is_dir()}
    assert names == {"webgpt-as-codex"}


def test_canonical_skill_version_and_name() -> None:
    manifest = json.loads((WAC_SKILL / "manifest.json").read_text(encoding="utf-8"))
    skill = (WAC_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert manifest["name"] == "webgpt-as-codex"
    version = re.search(
        r"(?m)^\s*version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$",
        skill,
    )
    assert version is not None
    assert manifest["version"] == version.group(1)
    assert manifest["canonical_skill"] is True
    assert "name: webgpt-as-codex" in skill


def test_experience_and_regressions_are_preserved() -> None:
    ledger = (WAC_SKILL / "experience-ledger.md").read_text(encoding="utf-8")
    assert "RDC online does not prove a live execution plane" in ledger
    assert "Release and local Agent Skill must share one portable core" in ledger
    scenarios = json.loads(
        (WAC_SKILL / "evals" / "scenarios.json").read_text(encoding="utf-8")
    )
    ids = {row["id"] for row in scenarios}
    assert len(scenarios) >= 53
    assert {"R01", "R52", "R53"} <= ids


def test_canonical_skill_excludes_machine_local_overlay() -> None:
    assert not (WAC_SKILL / "environment.local.md").exists()
    assert not (WAC_SKILL / "MCP-SKILLS-INVENTORY.md").exists()
    assert not (WAC_SKILL / "MCP-SKILLS-INVENTORY.json").exists()
    assert not (WAC_SKILL / "state").exists()


def test_sync_preserves_target_overlay(tmp_path: Path) -> None:
    target = tmp_path / "webgpt-as-codex"
    target.mkdir()
    overlay = target / "environment.local.md"
    overlay.write_text("machine-local", encoding="utf-8")
    copied = sync_portable(target)
    assert copied
    assert overlay.read_text(encoding="utf-8") == "machine-local"
    assert compare_portable(target) == []


def test_wheel_declares_only_webgpt_skill() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = project["tool"]["setuptools"]["data-files"]
    keys = [key for key in data_files if "/skills/" in key]
    assert keys
    assert all("/skills/webgpt-as-codex" in key for key in keys)
    assert not any("computer-agent" in key for key in keys)
    assert "share/webgpt-as-codex/skills/webgpt-as-codex/workflows" in data_files
    assert "share/webgpt-as-codex/skills/webgpt-as-codex/scripts" in data_files
