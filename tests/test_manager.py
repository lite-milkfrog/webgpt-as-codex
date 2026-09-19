import json
import threading
import urllib.error
import urllib.request
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
    runner = ActionRunner({"repair": lambda _: {"ok": True, "token": "must-not-leak"}})
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
        url = f"http://127.0.0.1:{server.server_address[1]}/api/actions/doctor"
        request = urllib.request.Request(
            url,
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request, timeout=3)
        assert exc.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_manager_ui_has_bounded_polling_and_no_secret_copy_surface() -> None:
    html = (Path(__file__).resolve().parents[1] / "manager" / "static" / "index.html").read_text(encoding="utf-8")
    assert "poll_after_ms" in html
    assert "setInterval(" not in html
    assert "/api/password" not in html
    assert "OAuth password" not in html
