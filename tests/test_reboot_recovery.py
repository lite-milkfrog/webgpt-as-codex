from __future__ import annotations

from pathlib import Path

import pytest

from webgpt_as_codex import doctor, launcher, runtime
from webgpt_as_codex.registry import Component


def _component(component_id: str, *, role: str = "test") -> Component:
    raw = {
        "id": component_id,
        "display_name": component_id.title(),
        "role": role,
        "required": True,
        "enabled_by_default": True,
        "transport": "streamable_http",
        "default_endpoint": "http://127.0.0.1:9999/mcp",
    }
    return Component(
        id=component_id,
        display_name=raw["display_name"],
        role=role,
        required=True,
        enabled_by_default=True,
        transport="streamable_http",
        default_endpoint=raw["default_endpoint"],
        raw=raw,
    )


def _not_ready_report() -> dict:
    return {
        "ready_for_edge": False,
        "next_steps": [{"id": "tailscale", "action": "tailscale-up-and-login", "blocking": True}],
    }


def _ready_report() -> dict:
    return {"ready_for_edge": True, "next_steps": []}


def test_start_all_waits_for_edge_prerequisites_until_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    reports = [_not_ready_report(), _ready_report()]

    def fake_report() -> dict:
        return reports.pop(0) if reports else _ready_report()

    monkeypatch.setattr(
        "webgpt_as_codex.prerequisites.environment_report", fake_report
    )
    components = {
        "mcpjungle": _component("mcpjungle", role="gateway"),
        "mcp-auth-proxy": _component("mcp-auth-proxy", role="oauth_edge"),
    }
    monkeypatch.setattr(runtime, "load_components", lambda: components)
    monkeypatch.setattr(
        runtime,
        "discover_all",
        lambda _components: {
            "mcpjungle": {"listener_up": True},
            "mcp-auth-proxy": {"listener_up": False},
        },
    )
    monkeypatch.setattr(runtime, "process_snapshot", list)
    monkeypatch.setattr(runtime, "process_health", lambda *_args: False)
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    supervisor = runtime.RuntimeSupervisor()
    starts: list[str] = []
    monkeypatch.setattr(
        supervisor,
        "start",
        lambda component_id: (
            starts.append(component_id)
            or {"ok": True, "component_id": component_id, "status": "started"}
        ),
    )

    result = supervisor.start_all(edge_prereq_wait=1.0)
    by_id = {row["component_id"]: row for row in result["results"]}

    assert starts == ["mcp-auth-proxy"]
    assert by_id["mcp-auth-proxy"]["status"] == "started"
    assert result["fully_ready"] is False or result["ok"] is True


def test_start_all_edge_wait_timeout_keeps_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "webgpt_as_codex.prerequisites.environment_report", _not_ready_report
    )
    components = {"mcp-auth-proxy": _component("mcp-auth-proxy", role="oauth_edge")}
    monkeypatch.setattr(runtime, "load_components", lambda: components)
    monkeypatch.setattr(
        runtime, "discover_all", lambda _components: {"mcp-auth-proxy": {"listener_up": False}}
    )
    monkeypatch.setattr(runtime, "process_snapshot", list)
    monkeypatch.setattr(runtime, "process_health", lambda *_args: False)
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    supervisor = runtime.RuntimeSupervisor()

    def must_not_start(component_id: str) -> dict:
        raise AssertionError(f"must not start {component_id}")

    monkeypatch.setattr(supervisor, "start", must_not_start)

    result = supervisor.start_all(edge_prereq_wait=0.1)
    by_id = {row["component_id"]: row for row in result["results"]}

    assert result["ok"] is False
    assert result["status"] == "managed-runtime-failure"
    edge_row = by_id["mcp-auth-proxy"]
    assert edge_row["status"] == "prerequisites-not-ready"
    assert edge_row["ok"] is False
    assert edge_row["prerequisite_wait_seconds"] == 0.1
    assert edge_row["next_steps"][0]["action"] == "tailscale-up-and-login"


def test_start_all_zero_wait_fails_fast_with_single_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    calls = {"count": 0}

    def fake_report() -> dict:
        calls["count"] += 1
        return _not_ready_report()

    monkeypatch.setattr(
        "webgpt_as_codex.prerequisites.environment_report", fake_report
    )
    components = {"mcp-auth-proxy": _component("mcp-auth-proxy", role="oauth_edge")}
    monkeypatch.setattr(runtime, "load_components", lambda: components)
    monkeypatch.setattr(
        runtime, "discover_all", lambda _components: {"mcp-auth-proxy": {"listener_up": False}}
    )
    monkeypatch.setattr(runtime, "process_snapshot", list)
    monkeypatch.setattr(runtime, "process_health", lambda *_args: False)
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    supervisor = runtime.RuntimeSupervisor()

    result = supervisor.start_all(edge_prereq_wait=0.0)
    edge_row = next(
        row for row in result["results"] if row["component_id"] == "mcp-auth-proxy"
    )

    assert calls["count"] == 1
    assert edge_row["status"] == "prerequisites-not-ready"
    assert edge_row["prerequisite_wait_seconds"] == 0.0


