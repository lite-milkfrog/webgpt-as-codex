from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from webgpt_as_codex import bootstrap, prerequisites, provision


def test_version_tuple_accepts_tailscale_style_versions() -> None:
    assert prerequisites._version_tuple("1.102.2\n  tailscale commit") == (1, 102, 2)
    assert prerequisites._version_tuple("v1.38.3") == (1, 38, 3)


def test_tailscale_environment_reports_missing_without_guessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prerequisites, "_tailscale_path", lambda: None)

    result = prerequisites.tailscale_environment()

    assert result["installed"] is False
    assert result["ready"] is False
    assert result["next_action"] == "install"
    assert result["funnel_policy"] == "unknown"


def test_tailscale_environment_requires_login_and_funnel_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    binary = tmp_path / "tailscale.exe"
    binary.write_bytes(b"stub")
    monkeypatch.setattr(prerequisites, "_tailscale_path", lambda: binary)

    def fake_run(command: list[str], *, timeout: float = 20.0) -> subprocess.CompletedProcess[str]:
        del timeout
        if command[-1] == "version":
            return subprocess.CompletedProcess(command, 0, "1.102.2\n", "")
        if command[-3:] == ["funnel", "status", "--json"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"AllowFunnel": {"443": True}}),
                "",
            )
        if command[-2:] == ["status", "--json"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "BackendState": "Running",
                        "MagicDNSSuffix": "example.ts.net",
                        "Self": {
                            "Online": True,
                            "DNSName": "host.example.ts.net.",
                        },
                    }
                ),
                "",
            )
        raise AssertionError(command)

    monkeypatch.setattr(prerequisites, "_run", fake_run)

    result = prerequisites.tailscale_environment()

    assert result["installed"] is True
    assert result["version_ok"] is True
    assert result["backend_state"] == "Running"
    assert result["online"] is True
    assert result["dns_name"] == "host.example.ts.net"
    assert result["funnel_cli_ok"] is True
    assert result["funnel_policy"] == "verified-configured"
    assert result["ready"] is True
    assert result["next_action"] == "publish-edge"


def test_environment_report_has_boolean_blocking_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        prerequisites,
        "python_environment",
        lambda: {"ok": True, "version": "3.12", "minimum": "3.11", "executable": "python"},
    )
    monkeypatch.setattr(
        prerequisites,
        "windows_environment",
        lambda: {"ok": True, "platform": "Windows", "release": "11", "version": "x", "reason": None},
    )
    monkeypatch.setattr(
        prerequisites,
        "winget_environment",
        lambda: {"available": False, "path": None, "version": None},
    )
    monkeypatch.setattr(
        prerequisites,
        "tailscale_environment",
        lambda: {
            "installed": False,
            "path": None,
            "version": None,
            "version_ok": False,
            "backend_state": None,
            "online": False,
            "dns_name": None,
            "magic_dns_suffix": None,
            "funnel_cli_ok": False,
            "funnel_policy": "unknown",
            "ready": False,
            "next_action": "install",
        },
    )
    monkeypatch.setattr(
        prerequisites,
        "runtime_binaries_environment",
        lambda: {
            "mcpjungle": {"ready": False, "path": "mcpjungle.exe"},
            "mcp_auth_proxy": {"ready": False, "path": "mcp-auth-proxy.exe"},
            "ready": False,
        },
    )

    result = prerequisites.environment_report()

    assert result["ready_for_edge"] is False
    assert {row["id"] for row in result["next_steps"]} == {
        "tailscale",
        "mcpjungle",
        "mcp-auth-proxy",
    }
    assert all(isinstance(row["blocking"], bool) for row in result["next_steps"])


def test_tailscale_install_preserves_healthy_existing_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = {
        "installed": True,
        "version_ok": True,
        "ready": True,
    }
    monkeypatch.setattr(prerequisites, "tailscale_environment", lambda: current)
    monkeypatch.setattr(prerequisites.shutil, "which", lambda _name: "winget.exe")

    result = prerequisites.install_tailscale_with_winget(confirm=True)

    assert result["ok"] is True
    assert result["status"] == "already-installed"
    assert result["tailscale"] is current


def test_provision_preserves_existing_webgpt_binary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(provision.platform, "machine", lambda: "AMD64")
    destination = tmp_path / "bin" / "mcpjungle" / "mcpjungle.exe"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")

    result = provision.provision_component("mcpjungle")

    assert result["ok"] is True
    assert result["status"] == "preserved-existing"
    assert result["mutation"] is False
    assert destination.read_bytes() == b"existing"


def test_bootstrap_can_install_missing_system_dependency_and_provision_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = {
        "tailscale": {"installed": False},
        "ready_for_edge": False,
    }
    after = {
        "tailscale": {"installed": True},
        "ready_for_edge": True,
    }
    reports = iter([before, after])
    calls: list[str] = []

    monkeypatch.setattr(bootstrap, "build_bootstrap_plan", lambda: {"mode": "plan", "items": []})
    monkeypatch.setattr(bootstrap, "environment_report", lambda: next(reports))
    monkeypatch.setattr(
        bootstrap,
        "install_tailscale_with_winget",
        lambda *, confirm: calls.append(f"tailscale:{confirm}") or {"ok": True, "status": "installed"},
    )
    monkeypatch.setattr(
        bootstrap,
        "provision_runtime_binaries",
        lambda: calls.append("runtime") or {"ok": True, "results": []},
    )

    result = bootstrap.run_bootstrap(
        apply=False,
        install_missing=True,
        provision_runtime=True,
    )

    assert result["environment"] == after
    assert result["environment_changed"] is True
    assert result["runtime_provision"]["ok"] is True
    assert calls == ["tailscale:True", "runtime"]
