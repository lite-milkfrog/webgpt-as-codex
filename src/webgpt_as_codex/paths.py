from __future__ import annotations

import getpass
import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    for name in ("logs", "pids", "downloads", "config", "secrets"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root
