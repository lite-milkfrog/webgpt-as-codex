from __future__ import annotations

from pathlib import Path

import pytest

from webgpt_as_codex import launcher, runtime
from webgpt_as_codex.runtime import RuntimeSpec, RuntimeSupervisor


def _manager_spec(*, generation: str = "current", contract: bool = True) -> RuntimeSpec:
    return RuntimeSpec(
        "manager",
        "Manager",
        "http://127.0.0.1:9200",
        "http://127.0.0.1:9200/healthz",
        lambda: ["python", "-m", "webgpt_as_codex", "manager"],
        Path.cwd,
        lambda: generation,
        lambda: contract,
    )


def test_current_owned_manager_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _manager_spec()
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (321, "owned"))
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: True)
    monkeypatch.setattr(
        runtime,
        "_load_pid_record",
        lambda _component: {"runtime_generation": "current"},
    )
    monkeypatch.setattr(
        runtime,
        "_bounded_stop",
        lambda _pid: (_ for _ in ()).throw(AssertionError("must not stop current manager")),
    )
    result = RuntimeSupervisor({"manager": spec}).start("manager")
    assert result["ok"] is True
    assert result["status"] == "preserved-owned"
    assert result["pid"] == 321


def test_stale_owned_manager_is_refreshed(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _manager_spec()
    listener = {"up": True}
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (321, "owned"))
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: listener["up"])
    monkeypatch.setattr(
        runtime,
        "_load_pid_record",
        lambda _component: {"runtime_generation": "old"},
    )

    stopped: list[int] = []

    def fake_stop(pid: int, graceful_seconds: float = 5.0) -> str:
        del graceful_seconds
        stopped.append(pid)
        listener["up"] = False
        return "graceful"

    monkeypatch.setattr(runtime, "_bounded_stop", fake_stop)
    monkeypatch.setattr(runtime, "_remove_pid_record", lambda _component: None)
    monkeypatch.setattr(runtime, "_spawn", lambda _spec: 654)
    monkeypatch.setattr(runtime, "_wait_ready", lambda _spec, _pid: True)

    result = RuntimeSupervisor({"manager": spec}).start("manager")
    assert result["ok"] is True
    assert result["status"] == "refreshed-owned-stale"
    assert result["pid"] == 654
    assert stopped == [321]


def test_stale_legacy_webgpt_manager_is_refreshed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = iter((False, True))
    spec = RuntimeSpec(
        "manager",
        "Manager",
        "http://127.0.0.1:9200",
        "http://127.0.0.1:9200/healthz",
        lambda: ["python", "-m", "webgpt_as_codex", "manager"],
        Path.cwd,
        lambda: "current",
        lambda: next(contract),
    )
    listener = {"up": True}
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: listener["up"])
    monkeypatch.setattr(runtime, "_listener_pid", lambda _endpoint: 321)
    monkeypatch.setattr(runtime, "_process_image_name", lambda _pid: "python.exe")
    monkeypatch.setattr(
        runtime,
        "_process_command_line",
        lambda _pid: (
            '"C:\\Python\\python.exe" -m webgpt_as_codex manager '
            "--host 127.0.0.1 --port 9200"
        ),
    )

    def fake_stop(_pid: int, graceful_seconds: float = 5.0) -> str:
        del graceful_seconds
        listener["up"] = False
        return "graceful"

    monkeypatch.setattr(runtime, "_bounded_stop", fake_stop)
    monkeypatch.setattr(runtime, "_spawn", lambda _spec: 654)
    monkeypatch.setattr(runtime, "_wait_ready", lambda _spec, _pid: True)

    result = RuntimeSupervisor({"manager": spec}).start("manager")
    assert result["ok"] is True
    assert result["status"] == "refreshed-legacy-stale"
    assert result["legacy_pid"] == 321
    assert result["pid"] == 654


def test_ambiguous_unmanaged_9200_listener_is_never_killed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _manager_spec(contract=False)
    monkeypatch.setattr(runtime, "_owned_pid", lambda _component: (None, "none"))
    monkeypatch.setattr(runtime, "_listener_up", lambda _endpoint: True)
    monkeypatch.setattr(runtime, "_legacy_manager_listener_pid", lambda _spec: None)
    monkeypatch.setattr(
        runtime,
        "_bounded_stop",
        lambda _pid: (_ for _ in ()).throw(AssertionError("must not kill unknown listener")),
    )
    result = RuntimeSupervisor({"manager": spec}).start("manager")
    assert result["ok"] is False
    assert result["status"] == "stale-or-unknown-unmanaged-listener"


def test_manager_receipt_rebinds_to_real_listener_pid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    pids = tmp_path / "pids"
    pids.mkdir(parents=True)
    (pids / "manager.json").write_text(
        """{
  "schema": 1,
  "component_id": "manager",
  "pid": 111,
  "birth_token": "launch-birth",
  "image_name": "pythonw.exe",
  "log_file": "logs/runtime/manager.log"
}""",
        encoding="utf-8",
    )
    spec = _manager_spec()
    monkeypatch.setattr(runtime, "_listener_pid", lambda _endpoint: 222)
    monkeypatch.setattr(runtime, "_manager_process_identity", lambda _pid: True)
    monkeypatch.setattr(
        runtime,
        "_process_birth_token",
        lambda pid: "listener-birth" if pid == 222 else "launch-birth",
    )
    monkeypatch.setattr(runtime, "_process_image_name", lambda _pid: "python.exe")
    assert runtime._sync_listener_identity(spec, 111) == 222
    receipt = runtime._load_pid_record("manager")
    assert receipt is not None
    assert receipt["pid"] == 222
    assert receipt["birth_token"] == "listener-birth"
    assert receipt["launcher_pid"] == 111
    assert receipt["launcher_birth_token"] == "launch-birth"


def test_browser_opener_reuses_existing_edge_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edge = Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe")
    calls: list[tuple[Path, str, str]] = []
    monkeypatch.setattr(launcher, "_edge_reuse_target", lambda: (edge, "Default"))
    monkeypatch.setattr(
        launcher,
        "_launch_edge_profile",
        lambda exe, profile, url: calls.append((exe, profile, url)) or True,
    )
    monkeypatch.setattr(
        launcher.webbrowser,
        "open",
        lambda _url: (_ for _ in ()).throw(AssertionError("fallback must not run")),
    )
    opened, mode = launcher._open_manager_url("http://127.0.0.1:9200/")
    assert opened is True
    assert mode == "existing-edge-profile"
    assert calls == [(edge, "Default", "http://127.0.0.1:9200/")]


def test_browser_opener_windows_fallback_uses_default_url_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    monkeypatch.setattr(launcher, "_edge_reuse_target", lambda: None)
    monkeypatch.setattr(launcher.os, "name", "nt")
    monkeypatch.setattr(launcher.os, "startfile", opened.append, raising=False)
    monkeypatch.setattr(
        launcher.webbrowser,
        "open",
        lambda _url: (_ for _ in ()).throw(AssertionError("webbrowser fallback must not run")),
    )
    ok, mode = launcher._open_manager_url("http://127.0.0.1:9200/")
    assert ok is True
    assert mode == "windows-default-url-handler"
    assert opened == ["http://127.0.0.1:9200/"]


def test_launcher_never_requests_isolated_browser_profile() -> None:
    source = Path(launcher.__file__).read_text(encoding="utf-8")
    assert "--user-data-dir" not in source
    assert "--inprivate" not in source.lower()
    assert "tempfile" not in source