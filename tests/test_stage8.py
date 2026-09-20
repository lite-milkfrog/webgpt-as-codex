import json
import os
from pathlib import Path

import pytest

from webgpt_as_codex import launcher, runtime
from webgpt_as_codex.manager import build_server
from webgpt_as_codex.registry import Component
from webgpt_as_codex.runtime import RuntimeSpec, RuntimeSupervisor


def _spec(component_id: str = "sample") -> RuntimeSpec:
    return RuntimeSpec(
        component_id,
        component_id.title(),
        "http://127.0.0.1:9999/mcp",
        "http://127.0.0.1:9999/health",
        lambda: ["sample-runtime"],
        lambda: Path.cwd(),
    )


def _component(component_id: str, *, required: bool = True) -> Component:
    raw = {
        "id": component_id,
        "display_name": component_id.title(),
        "role": "test",
        "required": required,
        "enabled_by_default": True,
        "transport": "streamable_http",
        "default_endpoint": "http://127.0.0.1:9999/mcp",
    }
    return Component(
        id=component_id,
        display_name=raw["display_name"],
        role="test",
        required=required,
        enabled_by_default=True,
        transport="streamable_http",
        default_endpoint=raw["default_endpoint"],
        raw=raw,
    )


def _owned_record(tmp_path: Path, component_id: str = "sample") -> Path:
    pids = tmp_path / "pids"
    pids.mkdir(parents=True, exist_ok=True)
    path = pids / f"{component_id}.json"
    path.write_text(
        json.dumps(
            {
                "component_id": component_id,
                "pid": 321,
                "birth_token": "birth-1",
                "image_name": "sample.exe",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_start_preserves_healthy_unmanaged_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    supervisor = RuntimeSupervisor({"sample": _spec()})
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: True)
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    monkeypatch.setattr(
        runtime,
        "_spawn",
        lambda _spec: (_ for _ in ()).throw(AssertionError("must not spawn duplicate")),
    )
    result = supervisor.start("sample")
    assert result["ok"] is True
    assert result["status"] == "preserved-unmanaged"


def test_stale_pid_reuse_is_removed_without_kill(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    pid_path = _owned_record(tmp_path)
    monkeypatch.setattr(runtime, "_pid_exists", lambda _pid: True)
    monkeypatch.setattr(runtime, "_process_birth_token", lambda _pid: "birth-2")
    monkeypatch.setattr(runtime, "_process_image_name", lambda _pid: "sample.exe")
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: False)
    status = RuntimeSupervisor({"sample": _spec()}).status("sample")
    assert status["owned"] is False
    assert status["state"] == "stopped"
    assert status["ownership_evidence"] == "stale-pid-reused"
    assert not pid_path.exists()


def test_owned_unhealthy_process_prevents_duplicate_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    _owned_record(tmp_path)
    monkeypatch.setattr(runtime, "_pid_exists", lambda _pid: True)
    monkeypatch.setattr(runtime, "_process_birth_token", lambda _pid: "birth-1")
    monkeypatch.setattr(runtime, "_process_image_name", lambda _pid: "sample.exe")
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: False)
    monkeypatch.setattr(
        runtime,
        "_spawn",
        lambda _spec: (_ for _ in ()).throw(AssertionError("must not duplicate")),
    )
    result = RuntimeSupervisor({"sample": _spec()}).start("sample")
    assert result["ok"] is False
    assert result["status"] == "owned-process-unhealthy"
    assert result["pid"] == 321


def test_owned_stop_uses_bounded_shutdown_and_removes_pid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    pid_path = _owned_record(tmp_path)
    monkeypatch.setattr(runtime, "_pid_exists", lambda _pid: True)
    monkeypatch.setattr(runtime, "_process_birth_token", lambda _pid: "birth-1")
    monkeypatch.setattr(runtime, "_process_image_name", lambda _pid: "sample.exe")
    monkeypatch.setattr(runtime, "_bounded_stop", lambda _pid: "graceful")
    result = RuntimeSupervisor({"sample": _spec()}).stop("sample")
    assert result["ok"] is True
    assert result["shutdown"] == "graceful"
    assert not pid_path.exists()


def test_restart_refuses_healthy_unmanaged_process(monkeypatch: pytest.MonkeyPatch) -> None:
    supervisor = RuntimeSupervisor({"sample": _spec()})
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: True)
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    result = supervisor.restart("sample")
    assert result["ok"] is False
    assert result["status"] == "healthy-but-unmanaged"


