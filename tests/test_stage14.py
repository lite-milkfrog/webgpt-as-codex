from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from webgpt_as_codex import edge_runtime, gateway, runtime
from webgpt_as_codex.registry import Component


def _component(
    component_id: str,
    endpoint: str,
    *,
    enabled: bool = True,
    transport: str = "streamable_http",
) -> Component:
    raw = {
        "id": component_id,
        "display_name": component_id.title(),
        "role": "test",
        "required": True,
        "enabled_by_default": enabled,
        "transport": transport,
        "default_endpoint": endpoint,
    }
    return Component(
        id=component_id,
        display_name=raw["display_name"],
        role="test",
        required=True,
        enabled_by_default=enabled,
        transport=transport,
        default_endpoint=endpoint,
        raw=raw,
    )


def test_list_registered_servers_parses_current_mcpjungle_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = """1. coding-tools
Coding Tools MCP via WebGPT-as-Codex
Transport: streamable_http
URL: http://127.0.0.1:8766/mcp

2. serena
Serena via WebGPT-as-Codex
Transport: streamable_http
URL: http://127.0.0.1:9121/mcp
"""
    monkeypatch.setattr(
        gateway.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, output, ""),
    )

    result = gateway.list_registered_servers("http://127.0.0.1:9330")

    assert result == {
        "coding-tools": {
            "transport": "streamable_http",
            "url": "http://127.0.0.1:8766/mcp",
        },
        "serena": {
            "transport": "streamable_http",
            "url": "http://127.0.0.1:9121/mcp",
        },
    }


def test_route_sync_preserves_same_registers_missing_and_updates_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    components = {
        "coding-tools": _component("coding-tools", "http://127.0.0.1:8766/mcp"),
        "serena": _component("serena", "http://127.0.0.1:9121/mcp"),
        "windows-mcp": _component("windows-mcp", "http://127.0.0.1:8001/mcp"),
        "playwright": _component("playwright", "http://localhost:8931/mcp"),
        "disabled": _component("disabled", "http://127.0.0.1:9998/mcp", enabled=False),
        "system": _component("system", "", transport="system"),
    }
    discovery = {
        component_id: {"listener_up": component_id != "playwright"}
        for component_id in components
    }
    existing = {
        "coding-tools": {
            "transport": "streamable_http",
            "url": "http://127.0.0.1:8766/mcp",
        },
        "serena": {
            "transport": "streamable_http",
            "url": "http://127.0.0.1:9999/mcp",
        },
    }
    calls: list[tuple[str, str, bool]] = []

    monkeypatch.setattr("webgpt_as_codex.registry.load_components", lambda: components)
    monkeypatch.setattr("webgpt_as_codex.discovery.discover_all", lambda _components: discovery)
    monkeypatch.setattr(gateway, "list_registered_servers", lambda _registry: existing)
    monkeypatch.setattr(
        gateway,
        "register_http",
        lambda _registry, name, url, _description, *, force=False: calls.append(
            (name, url, force)
        ),
    )

    result = gateway.sync_enabled_http_routes("http://127.0.0.1:9330")

    assert result["ok"] is True
    assert result["preserved"] == ["coding-tools"]
    assert result["updated"] == ["serena"]
    assert result["registered"] == ["windows-mcp"]
    assert {"id": "playwright", "reason": "listener-unavailable"} in result["skipped"]
    assert calls == [
        ("serena", "http://127.0.0.1:9121/mcp", True),
        ("windows-mcp", "http://127.0.0.1:8001/mcp", False),
    ]


def test_oauth_password_is_machine_local_reused_and_rotatable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))

    first = edge_runtime.ensure_oauth_password()
    second = edge_runtime.ensure_oauth_password()

    assert first == second
    assert len(first) >= 32
    assert edge_runtime.oauth_password_path() == tmp_path / "secrets" / "oauth-password.txt"
    assert edge_runtime.oauth_password_status()["configured"] is True

    edge_runtime.set_oauth_password("replacement-password-123")
    assert edge_runtime.read_oauth_password() == "replacement-password-123"


def test_runtime_owns_edge_wrapper_not_external_backends() -> None:
    spec = runtime.RUNTIME_SPECS["mcp-auth-proxy"]
    argv = spec.argv_builder()

    assert argv[-1] == "edge-runtime"
    assert spec.endpoint == "http://127.0.0.1:9341/mcp"
    assert "mcp-auth-proxy" in runtime.MANAGER_RESTARTABLE
    assert "serena" not in runtime.MANAGER_RESTARTABLE
    assert "coding-tools" not in runtime.MANAGER_RESTARTABLE


def test_production_edge_uses_standard_https_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(edge_runtime, "tailscale_dns_name", lambda: "node.example.ts.net")
    assert edge_runtime.PUBLIC_PORT == 443
    assert edge_runtime.public_base_url() == "https://node.example.ts.net"


def test_start_all_blocks_edge_when_prerequisites_are_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    components = {
        "mcpjungle": _component("mcpjungle", "http://127.0.0.1:9330/mcp"),
        "mcp-auth-proxy": _component("mcp-auth-proxy", "http://127.0.0.1:9340"),
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
    monkeypatch.setattr(
        "webgpt_as_codex.prerequisites.environment_report",
        lambda: {
            "ready_for_edge": False,
            "next_steps": [{"id": "tailscale", "action": "login", "blocking": True}],
        },
    )
    supervisor = runtime.RuntimeSupervisor()
    monkeypatch.setattr(
        supervisor,
        "start",
        lambda component_id: (_ for _ in ()).throw(
            AssertionError(f"must not start {component_id}")
        ),
    )

    result = supervisor.start_all()
    by_id = {row["component_id"]: row for row in result["results"]}

    assert by_id["mcpjungle"]["status"] == "preserved-unmanaged"
    assert by_id["mcp-auth-proxy"]["status"] == "prerequisites-not-ready"
