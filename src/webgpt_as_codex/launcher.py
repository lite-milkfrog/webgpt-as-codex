from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .doctor import probe_public_remote
from .paths import state_root, user_home
from .runtime import RuntimeSupervisor

_MARKER = "REM WebGPT-as-Codex managed launcher"
_DESKTOP_NAME = "WebGPT-as-Codex.cmd"
_AUTOSTART_NAME = "WebGPT-as-Codex-Autostart.cmd"
_LAUNCH_LOG_GENERATION = "v2"
_EXTERNAL_BACKEND_WAIT_ENV = "WEBGPT_CODEX_EXTERNAL_BACKEND_WAIT_SECONDS"
_BOOT_RECOVERY_ENV = "WEBGPT_CODEX_BOOT_RECOVERY"
_EXTERNAL_BACKEND_WAIT_DEFAULT = 60.0
_EXTERNAL_BACKEND_POLL = 2.0
_BOOT_RECOVERY_POLL = 10.0
_DESKTOP_RECOVERY_SECONDS = 180
_AUTOSTART_RECOVERY_SECONDS = 300
_RDC_START_TIMEOUT_SECONDS = 70.0
_RDC_REMOTE_LAUNCHER_MARKER = "# WebGPT-as-Codex managed RDC launcher"
_RDC_REMOTE_LAUNCHER_ENV = "WEBGPT_CODEX_RDC_LAUNCHER_PATH"
_RDC_WAC_RECOVERY_MARKER = "# WebGPT-as-Codex managed RDC-to-WAC recovery bridge"
_RDC_WAC_RECOVERY_ENV = "WEBGPT_CODEX_RDC_WAC_RECOVERY_PATH"


def _expand_shell_value(value: str) -> Path:
    home = user_home()
    expanded = os.path.expandvars(value)
    replacements = {
        "%USERPROFILE%": str(home),
        "%HOME%": str(home),
        "%APPDATA%": str(home / "AppData" / "Roaming"),
        "%LOCALAPPDATA%": str(home / "AppData" / "Local"),
    }
    for token, replacement in replacements.items():
        expanded = re.sub(
            re.escape(token),
            lambda _match, value=replacement: value,
            expanded,
            flags=re.IGNORECASE,
        )
    return Path(expanded)


def _shell_folder(value_name: str, fallback: Path, override_env: str) -> Path:
    override = os.getenv(override_env)
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        try:
            import winreg

            for key_name in ("Shell Folders", "User Shell Folders"):
                key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\{key_name}"
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                        value, _ = winreg.QueryValueEx(key, value_name)
                except OSError:
                    continue
                if value:
                    candidate = _expand_shell_value(str(value))
                    if candidate.is_absolute():
                        return candidate
        except (OSError, ImportError):
            pass
    return fallback.expanduser().resolve()


def desktop_dir() -> Path:
    return _shell_folder("Desktop", user_home() / "Desktop", "WEBGPT_CODEX_DESKTOP_DIR")


def startup_dir() -> Path:
    fallback = (
        user_home()
        / "AppData"
        / "Roaming"
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )
    return _shell_folder("Startup", fallback, "WEBGPT_CODEX_STARTUP_DIR")


def _rdc_remote_launcher_path() -> Path:
    override = os.getenv(_RDC_REMOTE_LAUNCHER_ENV)
    if override:
        return Path(override).expanduser().resolve()
    local_appdata = os.getenv("LOCALAPPDATA")
    root = (
        Path(local_appdata)
        if local_appdata
        else user_home() / "AppData" / "Local"
    )
    return root / "DesktopCommander" / "start-remote.ps1"


