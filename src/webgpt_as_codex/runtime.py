from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .discovery import discover_all, process_health, process_snapshot
from .gateway import mcpjungle_binary
from .paths import ensure_state_dirs, state_root
from .registry import load_components
from .stateio import atomic_write_json

ArgvBuilder = Callable[[], list[str]]
CwdBuilder = Callable[[], Path]


@dataclass(frozen=True)
class RuntimeSpec:
    id: str
    display_name: str
    endpoint: str
    health_url: str
    argv_builder: ArgvBuilder
    cwd_builder: CwdBuilder


def _mcpjungle_argv() -> list[str]:
    root = ensure_state_dirs()
    binary = mcpjungle_binary()
    return [
        str(binary),
        "start",
        "--port",
        "9330",
        "--sqlite-db-path",
        str(root / "gateway" / "runtime.db"),
    ]


def _mcpjungle_cwd() -> Path:
    path = ensure_state_dirs() / "gateway"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _manager_argv() -> list[str]:
    return [
        sys.executable,
        "-m",
        "webgpt_as_codex",
        "manager",
        "--host",
        "127.0.0.1",
        "--port",
        "9200",
    ]


def _manager_cwd() -> Path:
    return ensure_state_dirs()


RUNTIME_SPECS: dict[str, RuntimeSpec] = {
    "manager": RuntimeSpec(
        "manager",
        "WebGPT-as-Codex Manager",
        "http://127.0.0.1:9200",
        "http://127.0.0.1:9200/healthz",
        _manager_argv,
        _manager_cwd,
    ),
    "mcpjungle": RuntimeSpec(
        "mcpjungle",
        "MCPJungle",
        "http://127.0.0.1:9330/mcp",
        "http://127.0.0.1:9330/health",
        _mcpjungle_argv,
        _mcpjungle_cwd,
    ),
}

MANAGER_RESTARTABLE = frozenset({"mcpjungle"})


def _pid_path(component_id: str) -> Path:
    return ensure_state_dirs() / "pids" / f"{component_id}.json"


def _state_path() -> Path:
    return ensure_state_dirs() / "runtime" / "last-state.json"


def _log_path(component_id: str) -> Path:
    root = ensure_state_dirs() / "logs" / "runtime"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{component_id}.log"


def _listener_up(endpoint: str, timeout: float = 0.35) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(endpoint)
    if not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    import socket

    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except OSError:
        return False


def _health_ready(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status < 500
    except (OSError, TimeoutError, ValueError, urllib.error.URLError):
        return False


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _process_birth_token(pid: int) -> str | None:
    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            creation = ctypes.wintypes.FILETIME()
            exit_time = ctypes.wintypes.FILETIME()
            kernel = ctypes.wintypes.FILETIME()
            user = ctypes.wintypes.FILETIME()
            ok = ctypes.windll.kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel),
                ctypes.byref(user),
            )
            if not ok:
                return None
            value = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
            return f"win-filetime:{value}"
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    stat = Path(f"/proc/{pid}/stat")
    try:
        fields = stat.read_text(encoding="utf-8").split()
        return f"proc-start:{fields[21]}"
    except (OSError, IndexError):
        return None


def _process_image_name(pid: int) -> str | None:
    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            size = ctypes.wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(
                handle,
                0,
                buffer,
                ctypes.byref(size),
            )
            return Path(buffer.value).name.lower() if ok else None
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        return Path(os.readlink(f"/proc/{pid}/exe")).name.lower()
    except OSError:
        return None


def _load_pid_record(component_id: str) -> dict[str, Any] | None:
    path = _pid_path(component_id)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"invalid": True}
    return value if isinstance(value, dict) else {"invalid": True}


def _remove_pid_record(component_id: str) -> None:
    try:
        _pid_path(component_id).unlink()
    except FileNotFoundError:
        pass


def _owned_pid(component_id: str) -> tuple[int | None, str]:
    record = _load_pid_record(component_id)
    if not record:
        return None, "none"
    if record.get("component_id") != component_id:
        _remove_pid_record(component_id)
        return None, "stale-component"
    try:
        pid = int(record["pid"])
    except (KeyError, TypeError, ValueError):
        _remove_pid_record(component_id)
        return None, "stale-record"
    if not _pid_exists(pid):
        _remove_pid_record(component_id)
        return None, "stale-dead"
    actual_birth = _process_birth_token(pid)
    if not actual_birth or actual_birth != record.get("birth_token"):
        _remove_pid_record(component_id)
        return None, "stale-pid-reused"
    actual_image = _process_image_name(pid)
    expected_image = record.get("image_name")
    if expected_image and actual_image and actual_image != expected_image:
        _remove_pid_record(component_id)
        return None, "stale-image"
    return pid, "owned"


