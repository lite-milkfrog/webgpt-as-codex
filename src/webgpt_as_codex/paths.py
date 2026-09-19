from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    source_root = repo_root()
    if (
        (source_root / "components").is_dir()
        and (source_root / "manager" / "static" / "index.html").is_file()
    ):
        return source_root
    installed_root = Path(sys.prefix) / "share" / "webgpt-as-codex"
    if (
        (installed_root / "components").is_dir()
        and (installed_root / "manager" / "static" / "index.html").is_file()
    ):
        return installed_root
    return source_root


def _windows_local_appdata() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "Local AppData")
        if value:
            return Path(value)
    except (OSError, ImportError):
        pass
    drive = os.getenv("SystemDrive", "C:")
    username = getpass.getuser()
    candidate = Path(drive) / "Users" / username / "AppData" / "Local"
    return candidate if candidate.parent.parent.exists() else None


def user_home() -> Path:
    explicit = os.getenv("USERPROFILE") or os.getenv("HOME")
    if explicit:
        return Path(explicit)
    win_local = _windows_local_appdata()
    if win_local and len(win_local.parents) >= 2:
        return win_local.parents[1]
    drive = os.getenv("SystemDrive", "C:")
    return Path(drive) / "Users" / getpass.getuser()


def state_root() -> Path:
    override = os.getenv("WEBGPT_CODEX_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    local = os.getenv("LOCALAPPDATA")
    if local:
        return Path(local) / "WebGPT-as-Codex"
    win_local = _windows_local_appdata()
    if win_local:
        return win_local / "WebGPT-as-Codex"
    home = os.getenv("HOME") or os.getenv("USERPROFILE")
    if home:
        return Path(home) / ".local" / "state" / "webgpt-as-codex"
    return Path.cwd() / ".local-state"


def ensure_state_dirs() -> Path:
    root = state_root()
    for name in (
        "logs",
        "pids",
        "downloads",
        "config",
        "secrets",
        "bin",
        "doctor",
        "bootstrap",
        "repair",
        "handoffs",
        "loop",
        "runtime",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root
