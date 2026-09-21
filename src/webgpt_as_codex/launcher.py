from __future__ import annotations

import argparse
import ctypes
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

from .paths import state_root, user_home
from .runtime import RuntimeSupervisor

_MARKER = "REM WebGPT-as-Codex managed launcher"
_DESKTOP_NAME = "WebGPT-as-Codex.cmd"
_AUTOSTART_NAME = "WebGPT-as-Codex-Autostart.cmd"
_EXTERNAL_BACKEND_WAIT_ENV = "WEBGPT_CODEX_EXTERNAL_BACKEND_WAIT_SECONDS"
_EXTERNAL_BACKEND_WAIT_DEFAULT = 60.0
_EXTERNAL_BACKEND_POLL = 2.0


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


def _local_prestart_content(log_path: Path) -> str:
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
    log_path = log_root / ("desktop-launcher.log" if open_browser else "autostart.log")
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
    return (
        "@echo off\r\n"
        f"{_MARKER}\r\n"
        "setlocal\r\n"
        'set "WEBGPT_CODEX_UI_LANG=zh-CN"\r\n'
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


def _pre_guard_generation_matches(content: str, *, open_browser: bool) -> bool:
    python = str(Path(sys.executable))
    log_path = _launcher_log_dir() / (
        "desktop-launcher.log" if open_browser else "autostart.log"
    )
    expected = _launcher_content(open_browser=open_browser).replace(
        _python_runtime_guard_content(python, log_path, pause=open_browser),
        "",
        1,
    )
    return content.replace("\r\n", "\n") == expected.replace("\r\n", "\n")


def _prestartless_generation_matches(content: str, *, open_browser: bool) -> bool:
    flag = "--open" if open_browser else "--no-open"
    python = str(Path(sys.executable))
    log_path = _launcher_log_dir() / (
        "desktop-launcher.log" if open_browser else "autostart.log"
    )
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
        _pre_guard_generation_matches(content, open_browser=True)
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
        return _install(path, expected, legacy_matcher=legacy_matcher)
    if action == "uninstall":
        return _uninstall(path, expected, legacy_matcher=legacy_matcher)
    raise ValueError(action)


def autostart(action: str) -> dict[str, Any]:
    path = startup_dir() / _AUTOSTART_NAME
    expected = _launcher_content(open_browser=False)
    legacy_matcher = lambda content: (
        _pre_guard_generation_matches(content, open_browser=False)
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


def _start_all_until_ready(supervisor: RuntimeSupervisor) -> dict[str, Any]:
    result = supervisor.start_all(include_manager=False)
    if result.get("fully_ready"):
        return result
    missing = result.get("required_unmanaged_missing")
    if not isinstance(missing, list) or not missing:
        return result
    wait_seconds = _external_backend_wait_seconds()
    deadline = time.monotonic() + wait_seconds
    attempts = 1
    while time.monotonic() < deadline:
        time.sleep(min(_EXTERNAL_BACKEND_POLL, max(0.0, deadline - time.monotonic())))
        attempts += 1
        result = supervisor.start_all(include_manager=False, edge_prereq_wait=15.0)
        if result.get("fully_ready"):
            break
        missing = result.get("required_unmanaged_missing")
        if not isinstance(missing, list) or not missing:
            break
    result["launcher_backend_wait_attempts"] = attempts
    result["launcher_backend_wait_budget_seconds"] = wait_seconds
    return result


def run_launcher(*, open_browser: bool = True, start_all: bool = True) -> dict[str, Any]:
    supervisor = RuntimeSupervisor()
    manager = supervisor.start("manager")
    runtimes = _start_all_until_ready(supervisor) if start_all else None
    opened = False
    browser_mode = "not-requested"
    if manager.get("ok") and open_browser:
        opened, browser_mode = _open_manager_url("http://127.0.0.1:9200/")
    runtimes_ready = runtimes is None or bool(runtimes.get("fully_ready"))
    browser_ready = (not open_browser) or opened
    return {
        "ok": bool(manager.get("ok")) and runtimes_ready and browser_ready,
        "fully_ready": runtimes_ready,
        "manager": manager,
        "start_all": runtimes,
        "browser_open_requested": open_browser,
        "browser_open_dispatched": opened,
        "browser_open_mode": browser_mode,
        "runtime_lifetime_independent_of_browser": True,
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