def _rdc_remote_launcher_content() -> str:
    lines = [
        _RDC_REMOTE_LAUNCHER_MARKER,
        "$ErrorActionPreference = 'SilentlyContinue'",
        "",
        "$base = Split-Path -Parent $MyInvocation.MyCommand.Path",
        "$pidFile = Join-Path $base 'remote-agent.pid'",
        "$log = Join-Path $base 'remote-agent.log'",
        "$errLog = Join-Path $base 'remote-agent.err.log'",
        "",
        "New-Item -ItemType Directory -Force $base | Out-Null",
        "",
        "function Get-RemoteDesktopCommanderProcess {",
        "    Get-CimInstance Win32_Process | Where-Object {",
        "        $_.Name -eq 'node.exe' -and",
        "        $_.CommandLine -match 'desktop-commander' -and",
        "        $_.CommandLine -match '\\bremote\\b'",
        "    } | Select-Object -First 1",
        "}",
        "",
        "function Test-RemoteDesktopCommanderHealthy([int]$ProcessId) {",
        "    $connection = Get-NetTCPConnection -OwningProcess $ProcessId -State Established -ErrorAction SilentlyContinue | Select-Object -First 1",
        "    return [bool]$connection",
        "}",
        "",
        "$existing = Get-RemoteDesktopCommanderProcess",
        "if ($existing) {",
        "    if (Test-RemoteDesktopCommanderHealthy $existing.ProcessId) {",
        "        $existing.ProcessId | Set-Content -LiteralPath $pidFile",
        "        exit 0",
        "    }",
        "    $recentAuthorizationWait = $existing.CreationDate -and $existing.CreationDate -gt (Get-Date).AddMinutes(-2) -and (Select-String -LiteralPath $log -Pattern 'Waiting for authorization' -Quiet -ErrorAction SilentlyContinue)",
        "    if ($recentAuthorizationWait) {",
        "        $existing.ProcessId | Set-Content -LiteralPath $pidFile",
        "        exit 0",
        "    }",
        "    Add-Content -LiteralPath $log -Value ('Launcher self-heal: stale RDC remote process ' + $existing.ProcessId + ' has no established TCP connection; restarting.')",
        "    Stop-Process -Id $existing.ProcessId -Force -ErrorAction SilentlyContinue",
        "    Start-Sleep -Seconds 1",
        "}",
        "",
        "$node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source",
        "if (-not $node) {",
        "    Add-Content -LiteralPath $log -Value 'Launcher error: node.exe not found on PATH.'",
        "    exit 2",
        "}",
        "",
        "$entry = $null",
        "$runtimes = Get-ChildItem -LiteralPath $base -Directory -Filter 'runtime-*' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending",
        "foreach ($runtime in $runtimes) {",
        "    $candidate = Join-Path $runtime.FullName 'node_modules\\@wonderwhy-er\\desktop-commander\\dist\\index.js'",
        "    if (Test-Path -LiteralPath $candidate) {",
        "        $entry = $candidate",
        "        break",
        "    }",
        "}",
        "if (-not $entry) {",
        "    Add-Content -LiteralPath $log -Value 'Launcher error: no Desktop Commander runtime entry found.'",
        "    exit 3",
        "}",
        "",
        "Set-Content -LiteralPath $log -Value ('===== launcher ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' | proxy-aware self-heal =====') -Encoding UTF8",
        "Set-Content -LiteralPath $errLog -Value '' -Encoding UTF8",
        "",
        "$nodeArgs = @($entry, 'remote', '--debug')",
        "$proxySettings = Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' -ErrorAction SilentlyContinue",
        "$proxyValue = $null",
        "if ($proxySettings -and $proxySettings.ProxyEnable -eq 1 -and $proxySettings.ProxyServer) {",
        "    $proxyValue = [string]$proxySettings.ProxyServer",
        "    if ($proxyValue -match ';') {",
        "        $parts = $proxyValue -split ';'",
        "        $httpsPart = $parts | Where-Object { $_ -match '^https=' } | Select-Object -First 1",
        "        $httpPart = $parts | Where-Object { $_ -match '^http=' } | Select-Object -First 1",
        "        if ($httpsPart) { $proxyValue = $httpsPart.Substring($httpsPart.IndexOf('=') + 1) }",
        "        elseif ($httpPart) { $proxyValue = $httpPart.Substring($httpPart.IndexOf('=') + 1) }",
        "    } elseif ($proxyValue -match '^[^=]+=') {",
        "        $proxyValue = $proxyValue.Substring($proxyValue.IndexOf('=') + 1)",
        "    }",
        "    if ($proxyValue -and $proxyValue -notmatch '^[a-zA-Z][a-zA-Z0-9+.-]*://') {",
        "        $proxyValue = 'http://' + $proxyValue",
        "    }",
        "}",
        "",
        "if ($proxyValue) {",
        "    try {",
        "        $proxyUri = [uri]$proxyValue",
        "        if ($proxyUri.Host -in @('127.0.0.1', 'localhost', '::1')) {",
        "            $proxyDeadline = (Get-Date).AddSeconds(45)",
        "            do {",
        "                $proxyReady = Test-NetConnection -ComputerName $proxyUri.Host -Port $proxyUri.Port -InformationLevel Quiet -WarningAction SilentlyContinue",
        "                if ($proxyReady) { break }",
        "                Start-Sleep -Seconds 2",
        "            } while ((Get-Date) -lt $proxyDeadline)",
        "            if (-not $proxyReady) {",
        "                Add-Content -LiteralPath $log -Value ('Launcher error: Windows user proxy is configured but not reachable: ' + $proxyValue)",
        "                exit 5",
        "            }",
        "        }",
        "    } catch {",
        "        Add-Content -LiteralPath $log -Value ('Launcher warning: could not validate proxy URI: ' + $proxyValue)",
        "    }",
        "    $env:HTTP_PROXY = $proxyValue",
        "    $env:HTTPS_PROXY = $proxyValue",
        "    $env:NO_PROXY = '127.0.0.1,localhost,::1'",
        "    $env:NODE_USE_ENV_PROXY = '1'",
        '    $nodeHelp = (& $node --help 2>$null) -join "`n"',
        "    if ($nodeHelp -match '--use-env-proxy') {",
        "        $nodeArgs = @('--use-env-proxy', $entry, 'remote', '--debug')",
        "    }",
        "    Add-Content -LiteralPath $log -Value ('Launcher network: using Windows user proxy ' + $proxyValue)",
        "}",
        "",
        "Start-Process -FilePath $node -ArgumentList $nodeArgs -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $errLog",
        "",
        "$deadline = (Get-Date).AddSeconds(45)",
        "$started = $null",
        "do {",
        "    Start-Sleep -Milliseconds 750",
        "    $started = Get-RemoteDesktopCommanderProcess",
        "    if ($started -and (Test-RemoteDesktopCommanderHealthy $started.ProcessId)) {",
        "        $started.ProcessId | Set-Content -LiteralPath $pidFile",
        "        exit 0",
        "    }",
        "    if (-not $started) { continue }",
        "    if (Select-String -LiteralPath $log -Pattern 'Waiting for authorization' -Quiet -ErrorAction SilentlyContinue) {",
        "        $started.ProcessId | Set-Content -LiteralPath $pidFile",
        "        exit 0",
        "    }",
        "} while ((Get-Date) -lt $deadline)",
        "",
        "if ($started) {",
        "    Add-Content -LiteralPath $log -Value ('Launcher error: RDC process stayed alive but never established a TCP connection by ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))",
        "    Stop-Process -Id $started.ProcessId -Force -ErrorAction SilentlyContinue",
        "} else {",
        "    Add-Content -LiteralPath $log -Value ('Launcher error: RDC remote process did not stay alive by ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))",
        "}",
        "exit 4",
    ]
    return "\r\n".join(lines) + "\r\n"


def _ensure_rdc_remote_launcher() -> dict[str, Any]:
    path = _rdc_remote_launcher_path()
    expected = _rdc_remote_launcher_content()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            current = path.read_text(encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "status": "read-failed", "path": str(path), "error": str(exc)}
        if _RDC_REMOTE_LAUNCHER_MARKER not in current:
            return {"ok": True, "status": "preserved-existing-unmanaged-file", "path": str(path)}
        if current.replace("\r\n", "\n") == expected.replace("\r\n", "\n"):
            return {"ok": True, "status": "present", "path": str(path)}
        operation = "updated"
    else:
        operation = "installed"
    path.write_text(expected, encoding="utf-8", newline="")
    return {"ok": True, "status": operation, "path": str(path)}


