from __future__ import annotations

import ipaddress
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .discovery import discover_component
from .paths import ensure_state_dirs
from .registry import Component, load_components

HEALTH_LEVELS = ("process", "listener", "protocol", "safe_call", "oauth", "remote")
_SECRET_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "cookie",
    "authorization",
    "bearer",
    "private_key",
    "private-key",
)
_BEARER_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|token|secret|cookie|authorization|private[_-]?key)\b"
    r"(\s*[:=]\s*)([^\s,;]+)"
)


def _is_private_host(host: str | None) -> bool:
    if not host:
        return True
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def safe_url_for_output(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return "[redacted-url]"
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return value
    if _is_private_host(parts.hostname):
        return "[private-url]"
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def redact_text(value: str) -> str:
    text = _BEARER_RE.sub(r"\1[redacted]", value)
    text = _ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted]", text)
    return _URL_RE.sub(lambda match: safe_url_for_output(match.group(0)), text)


def sanitize_for_output(value: Any, *, key: str = "") -> Any:
    lowered = key.lower()
    if any(marker in lowered for marker in _SECRET_KEY_PARTS):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(k): sanitize_for_output(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_for_output(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_output(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def configured_public_mcp_url(config: dict[str, Any]) -> str | None:
    raw = config.get("public_mcp_url")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parts = urlsplit(raw.strip())
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname or _is_private_host(parts.hostname):
        return None
    if parts.username or parts.password or parts.query or parts.fragment:
        return None
    return safe_url_for_output(raw.strip())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _manifest_version(component: Component) -> tuple[str | None, str]:
    raw = component.raw
    for key in ("verified_release", "verified_local_binary", "version"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), f"manifest:{key}"
    strategy = raw.get("version_strategy")
    if isinstance(strategy, str) and strategy.strip():
        return strategy.strip(), "manifest:version_strategy"
    return None, "unknown"


def _doctor_component(doctor: dict[str, Any], component_id: str) -> dict[str, Any]:
    components = doctor.get("components")
    if not isinstance(components, dict):
        return {}
    row = components.get(component_id)
    return row if isinstance(row, dict) else {}


def _health_from_doctor(row: dict[str, Any]) -> dict[str, bool | None]:
    health = {name: None for name in HEALTH_LEVELS}
    source = row.get("health")
    if not isinstance(source, dict):
        return health
    for name in HEALTH_LEVELS:
        value = source.get(name)
        if value is None or isinstance(value, bool):
            health[name] = value
    return health


def _component_row(component: Component, doctor: dict[str, Any]) -> dict[str, Any]:
    discovered = discover_component(component)
    doctor_row = _doctor_component(doctor, component.id)
    health = _health_from_doctor(doctor_row)
    health["listener"] = discovered.get("listener_up")
    version = doctor_row.get("version")
    version_source = "doctor"
    if not isinstance(version, str) or not version.strip():
        version, version_source = _manifest_version(component)
    return {
        "id": component.id,
        "display_name": component.display_name,
        "role": component.role,
        "required": component.required,
        "enabled_by_default": component.enabled_by_default,
        "transport": component.transport,
        "installed": discovered.get("installed_by_path"),
        "version": sanitize_for_output(version) if version else None,
        "version_source": version_source,
        "health": health,
    }


def _plane_summary(components: list[dict[str, Any]], component_id: str) -> dict[str, Any]:
    row = next((item for item in components if item["id"] == component_id), None)
    if row is None:
        return {"configured": False, "health": {name: None for name in HEALTH_LEVELS}}
    return {"configured": True, "version": row["version"], "health": row["health"]}


def _doctor_summary(doctor: dict[str, Any]) -> dict[str, Any]:
    if not doctor:
        return {"available": False, "status": "never-run"}
    return sanitize_for_output(
        {
            "available": True,
            "status": doctor.get("status", "unknown"),
            "completed_at": doctor.get("completed_at"),
            "summary": doctor.get("summary"),
            "checks": doctor.get("checks", {}),
        }
    )


class ManagerStatusService:
    def __init__(self, *, cache_ttl_seconds: float = 5.0) -> None:
        self.cache_ttl_seconds = max(1.0, cache_ttl_seconds)
        self._cached_at = 0.0
        self._cached: dict[str, Any] | None = None
        self._cache_lock = threading.Lock()

    def snapshot(self, *, force: bool = False) -> dict[str, Any]:
        with self._cache_lock:
            now = time.monotonic()
            if not force and self._cached is not None and now - self._cached_at < self.cache_ttl_seconds:
                return self._cached

            state = ensure_state_dirs()
            config = _read_json(state / "config" / "manager.json")
            doctor = _read_json(state / "doctor" / "last-result.json")
            registry = load_components()
            with ThreadPoolExecutor(max_workers=min(8, max(1, len(registry)))) as pool:
                rows = list(pool.map(lambda item: _component_row(item, doctor), registry.values()))
            rows.sort(key=lambda item: (not item["required"], item["display_name"].lower()))

            result = {
                "generated_at": time.time(),
                "poll_after_ms": int(self.cache_ttl_seconds * 1000),
                "components": rows,
                "gateway": _plane_summary(rows, "mcpjungle"),
                "oauth": _plane_summary(rows, "mcp-auth-proxy"),
                "tailscale": _plane_summary(rows, "tailscale"),
                "remote_desktop_commander": _plane_summary(rows, "remote-desktop-commander"),
                "public_mcp_url": configured_public_mcp_url(config),
                "last_doctor": _doctor_summary(doctor),
                "health_levels": list(HEALTH_LEVELS),
            }
            self._cached = sanitize_for_output(result)
            self._cached_at = now
            return self._cached
