import json
from pathlib import Path

from webgpt_as_codex.discovery import discover_all
from webgpt_as_codex.registry import load_components

ROOT = Path(__file__).resolve().parents[1]


def test_builtin_component_manifests_load() -> None:
    components = load_components()
    for cid in ("serena", "coding-tools", "playwright", "windows-mcp", "mcpjungle", "mcp-auth-proxy", "tailscale"):
        assert cid in components


def test_component_ids_match_filenames() -> None:
    for path in (ROOT / "components").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert path.stem == data["id"]


def test_discovery_has_distinct_health_levels() -> None:
    result = discover_all(load_components())
    row = result["serena"]
    assert "listener_up" in row
    assert "protocol_healthy" in row
    assert row["protocol_healthy"] is None


def test_serena_health_probe_does_not_require_active_project() -> None:
    serena = load_components()["serena"]
    assert serena.raw.get("safe_tool") is None


def test_manifests_contain_no_credential_literals() -> None:
    text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "components").glob("*.json")).lower()
    for marker in ('"password":', '"bearer_token":', '"access_token":', '"refresh_token":'):
        assert marker not in text
