import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError

import pytest

from webgpt_as_codex import doctor
from webgpt_as_codex.health import ManagerStatusService
from webgpt_as_codex.mcp import McpResponse
from webgpt_as_codex.onboarding import (
    CapabilityEvidence,
    apply_onboarding_plan,
    build_onboarding_plan,
    build_operating_guide,
    discover_mcp_capabilities,
    validate_onboarding_manifest,
    validate_operating_guide,
)
from webgpt_as_codex.registry import Component, load_components
from webgpt_as_codex.runtime import MANAGER_RESTARTABLE


def _component(endpoint: str = "http://127.0.0.1:9999/mcp") -> Component:
    raw = {
        "id": "fake-mcp",
        "display_name": "Fake MCP",
        "role": "optional",
        "required": False,
        "enabled_by_default": True,
        "transport": "streamable_http",
        "default_endpoint": endpoint,
    }
    return Component(
        id=raw["id"],
        display_name=raw["display_name"],
        role=raw["role"],
        required=False,
        enabled_by_default=True,
        transport=raw["transport"],
        default_endpoint=endpoint,
        raw=raw,
    )


def _manifest(endpoint: str = "http://127.0.0.1:9999/mcp") -> dict:
    return dict(_component(endpoint).raw)


def test_public_components_attach_portable_operating_guides() -> None:
    root = Path(__file__).resolve().parents[1]
    components = load_components()
    for component_id in ("serena", "coding-tools"):
        guide_rel = components[component_id].raw["operating_guide"]
        guide_path = root / guide_rel
        assert guide_path.is_file()
        text = guide_path.read_text(encoding="utf-8")
        assert "Mental model" in text
        assert "Actual exposed capability evidence" in text


def test_operating_guide_schema_covers_required_sections() -> None:
    evidence = CapabilityEvidence(
        "success",
        "ok",
        "ok",
        1,
        {"name": "fake", "version": "1.0"},
        [{"name": "search", "input_schema": {"type": "object"}}],
    )
    guide = build_operating_guide(_component(), evidence)
    validate_operating_guide(guide)
    for key in (
        "mental_model",
        "best_use_cases",
        "poor_use_cases",
        "capability_evidence",
        "goal_oriented_patterns",
        "common_mistakes",
        "failure_diagnosis",
        "verification_signals",
        "performance_cost_notes",
        "accumulated_lessons",
        "better_alternatives",
    ):
        assert key in guide


def test_manifest_rejects_nested_secret_literals() -> None:
    data = _manifest()
    data["headers"] = {"Authorization": "Bearer should-not-persist"}
    with pytest.raises(ValueError, match="credential literals"):
        validate_onboarding_manifest(data)


def test_guide_rejects_secret_bearing_schema() -> None:
    evidence = CapabilityEvidence(
        "success",
        "ok",
        "ok",
        1,
        {},
        [{"name": "bad", "input_schema": {"default": "Bearer should-not-persist"}}],
    )
    guide = build_operating_guide(_component(), evidence)
    with pytest.raises(ValueError, match="secret-bearing"):
        validate_operating_guide(guide)


def test_bounded_fake_mcp_exercises_real_http_initialize_and_tools_list() -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            if request["method"] == "initialize":
                result = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "serverInfo": {"name": "bounded-fake", "version": "1.0"},
                    },
                }
                session = "fake-session"
            elif request["method"] == "tools/list":
                result = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "echo",
                                "description": "Return bounded test input",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"text": {"type": "string"}},
                                },
                            }
                        ]
                    },
                }
                session = None
            else:
                self.send_response(404)
                self.end_headers()
                return
            payload = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            if session:
                self.send_header("Mcp-Session-Id", session)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/mcp"
        evidence = discover_mcp_capabilities(_component(url))
        assert evidence.status == "success"
        assert evidence.tool_count == 1
        assert evidence.tools[0]["name"] == "echo"
        assert evidence.tools[0]["input_schema"]["properties"]["text"]["type"] == "string"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_capability_discovery_uses_actual_initialize_and_tools_list(monkeypatch) -> None:
    def fake_initialize(_url):
        return McpResponse(
            200,
            {"Mcp-Session-Id": "s1"},
            {"result": {"serverInfo": {"name": "fake", "version": "1"}}},
        )

    def fake_rpc(_url, method, **_kwargs):
        assert method == "tools/list"
        return McpResponse(
            200,
            {},
            {
                "result": {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search things",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"q": {"type": "string"}},
                            },
                        }
                    ]
                }
            },
        )

    monkeypatch.setattr("webgpt_as_codex.onboarding.initialize", fake_initialize)
    monkeypatch.setattr("webgpt_as_codex.onboarding.rpc", fake_rpc)
    evidence = discover_mcp_capabilities(_component())
    assert evidence.status == "success"
    assert evidence.tool_count == 1
    assert evidence.tools[0]["name"] == "search"
    assert evidence.tools[0]["input_schema"]["properties"]["q"]["type"] == "string"


