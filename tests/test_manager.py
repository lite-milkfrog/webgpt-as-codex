import http.client
import json
import threading
from pathlib import Path

import pytest

from webgpt_as_codex.health import (
    HEALTH_LEVELS,
    ManagerStatusService,
    configured_public_mcp_url,
    sanitize_for_output,
)
from webgpt_as_codex.manager import (
    ACTION_CONTRACTS,
    ActionConfirmationError,
    ActionRunner,
    build_server,
)
from webgpt_as_codex.skill_workflow import SkillWorkflowControlPlane


def test_public_url_accepts_https_and_rejects_private_or_credentialed() -> None:
    assert configured_public_mcp_url({"public_mcp_url": "https://example.test/mcp"}) == "https://example.test/mcp"
    assert configured_public_mcp_url({"public_mcp_url": "http://example.test/mcp"}) is None
    assert configured_public_mcp_url({"public_mcp_url": "https://127.0.0.1/mcp"}) is None
    assert configured_public_mcp_url({"public_mcp_url": "https://user:pass@example.test/mcp"}) is None
    assert configured_public_mcp_url({"public_mcp_url": "https://example.test/mcp?token=x"}) is None


def test_recursive_redaction_hides_secrets_and_private_urls() -> None:
    value = {
        "password": "secret-value",
        "nested": {"access_token": "abc", "url": "http://127.0.0.1:9000/mcp"},
        "message": "Bearer abc.def",
    }
    cleaned = sanitize_for_output(value)
    text = json.dumps(cleaned)
    assert "secret-value" not in text
    assert "abc.def" not in text
    assert "127.0.0.1" not in text
    assert cleaned["nested"]["url"] == "[private-url]"


def test_action_contracts_are_fixed_and_confirm_mutating_actions() -> None:
    assert set(ACTION_CONTRACTS) == {"start_all", "restart", "doctor", "repair", "update"}
    runner = ActionRunner(
        {"repair": lambda _contract, _payload: {"ok": True, "token": "must-not-leak"}}
    )
    with pytest.raises(ActionConfirmationError):
        runner.run("repair")
    result = runner.run("repair", confirm=True)
    assert result["ok"] is True
    assert result["token"] == "[redacted]"


def test_default_runner_does_not_execute_future_stage_actions() -> None:
    runner = ActionRunner()
    result = runner.run("start_all")
    assert result["ok"] is False
    assert result["status"] == "not-available-yet"
    assert result["owner_stage"] == "STAGE-8-DESKTOP-LAUNCHER-AND-AUTOSTART"


def test_status_schema_has_distinct_health_levels(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    snapshot = ManagerStatusService(cache_ttl_seconds=1).snapshot(force=True)
    assert snapshot["health_levels"] == list(HEALTH_LEVELS)
    assert "gateway" in snapshot and "oauth" in snapshot and "tailscale" in snapshot
    assert "remote_desktop_commander" in snapshot
    for component in snapshot["components"]:
        assert set(component["health"]) == set(HEALTH_LEVELS)
        assert "default_endpoint" not in component
        assert "raw" not in component


def test_status_reads_sanitized_last_doctor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    doctor_dir = tmp_path / "doctor"
    doctor_dir.mkdir(parents=True)
    (doctor_dir / "last-result.json").write_text(
        json.dumps(
            {
                "status": "pass",
                "summary": "Bearer should-not-leak",
                "checks": {"callback": "http://127.0.0.1:9999/private"},
            }
        ),
        encoding="utf-8",
    )
    snapshot = ManagerStatusService(cache_ttl_seconds=1).snapshot(force=True)
    text = json.dumps(snapshot)
    assert "should-not-leak" not in text
    assert "127.0.0.1" not in text


def test_manager_is_loopback_only() -> None:
    with pytest.raises(ValueError):
        build_server("0.0.0.0", 0)


def test_http_action_requires_control_header() -> None:
    server = build_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request(
            "POST",
            "/api/actions/doctor",
            body="{}",
            headers={
                "Host": f"127.0.0.1:{port}",
                "Content-Type": "application/json",
            },
        )
        response = conn.getresponse()
        response.read()
        assert response.status == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_manager_ui_has_bounded_polling_and_no_embedded_secret() -> None:
    static = Path(__file__).resolve().parents[1] / "manager" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "manager.js").read_text(encoding="utf-8")
    assert "poll_after_ms" in script
    assert "setInterval(" not in script
    assert "/api/password" not in html + script
    assert 'src="/manager.js"' in html
    assert "payload.component" in script