def test_start_all_discovers_first_preserves_external_and_starts_only_managed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    components = {
        "external": _component("external"),
        "mcpjungle": _component("mcpjungle"),
    }
    monkeypatch.setattr(runtime, "load_components", lambda: components)
    monkeypatch.setattr(runtime, "process_snapshot", list)
    monkeypatch.setattr(runtime, "process_health", lambda _component, _snapshot: False)
    monkeypatch.setattr(
        runtime,
        "discover_all",
        lambda _components: {
            "external": {"listener_up": True},
            "mcpjungle": {"listener_up": False},
        },
    )
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    supervisor = RuntimeSupervisor({"mcpjungle": _spec("mcpjungle")})
    starts: list[str] = []

    def fake_start(component_id: str) -> dict:
        starts.append(component_id)
        return {"ok": True, "component_id": component_id, "status": "started"}

    monkeypatch.setattr(supervisor, "start", fake_start)
    result = supervisor.start_all()
    by_id = {row["component_id"]: row for row in result["results"]}
    assert starts == ["mcpjungle"]
    assert by_id["external"]["status"] == "preserved-unmanaged"
    assert by_id["mcpjungle"]["status"] == "started"
    assert result["arbitrary_command_surface"] is False
    assert result["fully_ready"] is True
    assert result["required_unmanaged_missing"] == []


def test_start_all_preserves_process_only_system_component(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    system = _component("tailscale")
    system = Component(
        id=system.id,
        display_name=system.display_name,
        role=system.role,
        required=True,
        enabled_by_default=True,
        transport="system",
        default_endpoint=None,
        raw={**system.raw, "default_endpoint": None, "process_contains": ["tailscaled"]},
    )
    monkeypatch.setattr(runtime, "load_components", lambda: {"tailscale": system})
    monkeypatch.setattr(
        runtime,
        "discover_all",
        lambda _components: {"tailscale": {"listener_up": None}},
    )
    monkeypatch.setattr(runtime, "process_snapshot", lambda: ["tailscaled.exe"])
    monkeypatch.setattr(runtime, "process_health", lambda _component, _snapshot: True)
    result = RuntimeSupervisor({}).start_all()
    row = result["results"][0]
    assert row["status"] == "preserved-unmanaged"
    assert row["evidence"] == "process"
    assert result["fully_ready"] is True


def test_manager_preserves_stage8_start_restart_after_stage11_update_wiring() -> None:
    server = build_server("127.0.0.1", 0)
    try:
        actions = {row["name"]: row for row in server.action_runner.contracts()}
        assert actions["start_all"]["available"] is True
        assert actions["restart"]["available"] is True
        assert actions["doctor"]["available"] is True
        assert actions["repair"]["available"] is True
        assert actions["update"]["available"] is True
        assert actions["update"]["owner_stage"] == "STAGE-11-SECURITY-RELIABILITY-HARDENING"
    finally:
        server.server_close()


def test_manager_restart_requires_fixed_component_scope() -> None:
    result = runtime.manager_restart_executor(object(), {"component": "serena"})
    assert result["ok"] is False
    assert result["status"] == "invalid-component-scope"
    assert result["allowed_components"] == ["mcp-auth-proxy", "mcpjungle"]


def test_desktop_launcher_and_autostart_are_reversible_and_credential_free(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    desktop = tmp_path / "Desktop"
    startup = tmp_path / "Startup"
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(desktop))
    monkeypatch.setenv("WEBGPT_CODEX_STARTUP_DIR", str(startup))

    installed = launcher.desktop_launcher("install")
    auto = launcher.autostart("install")
    assert installed["ok"] is True and installed["managed"] is True
    assert auto["ok"] is True and auto["managed"] is True

    text = (desktop / "WebGPT-as-Codex.cmd").read_text(encoding="utf-8").lower()
    auto_text = (startup / "WebGPT-as-Codex-Autostart.cmd").read_text(encoding="utf-8").lower()
    for forbidden in ("password=", "token=", "secret=", "bearer "):
        assert forbidden not in text
        assert forbidden not in auto_text
    assert "local-launcher-overlay.cmd" in text
    assert "local-launcher-overlay.cmd" not in auto_text

    assert launcher.desktop_launcher("uninstall")["status"] == "uninstalled"
    assert launcher.autostart("uninstall")["status"] == "uninstalled"
    assert not (desktop / "WebGPT-as-Codex.cmd").exists()
    assert not (startup / "WebGPT-as-Codex-Autostart.cmd").exists()


def test_launcher_refuses_to_overwrite_unmanaged_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    target = desktop / "WebGPT-as-Codex.cmd"
    target.write_text("@echo off\necho user-owned\n", encoding="utf-8")
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(desktop))
    result = launcher.desktop_launcher("install")
    assert result["ok"] is False
    assert result["status"] == "existing-unmanaged-file"
    assert "user-owned" in target.read_text(encoding="utf-8")