def _rdc_webgpt_recovery_path() -> Path:
    override = os.getenv(_RDC_WAC_RECOVERY_ENV)
    if override:
        return Path(override).expanduser().resolve()
    local_appdata = os.getenv("LOCALAPPDATA")
    root = (
        Path(local_appdata)
        if local_appdata
        else user_home() / "AppData" / "Local"
    )
    return root / "WebGPT-as-Codex" / "rdc-recover-webgpt.ps1"


def _rdc_webgpt_recovery_content() -> str:
    expected_autostart_sha256 = hashlib.sha256(
        _launcher_content(open_browser=False).encode("utf-8")
    ).hexdigest()
    lines = [
        _RDC_WAC_RECOVERY_MARKER,
        "$ErrorActionPreference = 'SilentlyContinue'",
        "",
        "$base = Split-Path -Parent $MyInvocation.MyCommand.Path",
        "$log = Join-Path $base 'rdc-recovery-bridge.log'",
        "$managerUrl = 'http://127.0.0.1:9200/healthz'",
        "$mcpUrl = 'http://127.0.0.1:8766/mcp'",
        "$startup = Join-Path ([Environment]::GetFolderPath('Startup')) 'WebGPT-as-Codex-Autostart.cmd'",
        f"$expectedLauncherSha256 = '{expected_autostart_sha256}'",
        "",
        "function Test-ManagerHealth {",
        "    try {",
        "        $response = Invoke-WebRequest -UseBasicParsing -Uri $managerUrl -Method GET -TimeoutSec 3",
        "        return [bool]($response.StatusCode -eq 200)",
        "    } catch {",
        "        return $false",
        "    }",
        "}",
        "",
        "function Test-CodingToolsMcp {",
        "    try {",
        "        $body = '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"rdc-recovery-bridge\",\"version\":\"1.0\"}}}'",
        "        $headers = @{ Accept = 'application/json, text/event-stream' }",
        "        $response = Invoke-WebRequest -UseBasicParsing -Uri $mcpUrl -Method POST -Headers $headers -ContentType 'application/json' -Body $body -TimeoutSec 5",
        "        if ($response.StatusCode -ne 200) { return $false }",
        "        $payload = $response.Content | ConvertFrom-Json",
        "        return [bool]($payload.result.serverInfo.name -eq 'coding-tools-mcp')",
        "    } catch {",
        "        return $false",
        "    }",
        "}",
        "",
        "function Write-BridgeResult([bool]$Ok, [string]$Status, [bool]$Manager, [bool]$Mcp, [object]$LauncherExit) {",
        "    [ordered]@{",
        "        ok = $Ok",
        "        status = $Status",
        "        manager_health = $Manager",
        "        coding_tools_mcp_initialize = $Mcp",
        "        launcher_exit = $LauncherExit",
        "        rdc_execution_plane = 'requires ChatGPT-side RDC ping/get_config probe'",
        "    } | ConvertTo-Json -Compress | Write-Output",
        "}",
        "",
        "$managerHealthy = Test-ManagerHealth",
        "$mcpHealthy = Test-CodingToolsMcp",
        "if ($managerHealthy -and $mcpHealthy) {",
        "    Write-BridgeResult $true 'healthy' $managerHealthy $mcpHealthy $null",
        "    exit 0",
        "}",
        "",
        "if (-not (Test-Path -LiteralPath $startup)) {",
        "    Write-BridgeResult $false 'managed-autostart-missing' $managerHealthy $mcpHealthy $null",
        "    exit 2",
        "}",
        "if (-not (Select-String -LiteralPath $startup -SimpleMatch 'REM WebGPT-as-Codex managed launcher' -Quiet)) {",
        "    Write-BridgeResult $false 'refuse-unmanaged-autostart' $managerHealthy $mcpHealthy $null",
        "    exit 3",
        "}",
        "$actualLauncherSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $startup).Hash.ToLowerInvariant()",
        "if ($actualLauncherSha256 -ne $expectedLauncherSha256) {",
        "    Write-BridgeResult $false 'refuse-modified-autostart' $managerHealthy $mcpHealthy $null",
        "    exit 3",
        "}",
        "",
        "New-Item -ItemType Directory -Force $base | Out-Null",
        "Add-Content -LiteralPath $log -Value ('[' + (Get-Date -Format o) + '] RDC requested bounded WebGPT recovery.')",
        "& $startup | Out-Null",
        "$launcherExit = $LASTEXITCODE",
        "",
        "$deadline = (Get-Date).AddSeconds(30)",
        "do {",
        "    $managerHealthy = Test-ManagerHealth",
        "    $mcpHealthy = Test-CodingToolsMcp",
        "    if ($managerHealthy -and $mcpHealthy) {",
        "        Add-Content -LiteralPath $log -Value ('[' + (Get-Date -Format o) + '] WebGPT recovery verified by Manager + MCP initialize.')",
        "        Write-BridgeResult $true 'recovered' $managerHealthy $mcpHealthy $launcherExit",
        "        exit 0",
        "    }",
        "    Start-Sleep -Seconds 1",
        "} while ((Get-Date) -lt $deadline)",
        "",
        "Add-Content -LiteralPath $log -Value ('[' + (Get-Date -Format o) + '] WebGPT recovery verification failed.')",
        "Write-BridgeResult $false 'recovery-not-verified' $managerHealthy $mcpHealthy $launcherExit",
        "exit 4",
    ]
    return "\r\n".join(lines) + "\r\n"


