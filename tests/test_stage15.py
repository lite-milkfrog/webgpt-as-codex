from __future__ import annotations

from pathlib import Path

import pytest

from webgpt_as_codex import lifecycle
from webgpt_as_codex.lifecycle import LatestRelease
from webgpt_as_codex.registry import Component, load_components


def _component(
    component_id: str = "sample",
    *,
    strategy: str = "uv-tool",
    package: str | None = "sample-package",
    required: bool = True,
) -> Component:
    install: dict = {
        "strategy": strategy,
        "latest": {"source": "pypi", "package": package or "sample-package"},
    }
    if strategy != "manual":
        install["requirements"] = []
        install["compatibility"] = {
            "min_version": "0.0.0",
            "max_version_exclusive": "100.0.0",
        }
    if package is not None:
        install["package"] = package
    if strategy == "manual":
        install["latest"] = {"source": "npm", "package": package or "manual-package"}
    return Component(
        id=component_id,
        display_name=component_id,
        role="test",
        required=required,
        enabled_by_default=required,
        transport="streamable_http",
        default_endpoint="http://127.0.0.1:9999/mcp",
        raw={
            "id": component_id,
            "display_name": component_id,
            "role": "test",
            "required": required,
            "enabled_by_default": required,
            "transport": "streamable_http",
            "default_endpoint": "http://127.0.0.1:9999/mcp",
            "version_command": [component_id, "--version"],
            "install": install,
        },
    )


def _patch_plan_evidence(
    monkeypatch: pytest.MonkeyPatch,
    *,
    listener: bool | None,
    process: bool | None,
    installed: bool | None,
    current: str | None,
    latest: str = "2.0.0",
    owned: bool = False,
) -> None:
    monkeypatch.setattr(
        lifecycle,
        "discover_component",
        lambda _component: {
            "listener_up": listener,
            "installed_by_path": installed,
        },
    )
    monkeypatch.setattr(lifecycle, "process_snapshot", list)
    monkeypatch.setattr(
        lifecycle,
        "process_health",
        lambda _component, _snapshot: process,
    )
    monkeypatch.setattr(
        lifecycle,
        "installed_version",
        lambda _component, _spec: current,
    )
    monkeypatch.setattr(
        lifecycle,
        "_safe_latest",
        lambda component: (
            LatestRelease(component.id, latest, "test"),
            None,
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "ownership_receipt",
        lambda component_id: (
            {
                "component_id": component_id,
                "installed_by_webgpt": True,
                "runtime_lifecycle_authority": False,
                "version": current,
            }
            if owned
            else None
        ),
    )


def test_builtin_components_declare_install_metadata() -> None:
    components = load_components()
    expected = {
        "serena",
        "coding-tools",
        "playwright",
        "windows-mcp",
        "tailscale",
        "mcpjungle",
        "mcp-auth-proxy",
        "remote-desktop-commander",
    }

    assert expected <= set(components)
    for component_id in expected:
        assert lifecycle.install_spec(components[component_id]) is not None


def test_version_comparison_is_numeric_and_does_not_downgrade() -> None:
    assert lifecycle.compare_versions("1.7.0", "1.7.0") == 0
    assert lifecycle.compare_versions("1.7.0", "1.8.0") == -1
    assert lifecycle.compare_versions("2.0.0", "1.9.9") == 1


def test_latest_registry_adapters_use_stable_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    serena = load_components()["serena"]
    playwright = load_components()["playwright"]

    def fake_json(url: str) -> dict:
        if "pypi.org" in url:
            return {"info": {"version": "1.7.0"}}
        if "registry.npmjs.org" in url:
            return {"version": "0.0.82"}
        raise AssertionError(url)

    monkeypatch.setattr(lifecycle, "_request_json", fake_json)

    assert lifecycle.resolve_latest(serena).version == "1.7.0"
    assert lifecycle.resolve_latest(playwright).version == "0.0.82"


def test_latest_github_requires_asset_digest_and_approved_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = load_components()["mcpjungle"]
    monkeypatch.setattr(lifecycle, "_architecture", lambda: "amd64")
    monkeypatch.setattr(
        lifecycle,
        "_request_json",
        lambda _url: {
            "tag_name": "v0.4.6",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": "mcpjungle_Windows_x86_64.zip",
                    "digest": "sha256:" + "a" * 64,
                    "browser_download_url": (
                        "https://github.com/mcpjungle/MCPJungle/releases/download/"
                        "v0.4.6/mcpjungle_Windows_x86_64.zip"
                    ),
                }
            ],
        },
    )

    latest = lifecycle.resolve_latest(component)

    assert latest.version == "0.4.6"
    assert latest.sha256 == "a" * 64
    assert latest.artifact_name == "mcpjungle_Windows_x86_64.zip"


