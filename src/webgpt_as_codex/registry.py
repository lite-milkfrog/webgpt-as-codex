from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import ensure_state_dirs, repo_root


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


def _component_from_dict(data: dict[str, Any]) -> Component:
    required = {"id", "display_name", "role", "required", "enabled_by_default", "transport"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"component manifest missing: {', '.join(missing)}")
    return Component(
        id=data["id"],
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
    roots = [repo_root() / "components", ensure_state_dirs() / "config" / "components"]
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            component = _component_from_dict(data)
            components[component.id] = component
    return components


def write_custom_component(data: dict[str, Any]) -> Path:
    component = _component_from_dict(data)
    if any(k in data for k in ("password", "token", "secret", "bearer_token")):
        raise ValueError("credential literals are forbidden; use environment/credential references")
    root = ensure_state_dirs() / "config" / "components"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{component.id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def cli_add_mcp(argv: list[str]) -> int:
    from .onboarding import cli_add_mcp as run
    return run(argv)