def _write_pid_record(component_id: str, pid: int, log_path: Path) -> None:
    birth = _process_birth_token(pid)
    if not birth:
        raise RuntimeError(f"could not establish process identity for {component_id}")
    payload = {
        "schema": 1,
        "component_id": component_id,
        "pid": pid,
        "birth_token": birth,
        "image_name": _process_image_name(pid),
        "started_at": datetime.now(UTC).isoformat(),
        "log_file": str(log_path.relative_to(state_root())),
    }
    path = _pid_path(component_id)
    atomic_write_json(path, payload)


def _spawn(spec: RuntimeSpec) -> int:
    argv = spec.argv_builder()
    if not argv:
        raise RuntimeError(f"{spec.id} has no repository-owned launch adapter")
    executable = Path(argv[0])
    if executable.is_absolute() and not executable.exists():
        raise FileNotFoundError(executable)
    log_path = _log_path(spec.id)
    log = log_path.open("ab")
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    try:
        process = subprocess.Popen(
            argv,
            cwd=spec.cwd_builder(),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=creationflags,
        )
    finally:
        log.close()
    _write_pid_record(spec.id, process.pid, log_path)
    return process.pid


def _wait_ready(spec: RuntimeSpec, pid: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            return False
        if _health_ready(spec.health_url):
            return True
        time.sleep(0.25)
    return False


def _wait_dead(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            return True
        time.sleep(0.1)
    return not _pid_exists(pid)


def _bounded_stop(pid: int, graceful_seconds: float = 5.0) -> str:
    if os.name == "nt":
        ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
        if ctrl_break is not None:
            try:
                os.kill(pid, ctrl_break)
            except OSError:
                pass
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return "already-exited"
    if _wait_dead(pid, graceful_seconds):
        return "graceful"
    try:
        os.kill(pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
    except OSError:
        return "already-exited"
    if not _wait_dead(pid, 3.0):
        raise RuntimeError(f"process {pid} did not stop within bounded shutdown")
    return "forced"


class RuntimeSupervisor:
    def __init__(self, specs: dict[str, RuntimeSpec] | None = None) -> None:
        self.specs = dict(specs or RUNTIME_SPECS)

    def status(self, component_id: str) -> dict[str, Any]:
        spec = self.specs.get(component_id)
        if spec is None:
            return {
                "component_id": component_id,
                "managed": False,
                "owned": False,
                "listener_up": None,
                "state": "unmanaged",
            }
        pid, ownership = _owned_pid(component_id)
        listener = _listener_up(spec.endpoint)
        if pid is not None and listener:
            state = "running-owned"
        elif pid is not None:
            state = "owned-unhealthy"
        elif listener:
            state = "healthy-unmanaged"
        else:
            state = "stopped"
        return {
            "component_id": component_id,
            "display_name": spec.display_name,
            "managed": True,
            "owned": pid is not None,
            "pid": pid,
            "listener_up": listener,
            "ownership_evidence": ownership,
            "state": state,
        }

    def start(self, component_id: str) -> dict[str, Any]:
        spec = self.specs.get(component_id)
        if spec is None:
            return {
                "ok": False,
                "component_id": component_id,
                "status": "not-repository-managed",
            }
        before = self.status(component_id)
        if before["listener_up"]:
            return {
                "ok": True,
                "component_id": component_id,
                "status": "preserved-owned" if before["owned"] else "preserved-unmanaged",
                "pid": before["pid"],
            }
        if before["owned"]:
            return {
                "ok": False,
                "component_id": component_id,
                "status": "owned-process-unhealthy",
                "pid": before["pid"],
            }
        pid = _spawn(spec)
        if not _wait_ready(spec, pid):
            return {
                "ok": False,
                "component_id": component_id,
                "status": "started-but-not-ready",
                "pid": pid,
            }
        return {"ok": True, "component_id": component_id, "status": "started", "pid": pid}

    def stop(self, component_id: str) -> dict[str, Any]:
        if component_id not in self.specs:
            return {
                "ok": False,
                "component_id": component_id,
                "status": "not-repository-managed",
            }
        pid, ownership = _owned_pid(component_id)
        if pid is None:
            return {
                "ok": False,
                "component_id": component_id,
                "status": "not-owned",
                "ownership_evidence": ownership,
            }
        mode = _bounded_stop(pid)
        _remove_pid_record(component_id)
        return {
            "ok": True,
            "component_id": component_id,
            "status": "stopped",
            "shutdown": mode,
        }

    def restart(self, component_id: str) -> dict[str, Any]:
        if component_id not in self.specs:
            return {
                "ok": False,
                "component_id": component_id,
                "status": "not-repository-managed",
            }
        current = self.status(component_id)
        if current["listener_up"] and not current["owned"]:
            return {
                "ok": False,
                "component_id": component_id,
                "status": "healthy-but-unmanaged",
            }
        stopped: dict[str, Any] | None = None
        if current["owned"]:
            stopped = self.stop(component_id)
            if not stopped.get("ok"):
                return stopped
        started = self.start(component_id)
        return {
            "ok": bool(started.get("ok")),
            "component_id": component_id,
            "status": "restarted" if started.get("ok") else started.get("status"),
            "stop": stopped,
            "start": started,
        }

    def start_all(self, *, include_manager: bool = False) -> dict[str, Any]:
        components = load_components()
        discovery = discover_all(components)
        snapshot = process_snapshot()
        rows: list[dict[str, Any]] = []
        required_unmanaged_missing: list[str] = []
        for component_id, component in sorted(components.items()):
            live = discovery.get(component_id, {})
            process_up = process_health(component, snapshot)
            if live.get("listener_up") is True or (
                component.default_endpoint is None and process_up is True
            ):
                owned_pid, _ = _owned_pid(component_id)
                rows.append(
                    {
                        "component_id": component_id,
                        "status": "preserved-owned" if owned_pid else "preserved-unmanaged",
                        "ok": True,
                        "evidence": (
                            "listener"
                            if live.get("listener_up") is True
                            else "process"
                        ),
                    }
                )
            elif component_id in self.specs and component.enabled_by_default:
                rows.append(self.start(component_id))
            else:
                if component.required:
                    required_unmanaged_missing.append(component_id)
                rows.append(
                    {
                        "component_id": component_id,
                        "status": "unmanaged-not-started",
                        "ok": not component.required,
                    }
                )
        if include_manager:
            rows.append(self.start("manager"))
        managed_ok = all(
            row.get("ok", False)
            for row in rows
            if row["component_id"] in self.specs
        )
        result = {
            "ok": managed_ok,
            "status": (
                "complete"
                if managed_ok and not required_unmanaged_missing
                else "complete-with-unmanaged-required"
                if managed_ok
                else "managed-runtime-failure"
            ),
            "fully_ready": managed_ok and not required_unmanaged_missing,
            "required_unmanaged_missing": required_unmanaged_missing,
            "preserves_healthy_services": True,
            "arbitrary_command_surface": False,
            "results": rows,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        root = ensure_state_dirs()
        (root / "runtime").mkdir(parents=True, exist_ok=True)
        atomic_write_json(_state_path(), result)
        return result


def manager_start_all_executor(_contract: object, _payload: dict[str, Any]) -> dict[str, Any]:
    return RuntimeSupervisor().start_all(include_manager=False)


def manager_restart_executor(_contract: object, payload: dict[str, Any]) -> dict[str, Any]:
    component_id = payload.get("component")
    if not isinstance(component_id, str) or component_id not in MANAGER_RESTARTABLE:
        return {
            "ok": False,
            "status": "invalid-component-scope",
            "allowed_components": sorted(MANAGER_RESTARTABLE),
        }
    return RuntimeSupervisor().restart(component_id)


def cli_status(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex status")
    parser.add_argument("component", nargs="?")
    args = parser.parse_args(argv)
    supervisor = RuntimeSupervisor()
    if args.component:
        result: Any = supervisor.status(args.component)
    else:
        ids = sorted(set(load_components()) | set(supervisor.specs))
        result = {"components": [supervisor.status(component_id) for component_id in ids]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cli_start(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex start")
    parser.add_argument("component", nargs="?")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    if args.all:
        result = RuntimeSupervisor().start_all(include_manager=False)
    elif args.component:
        result = RuntimeSupervisor().start(args.component)
    else:
        parser.error("provide COMPONENT or --all")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


def cli_stop(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex stop")
    parser.add_argument("component")
    args = parser.parse_args(argv)
    result = RuntimeSupervisor().stop(args.component)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


def cli_restart(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex restart")
    parser.add_argument("component")
    args = parser.parse_args(argv)
    result = RuntimeSupervisor().restart(args.component)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2
