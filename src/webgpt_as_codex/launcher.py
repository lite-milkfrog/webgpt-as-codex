from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .paths import user_home
from .runtime import RuntimeSupervisor

_MARKER = "REM WebGPT-as-Codex managed launcher"
_DESKTOP_NAME = "WebGPT-as-Codex.cmd"
_AUTOSTART_NAME = "WebGPT-as-Codex-Autostart.cmd"


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


def _open_manager_url(url: str) -> tuple[bool, str]:
    edge = _edge_reuse_target()
    if edge and _launch_edge_profile(edge[0], edge[1], url):
        return True, "existing-edge-profile"
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True, "windows-default-url-handler"
        except OSError:
            pass
    return bool(webbrowser.open(url)), "default-webbrowser-fallback"


def _launcher_content(*, open_browser: bool) -> str:
    flag = "--open" if open_browser else "--no-open"
    python = str(_pythonw())
    return (
        "@echo off\r\n"
        f"{_MARKER}\r\n"
        "setlocal\r\n"
        'set "WEBGPT_CODEX_UI_LANG=zh-CN"\r\n'
        f'start "" /b "{python}" -m webgpt_as_codex launcher {flag} --start-all\r\n'
        "endlocal\r\n"
    )


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
    return {
        "installed": True,
        "managed": normalized == normalized_expected and _MARKER in content,
        "upgradeable": bool(
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
    legacy_matcher = lambda content: _legacy_launcher_matches(
        content,
        open_browser=True,
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
    legacy_matcher = lambda content: _legacy_launcher_matches(
        content,
        open_browser=False,
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


def run_launcher(*, open_browser: bool = True, start_all: bool = True) -> dict[str, Any]:
    supervisor = RuntimeSupervisor()
    manager = supervisor.start("manager")
    runtimes = supervisor.start_all(include_manager=False) if start_all else None
    opened = False
    browser_mode = "not-requested"
    if manager.get("ok") and open_browser:
        opened, browser_mode = _open_manager_url("http://127.0.0.1:9200/")
    return {
        "ok": bool(manager.get("ok")) and (runtimes is None or bool(runtimes.get("ok"))),
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
