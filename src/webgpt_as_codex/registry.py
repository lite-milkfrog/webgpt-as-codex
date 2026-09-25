from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .paths import ensure_state_dirs, resource_root
from .stateio import atomic_write_json

_SECRET_KEY_RE = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|authorization|cookie|private[_-]?key)"
)
_COMPONENT_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_CUSTOM_COMPONENT_KEYS = {
    "id",
    "display_name",
    "role",
    "required",
    "enabled_by_default",
    "transport",
    "default_endpoint",
    "safe_tool",
    "upstream",
    "ownership_mode",
    "startup_priority",
    "dependencies",
    "readiness_contract",
    "gateway_exposure",
    "refresh_registration",
    "process_contains",
    "safe_tool_args",
}
_OWNERSHIP_MODES = {"wac_owned", "external_local", "remote_connector", "gateway_only"}


@dataclass(frozen=True)
class Component:
    id: str
    display_name: str
    role: str
    required: bool
    enabled_by_default: bool
    transport: str
    default_endpoint: str | None
    raw: dict[str, Any]


def _component_from_dict(data: dict[str, Any], *, custom: bool = False) -> Component:
    required = {"id", "display_name", "role", "required", "enabled_by_default", "transport"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"component manifest missing: {', '.join(missing)}")
    cid = data["id"]
    if not isinstance(cid, str) or not _COMPONENT_ID_RE.fullmatch(cid):
        raise ValueError("component id must be lowercase kebab-case")
    for field in ("display_name", "role", "transport"):
        value = data[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise ValueError(f"{field} must be a non-empty string up to 128 characters")
    if not isinstance(data["required"], bool) or not isinstance(data["enabled_by_default"], bool):
        raise TypeError("required and enabled_by_default must be booleans")
    endpoint = data.get("default_endpoint")
    if endpoint is not None and not isinstance(endpoint, str):
        raise TypeError("default_endpoint must be a string or null")
    ownership_mode = data.get("ownership_mode")
    if ownership_mode is not None and ownership_mode not in _OWNERSHIP_MODES:
        raise ValueError("ownership_mode is invalid")
    startup_priority = data.get("startup_priority")
    if startup_priority is not None and (
        isinstance(startup_priority, bool)
        or not isinstance(startup_priority, int)
        or not 0 <= startup_priority <= 1000
    ):
        raise ValueError("startup_priority must be an integer from 0 to 1000")
    dependencies = data.get("dependencies")
    if dependencies is not None and (
        not isinstance(dependencies, list)
        or any(not isinstance(value, str) or not _COMPONENT_ID_RE.fullmatch(value) for value in dependencies)
    ):
        raise ValueError("dependencies must contain component ids")
    if data.get("refresh_registration") not in (None, True, False):
        raise ValueError("refresh_registration must be boolean")
    if custom:
        unknown = sorted(set(data) - _CUSTOM_COMPONENT_KEYS)
        if unknown:
            raise ValueError("custom component contains unsupported fields: " + ", ".join(unknown))
        if data["transport"] != "streamable_http":
            raise ValueError("custom components require streamable_http")
        if not endpoint or len(endpoint) > 2048:
            raise ValueError("custom component requires a bounded endpoint")
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("custom component endpoint is not credential-free http(s)")
        if data.get("safe_tool") is not None:
            raise ValueError("custom component safe_tool requires repository review")
    return Component(
        id=cid,
        display_name=data["display_name"],
        role=data["role"],
        required=bool(data["required"]),
        enabled_by_default=bool(data["enabled_by_default"]),
        transport=data["transport"],
        default_endpoint=data.get("default_endpoint"),
        raw=data,
    )


def load_components() -> dict[str, Component]:
    components: dict[str, Component] = {}
    builtin_root = resource_root() / "components"
    for path in sorted(builtin_root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        component = _component_from_dict(data)
        if component.id != path.stem:
            raise ValueError(f"builtin component id/path mismatch: {path.name}")
        if component.id in components:
            raise ValueError(f"duplicate builtin component id: {component.id}")
        components[component.id] = component

    custom_root = ensure_state_dirs() / "config" / "components"
    if custom_root.exists():
        for path in sorted(custom_root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                component = _component_from_dict(data, custom=True)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
            if component.id != path.stem or component.id in components:
                continue
            components[component.id] = component
    return components


def _credential_paths(value: Any, path: str = "$") -> list[str]:
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
            hits.extend(_credential_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_credential_paths(child, f"{path}[{index}]"))
    return hits


def write_custom_component(data: dict[str, Any]) -> Path:
    component = _component_from_dict(data, custom=True)
    secrets = _credential_paths(data)
    if secrets:
        raise ValueError(
            "credential literals are forbidden; use environment/credential references: "
            + ", ".join(secrets)
        )
    if (resource_root() / "components" / f"{component.id}.json").exists():
        raise ValueError("custom component cannot shadow a public registry component")
    root = ensure_state_dirs() / "config" / "components"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{component.id}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != data:
            raise ValueError("custom component already exists with different content")
        return path
    atomic_write_json(path, data)
    return path


def delete_custom_component(component_id: str) -> bool:
    if not isinstance(component_id, str) or not _COMPONENT_ID_RE.fullmatch(component_id):
        raise ValueError("component id must be lowercase kebab-case")
    if (resource_root() / "components" / f"{component_id}.json").exists():
        raise ValueError("builtin component cannot be deleted")
    path = ensure_state_dirs() / "config" / "components" / f"{component_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def cli_add_mcp(argv: list[str]) -> int:
    from .onboarding import cli_add_mcp as run
    return run(argv)
