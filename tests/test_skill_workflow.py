import json
from pathlib import Path

import pytest

from webgpt_as_codex.skill_workflow import SkillWorkflowControlPlane


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_registry(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workflows": [
                    {
                        "id": "demo",
                        "title": "Demo",
                        "description": "demo workflow",
                        "stages": [
                            {
                                "id": "design",
                                "title": "Design",
                                "skills": [
                                    {"name": "frontend-design", "required": True},
                                    {"name": "impeccable", "required": False},
                                    {
                                        "name": "brandkit",
                                        "required": False,
                                        "when": "brand_needed",
                                    },
                                ],
                                "gate": {
                                    "type": "review",
                                    "requires": ["design accepted"],
                                },
                            },
                            {
                                "id": "qa",
                                "title": "QA",
                                "when": "qa_needed",
                                "skills": [
                                    {"name": "webapp-testing", "required": True}
                                ],
                                "gate": {
                                    "type": "validation",
                                    "requires": ["critical flows pass"],
                                },
                            },
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_skill_snapshot_uses_router_membership_and_persists_logical_move(
    tmp_path: Path,
) -> None:
    root = tmp_path / "skills"
    write(
        root / "category-web-ui" / "SKILL.md",
        "---\nname: web-ui\n---\n# Web UI\n",
    )
    write(
        root / "category-web-ui" / "references" / "routes.md",
        "- frontend-design -> ../../frontend-design/REFERENCE.md\n",
    )
    write(
        root / "frontend-design" / "REFERENCE.md",
        "---\nname: Frontend Design\ndescription: Distinctive frontend design.\n---\n",
    )
    registry = tmp_path / "workflow-registry.json"
    make_registry(registry)
    state_dir = tmp_path / "state" / "skills"
    control = SkillWorkflowControlPlane(
        skill_roots=[root],
        workflow_registry_path=registry,
        local_state_dir=state_dir,
    )

    snapshot = control.skill_snapshot()
    frontend = next(row for row in snapshot["skills"] if row["slug"] == "frontend-design")
    assert frontend["category"] == "web-ui"
    assert frontend["category_source"] == "category-router"
    assert frontend["path"].endswith("frontend-design")

    result = control.move_skill(frontend["id"], "favorites", 2)
    assert result["filesystem_changed"] is False
    assert (root / "frontend-design" / "REFERENCE.md").is_file()

    after = control.skill_snapshot()
    moved = next(row for row in after["skills"] if row["slug"] == "frontend-design")
    assert moved["category"] == "favorites"
    assert moved["category_source"] == "machine-overlay"
    assert moved["position"] == 2

    overlay = json.loads((state_dir / "control-plane.json").read_text(encoding="utf-8"))
    assert overlay["assignments"][frontend["id"]]["category"] == "favorites"


def test_workflow_planner_resolves_required_optional_and_conditional_skills(
    tmp_path: Path,
) -> None:
    root = tmp_path / "skills"
    write(root / "frontend-design" / "REFERENCE.md", "# Frontend Design\n")
    write(root / "brandkit" / "REFERENCE.md", "# Brandkit\n")
    registry = tmp_path / "workflow-registry.json"
    make_registry(registry)
    control = SkillWorkflowControlPlane(
        skill_roots=[root],
        workflow_registry_path=registry,
        local_state_dir=tmp_path / "state" / "skills",
    )

    plan = control.plan_workflow(
        "demo",
        {"brand_needed": True, "qa_needed": False},
    )
    assert plan["blocked"] is False
    design = plan["stages"][0]
    assert design["status"] == "degraded"
    by_name = {row["name"]: row for row in design["skills"]}
    assert by_name["frontend-design"]["available"] is True
    assert by_name["impeccable"]["available"] is False
    assert by_name["impeccable"]["required"] is False
    assert by_name["brandkit"]["available"] is True
    assert plan["stages"][1]["status"] == "skipped"


def test_workflow_planner_blocks_when_required_skill_missing(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    root.mkdir()
    registry = tmp_path / "workflow-registry.json"
    make_registry(registry)
    control = SkillWorkflowControlPlane(
        skill_roots=[root],
        workflow_registry_path=registry,
        local_state_dir=tmp_path / "state" / "skills",
    )

    plan = control.plan_workflow("demo", {"qa_needed": False})
    assert plan["blocked"] is True
    assert plan["stages"][0]["status"] == "blocked"


def test_run_state_persists_and_advances(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write(root / "frontend-design" / "REFERENCE.md", "# Frontend Design\n")
    write(root / "webapp-testing" / "REFERENCE.md", "# Web App Testing\n")
    registry = tmp_path / "workflow-registry.json"
    make_registry(registry)
    control = SkillWorkflowControlPlane(
        skill_roots=[root],
        workflow_registry_path=registry,
        local_state_dir=tmp_path / "state" / "skills",
    )

    run = control.start_run("demo", {"qa_needed": True})
    assert run["current_stage"] == "design"
    assert run["stages"][0]["status"] == "in_progress"

    advanced = control.transition_run(
        run["run_id"],
        "design",
        "passed",
        "design evidence",
    )
    assert advanced["current_stage"] == "qa"
    assert advanced["stages"][0]["evidence"][0]["text"] == "design evidence"
    assert advanced["stages"][1]["status"] == "in_progress"

    complete = control.transition_run(
        run["run_id"],
        "qa",
        "passed",
        "browser evidence",
    )
    assert complete["status"] == "complete"
    assert complete["current_stage"] is None
    assert control.list_runs()[0]["run_id"] == run["run_id"]


def test_unknown_skill_id_cannot_be_used_as_arbitrary_path(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    root.mkdir()
    registry = tmp_path / "workflow-registry.json"
    make_registry(registry)
    control = SkillWorkflowControlPlane(
        skill_roots=[root],
        workflow_registry_path=registry,
        local_state_dir=tmp_path / "state" / "skills",
    )

    with pytest.raises(KeyError):
        control.open_skill_location(str(tmp_path / "outside"))