def test_start_all_is_idempotent_for_healthy_managed_components(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "webgpt_as_codex.prerequisites.environment_report", _ready_report
    )
    supervisor = runtime.RuntimeSupervisor(
        {
            "mcpjungle": runtime.RUNTIME_SPECS["mcpjungle"],
            "mcp-auth-proxy": runtime.RUNTIME_SPECS["mcp-auth-proxy"],
        }
    )
    healthy = {
        "mcpjungle": {
            "listener_up": True,
            "owned": True,
            "pid": 101,
            "generation_current": None,
            "contract_ready": None,
        },
        "mcp-auth-proxy": {
            "listener_up": True,
            "owned": True,
            "pid": 102,
            "generation_current": True,
            "contract_ready": True,
        },
    }
    monkeypatch.setattr(supervisor, "status", lambda component_id: healthy[component_id])
    monkeypatch.setattr(
        runtime, "_owned_pid", lambda _component: (101, "owned")
    )

    def must_not_spawn(_spec: runtime.RuntimeSpec) -> int:
        raise AssertionError("healthy component must be reused, not respawned")

    monkeypatch.setattr(runtime, "_spawn", must_not_spawn)
    monkeypatch.setattr(
        runtime, "_listener_up", lambda _endpoint: True
    )

    for _ in range(2):
        result = supervisor.start_all(edge_prereq_wait=0.0)
        assert result["ok"] is True
        by_id = {row["component_id"]: row for row in result["results"]}
        assert by_id["mcpjungle"]["status"] == "preserved-owned"
        assert by_id["mcp-auth-proxy"]["status"] == "preserved-owned"


def test_wait_for_edge_prerequisites_polls_with_bounded_interval() -> None:
    environment = _not_ready_report()
    sleeps: list[float] = []
    clock = iter([0.0, 0.0, 1.0, 2.0])
    reports = [_not_ready_report(), _ready_report()]

    def fake_report() -> dict:
        return reports.pop(0) if reports else _ready_report()

    from webgpt_as_codex import prerequisites

    original = prerequisites.environment_report
    prerequisites.environment_report = fake_report  # type: ignore[assignment]
    try:
        result, waited = runtime._wait_for_edge_prerequisites(
            environment,
            timeout=10.0,
            interval=1.0,
            sleep=sleeps.append,
            monotonic=lambda: next(clock),
        )
    finally:
        prerequisites.environment_report = original  # type: ignore[assignment]

    assert result["ready_for_edge"] is True
    assert waited == 2.0
    assert sleeps == [1.0, 1.0]


def test_wait_for_edge_prerequisites_times_out_fail_closed() -> None:
    environment = _not_ready_report()
    sleeps: list[float] = []
    clock = iter([0.0, 0.0, 1.0, 1.0])

    from webgpt_as_codex import prerequisites

    original = prerequisites.environment_report
    prerequisites.environment_report = _not_ready_report  # type: ignore[assignment]
    try:
        result, waited = runtime._wait_for_edge_prerequisites(
            environment,
            timeout=1.0,
            interval=5.0,
            sleep=sleeps.append,
            monotonic=lambda: next(clock),
        )
    finally:
        prerequisites.environment_report = original  # type: ignore[assignment]

    assert result["ready_for_edge"] is False
    assert waited == 1.0
    assert sleeps == [1.0]


def test_desktop_launcher_content_reports_ready_and_failure_paths() -> None:
    monkeypatch_path = launcher.Path("D:/AgentData/20_State/WebGPT-as-Codex/logs")
    original = launcher._launcher_log_dir
    launcher._launcher_log_dir = lambda: monkeypatch_path  # type: ignore[assignment]
    try:
        desktop = launcher._launcher_content(open_browser=True)
        autostart = launcher._launcher_content(open_browser=False)
    finally:
        launcher._launcher_log_dir = original  # type: ignore[assignment]

    assert "WebGPT-as-Codex is READY" in desktop
    assert "waiting for the network/Tailscale" in desktop
    assert "if errorlevel 1 (" in desktop
    assert "WebGPT launcher failed" in desktop
    assert "pause" in desktop
    assert "--open --start-all" in desktop
    assert "pythonw.exe" not in desktop.lower()
    assert 'start "" /b' not in desktop.lower()
    assert "pause" not in autostart
    assert "READY" not in autostart
    assert "--no-open --start-all" in autostart
    assert "local-prestart.cmd" in desktop
    assert "local-prestart.cmd" in autostart
    assert "Python runtime not found" in desktop
    assert "Remote Desktop Commander" not in autostart
    assert desktop.index("Python runtime not found") < desktop.index("local-prestart.cmd")
    assert desktop.index("local-prestart.cmd") < desktop.index("--open --start-all")
    assert desktop.index("WebGPT-as-Codex is READY") < desktop.index(
        "Remote Desktop Commander start requested successfully."
    )