def test_healthy_listener_prevents_duplicate_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan_evidence(
        monkeypatch,
        listener=True,
        process=True,
        installed=False,
        current=None,
        latest="9.9.9",
        owned=False,
    )

    plan = lifecycle.plan_component(_component())

    assert plan["action"] == "preserve-healthy"
    assert plan["mutation"] is False


def test_running_unhealthy_instance_is_diagnosed_not_reinstalled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan_evidence(
        monkeypatch,
        listener=False,
        process=True,
        installed=False,
        current=None,
    )

    plan = lifecycle.plan_component(_component())

    assert plan["action"] == "diagnose-running-unhealthy"
    assert plan["mutation"] is False


def test_missing_component_plans_latest_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan_evidence(
        monkeypatch,
        listener=False,
        process=False,
        installed=False,
        current=None,
        latest="2.1.0",
    )

    plan = lifecycle.plan_component(_component())

    assert plan["action"] == "install-missing"
    assert plan["latest_version"] == "2.1.0"


def test_external_older_component_is_not_silently_adopted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan_evidence(
        monkeypatch,
        listener=False,
        process=False,
        installed=True,
        current="1.0.0",
        latest="2.0.0",
        owned=False,
    )

    plan = lifecycle.plan_component(_component())

    assert plan["action"] == "upgrade-external-requires-adoption"
    assert plan["webgpt_install_owned"] is False


def test_owned_older_component_can_upgrade_when_stopped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan_evidence(
        monkeypatch,
        listener=False,
        process=False,
        installed=True,
        current="1.0.0",
        latest="2.0.0",
        owned=True,
    )

    plan = lifecycle.plan_component(_component())

    assert plan["action"] == "upgrade-owned"
    assert plan["runtime_lifecycle_authority"] is False


def test_apply_missing_component_records_install_ownership_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    component = _component()
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        lifecycle,
        "plan_component",
        lambda _component: {
            "component_id": component.id,
            "action": "install-missing",
            "mutation": False,
        },
    )
    monkeypatch.setattr(
        lifecycle,
        "_safe_latest",
        lambda _component: (LatestRelease(component.id, "2.0.0", "pypi"), None),
    )
    monkeypatch.setattr(
        lifecycle,
        "_install_uv",
        lambda _spec, _version: {"ok": True, "status": "installed"},
    )

    result = lifecycle.apply_component(component)
    receipt = lifecycle.ownership_receipt(component.id)

    assert result["ok"] is True
    assert result["applied"] is True
    assert receipt is not None
    assert receipt["installed_by_webgpt"] is True
    assert receipt["runtime_lifecycle_authority"] is False
    assert receipt["version"] == "2.0.0"


