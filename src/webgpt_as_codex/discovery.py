from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from .paths import state_root
from .registry import Component


def process_snapshot() -> list[str] | None:
    try:
        if os.name == "nt":
            command = (
                "Get-CimInstance Win32_Process | "
                "ForEach-Object { ($_.Name + ' ' + [string]$_.CommandLine) }"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                check=False,
            )
        else:
            result = subprocess.run(
                ["ps", "-eo", "comm=,args="],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                check=False,
            )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    return [line.lower() for line in result.stdout.splitlines() if line.strip()]


def process_markers(component: Component) -> list[str]:
    configured = component.raw.get("process_contains")
    if isinstance(configured, list):
        values = [str(value).strip().lower() for value in configured if str(value).strip()]
        if values:
            return values
    command = component.raw.get("version_command") or []
    if command and str(command[0]).lower() not in {"npx", "npm"}:
        return [Path(str(command[0])).stem.lower()]
    return []


def process_health(component: Component, snapshot: list[str] | None) -> bool | None:
    markers = process_markers(component)
    if not markers or snapshot is None:
        return None
    return any(all(marker in row for marker in markers) for row in snapshot)


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
