import json
from pathlib import Path

import pytest

from webgpt_as_codex import doctor
from webgpt_as_codex.bootstrap import build_bootstrap_plan
from webgpt_as_codex.manager import build_server
from webgpt_as_codex.registry import Component
from webgpt_as_codex.repair import build_repair_plan, run_repair


def _component(**overrides) -> Component:
    raw = {
        "id": "sample",
        "display_name": "Sample",
        "role": "code_semantics",
        "required": True,
        "enabled_by_default": True,
        "transport": "streamable_http",
        "default_endpoint": "http://127.0.0.1:9999/mcp",
        "version_command": ["sample", "--version"],
        "safe_tool": "health",
        "install_hint": "install sample",
        "process_contains": ["sample"],
    }
    raw.update(overrides)
    return Component(
        id=raw["id"],
        display_name=raw["display_name"],
        role=raw["role"],
        required=raw["required"],
        enabled_by_default=raw["enabled_by_default"],
        transport=raw["transport"],
        default_endpoint=raw.get("default_endpoint"),
        raw=raw,
    )


def test_bootstrap_is_idempotent_and_preserves_healthy_service() -> None:
    component = _component()
    discovery = {
        "sample": {
            "installed_by_path": True,
            "listener_up": True,
        }
    }
    first = build_bootstrap_plan({"sample": component}, discovery)
    second = build_bootstrap_plan({"sample": component}, discovery)
    assert first == second
    assert first["items"][0]["action"] == "preserve"
    assert first["service_mutation"] is False


def test_health_truth_does_not_promote_listener_to_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    component = _component()
    monkeypatch.setattr(
        doctor,
        "discover_component",
        lambda _: {"listener_up": True},
    )
    monkeypatch.setattr(doctor, "_version_probe", lambda _: {"value": "1", "source": "test"})
    monkeypatch.setattr(doctor, "initialize", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    row = doctor._check_component(component, ["sample running"], None, {"attempted": False})
    assert row["health"]["process"] is True
    assert row["health"]["listener"] is True
    assert row["health"]["protocol"] is False
    assert row["health"]["safe_call"] is None


def test_summary_does_not_count_unattempted_deeper_checks_as_failures() -> None:
    component = _component()
    rows = {
        "sample": {
            "health": {
                "process": True,
                "listener": False,
                "protocol": None,
                "safe_call": None,
                "oauth": None,
                "remote": None,
            }
        }
    }
    status, summary = doctor._summarize(
        {"sample": component},
        rows,
        remote_expected=False,
    )
    assert status == "fail"
    assert summary["required_failures"] == ["sample:listener"]
    assert summary["warnings"] == []


def test_version_probe_does_not_treat_ip_like_banner_text_as_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component(verified_release="0.4.5")
    monkeypatch.setattr(
        doctor,
        "_resolved_version_command",
        lambda _: (["sample", "--version"], None),
    )
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *_args, **_kwargs: doctor.subprocess.CompletedProcess(
            args=["sample", "--version"],
            returncode=0,
            stdout="MCP service listening at 127.0.0.1\n",
            stderr="",
        ),
    )
    result = doctor._version_probe(component)
    assert result["value"] == "0.4.5"
    assert result["source"] == "manifest:verified_release"
    assert result["note"] == "unparseable-version-output"


def test_doctor_persistence_is_machine_local_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    component = _component(default_endpoint=None, transport="system", safe_tool=None)
    monkeypatch.setattr(doctor, "load_components", lambda: {"sample": component})
    monkeypatch.setattr(doctor, "_process_snapshot", lambda: ["sample running"])
    monkeypatch.setattr(
        doctor,
        "_version_probe",
        lambda _: {
            "value": "Bearer secret-value",
            "source": "test",
            "probe_ok": True,
            "note": None,
        },
    )
    result = doctor.run_doctor(include_remote=False, persist=True)
    path = tmp_path / "doctor" / "last-result.json"
    persisted = path.read_text(encoding="utf-8")
    assert result["components"]["sample"]["health"]["process"] is True
    assert "secret-value" not in persisted
    assert "[redacted]" in persisted


def test_repair_is_fixed_dry_run_confirmed_and_reversible(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    config = tmp_path / "config"
    config.mkdir(parents=True)
    (config / "manager.json").write_text("{broken", encoding="utf-8")
    plan = build_repair_plan()
    assert any(row["id"] == "reset-invalid-manager-config" for row in plan["actions"])
    assert plan["arbitrary_command_surface"] is False
    with pytest.raises(PermissionError):
        run_repair(dry_run=False, confirm=False)
    with pytest.raises(ValueError):
        run_repair(requested_actions=["shell:whoami"])
    result = run_repair(
        dry_run=False,
        confirm=True,
        requested_actions=["reset-invalid-manager-config"],
    )
    assert result["status"] == "applied"
    assert json.loads((config / "manager.json").read_text(encoding="utf-8")) == {}
    backups = list((tmp_path / "repair" / "backups").glob("manager.json.*.bak"))
    assert backups


def test_manager_preserves_stage7_owned_actions_after_later_stage_wiring() -> None:
    server = build_server("127.0.0.1", 0)
    try:
        actions = {row["name"]: row for row in server.action_runner.contracts()}
        assert actions["doctor"]["available"] is True
        assert actions["repair"]["available"] is True
        assert actions["update"]["available"] is False
    finally:
        server.server_close()
