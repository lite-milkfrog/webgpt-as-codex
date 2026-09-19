import hashlib
import http.client
import json
import threading
from pathlib import Path

import pytest

from webgpt_as_codex.health import redact_text
from webgpt_as_codex.manager import (
    ActionBusyError,
    ActionPayloadError,
    ActionRunner,
    build_server,
)
from webgpt_as_codex.onboarding import _portable_tool, validate_onboarding_manifest
from webgpt_as_codex.registry import Component, load_components
from webgpt_as_codex.stateio import StateWriteError, atomic_write_text_bundle
from webgpt_as_codex.update import run_update


def _component(raw: dict) -> Component:
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


def test_manager_rejects_unknown_action_payload_fields() -> None:
    runner = ActionRunner({"doctor": lambda _contract, _payload: {"ok": True}})
    with pytest.raises(ActionPayloadError, match="unsupported action fields"):
        runner.run("doctor", payload={"command": "whoami"})


def test_manager_action_lock_fails_closed_under_concurrency() -> None:
    entered = threading.Event()
    release = threading.Event()

    def executor(_contract, _payload):
        entered.set()
        release.wait(timeout=2)
        return {"ok": True}

    runner = ActionRunner({"doctor": executor})
    worker = threading.Thread(target=lambda: runner.run("doctor"), daemon=True)
    worker.start()
    assert entered.wait(timeout=1)
    with pytest.raises(ActionBusyError):
        runner.run("doctor")
    release.set()
    worker.join(timeout=2)
    assert not worker.is_alive()


def test_manager_rejects_dns_rebinding_host_header() -> None:
    server = build_server("127.0.0.1", 0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        port = server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/healthz", headers={"Host": f"evil.example:{port}"})
        response = conn.getresponse()
        body = json.loads(response.read())
        assert response.status == 403
        assert body["error"] == "loopback-origin-required"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_manager_executor_failure_does_not_leak_exception_text() -> None:
    def fail(_contract, _payload):
        raise RuntimeError("Bearer do-not-leak http://127.0.0.1/private")

    server = build_server(
        "127.0.0.1",
        0,
        action_runner=ActionRunner({"doctor": fail}),
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        port = server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request(
            "POST",
            "/api/actions/doctor",
            body="{}",
            headers={
                "Host": f"127.0.0.1:{port}",
                "Content-Type": "application/json",
                "X-WebGPT-Control": "1",
            },
        )
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        assert response.status == 500
        assert "do-not-leak" not in raw
        assert "127.0.0.1" not in raw
        assert json.loads(raw)["failure_type"] == "RuntimeError"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_embedded_private_urls_are_redacted() -> None:
    cleaned = redact_text("callback=http://127.0.0.1:9000/private and https://example.test/mcp")
    assert "127.0.0.1" not in cleaned
    assert "[private-url]" in cleaned
    assert "https://example.test/mcp" in cleaned


def test_registry_custom_files_cannot_shadow_builtin_or_break_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    custom = tmp_path / "config" / "components"
    custom.mkdir(parents=True)
    (custom / "serena.json").write_text(
        json.dumps(
            {
                "id": "serena",
                "display_name": "Untrusted override",
                "role": "override",
                "required": False,
                "enabled_by_default": False,
                "transport": "streamable_http",
                "default_endpoint": "http://127.0.0.1:1/mcp",
            }
        ),
        encoding="utf-8",
    )
    (custom / "broken.json").write_text("{broken", encoding="utf-8")
    components = load_components()
    assert components["serena"].display_name == "Serena"
    assert "broken" not in components


def test_registry_ignores_custom_manifest_with_executable_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    custom = tmp_path / "config" / "components"
    custom.mkdir(parents=True)
    (custom / "evil.json").write_text(
        json.dumps(
            {
                "id": "evil",
                "display_name": "Evil",
                "role": "optional",
                "required": False,
                "enabled_by_default": True,
                "transport": "streamable_http",
                "default_endpoint": "http://127.0.0.1:9999/mcp",
                "safe_tool": None,
                "upstream": None,
                "version_command": ["powershell", "-Command", "whoami"],
            }
        ),
        encoding="utf-8",
    )
    assert "evil" not in load_components()


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://user:pass@example.test/mcp",
        "https://example.test/mcp?token=secret",
        "https://example.test/mcp#fragment",
    ],
)
def test_onboarding_rejects_credentialized_or_ambiguous_endpoint(endpoint: str) -> None:
    with pytest.raises(ValueError, match="credentials, query or fragment"):
        validate_onboarding_manifest(
            {
                "id": "example",
                "display_name": "Example",
                "role": "optional",
                "required": False,
                "enabled_by_default": True,
                "transport": "streamable_http",
                "default_endpoint": endpoint,
            }
        )