def test_launcher_waits_for_unmanaged_backends_during_boot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSupervisor:
        calls = 0

        def start_all(self, **_kwargs: object) -> dict:
            self.calls += 1
            if self.calls == 1:
                return {
                    "ok": True,
                    "fully_ready": False,
                    "required_unmanaged_missing": ["coding-tools", "playwright"],
                }
            return {
                "ok": True,
                "fully_ready": True,
                "required_unmanaged_missing": [],
            }

    supervisor = FakeSupervisor()
    monkeypatch.setenv("WEBGPT_CODEX_EXTERNAL_BACKEND_WAIT_SECONDS", "5")
    ticks = iter([0.0, 0.1, 0.2])
    monkeypatch.setattr(launcher.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(launcher.time, "sleep", lambda _seconds: None)

    result = launcher._start_all_until_ready(supervisor)  # type: ignore[arg-type]

    assert result["fully_ready"] is True
    assert result["launcher_backend_wait_attempts"] == 2
    assert supervisor.calls == 2


def test_installed_redirect_generation_launcher_is_upgradeable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(tmp_path))
    monkeypatch.setenv("WEBGPT_CODEX_LAUNCH_LOG_DIR", str(tmp_path / "logs"))
    old_generation = (
        "@echo off\r\n"
        f"{launcher._MARKER}\r\n"
        "setlocal\r\n"
        'set "WEBGPT_CODEX_UI_LANG=zh-CN"\r\n'
        f'if not exist "{tmp_path / "logs"}" mkdir "{tmp_path / "logs"}"\r\n'
        f'"{launcher.Path(launcher.sys.executable)}" -m webgpt_as_codex launcher '
        f'--open --start-all > "{tmp_path / "logs" / "desktop-launcher.log"}" 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        "  echo WebGPT launcher failed. Diagnostic output:\r\n"
        f'  type "{tmp_path / "logs" / "desktop-launcher.log"}"\r\n'
        f'  echo Full log: {tmp_path / "logs" / "desktop-launcher.log"}\r\n'
        "  pause\r\n"
        "  exit /b 2\r\n"
        " )\r\n"
        "endlocal\r\n"
    )
    target = tmp_path / "WebGPT-as-Codex.cmd"
    target.write_text(old_generation, encoding="utf-8", newline="")

    status = launcher.desktop_launcher("status")
    assert status["installed"] is True
    assert status["managed"] is False
    assert status["upgradeable"] is True

    install = launcher.desktop_launcher("install")
    assert install["ok"] is True
    assert install["status"] == "updated"
    assert "WebGPT-as-Codex is READY" in target.read_text(encoding="utf-8")


def test_installed_visible_ready_generation_launcher_is_upgradeable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(tmp_path))
    monkeypatch.setenv("WEBGPT_CODEX_LAUNCH_LOG_DIR", str(tmp_path / "logs"))
    old_generation = (
        "@echo off\r\n"
        f"{launcher._MARKER}\r\n"
        "setlocal\r\n"
        'set "WEBGPT_CODEX_UI_LANG=zh-CN"\r\n'
        "echo WebGPT-as-Codex: detecting environment and waiting for real readiness...\r\n"
        "echo (After a reboot, waiting for the network/Tailscale can take up to 3 minutes.)\r\n"
        f'if not exist "{tmp_path / "logs"}" mkdir "{tmp_path / "logs"}"\r\n'
        f'"{launcher.Path(launcher.sys.executable)}" -m webgpt_as_codex launcher '
        f'--open --start-all > "{tmp_path / "logs" / "desktop-launcher.log"}" 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        "  echo WebGPT launcher failed. Diagnostic output:\r\n"
        f'  type "{tmp_path / "logs" / "desktop-launcher.log"}"\r\n'
        f'  echo Full log: {tmp_path / "logs" / "desktop-launcher.log"}\r\n'
        "  pause\r\n"
        "  exit /b 2\r\n"
        " )\r\n"
        "echo WebGPT-as-Codex is READY. Manager: http://127.0.0.1:9200/\r\n"
        "endlocal\r\n"
    )
    target = tmp_path / "WebGPT-as-Codex.cmd"
    target.write_text(old_generation, encoding="utf-8", newline="")

    status = launcher.desktop_launcher("status")
    assert status["installed"] is True
    assert status["managed"] is False
    assert status["upgradeable"] is True

    install = launcher.desktop_launcher("install")
    assert install["ok"] is True
    assert install["status"] == "updated"
    updated = target.read_text(encoding="utf-8")
    assert "Remote Desktop Commander start requested successfully." in updated