def test_shell_value_expands_userprofile_when_service_env_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setattr(launcher, "user_home", lambda: Path("C:/Users/TestUser"))
    path = launcher._expand_shell_value(r"%USERPROFILE%\Desktop")
    assert path == Path("C:/Users/TestUser/Desktop")
    assert "%" not in str(path)


def test_launcher_exits_without_owning_runtime_lifetime(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSupervisor:
        def start(self, component_id: str) -> dict:
            assert component_id == "manager"
            return {"ok": True, "status": "started"}

        def start_all(self, *, include_manager: bool = False) -> dict:
            assert include_manager is False
            return {"ok": True, "status": "complete", "fully_ready": True}

    monkeypatch.setattr(launcher, "RuntimeSupervisor", FakeSupervisor)
    monkeypatch.setattr(launcher.webbrowser, "open", lambda _url: True)
    result = launcher.run_launcher(open_browser=True, start_all=True)
    assert result["ok"] is True
    assert result["browser_open_dispatched"] is True
    assert result["runtime_lifetime_independent_of_browser"] is True



def test_explicit_open_reopens_browser_for_existing_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSupervisor:
        def start(self, component_id: str) -> dict:
            assert component_id == "manager"
            return {"ok": True, "status": "preserved-owned"}

        def start_all(self, *, include_manager: bool = False) -> dict:
            assert include_manager is False
            return {"ok": True, "status": "complete", "fully_ready": True}

    opened: list[str] = []
    monkeypatch.setattr(launcher, "RuntimeSupervisor", FakeSupervisor)
    monkeypatch.setattr(
        launcher,
        "_open_manager_url",
        lambda url: (opened.append(url) or True, "unexpected"),
    )
    result = launcher.run_launcher(open_browser=True, start_all=True)
    assert result["ok"] is True
    assert result["browser_open_requested"] is True
    assert result["browser_open_dispatched"] is True
    assert result["browser_open_mode"] == "unexpected"
    assert opened == ["http://127.0.0.1:9200/"]

@pytest.mark.skipif(os.name != "nt", reason="Windows PID identity contract")
def test_windows_process_identity_probe() -> None:
    assert runtime._process_birth_token(os.getpid()).startswith("win-filetime:")
    assert runtime._process_image_name(os.getpid())
