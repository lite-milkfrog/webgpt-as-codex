from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .edge import auth_proxy_binary
from .gateway import mcpjungle_binary

MIN_PYTHON = (3, 11)
TAILSCALE_MIN_VERSION = (1, 38, 3)
TAILSCALE_WINGET_ID = "Tailscale.Tailscale"


def _run(command: list[str], *, timeout: float = 20.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _version_tuple(value: str) -> tuple[int, ...]:
    head = value.strip().splitlines()[0].strip() if value.strip() else ""
    parts: list[int] = []
    for token in head.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _tailscale_path() -> Path | None:
    override = os.getenv("WEBGPT_CODEX_TAILSCALE")
    if override:
        candidate = Path(override)
        return candidate if candidate.is_file() else None
    found = shutil.which("tailscale")
    if found:
        return Path(found)
    if os.name == "nt":
        for raw in (
            r"C:\Program Files\Tailscale\tailscale.exe",
            r"C:\Program Files (x86)\Tailscale\tailscale.exe",
        ):
            candidate = Path(raw)
            if candidate.is_file():
                return candidate
    return None


def python_environment() -> dict[str, Any]:
    current = tuple(sys.version_info[:3])
    return {
        "ok": current >= MIN_PYTHON,
        "version": ".".join(str(part) for part in current),
        "minimum": ".".join(str(part) for part in MIN_PYTHON),
        "executable": sys.executable,
    }


def windows_environment() -> dict[str, Any]:
    release = platform.release()
    version = platform.version()
    is_windows = os.name == "nt"
    return {
        "ok": is_windows,
        "platform": platform.system(),
        "release": release,
        "version": version,
        "reason": None if is_windows else "current production bootstrap targets Windows",
    }


def winget_environment() -> dict[str, Any]:
    path = shutil.which("winget") if os.name == "nt" else None
    if not path:
        return {"available": False, "path": None, "version": None}
    try:
        result = _run([path, "--version"], timeout=10)
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "path": path, "version": None}
    return {
        "available": result.returncode == 0,
        "path": path,
        "version": (result.stdout or result.stderr).strip() or None,
    }


def tailscale_environment() -> dict[str, Any]:
    path = _tailscale_path()
    if path is None:
        return {
            "installed": False,
            "path": None,
            "version": None,
            "version_ok": False,
            "backend_state": None,
            "online": False,
            "dns_name": None,
            "magic_dns_suffix": None,
            "funnel_cli_ok": False,
            "funnel_policy": "unknown",
            "ready": False,
            "next_action": "install",
        }

    version: str | None = None
    version_ok = False
    try:
        version_result = _run([str(path), "version"], timeout=10)
        if version_result.returncode == 0:
            version = version_result.stdout.strip().splitlines()[0] or None
            version_ok = _version_tuple(version or "") >= TAILSCALE_MIN_VERSION
    except (OSError, subprocess.SubprocessError):
        pass

    backend_state = None
    online = False
    dns_name = None
    magic_dns_suffix = None
    status_error = None
    try:
        status_result = _run([str(path), "status", "--json"], timeout=15)
        if status_result.returncode == 0:
            status = json.loads(status_result.stdout)
            if isinstance(status, dict):
                backend_state = status.get("BackendState")
                magic_dns_suffix = status.get("MagicDNSSuffix")
                self_row = status.get("Self")
                if isinstance(self_row, dict):
                    online = bool(self_row.get("Online"))
                    dns_name = str(self_row.get("DNSName") or "").rstrip(".") or None
        else:
            status_error = (status_result.stderr or status_result.stdout).strip() or "status failed"
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        status_error = type(exc).__name__

    funnel_cli_ok = False
    funnel_policy = "unknown"
    funnel_error = None
    try:
        funnel_result = _run([str(path), "funnel", "status", "--json"], timeout=15)
        if funnel_result.returncode == 0:
            funnel_cli_ok = True
            try:
                funnel = json.loads(funnel_result.stdout or "{}")
            except json.JSONDecodeError:
                funnel = {}
            allow = funnel.get("AllowFunnel") if isinstance(funnel, dict) else None
            funnel_policy = "verified-configured" if isinstance(allow, dict) and bool(allow) else "available-unverified"
        else:
            funnel_error = (funnel_result.stderr or funnel_result.stdout).strip() or "funnel status failed"
    except (OSError, subprocess.SubprocessError) as exc:
        funnel_error = type(exc).__name__

    ready = bool(
        version_ok
        and backend_state == "Running"
        and online
        and dns_name
        and magic_dns_suffix
        and funnel_cli_ok
    )
    if not version_ok:
        next_action = "upgrade"
    elif backend_state != "Running" or not online or not dns_name:
        next_action = "login"
    elif not funnel_cli_ok:
        next_action = "enable-funnel"
    else:
        next_action = "publish-edge"

    return {
        "installed": True,
        "path": str(path),
        "version": version,
        "minimum_version": ".".join(str(part) for part in TAILSCALE_MIN_VERSION),
        "version_ok": version_ok,
        "backend_state": backend_state,
        "online": online,
        "dns_name": dns_name,
        "magic_dns_suffix": magic_dns_suffix,
        "funnel_cli_ok": funnel_cli_ok,
        "funnel_policy": funnel_policy,
        "ready": ready,
        "next_action": next_action,
        "status_error": status_error,
        "funnel_error": funnel_error,
    }


