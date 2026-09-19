from __future__ import annotations

import shutil
import socket
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from .paths import state_root
from .registry import Component


def _listener(endpoint: str | None, timeout: float = 0.35) -> bool | None:
    if not endpoint:
        return None
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except OSError:
        return False


def discover_component(component: Component) -> dict:
    version_command = component.raw.get("version_command") or []
    executable = version_command[0] if version_command else None
    executable_path = shutil.which(executable) if executable else None
    machine_binary = component.raw.get("machine_binary")
    machine_binary_path: Path | None = None
    if isinstance(machine_binary, str) and machine_binary.strip():
        relative = Path(machine_binary)
        if not relative.is_absolute() and ".." not in relative.parts:
            candidate = state_root() / relative
            machine_binary_path = candidate if candidate.is_file() else None
    if executable is not None or machine_binary is not None:
        installed = bool(executable_path or machine_binary_path)
    else:
        installed = None
    return {
        **asdict(component),
        "executable": executable,
        "executable_path": executable_path,
        "machine_binary_path": str(machine_binary_path) if machine_binary_path else None,
        "installed_by_path": installed,
        "listener_up": _listener(component.default_endpoint),
        "protocol_healthy": None,
        "safe_call_healthy": None,
    }


def discover_all(components: dict[str, Component]) -> dict[str, dict]:
    return {cid: discover_component(c) for cid, c in components.items()}
