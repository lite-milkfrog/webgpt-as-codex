from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_skills_manager_component_contract() -> None:
    data = json.loads(
        (ROOT / "components" / "skills-control-plane.json").read_text(encoding="utf-8")
    )
    assert data["id"] == "skills-control-plane"
    assert data["upstream"] == "https://github.com/lite-milkfrog/skills-manager"
    assert data["default_endpoint"] == "http://127.0.0.1:8943/mcp"
    assert data["ownership_mode"] == "external_local"
    assert data["readiness_contract"] == "mcp-initialize-tools-list"
    assert data["gateway_exposure"] == "gateway"
    assert data["refresh_registration"] is True
    assert data["safe_tool"] == "skills_status"
    assert data["dependencies"] == ["mcpjungle"]


def test_skills_manager_installer_is_non_destructive() -> None:
    script = (ROOT / "scripts" / "install_skills_manager.ps1").read_text(
        encoding="utf-8"
    )
    assert "status --porcelain" in script
    assert "git -C $ResolvedTarget" in script
    assert "refusing automatic update" in script
    assert "merge" in script and "--ff-only" in script
    assert "import-production.py" in script
    assert "install-integration.ps1" in script
    assert "SKILLS_MANAGER_HOME" in script
    assert "skills-control-plane" in script


def test_one_click_deployment_requires_latest_standalone_skills_manager() -> None:
    prompt = (ROOT / "prompts" / "ONE-CLICK-AGENT-DEPLOY.md").read_text(encoding="utf-8")
    deployment = (ROOT / "docs" / "DEPLOYMENT.md").read_text(encoding="utf-8")
    for text in (prompt, deployment):
        assert "scripts/install_skills_manager.ps1" in text
        assert "lite-milkfrog/skills-manager" in text
    assert "SKILLS_MANAGER_HEAD" in prompt
    assert "8943" in prompt


def test_skills_manager_guides_keep_execution_boundary() -> None:
    guide = (
        ROOT / "skills" / "webgpt-as-codex" / "mcp-guides" / "skills-manager.md"
    ).read_text(encoding="utf-8")
    assert "Do not rebuild a second Workflow executor inside WAC." in guide
    assert "skills_resolve" in guide
    assert "Frontend Product Builder v4" in guide
    assert "Creator Studio v4" in guide
