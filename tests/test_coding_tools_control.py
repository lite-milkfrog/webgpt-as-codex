from __future__ import annotations

from pathlib import Path

import pytest

from webgpt_as_codex import coding_tools_control as control


def test_config_requires_existing_absolute_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(state))

    saved = control.write_coding_tools_config(
        {
            "workspace": str(workspace),
            "permission_mode": "trusted",
            "workspace_mutation": "unrestricted",
            "shell_env_inherit": "core",
            "allow_network": False,
            "enable_view_image": True,
        }
    )
    assert saved["workspace"] == str(workspace.resolve())
    assert control.read_coding_tools_config()["permission_mode"] == "trusted"

    with pytest.raises(ValueError):
        control.write_coding_tools_config({**saved, "workspace": "relative/path"})
    with pytest.raises(ValueError):
        control.write_coding_tools_config(
            {**saved, "workspace": str(tmp_path / "missing")}
        )
    with pytest.raises(ValueError):
        control.write_coding_tools_config({**saved, "permission_mode": "root"})


def test_public_status_reports_saved_and_live_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    control.write_coding_tools_config(
        {
            "workspace": str(workspace),
            "permission_mode": "safe",
            "workspace_mutation": "unrestricted",
            "shell_env_inherit": "core",
            "allow_network": False,
            "enable_view_image": True,
        }
    )
    monkeypatch.setattr(
        control,
        "probe_coding_tools_live",
        lambda: {
            "reachable": True,
            "workspace": str(workspace.resolve()),
            "permission_mode": "trusted",
            "workspace_mutation": "unrestricted",
            "shell_env_inherit": "core",
        },
    )

    status = control.coding_tools_public_status()

    assert status["configured"]["permission_mode"] == "safe"
    assert status["live"]["permission_mode"] == "trusted"
    assert status["restart_required"] is True
    assert status["permission_modes"] == ["safe", "trusted", "dangerous"]


def test_managed_launcher_upgrades_known_legacy_wrapper_and_uses_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    server = tmp_path / "coding-tools-mcp.exe"
    server.write_bytes(b"stub")
    legacy = tmp_path / "start-coding-tools-remote-v2.ps1"
    legacy.write_text("Write-Output legacy\n", encoding="utf-8")
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(state))
    monkeypatch.setattr(control, "_coding_tools_executable", lambda: server)
    monkeypatch.setattr(control, "_legacy_launcher", lambda: legacy)

    launcher = state / "external-ensure" / "coding-tools.ps1"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        '& powershell.exe -File "start-coding-tools-remote-v2.ps1"\n',
        encoding="utf-8",
    )
    control.write_coding_tools_config(
        {
            "workspace": str(workspace),
            "permission_mode": "trusted",
            "workspace_mutation": "unrestricted",
            "shell_env_inherit": "core",
            "allow_network": False,
            "enable_view_image": True,
        }
    )

    result = control.ensure_coding_tools_external_launcher()
    text = launcher.read_text(encoding="utf-8")

    assert result["ok"] is True
    assert control._MANAGED_MARKER in text
    assert "coding-tools.json" in text
    assert "--permission-mode" in text
    assert "--workspace-mutation" in text
    assert "Port 8766 is owned by an unexpected process" in text
    assert "start-coding-tools-remote-v2.ps1" in text
    assert "if (-not $Restart -and $legacy" in text


def test_apply_config_can_save_without_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        control,
        "ensure_coding_tools_external_launcher",
        lambda: {"ok": True, "status": "present"},
    )
    monkeypatch.setattr(
        control,
        "probe_coding_tools_live",
        lambda: {
            "reachable": True,
            "workspace": str(workspace.resolve()),
            "permission_mode": "safe",
        },
    )

    result = control.apply_coding_tools_config(
        workspace=str(workspace),
        permission_mode="safe",
        restart=False,
    )

    assert result["ok"] is True
    assert result["status"] == "saved"
    assert control.read_coding_tools_config()["workspace"] == str(workspace.resolve())


def test_restart_coding_tools_does_not_capture_child_pipes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = tmp_path / "coding-tools.ps1"
    launcher.write_text("Write-Output ok\n", encoding="utf-8")
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0

    def fake_run(*args: object, **kwargs: object) -> Completed:
        captured.update(kwargs)
        return Completed()

    monkeypatch.setattr(
        control,
        "ensure_coding_tools_external_launcher",
        lambda: {"ok": True, "status": "present"},
    )
    monkeypatch.setattr(control, "_launcher_path", lambda: launcher)
    monkeypatch.setattr(control.subprocess, "run", fake_run)
    monkeypatch.setattr(
        control,
        "probe_coding_tools_live",
        lambda: {"reachable": True, "workspace": str(tmp_path)},
    )

    result = control.restart_coding_tools()

    assert result["ok"] is True
    assert captured["stdin"] is control.subprocess.DEVNULL
    assert captured["stdout"] is control.subprocess.DEVNULL
    assert captured["stderr"] is control.subprocess.DEVNULL
    assert "capture_output" not in captured