def test_installed_isolated_rdc_suffix_launcher_is_upgradeable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(tmp_path))
    monkeypatch.setenv("WEBGPT_CODEX_LAUNCH_LOG_DIR", str(tmp_path / "logs"))
    rdc_root = "C:\\Users\\Example\\AppData\\Local\\DesktopCommander"
    old_generation = (
        "@echo off\r\n"
        f"{launcher._MARKER}\r\n"
        "setlocal\r\n"
        'set "WEBGPT_CODEX_UI_LANG=zh-CN"\r\n'
        "echo WebGPT-as-Codex: detecting environment and waiting for real readiness...\r\n"
        "echo (After a reboot, waiting for the network/Tailscale can take up to 3 minutes.)\r\n"
        f'if not exist "{tmp_path / "logs"}" mkdir "{tmp_path / "logs"}"\r\n'
        f'"{launcher.Path(launcher.sys.executable)}" -m webgpt_as_codex launcher '
        f'--open --start-all > "{tmp_path / "logs" / "desktop-launcher.log"}" 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        "  echo WebGPT launcher failed. Diagnostic output:\r\n"
        f'  type "{tmp_path / "logs" / "desktop-launcher.log"}"\r\n'
        f'  echo Full log: {tmp_path / "logs" / "desktop-launcher.log"}\r\n'
        "  pause\r\n"
        "  exit /b 2\r\n"
        " )\r\n"
        "echo WebGPT-as-Codex is READY. Manager: http://127.0.0.1:9200/\r\n"
        "REM Remote Desktop Commander is isolated from the WebGPT-as-Codex startup path.\r\n"
        "REM A failure here must never turn a healthy WebGPT-as-Codex launch into a failure.\r\n"
        f'powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{rdc_root}\\start-remote.ps1"\r\n'
        "if errorlevel 1 (\r\n"
        "  echo Remote Desktop Commander start failed. WebGPT-as-Codex remains READY.\r\n"
        f"  echo RDC log: {rdc_root}\\remote-agent.log\r\n"
        ") else (\r\n"
        "  echo Remote Desktop Commander start requested successfully.\r\n"
        ")\r\n"
        "endlocal"
    )
    target = tmp_path / "WebGPT-as-Codex.cmd"
    target.write_text(old_generation, encoding="utf-8", newline="")

    status = launcher.desktop_launcher("status")
    assert status["installed"] is True
    assert status["managed"] is False
    assert status["upgradeable"] is True

    install = launcher.desktop_launcher("install")
    assert install["ok"] is True
    assert install["status"] == "updated"
    updated = target.read_text(encoding="utf-8")
    assert "WebGPT-as-Codex is READY" in updated
    assert "Remote Desktop Commander start requested successfully." in updated
    assert "%LOCALAPPDATA%\\DesktopCommander\\start-remote.ps1" in updated


def test_doctor_includes_edge_prerequisites_when_edge_listener_down(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    edge = _component("mcp-auth-proxy", role="oauth_edge")
    monkeypatch.setattr(doctor, "load_components", lambda: {"mcp-auth-proxy": edge})
    monkeypatch.setattr(doctor, "_process_snapshot", list)
    monkeypatch.setattr(
        doctor, "discover_component", lambda _component: {"listener_up": False}
    )
    monkeypatch.setattr(
        "webgpt_as_codex.prerequisites.environment_report",
        lambda: {
            "ready_for_edge": False,
            "tailscale": {
                "installed": True,
                "backend_state": "Running",
                "online": False,
                "dns_name": None,
                "funnel_cli_ok": True,
                "next_action": "login",
            },
            "next_steps": [
                {"id": "tailscale", "action": "tailscale-up-and-login", "blocking": True}
            ],
        },
    )

    result = doctor.run_doctor(include_remote=False, persist=False)
    context = result["checks"]["edge_prerequisites"]

    assert context["ready_for_edge"] is False
    assert context["tailscale"]["online"] is False
    assert context["tailscale"]["next_action"] == "login"
    assert context["next_steps"][0]["action"] == "tailscale-up-and-login"
