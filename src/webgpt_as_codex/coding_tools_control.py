from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
from pathlib import Path
from typing import Any

from .mcp import initialize as mcp_initialize
from .mcp import rpc as mcp_rpc
from .mcp import session_id as mcp_session_id
from .paths import ensure_state_dirs
from .stateio import atomic_write_json, atomic_write_text

CODING_TOOLS_ENDPOINT = "http://127.0.0.1:8766/mcp"
_PERMISSION_MODES = {"safe", "trusted", "dangerous"}
_MUTATION_MODES = {"unrestricted", "structured-only"}
_SHELL_ENV_MODES = {"core", "all", "none"}
_MANAGED_MARKER = "# WebGPT-as-Codex managed Coding Tools launcher v1"


def _config_path() -> Path:
    return ensure_state_dirs() / "config" / "coding-tools.json"


def _launcher_path() -> Path:
    root = ensure_state_dirs() / "external-ensure"
    root.mkdir(parents=True, exist_ok=True)
    return root / "coding-tools.ps1"


def _defaults() -> dict[str, Any]:
    return {
        "workspace": None,
        "permission_mode": "trusted",
        "workspace_mutation": "unrestricted",
        "shell_env_inherit": "core",
        "allow_network": False,
        "enable_view_image": True,
    }


def _validate_workspace(value: Any, *, require_exists: bool) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError("workspace must be a bounded path string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("workspace must be an absolute path")
    if require_exists and (not path.exists() or not path.is_dir()):
        raise ValueError("workspace must be an existing directory")
    return str(path.resolve()) if path.exists() else str(path)


def _validated_config(data: dict[str, Any], *, require_workspace_exists: bool) -> dict[str, Any]:
    defaults = _defaults()
    unknown = sorted(set(data) - set(defaults))
    if unknown:
        raise ValueError("unsupported Coding Tools config fields: " + ", ".join(unknown))
    merged = {**defaults, **data}
    merged["workspace"] = _validate_workspace(
        merged.get("workspace"),
        require_exists=require_workspace_exists,
    )
    if merged["permission_mode"] not in _PERMISSION_MODES:
        raise ValueError("permission_mode must be safe, trusted, or dangerous")
    if merged["workspace_mutation"] not in _MUTATION_MODES:
        raise ValueError("workspace_mutation is invalid")
    if merged["shell_env_inherit"] not in _SHELL_ENV_MODES:
        raise ValueError("shell_env_inherit is invalid")
    for key in ("allow_network", "enable_view_image"):
        if not isinstance(merged[key], bool):
            raise TypeError(f"{key} must be boolean")
    return merged


def read_coding_tools_config() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return _defaults()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _defaults()
    if not isinstance(raw, dict):
        return _defaults()
    try:
        return _validated_config(raw, require_workspace_exists=False)
    except (TypeError, ValueError):
        return _defaults()


def write_coding_tools_config(data: dict[str, Any]) -> dict[str, Any]:
    config = _validated_config(data, require_workspace_exists=True)
    if config["workspace"] is None:
        raise ValueError("workspace is required")
    atomic_write_json(_config_path(), config, sort_keys=True)
    return config


def probe_coding_tools_live() -> dict[str, Any]:
    try:
        initialized = mcp_initialize(CODING_TOOLS_ENDPOINT)
        sid = mcp_session_id(initialized)
        response = mcp_rpc(
            CODING_TOOLS_ENDPOINT,
            "tools/call",
            {"name": "server_info", "arguments": {}},
            request_id=2,
            session_id=sid,
            timeout=5,
        )
        structured = response.body.get("result", {}).get("structuredContent")
        if not isinstance(structured, dict):
            return {"reachable": False, "reason": "server-info-missing"}
        mutation = structured.get("workspace_mutation_policy")
        if not isinstance(mutation, dict):
            mutation = {}
        return {
            "reachable": True,
            "version": structured.get("version"),
            "workspace": structured.get("workspace"),
            "permission_mode": structured.get("permission_mode"),
            "workspace_mutation": mutation.get("mode"),
            "shell_env_inherit": structured.get("shell_env_inherit"),
            "network_allowed": structured.get("network_allowed"),
            "view_image_enabled": "view_image" in (structured.get("tools") or []),
        }
    except (OSError, TimeoutError, TypeError, ValueError, urllib.error.URLError):
        return {"reachable": False}


def coding_tools_public_status() -> dict[str, Any]:
    configured = read_coding_tools_config()
    live = probe_coding_tools_live()
    desired_workspace = configured.get("workspace") or live.get("workspace")
    desired_permission = configured.get("permission_mode")
    restart_required = bool(
        live.get("reachable")
        and configured.get("workspace")
        and (
            live.get("workspace") != configured.get("workspace")
            or live.get("permission_mode") != desired_permission
            or live.get("workspace_mutation") != configured.get("workspace_mutation")
            or live.get("shell_env_inherit") != configured.get("shell_env_inherit")
        )
    )
    return {
        "configured": {
            "workspace": desired_workspace,
            "permission_mode": desired_permission,
            "workspace_mutation": configured.get("workspace_mutation"),
            "shell_env_inherit": configured.get("shell_env_inherit"),
        },
        "live": live,
        "restart_required": restart_required,
        "permission_modes": ["safe", "trusted", "dangerous"],
    }


def _coding_tools_executable() -> Path | None:
    override = os.getenv("WEBGPT_CODEX_CODING_TOOLS_EXE")
    candidates = [
        Path(override).expanduser() if override else None,
        Path("D:/AgentData/20_State/coding-tools-mcp/venv/Scripts/coding-tools-mcp.exe"),
    ]
    found = shutil.which("coding-tools-mcp")
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    return None


def _legacy_launcher() -> Path | None:
    override = os.getenv("WEBGPT_CODEX_CODING_TOOLS_LEGACY_LAUNCHER")
    candidates = [
        Path(override).expanduser() if override else None,
        Path("D:/AgentData/20_State/coding-tools-mcp-tailscale/start-coding-tools-remote-v2.ps1"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    return None


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _managed_launcher_content(server: Path, legacy: Path | None) -> str:
    config = _config_path()
    legacy_text = _ps_quote(str(legacy)) if legacy else "$null"
    return f"""param([switch]$Restart)
{_MANAGED_MARKER}
$ErrorActionPreference = 'Stop'
$configPath = {_ps_quote(str(config))}
$server = {_ps_quote(str(server))}
$legacy = {legacy_text}
$runtimeRoot = 'D:\\AgentData\\20_State\\coding-tools-mcp'
$logRoot = Join-Path $runtimeRoot 'logs'
New-Item -ItemType Directory -Force -Path $logRoot,(Join-Path $runtimeRoot 'runtime') | Out-Null

function Get-ListenerPid {{
  $listener = Get-NetTCPConnection -State Listen -LocalPort 8766 -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($listener) {{ return [int]$listener.OwningProcess }}
  return $null
}}

function Wait-Port([bool]$Present, [int]$Seconds = 20) {{
  $deadline = (Get-Date).AddSeconds($Seconds)
  do {{
    $pidValue = Get-ListenerPid
    if ($Present -and $pidValue) {{ return $true }}
    if (-not $Present -and -not $pidValue) {{ return $true }}
    Start-Sleep -Milliseconds 250
  }} while ((Get-Date) -lt $deadline)
  return $false
}}

$cfg = $null
if (Test-Path -LiteralPath $configPath) {{
  $cfg = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
}}

if (-not $cfg -or -not $cfg.workspace) {{
  if ($legacy -and (Test-Path -LiteralPath $legacy)) {{
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $legacy
    exit $LASTEXITCODE
  }}
  throw 'Coding Tools workspace is not configured and no legacy launcher is available.'
}}

$workspace = [string]$cfg.workspace
if (-not (Test-Path -LiteralPath $workspace -PathType Container)) {{
  throw 'Configured Coding Tools workspace does not exist.'
}}

if ($Restart) {{
  $pidValue = Get-ListenerPid
  if ($pidValue) {{
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue"
    $cmd = [string]$proc.CommandLine
    if (-not $cmd.ToLowerInvariant().Contains('coding-tools-mcp')) {{
      throw 'Port 8766 is owned by an unexpected process; refusing to stop it.'
    }}
    Stop-Process -Id $pidValue -Force
    if (-not (Wait-Port $false 10)) {{ throw 'Coding Tools port 8766 did not stop.' }}
  }}
}}

if (-not (Get-ListenerPid)) {{
  $args = @(
    '--workspace',$workspace,
    '--host','127.0.0.1',
    '--port','8766',
    '--permission-mode',[string]$cfg.permission_mode,
    '--workspace-mutation',[string]$cfg.workspace_mutation,
    '--shell-env-inherit',[string]$cfg.shell_env_inherit
  )
  if ([bool]$cfg.allow_network) {{ $args += '--allow-network' }}
  if ([bool]$cfg.enable_view_image) {{ $args += '--enable-view-image' }}
  $env:CODING_TOOLS_MCP_TELEMETRY = 'off'
  $env:CODING_TOOLS_MCP_RUNTIME_ROOT = Join-Path $runtimeRoot 'runtime'
  $p = Start-Process -FilePath $server -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'server.stdout.log') -RedirectStandardError (Join-Path $logRoot 'server.stderr.log')
  $p.Id | Set-Content -LiteralPath (Join-Path $runtimeRoot 'coding-tools.pid')
}}
if (-not (Wait-Port $true 20)) {{ throw 'Coding Tools failed to listen on 8766.' }}

if (-not $Restart -and $legacy -and (Test-Path -LiteralPath $legacy)) {{
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $legacy
  if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
}}
Write-Output 'READY=http://127.0.0.1:8766/mcp'
"""


def ensure_coding_tools_external_launcher() -> dict[str, Any]:
    server = _coding_tools_executable()
    if server is None:
        return {"ok": False, "status": "coding-tools-executable-not-found"}
    path = _launcher_path()
    desired = _managed_launcher_content(server, _legacy_launcher())
    if path.exists():
        current = path.read_text(encoding="utf-8", errors="replace")
        legacy_signature = "start-coding-tools-remote-v2.ps1"
        if _MANAGED_MARKER not in current and legacy_signature not in current:
            return {
                "ok": False,
                "status": "preserved-unmanaged-launcher",
                "launcher": path.name,
            }
        if current.replace("\r\n", "\n") == desired.replace("\r\n", "\n"):
            return {"ok": True, "status": "present", "launcher": path.name}
    atomic_write_text(path, desired)
    return {"ok": True, "status": "updated", "launcher": path.name}


def restart_coding_tools() -> dict[str, Any]:
    ensured = ensure_coding_tools_external_launcher()
    if not ensured.get("ok"):
        return {"ok": False, "status": ensured.get("status"), "launcher": ensured}
    path = _launcher_path()
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(path),
                "-Restart",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=45,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "ok": False,
            "status": "restart-launch-failed",
            "failure_type": type(exc).__name__,
        }
    if completed.returncode != 0:
        return {
            "ok": False,
            "status": "restart-failed",
            "returncode": completed.returncode,
        }
    deadline = time.monotonic() + 15
    live = probe_coding_tools_live()
    while not live.get("reachable") and time.monotonic() < deadline:
        time.sleep(0.25)
        live = probe_coding_tools_live()
    return {
        "ok": bool(live.get("reachable")),
        "status": "restarted" if live.get("reachable") else "restart-not-ready",
        "live": live,
    }


def apply_coding_tools_config(
    *,
    workspace: str,
    permission_mode: str,
    restart: bool = True,
) -> dict[str, Any]:
    previous = read_coding_tools_config()
    candidate = {
        **previous,
        "workspace": workspace,
        "permission_mode": permission_mode,
    }
    config = write_coding_tools_config(candidate)
    launcher = ensure_coding_tools_external_launcher()
    if not launcher.get("ok"):
        return {
            "ok": False,
            "status": launcher.get("status"),
            "configured": {
                "workspace": config["workspace"],
                "permission_mode": config["permission_mode"],
            },
            "launcher": launcher,
        }
    restarted = restart_coding_tools() if restart else None
    live = restarted.get("live") if isinstance(restarted, dict) else probe_coding_tools_live()
    ok = bool(restarted.get("ok")) if restarted is not None else True
    return {
        "ok": ok,
        "status": "applied-and-restarted" if restarted is not None and ok else "saved",
        "configured": {
            "workspace": config["workspace"],
            "permission_mode": config["permission_mode"],
        },
        "restart": restarted,
        "live": live,
    }
