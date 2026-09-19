from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from .mcp import initialize, rpc, session_id
from .paths import ensure_state_dirs, repo_root
from .registry import Component, write_custom_component

GUIDE_SCHEMA_VERSION = 1
_SECRET_KEY_RE = re.compile(r"(?i)(password|secret|token|api[_-]?key|authorization|cookie|private[_-]?key)")
_SECRET_VALUE_RE = re.compile(r"(?i)\b(bearer\s+[A-Za-z0-9._~+/=-]{8,}|sk-[A-Za-z0-9_-]{8,})\b")


@dataclass(frozen=True)
class CapabilityEvidence:
    status: str
    initialize: str
    tools_list: str
    tool_count: int | None
    server_info: dict[str, Any]
    tools: list[dict[str, Any]]
    reason: str | None = None


def _secret_paths(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if (
                _SECRET_KEY_RE.search(str(key))
                and not isinstance(child, (dict, list))
                and child not in (None, "", False)
            ):
                hits.append(child_path)
            hits.extend(_secret_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_secret_paths(child, f"{path}[{index}]"))
    elif isinstance(value, str) and _SECRET_VALUE_RE.search(value):
        hits.append(path)
    return hits


def validate_onboarding_manifest(data: dict[str, Any]) -> None:
    required = {"id", "display_name", "role", "required", "enabled_by_default", "transport", "default_endpoint"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"component manifest missing: {', '.join(missing)}")
    cid = str(data["id"])
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", cid):
        raise ValueError("component id must be lowercase kebab-case")
    if data["transport"] != "streamable_http":
        raise ValueError("generic onboarding currently requires streamable_http")
    endpoint = data.get("default_endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
        raise ValueError("default_endpoint must be an http(s) MCP endpoint")
    secrets = _secret_paths(data)
    if secrets:
        raise ValueError("credential literals are forbidden: " + ", ".join(secrets))


def _portable_tool(tool: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"name": str(tool.get("name", ""))}
    description = tool.get("description")
    if isinstance(description, str) and description.strip():
        result["description"] = description.strip()
    schema = tool.get("inputSchema")
    if isinstance(schema, dict):
        result["input_schema"] = schema
    return result


def discover_mcp_capabilities(component: Component, *, timeout: float = 8.0) -> CapabilityEvidence:
    if component.transport != "streamable_http" or not component.default_endpoint:
        return CapabilityEvidence("unattempted", "unattempted", "unattempted", None, {}, [], "unsupported-transport")
    try:
        initialized = initialize(component.default_endpoint)
        if initialized.status != 200 or not isinstance(initialized.body.get("result"), dict):
            return CapabilityEvidence("failed", "failed", "unattempted", None, {}, [], "malformed-initialize")
        result = initialized.body["result"]
        sid = session_id(initialized)
        listed = rpc(component.default_endpoint, "tools/list", request_id=2, session_id=sid, timeout=timeout)
        tools = listed.body.get("result", {}).get("tools")
        if listed.status != 200 or not isinstance(tools, list) or not all(isinstance(item, dict) for item in tools):
            return CapabilityEvidence("failed", "ok", "failed", None, result.get("serverInfo") or {}, [], "malformed-tools-list")
        portable = [_portable_tool(item) for item in tools]
        return CapabilityEvidence("success", "ok", "ok", len(portable), result.get("serverInfo") or {}, portable)
    except (ConnectionError, TimeoutError, OSError, HTTPError, URLError) as exc:
        return CapabilityEvidence("unavailable", "unavailable", "unattempted", None, {}, [], type(exc).__name__)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return CapabilityEvidence("failed", "failed", "unattempted", None, {}, [], type(exc).__name__)


def build_operating_guide(component: Component, evidence: CapabilityEvidence) -> dict[str, Any]:
    return {
        "schema_version": GUIDE_SCHEMA_VERSION,
        "component_id": component.id,
        "mental_model": f"{component.display_name} is an MCP capability provider; route by exposed schema, not by name.",
        "best_use_cases": [],
        "poor_use_cases": [],
        "capability_evidence": {
            "status": evidence.status,
            "initialize": evidence.initialize,
            "tools_list": evidence.tools_list,
            "tool_count": evidence.tool_count,
            "server_info": evidence.server_info,
            "tools": evidence.tools,
            "reason": evidence.reason,
        },
        "goal_oriented_patterns": [],
        "common_mistakes": [
            "Inferring capability from server or tool names without inspecting schema.",
            "Treating one failed call as proof that the MCP is unavailable.",
        ],
        "failure_diagnosis": [
            "Separate transport/listener failure from initialize failure and tools/list schema failure.",
            "Verify session, authentication, binding and post-state before fallback.",
        ],
        "verification_signals": ["initialize succeeds", "tools/list returns a schema-valid tool list"],
        "performance_cost_notes": [],
        "accumulated_lessons": [],
        "better_alternatives": [],
    }


def validate_operating_guide(guide: dict[str, Any]) -> None:
    required = {
        "schema_version", "component_id", "mental_model", "best_use_cases", "poor_use_cases",
        "capability_evidence", "goal_oriented_patterns", "common_mistakes", "failure_diagnosis",
        "verification_signals", "performance_cost_notes", "accumulated_lessons", "better_alternatives",
    }
    missing = sorted(required - guide.keys())
    if missing:
        raise ValueError("Operating Guide missing: " + ", ".join(missing))
    if guide["schema_version"] != GUIDE_SCHEMA_VERSION:
        raise ValueError("unsupported Operating Guide schema version")
    secrets = _secret_paths(guide)
    if secrets:
        raise ValueError("Operating Guide contains secret-bearing data: " + ", ".join(secrets))


def routing_recommendation(component: Component, evidence: CapabilityEvidence) -> dict[str, Any]:
    names = [tool.get("name") for tool in evidence.tools if tool.get("name")]
    return {
        "component_id": component.id,
        "role": component.role,
        "status": "recommend-review" if evidence.status == "success" else "defer-until-capability-evidence",
        "basis": "actual-tools-list" if evidence.status == "success" else evidence.status,
        "tool_names": names,
    }


def _state_paths(component_id: str) -> tuple[Path, Path]:
    root = ensure_state_dirs()
    guide = root / "config" / "mcp-guides" / f"{component_id}.json"
    inventory = root / "config" / "mcp-onboarding" / f"{component_id}.json"
    guide.parent.mkdir(parents=True, exist_ok=True)
    inventory.parent.mkdir(parents=True, exist_ok=True)
    return guide, inventory


def build_onboarding_plan(data: dict[str, Any]) -> dict[str, Any]:
    validate_onboarding_manifest(data)
    component = Component(
        id=data["id"], display_name=data["display_name"], role=data["role"],
        required=bool(data["required"]), enabled_by_default=bool(data["enabled_by_default"]),
        transport=data["transport"], default_endpoint=data["default_endpoint"], raw=data,
    )
    evidence = discover_mcp_capabilities(component)
    guide = build_operating_guide(component, evidence)
    validate_operating_guide(guide)
    routing = routing_recommendation(component, evidence)
    return {
        "component": data,
        "capability_evidence": asdict(evidence),
        "guide": guide,
        "routing": routing,
        "mutation": "none-until-explicit-apply",
    }


def apply_onboarding_plan(plan: dict[str, Any]) -> dict[str, Any]:
    data = dict(plan["component"])
    validate_onboarding_manifest(data)
    guide = dict(plan["guide"])
    validate_operating_guide(guide)
    builtin_path = repo_root() / "components" / f"{data['id']}.json"
    custom_path = ensure_state_dirs() / "config" / "components" / f"{data['id']}.json"
    if builtin_path.exists():
        raise ValueError("component id already exists in public registry; update that component instead")
    if custom_path.exists():
        existing = json.loads(custom_path.read_text(encoding="utf-8"))
        if existing != data:
            raise ValueError("component id already onboarded with a different manifest")
    component_path = write_custom_component(data)
    guide_path, inventory_path = _state_paths(data["id"])
    guide_path.write_text(json.dumps(guide, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inventory_payload = {
        "component_id": data["id"],
        "capability_status": plan["capability_evidence"]["status"],
        "routing": plan["routing"],
        "guide_path": str(guide_path),
        "machine_local": True,
    }
    inventory_path.write_text(json.dumps(inventory_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "component_path": str(component_path),
        "guide_path": str(guide_path),
        "inventory_path": str(inventory_path),
        "capability_status": plan["capability_evidence"]["status"],
    }


def cli_add_mcp(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex add-mcp")
    parser.add_argument("name")
    parser.add_argument("url")
    parser.add_argument("--role", default="optional")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    data = {
        "id": args.name,
        "display_name": args.name,
        "role": args.role,
        "required": False,
        "enabled_by_default": True,
        "transport": "streamable_http",
        "default_endpoint": args.url,
        "safe_tool": None,
        "upstream": None,
    }
    plan = build_onboarding_plan(data)
    result = {"mode": "apply" if args.apply else "dry-run", "plan": plan}
    if args.apply:
        result["applied"] = apply_onboarding_plan(plan)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