def runtime_binaries_environment() -> dict[str, Any]:
    gateway = mcpjungle_binary()
    oauth = auth_proxy_binary()
    return {
        "mcpjungle": {"ready": gateway.is_file(), "path": str(gateway)},
        "mcp_auth_proxy": {"ready": oauth.is_file(), "path": str(oauth)},
        "ready": gateway.is_file() and oauth.is_file(),
    }


def environment_report() -> dict[str, Any]:
    python = python_environment()
    windows = windows_environment()
    winget = winget_environment()
    tailscale = tailscale_environment()
    binaries = runtime_binaries_environment()

    next_steps: list[dict[str, str]] = []
    if not python["ok"]:
        next_steps.append({"id": "python", "action": "install-python-3.11+", "blocking": True})
    if not windows["ok"]:
        next_steps.append({"id": "windows", "action": "use-supported-windows", "blocking": True})
    if not tailscale["installed"]:
        next_steps.append(
            {
                "id": "tailscale",
                "action": "install-with-winget" if winget["available"] else "install-from-official-windows-installer",
                "blocking": True,
            }
        )
    elif not tailscale["version_ok"]:
        next_steps.append({"id": "tailscale", "action": "upgrade-tailscale", "blocking": True})
    elif not tailscale["online"]:
        next_steps.append({"id": "tailscale", "action": "tailscale-up-and-login", "blocking": True})
    elif not tailscale["funnel_cli_ok"]:
        next_steps.append({"id": "tailscale-funnel", "action": "enable-magicdns-https-and-funnel", "blocking": True})
    elif tailscale["funnel_policy"] == "available-unverified":
        next_steps.append(
            {
                "id": "tailscale-funnel",
                "action": "first-publish-will-verify-tailnet-funnel-policy",
                "blocking": False,
            }
        )
    if not binaries["mcpjungle"]["ready"]:
        next_steps.append({"id": "mcpjungle", "action": "provision-verified-binary", "blocking": True})
    if not binaries["mcp_auth_proxy"]["ready"]:
        next_steps.append({"id": "mcp-auth-proxy", "action": "provision-verified-binary", "blocking": True})

    ready_for_edge = bool(
        python["ok"]
        and windows["ok"]
        and tailscale["ready"]
        and binaries["ready"]
    )
    return {
        "python": python,
        "windows": windows,
        "winget": winget,
        "tailscale": tailscale,
        "runtime_binaries": binaries,
        "ready_for_local_manager": bool(python["ok"] and windows["ok"]),
        "ready_for_gateway": bool(python["ok"] and windows["ok"] and binaries["mcpjungle"]["ready"]),
        "ready_for_edge": ready_for_edge,
        "next_steps": next_steps,
    }


def install_tailscale_with_winget(*, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "status": "confirmation-required"}
    if os.name != "nt":
        return {"ok": False, "status": "unsupported-platform"}
    winget = shutil.which("winget")
    if not winget:
        return {
            "ok": False,
            "status": "winget-unavailable",
            "next_action": "install-from-official-windows-installer",
        }

    before = tailscale_environment()
    if before["installed"] and before["version_ok"]:
        return {"ok": True, "status": "already-installed", "tailscale": before}

    result = _run(
        [
            winget,
            "install",
            "--id",
            TAILSCALE_WINGET_ID,
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
        ],
        timeout=180,
    )
    after = tailscale_environment()
    return {
        "ok": result.returncode == 0 and after["installed"],
        "status": "installed" if result.returncode == 0 and after["installed"] else "install-failed",
        "returncode": result.returncode,
        "tailscale": after,
    }