def test_remote_desktop_commander_stays_manual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = load_components()["remote-desktop-commander"]
    monkeypatch.setattr(
        lifecycle,
        "discover_component",
        lambda _component: {"listener_up": None, "installed_by_path": None},
    )
    monkeypatch.setattr(lifecycle, "process_snapshot", list)
    monkeypatch.setattr(lifecycle, "process_health", lambda *_args: False)
    monkeypatch.setattr(lifecycle, "ownership_receipt", lambda _component_id: None)
    monkeypatch.setattr(
        lifecycle,
        "_safe_latest",
        lambda _component: (
            LatestRelease(component.id, "0.2.51", "npm"),
            None,
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "installed_version",
        lambda _component, _spec: None,
    )

    plan = lifecycle.plan_component(component)

    assert plan["action"] == "manual-required"
    assert plan["mutation"] is False



def test_healthy_system_process_without_listener_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component("tailscale", strategy="winget", package=None)
    component = Component(
        id=component.id,
        display_name=component.display_name,
        role=component.role,
        required=component.required,
        enabled_by_default=component.enabled_by_default,
        transport="system",
        default_endpoint=None,
        raw={
            **component.raw,
            "transport": "system",
            "default_endpoint": None,
            "install": {
                "strategy": "winget",
                "winget_id": "Tailscale.Tailscale",
                "latest": {"source": "winget"},
                "requirements": [],
                "compatibility": {
                    "min_version": "1.38.3",
                    "max_version_exclusive": "2.0.0",
                },
            },
        },
    )
    _patch_plan_evidence(
        monkeypatch,
        listener=None,
        process=True,
        installed=True,
        current="1.102.2",
        latest="1.102.2",
        owned=False,
    )

    plan = lifecycle.plan_component(component)

    assert plan["action"] == "preserve-healthy-system"
    assert plan["mutation"] is False


def test_owned_github_upgrade_forces_verified_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = load_components()["mcpjungle"]
    latest = LatestRelease(
        component.id,
        "0.4.7",
        "github-release",
        artifact_name="mcpjungle_Windows_x86_64.zip",
        download_url=(
            "https://github.com/mcpjungle/MCPJungle/releases/download/"
            "0.4.7/mcpjungle_Windows_x86_64.zip"
        ),
        sha256="b" * 64,
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(lifecycle, "_architecture", lambda: "amd64")
    monkeypatch.setattr(
        lifecycle,
        "provision_artifact",
        lambda artifact, *, force=False: (
            seen.update({"artifact": artifact, "force": force})
            or {"ok": True, "status": "provisioned"}
        ),
    )

    result = lifecycle._install_github(
        component,
        lifecycle.install_spec(component),
        latest,
        force=True,
    )

    assert result["ok"] is True
    assert seen["force"] is True
    assert seen["artifact"].version == "0.4.7"


def test_owned_winget_upgrade_uses_upgrade_verb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = load_components()["tailscale"]
    spec = lifecycle.install_spec(component)
    assert spec is not None
    commands: list[list[str]] = []
    monkeypatch.setattr(lifecycle.shutil, "which", lambda name: "winget.exe" if name == "winget" else None)

    def fake_run(command: list[str], *, timeout: float = 120.0):
        del timeout
        commands.append(command)
        return lifecycle.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(lifecycle, "_run", fake_run)

    result = lifecycle._install_winget(spec, upgrade=True)

    assert result["ok"] is True
    assert commands[0][1] == "upgrade"


def test_default_deploy_keeps_manual_remote_desktop_step_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    automatic = _component("automatic")
    manual = _component(
        "remote-desktop-commander",
        strategy="manual",
        package="@wonderwhy-er/desktop-commander",
        required=False,
    )
    monkeypatch.setattr(
        lifecycle,
        "load_components",
        lambda: {automatic.id: automatic, manual.id: manual},
    )
    monkeypatch.setattr(
        lifecycle,
        "plan_component",
        lambda component: {
            "component_id": component.id,
            "action": "manual-required" if component.id == manual.id else "preserve-healthy",
        },
    )
    monkeypatch.setattr(lifecycle, "toolchain_environment", dict)

    result = lifecycle.run_deploy()

    assert [row["component_id"] for row in result["components"]] == [
        "automatic",
        "remote-desktop-commander",
    ]


def test_latest_outside_compatibility_window_blocks_missing_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component()
    component.raw["install"]["compatibility"] = {
        "min_version": "1.0.0",
        "max_version_exclusive": "2.0.0",
    }
    _patch_plan_evidence(
        monkeypatch,
        listener=False,
        process=False,
        installed=False,
        current=None,
        latest="2.0.0",
    )

    plan = lifecycle.plan_component(component)

    assert plan["action"] == "install-blocked-incompatible-latest"
    assert plan["latest_compatible"] is False
    assert plan["blocking"] is True


def test_newer_compatible_install_is_preserved_without_downgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component()
    component.raw["install"]["compatibility"] = {
        "min_version": "1.0.0",
        "max_version_exclusive": "3.0.0",
    }
    _patch_plan_evidence(
        monkeypatch,
        listener=False,
        process=False,
        installed=True,
        current="2.5.0",
        latest="2.0.0",
    )

    plan = lifecycle.plan_component(component)

    assert plan["action"] == "preserve-newer"
    assert plan["verified_compatible"] is True
    assert plan["mutation"] is False


def test_latest_network_failure_is_not_reported_as_up_to_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component()
    _patch_plan_evidence(
        monkeypatch,
        listener=True,
        process=True,
        installed=False,
        current=None,
        latest="2.0.0",
    )
    monkeypatch.setattr(
        lifecycle,
        "_safe_latest",
        lambda _component: (None, "ConnectionError"),
    )

    plan = lifecycle.plan_component(component)

    assert plan["action"] == "preserve-existing-latest-unavailable"
    assert plan["latest_version"] is None
    assert plan["latest_error"] == "ConnectionError"
    assert plan["blocking"] is True


def test_known_protocol_conflict_blocks_duplicate_endpoint_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component()
    _patch_plan_evidence(
        monkeypatch,
        listener=True,
        process=False,
        installed=False,
        current=None,
        latest="2.0.0",
    )
    monkeypatch.setattr(
        lifecycle,
        "discover_component",
        lambda _component: {
            "listener_up": True,
            "installed_by_path": False,
            "protocol_healthy": False,
        },
    )

    plan = lifecycle.plan_component(component)

    assert plan["action"] == "diagnose-listener-conflict"
    assert plan["mutation"] is False
    assert plan["blocking"] is True


def test_builtin_install_requirements_are_explicit() -> None:
    components = load_components()
    expected = {
        "coding-tools": ("uv",),
        "serena": ("uv",),
        "windows-mcp": ("uv",),
        "playwright": ("node", "npm"),
        "tailscale": ("winget",),
        "mcpjungle": (),
        "mcp-auth-proxy": (),
        "remote-desktop-commander": ("node", "npm"),
    }

    assert {
        component_id: lifecycle.install_spec(components[component_id]).requirements
        for component_id in expected
    } == expected


def test_external_upgrade_requires_explicit_adoption(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    component = _component()
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        lifecycle,
        "plan_component",
        lambda _component: {
            "component_id": component.id,
            "action": "upgrade-external-requires-adoption",
            "mutation": False,
        },
    )
    monkeypatch.setattr(
        lifecycle,
        "_safe_latest",
        lambda _component: (LatestRelease(component.id, "2.0.0", "pypi"), None),
    )
    monkeypatch.setattr(
        lifecycle,
        "_install_uv",
        lambda _spec, _version: {"ok": True, "status": "installed"},
    )

    denied = lifecycle.apply_component(component)
    adopted = lifecycle.apply_component(component, adopt_external=True)

    assert denied["applied"] is False
    assert adopted["applied"] is True
    assert lifecycle.ownership_receipt(component.id)["installed_by_webgpt"] is True


def test_machine_binary_version_resolves_when_not_on_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    component = load_components()["mcpjungle"]
    spec = lifecycle.install_spec(component)
    assert spec is not None
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    target = tmp_path / "bin" / "mcpjungle" / "mcpjungle.exe"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"stub")
    monkeypatch.setattr(lifecycle, "_find_command", lambda _name: None)

    def fake_run(command: list[str], *, timeout: float = 120.0):
        del timeout
        assert Path(command[0]) == target
        return lifecycle.subprocess.CompletedProcess(
            command,
            0,
            "mcpjungle version 0.4.6\n",
            "",
        )

    monkeypatch.setattr(lifecycle, "_run", fake_run)

    assert lifecycle.installed_version(component, spec) == "0.4.6"


def test_prerelease_latest_is_rejected_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = load_components()["playwright"]
    monkeypatch.setattr(
        lifecycle,
        "_request_json",
        lambda _url: {"version": "0.0.83-beta.1"},
    )

    with pytest.raises(ValueError):
        lifecycle.resolve_latest(component)



def test_latest_resolution_uses_fresh_verified_cache_on_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    component = load_components()["mcpjungle"]
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    latest = LatestRelease(
        component.id,
        "0.4.6",
        "github-release",
        artifact_name="mcpjungle_Windows_x86_64.zip",
        download_url=(
            "https://github.com/mcpjungle/MCPJungle/releases/download/"
            "0.4.6/mcpjungle_Windows_x86_64.zip"
        ),
        sha256="a" * 64,
    )
    lifecycle._write_latest_cache(component, latest)
    monkeypatch.setattr(
        lifecycle,
        "resolve_latest",
        lambda _component: (_ for _ in ()).throw(lifecycle.requests.HTTPError("rate limited")),
    )

    resolved, error = lifecycle._safe_latest(component)

    assert resolved == latest
    assert error == "HTTPError:using-verified-cache"


def test_verified_cache_is_evidence_not_install_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component()
    _patch_plan_evidence(
        monkeypatch,
        listener=False,
        process=False,
        installed=False,
        current=None,
        latest="2.0.0",
    )
    monkeypatch.setattr(
        lifecycle,
        "_safe_latest",
        lambda _component: (
            LatestRelease(component.id, "2.0.0", "pypi"),
            "HTTPError:using-verified-cache",
        ),
    )

    plan = lifecycle.plan_component(component)

    assert plan["action"] == "install-blocked-latest-unavailable"
    assert plan["latest_version"] == "2.0.0"
    assert plan["latest_fresh"] is False
    assert plan["latest_provenance"] == "verified-cache"
    assert plan["blocking"] is True


def test_apply_refuses_cached_latest_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _component()
    monkeypatch.setattr(
        lifecycle,
        "plan_component",
        lambda _component: {
            "component_id": component.id,
            "action": "install-missing",
            "mutation": False,
        },
    )
    monkeypatch.setattr(
        lifecycle,
        "_safe_latest",
        lambda _component: (
            LatestRelease(component.id, "2.0.0", "pypi"),
            "HTTPError:using-verified-cache",
        ),
    )
    called = {"install": False}
    monkeypatch.setattr(
        lifecycle,
        "_install_uv",
        lambda _spec, _version: called.update(install=True),
    )

    result = lifecycle.apply_component(component)

    assert result["applied"] is False
    assert result["ok"] is False
    assert result["status"] == "latest-resolution-failed"
    assert called["install"] is False