def _ensure_rdc_webgpt_recovery_bridge() -> dict[str, Any]:
    path = _rdc_webgpt_recovery_path()
    expected = _rdc_webgpt_recovery_content()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            current = path.read_text(encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "status": "read-failed", "path": str(path), "error": str(exc)}
        if _RDC_WAC_RECOVERY_MARKER not in current:
            return {"ok": True, "status": "preserved-existing-unmanaged-file", "path": str(path)}
        if current.replace("\r\n", "\n") == expected.replace("\r\n", "\n"):
            return {"ok": True, "status": "present", "path": str(path)}
        operation = "updated"
    else:
        operation = "installed"
    path.write_text(expected, encoding="utf-8", newline="")
    return {"ok": True, "status": operation, "path": str(path)}


def _pythonw() -> Path:
    current = Path(sys.executable)
    if os.name == "nt":
        candidate = current.with_name("pythonw.exe")
        if candidate.is_file():
            return candidate
    return current


def _edge_executable() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, None)
            except OSError:
                continue
            candidate = Path(str(value).strip('"'))
            if candidate.is_file():
                return candidate
    except (OSError, ImportError):
        pass
    candidates = [
        Path(os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
        Path(os.getenv("ProgramFiles", r"C:\Program Files"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
    ]
    return next((path for path in candidates if path.is_file()), None)


def _edge_reuse_target() -> tuple[Path, str] | None:
    if os.name != "nt":
        return None
    try:
        running = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq msedge.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if "msedge.exe" not in running.stdout.lower():
        return None
    local = os.getenv("LOCALAPPDATA")
    user_data = (
        Path(local)
        if local
        else user_home() / "AppData" / "Local"
    ) / "Microsoft" / "Edge" / "User Data"
    try:
        state = json.loads((user_data / "Local State").read_text(encoding="utf-8"))
        profile = state.get("profile", {}).get("last_used")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(profile, str) or not re.fullmatch(r"(?:Default|Profile \d+)", profile):
        return None
    executable = _edge_executable()
    return (executable, profile) if executable else None


def _launch_edge_profile(executable: Path, profile: str, url: str) -> bool:
    try:
        subprocess.Popen(
            [str(executable), f"--profile-directory={profile}", url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except OSError:
        return False


def _focus_existing_edge_window() -> bool:
    """Best-effort foreground activation for a normal existing Edge window.

    This intentionally does not inspect browser DOM/tabs and does not require a
    Playwright/DevTools profile. The user-facing desktop launcher only needs to
    make the normal browser visible after dispatching the Manager URL.
    """
    if os.name != "nt":
        return False
    try:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, ImportError):
        return False

    process_query_limited_information = 0x1000
    sw_restore = 9
    candidates: list[int] = []

    def is_edge_window(hwnd: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return False
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, pid.value
        )
        if not handle:
            return False
        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                return False
            return Path(buffer.value).name.casefold() == "msedge.exe"
        finally:
            kernel32.CloseHandle(handle)

    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )

    @callback_type
    def collect(hwnd: int, _lparam: int) -> bool:
        if is_edge_window(hwnd):
            candidates.append(int(hwnd))
        return True

    try:
        user32.EnumWindows(collect, 0)
        if not candidates:
            return False
        hwnd = candidates[0]
        user32.ShowWindowAsync(hwnd, sw_restore)
        return bool(user32.SetForegroundWindow(hwnd))
    except (OSError, ValueError):
        return False


def _open_manager_url(url: str) -> tuple[bool, str]:
    edge = _edge_reuse_target()
    if edge and _launch_edge_profile(edge[0], edge[1], url):
        _focus_existing_edge_window()
        return True, "existing-edge-profile"
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            _focus_existing_edge_window()
            return True, "windows-default-url-handler"
        except OSError:
            pass
    return bool(webbrowser.open(url)), "default-webbrowser-fallback"


def _launcher_log_dir() -> Path:
    override = os.getenv("WEBGPT_CODEX_LAUNCH_LOG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    agent_data = Path("D:/AgentData")
    if os.name == "nt" and agent_data.is_dir():
        return agent_data / "20_State" / "WebGPT-as-Codex" / "logs"
    return state_root() / "logs" / "launcher"


def _launcher_log_path(*, open_browser: bool) -> Path:
    stem = "desktop-launcher" if open_browser else "autostart"
    return _launcher_log_dir() / f"{stem}-{_LAUNCH_LOG_GENERATION}.log"


def _legacy_launcher_log_path(*, open_browser: bool) -> Path:
    return _launcher_log_dir() / (
        "desktop-launcher.log" if open_browser else "autostart.log"
    )


def _local_prestart_content(log_path: Path) -> str:
    """Run the machine-local bootstrap without leaking launcher log handles.

    Legacy backend bootstrap scripts may spawn long-lived grandchildren. Redirecting
    the CALL itself into the launcher log lets those descendants inherit the file
    handle on Windows, which can make the following WebGPT launcher redirection fail
    with ERROR_SHARING_VIOLATION. Send bootstrap output to NUL and write only the
    bootstrap outcome to the launcher log after CALL returns.
    """
    return (
        'if exist "%LOCALAPPDATA%\\WebGPT-as-Codex\\local-prestart.cmd" (\r\n'
        '  call "%LOCALAPPDATA%\\WebGPT-as-Codex\\local-prestart.cmd" >nul 2>&1\r\n'
        "  if errorlevel 1 (\r\n"
        '    echo Local prestart hook reported a failure; readiness checks will decide final status. >> "'
        + str(log_path)
        + '"\r\n'
        "  ) else (\r\n"
        '    echo Local prestart hook completed. >> "'
        + str(log_path)
        + '"\r\n'
        "  )\r\n"
        ")\r\n"
    )


def _python_runtime_guard_content(python: str, log_path: Path, *, pause: bool) -> str:
    tail = "  pause\r\n" if pause else ""
    return (
        f'if not exist "{python}" (\r\n'
        + f'  echo WebGPT launcher failed. Python runtime not found: {python} > "{log_path}"\r\n'
        + f'  type "{log_path}"\r\n'
        + f"  echo Full log: {log_path}\r\n"
        + tail
        + "  exit /b 2\r\n"
        + ")\r\n"
    )


def _launcher_content(*, open_browser: bool) -> str:
    flag = "--open" if open_browser else "--no-open"
    python = str(Path(sys.executable))
    log_root = _launcher_log_dir()
    log_path = _launcher_log_path(open_browser=open_browser)
    prestart = _local_prestart_content(log_path)
    if open_browser:
        visible = (
            "echo WebGPT-as-Codex: detecting environment and waiting for real readiness...\r\n"
            "echo (After a reboot, waiting for the network/Tailscale can take up to 3 minutes.)\r\n"
        )
        success = (
            "echo WebGPT-as-Codex is READY. Manager: http://127.0.0.1:9200/\r\n"
        )
        remote_desktop_commander = (
            'if exist "%LOCALAPPDATA%\\DesktopCommander\\start-remote.ps1" (\r\n'
            '  powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\\DesktopCommander\\start-remote.ps1"\r\n'
            "  if errorlevel 1 (\r\n"
            "    echo Remote Desktop Commander start failed. WebGPT-as-Codex remains READY.\r\n"
            "    echo RDC log: %LOCALAPPDATA%\\DesktopCommander\\remote-agent.log\r\n"
            "  ) else (\r\n"
            "    echo Remote Desktop Commander start requested successfully.\r\n"
            "  )\r\n"
            ")\r\n"
        )
        local_overlay = (
            'if exist "%LOCALAPPDATA%\\WebGPT-as-Codex\\local-launcher-overlay.cmd" (\r\n'
            '  call "%LOCALAPPDATA%\\WebGPT-as-Codex\\local-launcher-overlay.cmd"\r\n'
            "  if errorlevel 1 (\r\n"
            "    echo Local desktop overlay failed. WebGPT-as-Codex remains READY.\r\n"
            "  )\r\n"
            ")\r\n"
        )
        tail = "  pause\r\n"
    else:
        visible = ""
        success = ""
        remote_desktop_commander = ""
        local_overlay = ""
        tail = ""
    recovery_seconds = (
        _DESKTOP_RECOVERY_SECONDS if open_browser else _AUTOSTART_RECOVERY_SECONDS
    )
    boot_recovery = 'set "WEBGPT_CODEX_BOOT_RECOVERY=1"\r\n' if not open_browser else ""
    return (
        "@echo off\r\n"
        f"{_MARKER}\r\n"
        "setlocal\r\n"
        'set "WEBGPT_CODEX_UI_LANG=zh-CN"\r\n'
        + f'set "WEBGPT_CODEX_EXTERNAL_BACKEND_WAIT_SECONDS={recovery_seconds}"\r\n'
        + boot_recovery
        + visible
        + f'if not exist "{log_root}" mkdir "{log_root}"\r\n'
        + _python_runtime_guard_content(python, log_path, pause=open_browser)
        + f'type nul > "{log_path}"\r\n'
        + prestart
        + f'"{python}" -m webgpt_as_codex launcher {flag} --start-all >> "{log_path}" 2>&1\r\n'
        + "if errorlevel 1 (\r\n"
        + "  echo WebGPT launcher failed. Diagnostic output:\r\n"
        + f'  type "{log_path}"\r\n'
        + f"  echo Full log: {log_path}\r\n"
        + tail
        + "  exit /b 2\r\n"
        + " )\r\n"
        + success
        + local_overlay
        + remote_desktop_commander
        + "endlocal\r\n"
    )


def _log_redirecting_prestart_generation_content(log_path: Path) -> str:
    """Exact prestart block shipped immediately before handle-isolation hardening."""
    return (
        'if exist "%LOCALAPPDATA%\\WebGPT-as-Codex\\local-prestart.cmd" (\r\n'
        '  call "%LOCALAPPDATA%\\WebGPT-as-Codex\\local-prestart.cmd" >> "'
        + str(log_path)
        + '" 2>&1\r\n'
        "  if errorlevel 1 (\r\n"
        "    echo Local prestart hook reported a failure; readiness checks will decide final status.\r\n"
        "  )\r\n"
        ")\r\n"
    )


def _legacy_log_path_generation_matches(content: str, *, open_browser: bool) -> bool:
    """Recognize the handle-isolated generation installed before the v2 log migration."""
    current_log = _launcher_log_path(open_browser=open_browser)
    legacy_log = _legacy_launcher_log_path(open_browser=open_browser)
    expected = _launcher_content(open_browser=open_browser).replace(
        str(current_log),
        str(legacy_log),
    )
    return content.replace("\r\n", "\n") == expected.replace("\r\n", "\n")


def _pre_boot_recovery_generation_matches(content: str, *, open_browser: bool) -> bool:
    """Recognize the committed launcher immediately before boot-recovery hardening."""
    current_log = _launcher_log_path(open_browser=open_browser)
    legacy_log = _legacy_launcher_log_path(open_browser=open_browser)
    recovery_seconds = (
        _DESKTOP_RECOVERY_SECONDS if open_browser else _AUTOSTART_RECOVERY_SECONDS
    )
    expected = _launcher_content(open_browser=open_browser).replace(
        str(current_log),
        str(legacy_log),
    )
    expected = expected.replace(
        f'set "WEBGPT_CODEX_EXTERNAL_BACKEND_WAIT_SECONDS={recovery_seconds}"\r\n',
        "",
        1,
    )
    if not open_browser:
        expected = expected.replace('set "WEBGPT_CODEX_BOOT_RECOVERY=1"\r\n', "", 1)
    expected = expected.replace(
        _local_prestart_content(legacy_log),
        _log_redirecting_prestart_generation_content(legacy_log),
        1,
    )
    return content.replace("\r\n", "\n") == expected.replace("\r\n", "\n")


def _pre_guard_generation_matches(content: str, *, open_browser: bool) -> bool:
    python = str(Path(sys.executable))
    log_path = _launcher_log_path(open_browser=open_browser)
    expected = _launcher_content(open_browser=open_browser).replace(
        _python_runtime_guard_content(python, log_path, pause=open_browser),
        "",
        1,
    )
    return content.replace("\r\n", "\n") == expected.replace("\r\n", "\n")


def _prestartless_generation_matches(content: str, *, open_browser: bool) -> bool:
    flag = "--open" if open_browser else "--no-open"
    python = str(Path(sys.executable))
    log_path = _launcher_log_path(open_browser=open_browser)
    expected = _launcher_content(open_browser=open_browser)
    expected = expected.replace(
        _python_runtime_guard_content(python, log_path, pause=open_browser),
        "",
        1,
    )
    expected = expected.replace(
        f'type nul > "{log_path}"\r\n' + _local_prestart_content(log_path),
        "",
        1,
    )
    expected = expected.replace(
        f'"{python}" -m webgpt_as_codex launcher {flag} --start-all >> "{log_path}" 2>&1',
        f'"{python}" -m webgpt_as_codex launcher {flag} --start-all > "{log_path}" 2>&1',
        1,
    )
    return content.replace("\r\n", "\n") == expected.replace("\r\n", "\n")


def _previous_launcher_matches(content: str, *, open_browser: bool) -> bool:
    normalized = content.replace("\r\n", "\n").strip()
    flag = "--open" if open_browser else "--no-open"
    pattern = (
        r"@echo off\n" + re.escape(_MARKER)
        + r"\nsetlocal\nset \"WEBGPT_CODEX_UI_LANG=zh-CN\"\n"
        + r'start "" /b "([^"\n]+\\(?:pythonw|python)\.exe)" '
        + re.escape(f"-m webgpt_as_codex launcher {flag} --start-all")
        + r"\nendlocal"
    )
    return re.fullmatch(pattern, normalized, flags=re.IGNORECASE) is not None


def _legacy_launcher_content(*, open_browser: bool) -> str:
    flag = "--open" if open_browser else "--no-open"
    python = str(_pythonw())
    return (
        "@echo off\r\n"
        f"{_MARKER}\r\n"
        "setlocal\r\n"
        f'start "" /b "{python}" -m webgpt_as_codex launcher {flag} --start-all\r\n'
        "endlocal\r\n"
    )


def _legacy_launcher_matches(content: str, *, open_browser: bool) -> bool:
    normalized = content.replace("\r\n", "\n").strip()
    flag = "--open" if open_browser else "--no-open"
    pattern = (
        r"@echo off\n"
        + re.escape(_MARKER)
        + r"\nsetlocal\n"
        + r'start "" /b "([^"\n]+\\(?:pythonw|python)\.exe)" '
        + re.escape(f"-m webgpt_as_codex launcher {flag} --start-all")
        + r"\nendlocal"
    )
    return re.fullmatch(pattern, normalized, flags=re.IGNORECASE) is not None


def _redirect_generation_matches(content: str, *, open_browser: bool) -> bool:
    flag = "--open" if open_browser else "--no-open"
    normalized = content.replace("\r\n", "\n").strip()
    pause = r"  pause\n" if open_browser else ""
    pattern = (
        r"@echo off\n"
        + re.escape(_MARKER)
        + r"\nsetlocal\nset \"WEBGPT_CODEX_UI_LANG=zh-CN\"\n"
        + r'if not exist "[^"\n]+" mkdir "[^"\n]+"\n'
        + r'"([^"\n]+)" '
        + re.escape(f"-m webgpt_as_codex launcher {flag} --start-all")
        + r' > "([^"\n]+)" 2>&1\n'
        + r"if errorlevel 1 \(\n"
        + r"  echo WebGPT launcher failed\. Diagnostic output:\n"
        + r'  type "[^"\n]+"\n'
        + r"  echo Full log: [^\n]+\n"
        + pause
        + r"  exit /b 2\n"
        + r" \)\n"
        + r"endlocal"
    )
    return re.fullmatch(pattern, normalized, flags=re.IGNORECASE) is not None


def _visible_ready_generation_matches(content: str) -> bool:
    normalized = content.replace("\r\n", "\n").strip()
    pattern = (
        r"@echo off\n"
        + re.escape(_MARKER)
        + r"\nsetlocal\nset \"WEBGPT_CODEX_UI_LANG=zh-CN\"\n"
        + re.escape(
            "echo WebGPT-as-Codex: detecting environment and waiting for real readiness...\n"
            "echo (After a reboot, waiting for the network/Tailscale can take up to 3 minutes.)\n"
        )
        + r'if not exist "[^"\n]+" mkdir "[^"\n]+"\n'
        + r'"([^"\n]+)" '
        + re.escape("-m webgpt_as_codex launcher --open --start-all")
        + r' > "([^"\n]+)" 2>&1\n'
        + r"if errorlevel 1 \(\n"
        + r"  echo WebGPT launcher failed\. Diagnostic output:\n"
        + r'  type "[^"\n]+"\n'
        + r"  echo Full log: [^\n]+\n"
        + r"  pause\n"
        + r"  exit /b 2\n"
        + r" \)\n"
        + re.escape(
            "echo WebGPT-as-Codex is READY. Manager: http://127.0.0.1:9200/\n"
        )
        + r"endlocal"
    )
    return re.fullmatch(pattern, normalized, flags=re.IGNORECASE) is not None


def _isolated_rdc_suffix_generation_matches(content: str) -> bool:
    normalized = content.replace("\r\n", "\n").strip()
    pattern = (
        r"@echo off\n"
        + re.escape(_MARKER)
        + r"\nsetlocal\nset \"WEBGPT_CODEX_UI_LANG=zh-CN\"\n"
        + re.escape(
            "echo WebGPT-as-Codex: detecting environment and waiting for real readiness...\n"
            "echo (After a reboot, waiting for the network/Tailscale can take up to 3 minutes.)\n"
        )
        + r'if not exist "[^"\n]+" mkdir "[^"\n]+"\n'
        + r'"([^"\n]+)" '
        + re.escape("-m webgpt_as_codex launcher --open --start-all")
        + r' > "([^"\n]+)" 2>&1\n'
        + r"if errorlevel 1 \(\n"
        + r"  echo WebGPT launcher failed\. Diagnostic output:\n"
        + r'  type "[^"\n]+"\n'
        + r"  echo Full log: [^\n]+\n"
        + r"  pause\n"
        + r"  exit /b 2\n"
        + r" \)\n"
        + re.escape(
            "echo WebGPT-as-Codex is READY. Manager: http://127.0.0.1:9200/\n"
            "REM Remote Desktop Commander is isolated from the WebGPT-as-Codex startup path.\n"
            "REM A failure here must never turn a healthy WebGPT-as-Codex launch into a failure.\n"
        )
        + r'powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File '
        + r'"[^"\n]+\\AppData\\Local\\DesktopCommander\\start-remote\.ps1"\n'
        + r"if errorlevel 1 \(\n"
        + re.escape(
            "  echo Remote Desktop Commander start failed. WebGPT-as-Codex remains READY.\n"
        )
        + r"  echo RDC log: [^\n]+\\AppData\\Local\\DesktopCommander\\remote-agent\.log\n"
        + r"\) else \(\n"
        + re.escape("  echo Remote Desktop Commander start requested successfully.\n")
        + r"\)\n"
        + r"endlocal"
    )
    return re.fullmatch(pattern, normalized, flags=re.IGNORECASE) is not None


def _managed_file_status(
    path: Path,
    expected: str,
    *,
    legacy_matcher: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "installed": False,
            "managed": False,
            "upgradeable": False,
            "path": str(path),
        }
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "installed": True,
            "managed": False,
            "upgradeable": False,
            "path": str(path),
        }
    normalized = content.replace("\r\n", "\n")
    normalized_expected = expected.replace("\r\n", "\n")
    managed = normalized == normalized_expected and _MARKER in content
    return {
        "installed": True,
        "managed": managed,
        "upgradeable": bool(
            not managed
            and
            legacy_matcher
            and _MARKER in content
            and legacy_matcher(content)
        ),
        "path": str(path),
    }


def _install(
    path: Path,
    content: str,
    *,
    legacy_matcher: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    status = _managed_file_status(path, content, legacy_matcher=legacy_matcher)
    if status["installed"] and not status["managed"] and not status["upgradeable"]:
        return {"ok": False, "status": "existing-unmanaged-file", **status}
    operation = "updated" if status["upgradeable"] else "installed"
    path.write_text(content, encoding="utf-8", newline="")
    return {
        "ok": True,
        "status": operation,
        **_managed_file_status(path, content, legacy_matcher=legacy_matcher),
    }


def _uninstall(
    path: Path,
    expected: str,
    *,
    legacy_matcher: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    status = _managed_file_status(path, expected, legacy_matcher=legacy_matcher)
    if not status["installed"]:
        return {"ok": True, "status": "already-absent", **status}
    if not status["managed"] and not status["upgradeable"]:
        return {"ok": False, "status": "refuse-unmanaged-file", **status}
    path.unlink()
    return {
        "ok": True,
        "status": "uninstalled",
        **_managed_file_status(path, expected, legacy_matcher=legacy_matcher),
    }


def desktop_launcher(action: str) -> dict[str, Any]:
    path = desktop_dir() / _DESKTOP_NAME
    expected = _launcher_content(open_browser=True)
    legacy_matcher = lambda content: (
        _legacy_log_path_generation_matches(content, open_browser=True)
        or _pre_boot_recovery_generation_matches(content, open_browser=True)
        or _pre_guard_generation_matches(content, open_browser=True)
        or _prestartless_generation_matches(content, open_browser=True)
        or _legacy_launcher_matches(content, open_browser=True)
        or _previous_launcher_matches(content, open_browser=True)
        or _redirect_generation_matches(content, open_browser=True)
        or _visible_ready_generation_matches(content)
        or _isolated_rdc_suffix_generation_matches(content)
    )
    if action == "status":
        return {
            "ok": True,
            "status": "present" if path.exists() else "absent",
            **_managed_file_status(path, expected, legacy_matcher=legacy_matcher),
        }
    if action == "install":
        result = _install(path, expected, legacy_matcher=legacy_matcher)
        if result.get("ok"):
            result["rdc_launcher"] = _ensure_rdc_remote_launcher()
            result["rdc_webgpt_recovery"] = _ensure_rdc_webgpt_recovery_bridge()
        return result
    if action == "uninstall":
        return _uninstall(path, expected, legacy_matcher=legacy_matcher)
    raise ValueError(action)


def autostart(action: str) -> dict[str, Any]:
    path = startup_dir() / _AUTOSTART_NAME
    expected = _launcher_content(open_browser=False)
    legacy_matcher = lambda content: (
        _legacy_log_path_generation_matches(content, open_browser=False)
        or _pre_boot_recovery_generation_matches(content, open_browser=False)
        or _pre_guard_generation_matches(content, open_browser=False)
        or _prestartless_generation_matches(content, open_browser=False)
        or _legacy_launcher_matches(content, open_browser=False)
        or _previous_launcher_matches(content, open_browser=False)
        or _redirect_generation_matches(content, open_browser=False)
    )
    if action == "status":
        return {
            "ok": True,
            "status": "present" if path.exists() else "absent",
            **_managed_file_status(path, expected, legacy_matcher=legacy_matcher),
        }
    if action == "install":
        return _install(path, expected, legacy_matcher=legacy_matcher)
    if action == "uninstall":
        return _uninstall(path, expected, legacy_matcher=legacy_matcher)
    raise ValueError(action)


def _external_backend_wait_seconds() -> float:
    raw = os.getenv(_EXTERNAL_BACKEND_WAIT_ENV)
    if raw is None:
        return _EXTERNAL_BACKEND_WAIT_DEFAULT
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _EXTERNAL_BACKEND_WAIT_DEFAULT


def _boot_recovery_enabled() -> bool:
    return os.getenv(_BOOT_RECOVERY_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _retryable_start_result(result: dict[str, Any], *, boot_recovery: bool) -> bool:
    if result.get("fully_ready"):
        return False
    if boot_recovery:
        # At logon the local services can be healthy before Windows networking,
        # Tailscale, Funnel and the OAuth edge settle. Treat not-ready as transient
        # for the bounded boot-recovery window.
        return True
    missing = result.get("required_unmanaged_missing")
    return isinstance(missing, list) and bool(missing)


def _start_all_until_ready(supervisor: RuntimeSupervisor) -> dict[str, Any]:
    result = supervisor.start_all(include_manager=False)
    if result.get("fully_ready"):
        return result

    boot_recovery = _boot_recovery_enabled()
    if not _retryable_start_result(result, boot_recovery=boot_recovery):
        return result

    wait_seconds = _external_backend_wait_seconds()
    deadline = time.monotonic() + wait_seconds
    attempts = 1
    poll = _BOOT_RECOVERY_POLL if boot_recovery else _EXTERNAL_BACKEND_POLL
    while time.monotonic() < deadline:
        time.sleep(min(poll, max(0.0, deadline - time.monotonic())))
        attempts += 1
        result = supervisor.start_all(include_manager=False, edge_prereq_wait=15.0)
        if not _retryable_start_result(result, boot_recovery=boot_recovery):
            break
    result["launcher_backend_wait_attempts"] = attempts
    result["launcher_backend_wait_budget_seconds"] = wait_seconds
    result["launcher_boot_recovery"] = boot_recovery
    return result



def _start_rdc_external_backend() -> dict[str, Any]:
    """Best-effort Windows RDC recovery that never gates WebGPT readiness."""
    if not sys.platform.startswith("win"):
        return {
            "ok": True,
            "attempted": False,
            "status": "not-windows",
            "gates_webgpt_ready": False,
        }

    helper = _ensure_rdc_remote_launcher()
    path = _rdc_remote_launcher_path()
    base: dict[str, Any] = {
        "ok": bool(helper.get("ok")),
        "attempted": False,
        "status": "helper-not-ready",
        "path": str(path),
        "helper": helper,
        "gates_webgpt_ready": False,
    }
    if not helper.get("ok"):
        return base
    if helper.get("status") == "preserved-existing-unmanaged-file":
        return {
            **base,
            "ok": True,
            "status": "preserved-unmanaged-helper",
        }
    if not path.exists():
        return {
            **base,
            "ok": False,
            "status": "helper-missing-after-ensure",
        }

    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_RDC_START_TIMEOUT_SECONDS,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return {
            **base,
            "ok": False,
            "attempted": True,
            "status": "powershell-not-found",
        }
    except subprocess.TimeoutExpired:
        return {
            **base,
            "ok": False,
            "attempted": True,
            "status": "start-timeout",
            "timeout_seconds": _RDC_START_TIMEOUT_SECONDS,
        }

    return {
        **base,
        "ok": completed.returncode == 0,
        "attempted": True,
        "status": (
            "started-or-already-healthy"
            if completed.returncode == 0
            else "start-failed"
        ),
        "returncode": completed.returncode,
    }

def _wait_public_remote_ready() -> tuple[bool | None, dict[str, Any]]:
    health, evidence = probe_public_remote()
    attempts = 1
    wait_seconds = _external_backend_wait_seconds()
    if health is False and wait_seconds > 0:
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            time.sleep(
                min(
                    _EXTERNAL_BACKEND_POLL,
                    max(0.0, deadline - time.monotonic()),
                )
            )
            attempts += 1
            health, evidence = probe_public_remote()
            if health is not False:
                break
    details = dict(evidence)
    details["launcher_public_wait_attempts"] = attempts
    details["launcher_public_wait_budget_seconds"] = wait_seconds
    return health, details


def run_launcher(*, open_browser: bool = True, start_all: bool = True) -> dict[str, Any]:
    supervisor = RuntimeSupervisor()
    manager = supervisor.start("manager")
    runtimes = _start_all_until_ready(supervisor) if start_all else None
    opened = False
    browser_mode = "not-requested"
    if manager.get("ok") and open_browser:
        opened, browser_mode = _open_manager_url("http://127.0.0.1:9200/")
    runtimes_ready = runtimes is None or bool(runtimes.get("fully_ready"))
    public_remote_ready: bool | None = None
    public_remote: dict[str, Any] = {
        "attempted": False,
        "reason": "start-all-disabled" if not start_all else "local-runtimes-not-ready",
    }
    if start_all and runtimes_ready:
        public_remote_ready, public_remote = _wait_public_remote_ready()
    public_ready = public_remote_ready is not False
    browser_ready = (not open_browser) or opened
    fully_ready = runtimes_ready and public_ready
    remote_desktop_commander: dict[str, Any] = {
        "ok": True,
        "attempted": False,
        "status": "skipped",
        "reason": "start-all-disabled" if not start_all else "webgpt-not-ready",
        "gates_webgpt_ready": False,
    }
    if start_all and fully_ready:
        remote_desktop_commander = _start_rdc_external_backend()
    return {
        "ok": bool(manager.get("ok")) and fully_ready and browser_ready,
        "fully_ready": fully_ready,
        "manager": manager,
        "start_all": runtimes,
        "public_remote_ready": public_remote_ready,
        "public_remote": public_remote,
        "browser_open_requested": open_browser,
        "browser_open_dispatched": opened,
        "browser_open_mode": browser_mode,
        "runtime_lifetime_independent_of_browser": True,
        "remote_desktop_commander": remote_desktop_commander,
    }

def cli_launcher(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex launcher")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--open", action="store_true", dest="open_browser")
    group.add_argument("--no-open", action="store_false", dest="open_browser")
    parser.set_defaults(open_browser=True)
    parser.add_argument("--start-all", action="store_true")
    args = parser.parse_args(argv)
    result = run_launcher(open_browser=args.open_browser, start_all=args.start_all)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


def cli_desktop_launcher(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex desktop-launcher")
    parser.add_argument("action", choices=("install", "status", "uninstall"))
    args = parser.parse_args(argv)
    result = desktop_launcher(args.action)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


def cli_autostart(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex autostart")
    parser.add_argument("action", choices=("install", "status", "uninstall"))
    args = parser.parse_args(argv)
    result = autostart(args.action)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2
