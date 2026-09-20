from __future__ import annotations

import os
import subprocess

import pytest

from webgpt_as_codex import edge_runtime, launcher, runtime


class _FakeResponse:
    status_code = 200

    def __init__(self, issuer: str) -> None:
        self._issuer = issuer

    def json(self) -> dict[str, str]:
        return {"issuer": self._issuer}


class _FakeProcess:
    pid = 111
    returncode = None

    def poll(self) -> None:
        return None


def test_auth_proxy_contract_requires_expected_public_issuer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        edge_runtime.requests,
        "get",
        lambda *_args, **_kwargs: _FakeResponse("https://node.example.ts.net:10003"),
    )
    monkeypatch.setattr(edge_runtime.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(edge_runtime, "_auth_listener_pid", lambda: 111)
    ticks = iter([0.0, 0.0, 1.0])
    monkeypatch.setattr(edge_runtime.time, "monotonic", lambda: next(ticks))
    with pytest.raises(RuntimeError, match="expected public issuer"):
        edge_runtime._wait_auth_proxy_contract(
            _FakeProcess(),  # type: ignore[arg-type]
            "https://node.example.ts.net",
            timeout=0.5,
        )


def test_auth_proxy_refuses_old_listener_even_when_issuer_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(edge_runtime, "_auth_listener_pid", lambda: 222)
    with pytest.raises(RuntimeError, match="different process generation"):
        edge_runtime._wait_auth_proxy_contract(
            _FakeProcess(),  # type: ignore[arg-type]
            "https://node.example.ts.net",
            timeout=0.5,
        )


def test_auth_edge_runtime_spec_has_generation_and_contract() -> None:
    spec = runtime.RUNTIME_SPECS["mcp-auth-proxy"]
    assert spec.generation_builder is not None
    assert spec.contract_probe is not None


def test_runtime_start_refreshes_stale_owned_auth_edge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supervisor = runtime.RuntimeSupervisor(
        {"mcp-auth-proxy": runtime.RUNTIME_SPECS["mcp-auth-proxy"]}
    )
    monkeypatch.setattr(
        supervisor,
        "status",
        lambda _component_id: {
            "listener_up": True,
            "owned": True,
            "pid": 111,
            "generation_current": False,
            "contract_ready": False,
        },
    )
    monkeypatch.setattr(
        supervisor,
        "stop",
        lambda _component_id: {"ok": True, "status": "stopped"},
    )
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: False)
    monkeypatch.setattr(runtime, "_spawn", lambda _spec: 222)
    monkeypatch.setattr(runtime, "_wait_ready", lambda _spec, _pid: True)
    monkeypatch.setattr(runtime, "_runtime_contract_ready", lambda _spec: True)
    monkeypatch.setattr(runtime, "_sync_listener_identity", lambda _spec, pid: pid)

    result = supervisor.start("mcp-auth-proxy")

    assert result["ok"] is True
    assert result["status"] == "refreshed-owned-stale"
    assert result["pid"] == 222


def test_desktop_launcher_has_visible_failure_and_d_drive_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        launcher,
        "_launcher_log_dir",
        lambda: launcher.Path("D:/AgentData/20_State/WebGPT-as-Codex/logs"),
    )
    content = launcher._launcher_content(open_browser=True)
    assert "pythonw.exe" not in content.lower()
    assert 'start "" /b' not in content.lower()
    assert str(launcher.Path("D:/AgentData/20_State/WebGPT-as-Codex/logs")) in content
    assert "if errorlevel 1 (" in content
    assert "pause" in content
    assert "--open --start-all" in content
    assert "pause" not in launcher._launcher_content(open_browser=False)