def test_capability_discovery_marks_unavailable_separately(monkeypatch) -> None:
    def unavailable(_url):
        raise URLError("down")

    monkeypatch.setattr("webgpt_as_codex.onboarding.initialize", unavailable)
    evidence = discover_mcp_capabilities(_component())
    assert evidence.status == "unavailable"
    assert evidence.initialize == "unavailable"
    assert evidence.tools_list == "unattempted"


def test_capability_discovery_marks_malformed_tools_list_failed(monkeypatch) -> None:
    monkeypatch.setattr(
        "webgpt_as_codex.onboarding.initialize",
        lambda _url: McpResponse(200, {}, {"result": {"serverInfo": {"name": "fake"}}}),
    )
    monkeypatch.setattr(
        "webgpt_as_codex.onboarding.rpc",
        lambda *_args, **_kwargs: McpResponse(200, {}, {"result": {"tools": "not-a-list"}}),
    )
    evidence = discover_mcp_capabilities(_component())
    assert evidence.status == "failed"
    assert evidence.initialize == "ok"
    assert evidence.tools_list == "failed"
    assert evidence.reason == "malformed-tools-list"


def test_dry_run_does_not_persist_and_apply_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "webgpt_as_codex.onboarding.discover_mcp_capabilities",
        lambda _component: CapabilityEvidence(
            "success",
            "ok",
            "ok",
            1,
            {"name": "fake"},
            [{"name": "search", "input_schema": {"type": "object"}}],
        ),
    )
    plan = build_onboarding_plan(_manifest())
    assert plan["mutation"] == "none-until-explicit-apply"
    assert not (tmp_path / "config" / "components" / "fake-mcp.json").exists()

    first = apply_onboarding_plan(plan)
    second = apply_onboarding_plan(plan)
    assert first == second
    assert Path(first["component_path"]).is_file()
    assert Path(first["guide_path"]).is_file()
    assert Path(first["inventory_path"]).is_file()

    components = load_components()
    assert "fake-mcp" in components
    assert "fake-mcp" not in MANAGER_RESTARTABLE

    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*.json")
    ).lower()
    assert "should-not-persist" not in persisted


def test_new_component_is_visible_to_manager_and_doctor_without_restart_authority(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "webgpt_as_codex.onboarding.discover_mcp_capabilities",
        lambda _component: CapabilityEvidence("unavailable", "unavailable", "unattempted", None, {}, [], "down"),
    )
    apply_onboarding_plan(build_onboarding_plan(_manifest()))

    manager = ManagerStatusService(cache_ttl_seconds=1).snapshot(force=True)
    assert any(row["id"] == "fake-mcp" for row in manager["components"])
    assert "fake-mcp" not in MANAGER_RESTARTABLE

    def fake_check(component, _process_rows, _remote_health, _remote_evidence):
        return {
            "id": component.id,
            "display_name": component.display_name,
            "required": component.required,
            "version": None,
            "version_source": "unknown",
            "health": {
                "process": None,
                "listener": False if component.id == "fake-mcp" else None,
                "protocol": None,
                "safe_call": None,
                "oauth": None,
                "remote": None,
            },
            "evidence": {},
        }

    monkeypatch.setattr(doctor, "_check_component", fake_check)
    result = doctor.run_doctor(include_remote=False, persist=False)
    assert "fake-mcp" in result["components"]
    assert result["components"]["fake-mcp"]["health"]["listener"] is False


def test_duplicate_id_with_different_manifest_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "webgpt_as_codex.onboarding.discover_mcp_capabilities",
        lambda _component: CapabilityEvidence("unavailable", "unavailable", "unattempted", None, {}, [], "down"),
    )
    first = build_onboarding_plan(_manifest("http://127.0.0.1:9999/mcp"))
    apply_onboarding_plan(first)
    second = build_onboarding_plan(_manifest("http://127.0.0.1:9998/mcp"))
    with pytest.raises(ValueError, match="different manifest"):
        apply_onboarding_plan(second)


def test_builtin_component_id_cannot_be_shadowed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    data = _manifest()
    data["id"] = "serena"
    data["display_name"] = "Serena override"
    monkeypatch.setattr(
        "webgpt_as_codex.onboarding.discover_mcp_capabilities",
        lambda _component: CapabilityEvidence("unavailable", "unavailable", "unattempted", None, {}, [], "down"),
    )
    plan = build_onboarding_plan(data)
    with pytest.raises(ValueError, match="public registry"):
        apply_onboarding_plan(plan)


def test_routing_is_attached_to_inventory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "webgpt_as_codex.onboarding.discover_mcp_capabilities",
        lambda _component: CapabilityEvidence(
            "success",
            "ok",
            "ok",
            2,
            {},
            [{"name": "alpha"}, {"name": "beta"}],
        ),
    )
    plan = build_onboarding_plan(_manifest())
    result = apply_onboarding_plan(plan)
    inventory = json.loads(Path(result["inventory_path"]).read_text(encoding="utf-8"))
    assert inventory["machine_local"] is True
    assert inventory["routing"]["basis"] == "actual-tools-list"
    assert inventory["routing"]["tool_names"] == ["alpha", "beta"]
