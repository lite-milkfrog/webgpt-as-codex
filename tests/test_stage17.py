from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path

import pytest

from webgpt_as_codex import launcher
from webgpt_as_codex.launcher import _launcher_content
from webgpt_as_codex.manager import ActionRunner, build_server


class _Status:
    def snapshot(self, *, force: bool = False) -> dict:
        del force
        return {
            "poll_after_ms": 3000,
            "components": [],
            "gateway": {"configured": True, "health": {"listener": True}},
            "oauth": {"configured": True, "health": {"listener": True}},
            "tailscale": {"configured": True, "health": {"process": True}},
            "public_mcp_url": "https://example.test/mcp",
        }


@pytest.fixture
def manager_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "webgpt_as_codex.manager.environment_report",
        lambda: {
            "python": {"ok": True, "version": "3.12.0", "minimum": "3.11", "executable": "SECRET_PATH"},
            "windows": {"ok": True, "platform": "Windows", "release": "11", "version": "x", "reason": None},
            "winget": {"available": True, "version": "v1", "path": "SECRET_PATH"},
            "tailscale": {
                "installed": True,
                "version": "1.2.3",
                "ready": True,
                "path": "SECRET_PATH",
                "dns_name": "private-host.example.ts.net",
                "magic_dns_suffix": "private.example.ts.net",
            },
            "runtime_binaries": {
                "mcpjungle": {"ready": True, "path": "SECRET_PATH"},
                "mcp_auth_proxy": {"ready": True, "path": "SECRET_PATH"},
                "ready": True,
            },
            "ready_for_local_manager": True,
            "ready_for_gateway": True,
            "ready_for_edge": True,
            "next_steps": [],
        },
    )
    server = build_server(
        "127.0.0.1",
        0,
        status_service=_Status(),
        action_runner=ActionRunner({"doctor": lambda _c, _p: {"ok": True, "status": "pass"}}),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def _request(server, method: str, path: str, payload: dict | None = None):
    port = server.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    headers = {"Host": f"127.0.0.1:{port}"}
    body = None
    if payload is not None:
        body = json.dumps(payload)
        headers.update({"Content-Type": "application/json", "X-WebGPT-Control": "1"})
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    return response.status, raw, dict(response.getheaders())


def test_bilingual_resources_share_one_functional_contract(monkeypatch, manager_server) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_UI_LANG", "zh-CN")
    status, root, _ = _request(manager_server, "GET", "/")
    assert status == 200 and b'lang="zh-CN"' in root
    assert _request(manager_server, "GET", "/en")[0] == 200
    assert _request(manager_server, "GET", "/zh")[0] == 200
    assert _request(manager_server, "GET", "/manager.js")[0] == 200
    assert _request(manager_server, "GET", "/manager.css")[0] == 200

    static = Path(__file__).resolve().parents[1] / "manager" / "static"
    english = (static / "index.html").read_text(encoding="utf-8")
    chinese = (static / "index.zh-CN.html").read_text(encoding="utf-8")
    script = (static / "manager.js").read_text(encoding="utf-8")
    css = (static / "manager.css").read_text(encoding="utf-8")
    for html in (english, chinese):
        assert 'data-ui-contract="manager-v2"' in html
        assert 'src="/manager.js"' in html
        assert 'href="/manager.css"' in html
        assert 'aria-live="polite"' in html
    for endpoint in ("/api/local-config", "/api/oauth-password", "/api/components", "/api/environment", "/api/activity"):
        assert endpoint in script
    assert "navigator.clipboard" in script and "window.open" in script
    assert "prefers-reduced-motion" in css and ":focus-visible" in css


def test_local_config_is_public_safe(manager_server) -> None:
    status, raw, _ = _request(manager_server, "GET", "/api/local-config")
    assert status == 200
    text = raw.decode()
    body = json.loads(text)
    assert body["product_version"] == "0.1.0"
    assert body["oauth_password"] == {"configured": False}
    assert body["deployment"] == {
        "manager_ready": True,
        "gateway_ready": True,
        "edge_ready": True,
        "mode": "unified-gateway",
    }
    assert "SECRET_PATH" not in text
    assert "dns_name" not in text
    assert "magic_dns_suffix" not in text
    assert "secrets" not in text


def test_oauth_set_reveal_regenerate_and_activity_are_secret_safe(manager_server) -> None:
    first = "A" * 16
    assert _request(manager_server, "POST", "/api/oauth-password", {"action": "set", "value": first, "confirm": True})[0] == 200
    status, raw, _ = _request(manager_server, "POST", "/api/oauth-password", {"action": "reveal", "confirm": True})
    assert status == 200 and json.loads(raw)["password"] == first
    assert _request(manager_server, "POST", "/api/oauth-password", {"action": "generate", "confirm": True})[0] == 200
    _, raw, _ = _request(manager_server, "POST", "/api/oauth-password", {"action": "reveal", "confirm": True})
    second = json.loads(raw)["password"]
    assert second != first and len(second) >= 12
    _, activity, _ = _request(manager_server, "GET", "/api/activity")
    activity_text = activity.decode()
    assert first not in activity_text and second not in activity_text


def test_local_mutations_validate_payload_and_protect_builtins(manager_server, monkeypatch) -> None:
    assert _request(manager_server, "POST", "/api/oauth-password", {"action": "set", "value": "B" * 16, "confirm": True, "command": "x"})[0] == 400
    assert _request(manager_server, "POST", "/api/components", {"operation": "create", "id": "../bad", "display_name": "Bad", "role": "custom_mcp", "endpoint": "http://127.0.0.1:1/mcp", "confirm": True})[0] == 400
    status, raw, _ = _request(manager_server, "POST", "/api/components", {"operation": "delete", "id": "serena", "confirm": True})
    assert status == 409 and json.loads(raw)["error"] == "builtin-component-protected"

    candidate = {"operation": "create", "id": "stage17-fake", "display_name": "Stage 17 Fake", "role": "custom_mcp", "endpoint": "http://127.0.0.1:9876/mcp", "confirm": True}
    for _ in range(2):
        status, raw, _ = _request(manager_server, "POST", "/api/components", candidate)
        body = json.loads(raw)
        assert status == 200 and body["route_applied"] is False and body["lifecycle_authority"] is False
    status, raw, _ = _request(manager_server, "POST", "/api/components", {"operation": "delete", "id": "stage17-fake", "confirm": True})
    assert status == 200 and json.loads(raw)["removed"] is True
    status, raw, _ = _request(manager_server, "POST", "/api/components", {"operation": "delete", "id": "stage17-fake", "confirm": True})
    assert status == 200 and json.loads(raw)["removed"] is False

    monkeypatch.setattr("webgpt_as_codex.manager.install_tailscale_with_winget", lambda *, confirm=False: {"ok": True, "status": "already-installed", "tailscale": {"installed": True, "ready": True, "version": "1.2.3"}})
    assert _request(manager_server, "POST", "/api/environment", {"operation": "install-tailscale", "confirm": False})[0] == 409
    assert _request(manager_server, "POST", "/api/environment", {"operation": "install-tailscale", "confirm": True})[0] == 200


def test_local_mutation_lock_and_control_header_fail_closed(manager_server) -> None:
    port = manager_server.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("POST", "/api/oauth-password", body="{}", headers={"Host": f"127.0.0.1:{port}", "Content-Type": "application/json"})
    assert conn.getresponse().status == 403

    assert manager_server.local_mutation_lock.acquire(blocking=False)
    try:
        status, raw, _ = _request(manager_server, "POST", "/api/oauth-password", {"action": "generate", "confirm": True})
        assert status == 409 and json.loads(raw)["error"] == "manager-mutation-busy"
    finally:
        manager_server.local_mutation_lock.release()


def test_local_endpoints_reject_cross_origin_and_oversize_body(manager_server) -> None:
    port = manager_server.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request(
        "POST",
        "/api/oauth-password",
        body=json.dumps({"action": "generate", "confirm": True}),
        headers={
            "Host": f"127.0.0.1:{port}",
            "Origin": "http://evil.example",
            "Content-Type": "application/json",
            "X-WebGPT-Control": "1",
        },
    )
    response = conn.getresponse()
    assert response.status == 403
    response.read()

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    oversized = "x" * 5000
    conn.request(
        "POST",
        "/api/oauth-password",
        body=oversized,
        headers={
            "Host": f"127.0.0.1:{port}",
            "Content-Type": "application/json",
            "Content-Length": str(len(oversized)),
            "X-WebGPT-Control": "1",
        },
    )
    response = conn.getresponse()
    raw = response.read()
    assert response.status == 400
    assert json.loads(raw)["error"] == "invalid-action-payload"


def test_local_endpoint_exception_text_is_sanitized(manager_server, monkeypatch) -> None:
    monkeypatch.setattr(
        "webgpt_as_codex.manager.regenerate_oauth_password",
        lambda: (_ for _ in ()).throw(RuntimeError("Bearer secret-do-not-leak")),
    )
    status, raw, _ = _request(
        manager_server,
        "POST",
        "/api/oauth-password",
        {"action": "generate", "confirm": True},
    )
    text = raw.decode()
    assert status == 500
    assert "secret-do-not-leak" not in text
    assert json.loads(text)["failure_type"] == "RuntimeError"


def test_desktop_launcher_defaults_to_chinese_manager() -> None:
    content = _launcher_content(open_browser=True)
    assert 'WEBGPT_CODEX_UI_LANG=zh-CN' in content
    assert "--open --start-all" in content


def test_previous_managed_launcher_can_upgrade_to_chinese_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    desktop = tmp_path / "Desktop"
    startup = tmp_path / "Startup"
    desktop.mkdir()
    startup.mkdir()
    monkeypatch.setenv("WEBGPT_CODEX_DESKTOP_DIR", str(desktop))
    monkeypatch.setenv("WEBGPT_CODEX_STARTUP_DIR", str(startup))

    old_desktop = launcher._legacy_launcher_content(open_browser=True)
    old_autostart = launcher._legacy_launcher_content(open_browser=False)
    (desktop / "WebGPT-as-Codex.cmd").write_text(
        old_desktop,
        encoding="utf-8",
        newline="",
    )
    (startup / "WebGPT-as-Codex-Autostart.cmd").write_text(
        old_autostart,
        encoding="utf-8",
        newline="",
    )

    before = launcher.desktop_launcher("status")
    assert before["managed"] is False and before["upgradeable"] is True
    assert launcher.desktop_launcher("install")["status"] == "updated"
    assert launcher.autostart("install")["status"] == "updated"
    assert launcher.desktop_launcher("status")["managed"] is True
    assert launcher.autostart("status")["managed"] is True
    assert "WEBGPT_CODEX_UI_LANG=zh-CN" in (
        desktop / "WebGPT-as-Codex.cmd"
    ).read_text(encoding="utf-8")