def test_current_installed_launcher_is_upgradeable_without_clobbering_other_files(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(tmp_path))
    existing = tmp_path / "WebGPT-as-Codex.cmd"
    existing.write_text(
        launcher._legacy_launcher_content(open_browser=True).replace(
            "setlocal\r\n", 'setlocal\r\nset "WEBGPT_CODEX_UI_LANG=zh-CN"\r\n'
        ),
        encoding="utf-8",
        newline="",
    )
    assert launcher.desktop_launcher("status")["upgradeable"] is True
    assert launcher.desktop_launcher("install")["status"] == "updated"
    assert launcher.desktop_launcher("status")["managed"] is True


def test_browser_launch_failure_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSupervisor:
        def start(self, _component_id: str) -> dict:
            return {"ok": True}

        def start_all(self, *, include_manager: bool = False) -> dict:
            return {"ok": True, "fully_ready": True}

    monkeypatch.setattr(launcher, "RuntimeSupervisor", FakeSupervisor)
    monkeypatch.setattr(launcher, "_open_manager_url", lambda _url: (False, "failed"))
    result = launcher.run_launcher(open_browser=True, start_all=True)
    assert result["ok"] is False
    assert result["browser_open_dispatched"] is False


@pytest.mark.skipif(os.name != "nt", reason="Windows desktop batch launcher")
def test_failed_desktop_batch_exposes_error_and_keeps_diagnostics(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(tmp_path))
    monkeypatch.setenv("WEBGPT_CODEX_LAUNCH_LOG_DIR", str(tmp_path / "diagnostics"))
    monkeypatch.setattr(launcher.sys, "executable", str(tmp_path / "missing-python.exe"))
    assert launcher.desktop_launcher("install")["ok"] is True
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(tmp_path / "WebGPT-as-Codex.cmd")],
        input="\n",
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 2
    assert "WebGPT launcher failed" in result.stdout
    assert (tmp_path / "diagnostics" / "desktop-launcher.log").is_file()


def test_start_all_does_not_false_green_on_raw_auth_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EdgeComponent:
        enabled_by_default = True
        default_endpoint = "http://127.0.0.1:9340"
        required = True

    monkeypatch.setattr(runtime, "load_components", lambda: {"mcp-auth-proxy": EdgeComponent()})
    monkeypatch.setattr(
        runtime, "discover_all", lambda _components: {"mcp-auth-proxy": {"listener_up": True}}
    )
    monkeypatch.setattr(runtime, "process_snapshot", list)
    monkeypatch.setattr(runtime, "process_health", lambda *_args: False)
    monkeypatch.setattr(
        "webgpt_as_codex.prerequisites.environment_report",
        lambda: {"ready_for_edge": True, "next_steps": []},
    )
    supervisor = runtime.RuntimeSupervisor()
    calls: list[str] = []
    monkeypatch.setattr(
        supervisor, "start",
        lambda component_id: calls.append(component_id)
        or {"ok": True, "component_id": component_id, "status": "started"},
    )
    result = supervisor.start_all()
    assert calls == ["mcp-auth-proxy"]
    assert result["fully_ready"] is True


def test_existing_auth_proxy_reuse_requires_current_issuer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        status_code = 200

        def __init__(self, issuer: str) -> None:
            self.issuer = issuer

        def json(self) -> dict[str, str]:
            return {"issuer": self.issuer}

    monkeypatch.setattr(edge_runtime, "_auth_listener_pid", lambda: 321)
    monkeypatch.setattr(runtime, "_webgpt_auth_listener_pid", lambda: 321)
    monkeypatch.setattr(
        edge_runtime.requests,
        "get",
        lambda *_args, **_kwargs: Response("https://node.example.ts.net/"),
    )
    assert edge_runtime._existing_auth_proxy_matches(
        "https://node.example.ts.net", 321
    )
    assert not edge_runtime._existing_auth_proxy_matches(
        "https://node.example.ts.net", 999
    )
    monkeypatch.setattr(
        edge_runtime.requests,
        "get",
        lambda *_args, **_kwargs: Response("https://old.example.ts.net/"),
    )
    assert not edge_runtime._existing_auth_proxy_matches(
        "https://node.example.ts.net", 321
    )