def _manager_control_plane(tmp_path: Path) -> SkillWorkflowControlPlane:
    root = tmp_path / "skills"
    skill = root / "frontend-design"
    skill.mkdir(parents=True)
    (skill / "REFERENCE.md").write_text("# Frontend Design\n", encoding="utf-8")
    registry = tmp_path / "workflow-registry.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workflows": [
                    {
                        "id": "demo",
                        "title": "Demo",
                        "stages": [
                            {
                                "id": "design",
                                "title": "Design",
                                "skills": [
                                    {
                                        "name": "frontend-design",
                                        "required": True,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return SkillWorkflowControlPlane(
        skill_roots=[root],
        workflow_registry_path=registry,
        local_state_dir=tmp_path / "state" / "skills",
    )


def test_manager_exposes_skill_and_workflow_read_models(tmp_path: Path) -> None:
    control = _manager_control_plane(tmp_path)
    server = build_server("127.0.0.1", 0, skill_workflow=control)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/api/skills", headers={"Host": f"127.0.0.1:{port}"})
        response = conn.getresponse()
        skills = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert skills["skills"][0]["slug"] == "frontend-design"

        conn.request("GET", "/api/workflows", headers={"Host": f"127.0.0.1:{port}"})
        response = conn.getresponse()
        workflows = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert workflows["workflows"][0]["id"] == "demo"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_manager_skill_move_requires_confirmation_and_persists(tmp_path: Path) -> None:
    control = _manager_control_plane(tmp_path)
    server = build_server("127.0.0.1", 0, skill_workflow=control)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        headers = {
            "Host": f"127.0.0.1:{port}",
            "Content-Type": "application/json",
            "X-WebGPT-Control": "1",
        }
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request(
            "POST",
            "/api/skills",
            body=json.dumps(
                {
                    "operation": "move",
                    "id": "frontend-design",
                    "category": "favorites",
                    "confirm": False,
                }
            ),
            headers=headers,
        )
        response = conn.getresponse()
        response.read()
        assert response.status == 409

        conn.request(
            "POST",
            "/api/skills",
            body=json.dumps(
                {
                    "operation": "move",
                    "id": "frontend-design",
                    "category": "favorites",
                    "position": 1,
                    "confirm": True,
                }
            ),
            headers=headers,
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["move_kind"] == "logical-category"
        moved = control.skill_snapshot()["skills"][0]
        assert moved["category"] == "favorites"
        assert moved["position"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_manager_can_start_and_transition_workflow_run(tmp_path: Path) -> None:
    control = _manager_control_plane(tmp_path)
    server = build_server("127.0.0.1", 0, skill_workflow=control)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        headers = {
            "Host": f"127.0.0.1:{port}",
            "Content-Type": "application/json",
            "X-WebGPT-Control": "1",
        }
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request(
            "POST",
            "/api/workflow-runs",
            body=json.dumps(
                {
                    "operation": "start",
                    "workflow_id": "demo",
                    "context": {},
                    "confirm": True,
                }
            ),
            headers=headers,
        )
        response = conn.getresponse()
        run = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert run["current_stage"] == "design"

        conn.request(
            "POST",
            "/api/workflow-runs",
            body=json.dumps(
                {
                    "operation": "transition",
                    "run_id": run["run_id"],
                    "stage_id": "design",
                    "status": "passed",
                    "evidence": "validated",
                    "confirm": True,
                }
            ),
            headers=headers,
        )
        response = conn.getresponse()
        completed = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert completed["status"] == "complete"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