def test_external_tool_schema_is_sanitized_before_persistence() -> None:
    portable = _portable_tool(
        {
            "name": "sample",
            "description": "callback http://127.0.0.1:9999/private",
            "inputSchema": {
                "type": "object",
                "description": "Bearer abc.def.ghi",
                "examples": ["http://localhost:8000/private"],
            },
        }
    )
    text = json.dumps(portable)
    assert "127.0.0.1" not in text
    assert "localhost" not in text
    assert "abc.def.ghi" not in text


def test_atomic_bundle_rolls_back_partial_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from webgpt_as_codex import stateio

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    third = tmp_path / "third.json"
    first.write_text("old-first\n", encoding="utf-8")
    second.write_text("old-second\n", encoding="utf-8")
    original_replace = stateio.os.replace
    calls = 0

    def flaky_replace(source, target):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("simulated third-file failure")
        return original_replace(source, target)

    monkeypatch.setattr(stateio.os, "replace", flaky_replace)
    with pytest.raises(StateWriteError, match="state bundle commit failed"):
        atomic_write_text_bundle(
            {
                first: "new-first\n",
                second: "new-second\n",
                third: "new-third\n",
            }
        )
    assert first.read_text(encoding="utf-8") == "old-first\n"
    assert second.read_text(encoding="utf-8") == "old-second\n"
    assert not third.exists()


def test_fixed_manager_update_is_verified_idempotent_and_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    artifact = b"verified staged update"
    digest = hashlib.sha256(artifact).hexdigest()
    raw = {
        "id": "mcpjungle",
        "display_name": "MCPJungle",
        "role": "gateway",
        "required": True,
        "enabled_by_default": True,
        "transport": "streamable_http",
        "default_endpoint": "http://127.0.0.1:9330/mcp",
        "upstream": "https://github.com/mcpjungle/MCPJungle",
        "machine_binary": "bin/mcpjungle/mcpjungle.exe",
        "approved_update": {
            "version": "1.2.3",
            "artifact": "mcpjungle.exe",
            "sha256": digest,
            "source_url": (
                "https://github.com/mcpjungle/MCPJungle/"
                "releases/download/v1.2.3/mcpjungle.exe"
            ),
        },
    }
    component = _component(raw)
    monkeypatch.setattr(
        "webgpt_as_codex.update.load_components",
        lambda: {"mcpjungle": component},
    )
    monkeypatch.setattr(
        "webgpt_as_codex.update.discover_component",
        lambda _component: {"listener_up": False},
    )
    monkeypatch.setattr(
        "webgpt_as_codex.runtime.RuntimeSupervisor.status",
        lambda _self, _component_id: {"state": "stopped"},
    )
    staged = (
        tmp_path
        / "downloads"
        / "approved-updates"
        / "mcpjungle"
        / "1.2.3"
        / "mcpjungle.exe"
    )
    staged.parent.mkdir(parents=True)
    staged.write_bytes(artifact)

    first = run_update("mcpjungle")
    second = run_update("mcpjungle")
    destination = tmp_path / "bin" / "mcpjungle" / "mcpjungle.exe"
    assert first["status"] == "updated"
    assert second["status"] == "already-current"
    assert destination.read_bytes() == artifact
