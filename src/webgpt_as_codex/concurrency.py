from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .paths import ensure_state_dirs, user_home
from .runtime import _bounded_stop, _pid_exists, _process_birth_token, _process_image_name
from .stateio import atomic_write_json

SHARED_SERENA_PORT = 9121
DEFAULT_SERENA_PORTS = tuple(range(9410, 9490))
_DEFAULT_LEASE_SECONDS = 30 * 60


class LeaseBusy(RuntimeError):
    pass


class BindingMismatch(RuntimeError):
    pass


def _now() -> float:
    return time.time()


def _key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


@contextmanager
def _exclusive_guard(path: Path, *, wait_seconds: float = 2.0, stale_seconds: float = 30.0) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}:{uuid.uuid4().hex}"
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = _now() - path.stat().st_mtime
            except OSError:
                age = 0.0
            if age > stale_seconds:
                try:
                    path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise LeaseBusy(f"state guard busy: {path.name}")
            time.sleep(0.02)
            continue
        try:
            os.write(fd, token.encode("utf-8"))
        finally:
            os.close(fd)
        break
    try:
        yield
    finally:
        try:
            if path.read_text(encoding="utf-8") == token:
                path.unlink()
        except OSError:
            pass


def _process_identity(pid: int) -> dict[str, Any] | None:
    if not _pid_exists(pid):
        return None
    birth = _process_birth_token(pid)
    if not birth:
        return None
    return {
        "pid": pid,
        "birth_token": birth,
        "image_name": _process_image_name(pid),
    }


def _identity_matches(receipt: dict[str, Any]) -> bool:
    try:
        pid = int(receipt["pid"])
    except (KeyError, TypeError, ValueError):
        return False
    current = _process_identity(pid)
    if current is None or current["birth_token"] != receipt.get("birth_token"):
        return False
    expected_image = receipt.get("image_name")
    return not (expected_image and current.get("image_name") and current["image_name"] != expected_image)


def _port_available(port: int) -> bool:
    if port == SHARED_SERENA_PORT:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _listener_open(port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_listener(port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _listener_open(port):
            return True
        time.sleep(0.1)
    return _listener_open(port)


def _stop_verified_process(receipt: dict[str, Any]) -> str:
    pid = int(receipt["pid"])
    try:
        return _bounded_stop(pid)
    except RuntimeError:
        # A shutdown timeout/non-zero can race with real process exit. Re-check
        # identity in a bounded observation window before deciding whether any
        # second destructive action would be legal.
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if _process_identity(pid) is None:
                return "post-state-exited"
            time.sleep(0.05)
        if _process_identity(pid) is None:
            return "post-state-exited"
        raise


def _serena_executable() -> Path:
    configured = os.getenv("WEBGPT_CODEX_SERENA_EXE")
    if configured:
        return Path(configured).expanduser().resolve()
    home = user_home()
    candidate = home / ".local" / "bin" / ("serena.exe" if os.name == "nt" else "serena")
    if candidate.is_file():
        return candidate
    raise FileNotFoundError("Serena executable not found; set WEBGPT_CODEX_SERENA_EXE")


def _launch_serena(project: Path, port: int, slot_dir: Path) -> dict[str, Any]:
    if port == SHARED_SERENA_PORT:
        raise ValueError("shared Serena port 9121 is never managed by the slot pool")
    executable = _serena_executable()
    argv = [
        str(executable),
        "start-mcp-server",
        "--project",
        str(project),
        "--transport",
        "streamable-http",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--enable-web-dashboard",
        "false",
        "--open-web-dashboard",
        "false",
        "--enable-gui-log-window",
        "false",
    ]
    slot_dir.mkdir(parents=True, exist_ok=True)
    log_path = slot_dir / "serena.log"
    env = os.environ.copy()
    home = str(user_home())
    env.setdefault("HOME", home)
    env.setdefault("USERPROFILE", home)
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
            cwd=project,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=creationflags,
        )
    finally:
        log.close()
    identity = _process_identity(process.pid)
    if identity is None:
        try:
            _bounded_stop(process.pid, graceful_seconds=1.0)
        except RuntimeError:
            pass
        raise RuntimeError("could not establish Serena slot process identity")
    return {
        **identity,
        "launch_fingerprint": hashlib.sha256(
            json.dumps(argv, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "log_file": str(log_path),
    }


class SerenaSlotPool:
    def __init__(
        self,
        *,
        ports: tuple[int, ...] = DEFAULT_SERENA_PORTS,
        lease_seconds: float = _DEFAULT_LEASE_SECONDS,
    ) -> None:
        if SHARED_SERENA_PORT in ports:
            raise ValueError("shared Serena port 9121 cannot be part of the pool")
        self.ports = tuple(dict.fromkeys(int(port) for port in ports))
        self.lease_seconds = float(lease_seconds)
        self.root = ensure_state_dirs() / "concurrency" / "serena-slots"
        self.root.mkdir(parents=True, exist_ok=True)
        self.guard = self.root / ".pool.lock"

    def _receipts(self) -> list[tuple[Path, dict[str, Any]]]:
        rows: list[tuple[Path, dict[str, Any]]] = []
        for path in self.root.glob("slot-*.json"):
            receipt = _read_json(path)
            if receipt:
                rows.append((path, receipt))
        return rows

    def _write(self, path: Path, receipt: dict[str, Any]) -> None:
        atomic_write_json(path, receipt, sort_keys=True)

    def _live_or_remove_stale(self, path: Path, receipt: dict[str, Any]) -> bool:
        if receipt.get("port") == SHARED_SERENA_PORT:
            return False
        if _identity_matches(receipt):
            if receipt.get("owner_id") and float(receipt.get("expires_at", 0)) <= _now():
                receipt["owner_id"] = None
                receipt["released_at"] = _now()
                receipt["release_reason"] = "owner-lease-expired"
                self._write(path, receipt)
            return True
        path.unlink(missing_ok=True)
        return False

    def acquire(self, project: str | Path, owner_id: str) -> dict[str, Any]:
        project_path = Path(project).expanduser().resolve()
        if not project_path.is_dir():
            raise FileNotFoundError(project_path)
        if not owner_id:
            raise ValueError("owner_id is required")
        project_id = _key(str(project_path).casefold())
        with _exclusive_guard(self.guard):
            live_rows: list[tuple[Path, dict[str, Any]]] = []
            for path, receipt in self._receipts():
                if self._live_or_remove_stale(path, receipt):
                    live_rows.append((path, receipt))

            for path, receipt in live_rows:
                if receipt.get("project_id") != project_id:
                    continue
                if receipt.get("owner_id") == owner_id:
                    return {**receipt, "status": "already-owned"}
                if receipt.get("owner_id") is None:
                    receipt.update(
                        owner_id=owner_id,
                        acquired_at=_now(),
                        heartbeat_at=_now(),
                        expires_at=_now() + self.lease_seconds,
                    )
                    self._write(path, receipt)
                    return {**receipt, "status": "reused"}

            used_ports = {int(receipt["port"]) for _, receipt in live_rows if "port" in receipt}
            port = next(
                (
                    candidate
                    for candidate in self.ports
                    if candidate not in used_ports and _port_available(candidate)
                ),
                None,
            )
            if port is None:
                raise LeaseBusy("no isolated Serena slot port is available")

            slot_dir = self.root / f"slot-{port}"
            launch = _launch_serena(project_path, port, slot_dir)
            if not _wait_listener(port):
                identity = _process_identity(int(launch["pid"]))
                if identity and identity["birth_token"] == launch["birth_token"]:
                    try:
                        _bounded_stop(int(launch["pid"]), graceful_seconds=1.0)
                    except RuntimeError:
                        pass
                raise RuntimeError(f"Serena slot {port} did not become ready")

            receipt = {
                "schema_version": 1,
                "kind": "serena-fixed-project-slot",
                "managed_by": "webgpt-as-codex",
                "project_id": project_id,
                "project_path": str(project_path),
                "owner_id": owner_id,
                "port": port,
                "endpoint": f"http://127.0.0.1:{port}/mcp",
                "pid": launch["pid"],
                "birth_token": launch["birth_token"],
                "image_name": launch.get("image_name"),
                "launch_fingerprint": launch["launch_fingerprint"],
                "created_at": _now(),
                "acquired_at": _now(),
                "heartbeat_at": _now(),
                "expires_at": _now() + self.lease_seconds,
            }
            path = self.root / f"slot-{port}.json"
            self._write(path, receipt)
            return {**receipt, "status": "started"}

    def heartbeat(self, port: int, owner_id: str) -> dict[str, Any]:
        if port == SHARED_SERENA_PORT:
            raise ValueError("shared Serena port 9121 is excluded")
        path = self.root / f"slot-{port}.json"
        with _exclusive_guard(self.guard):
            receipt = _read_json(path)
            if not receipt or receipt.get("owner_id") != owner_id:
                raise LeaseBusy("Serena slot is not owned by this owner")
            if not self._live_or_remove_stale(path, receipt):
                raise RuntimeError("Serena slot process identity is stale")
            receipt["heartbeat_at"] = _now()
            receipt["expires_at"] = _now() + self.lease_seconds
            self._write(path, receipt)
            return {**receipt, "status": "heartbeat"}

    def release(self, port: int, owner_id: str) -> dict[str, Any]:
        if port == SHARED_SERENA_PORT:
            raise ValueError("shared Serena port 9121 is excluded")
        path = self.root / f"slot-{port}.json"
        with _exclusive_guard(self.guard):
            receipt = _read_json(path)
            if receipt is None:
                return {"ok": True, "status": "already-released", "port": port}
            current_owner = receipt.get("owner_id")
            if current_owner is None:
                return {**receipt, "ok": True, "status": "already-released"}
            if current_owner != owner_id:
                raise LeaseBusy("Serena slot belongs to another owner")
            receipt["owner_id"] = None
            receipt["released_at"] = _now()
            receipt["expires_at"] = 0
            self._write(path, receipt)
            return {**receipt, "ok": True, "status": "released"}

    def destroy(self, port: int, owner_id: str) -> dict[str, Any]:
        if port == SHARED_SERENA_PORT:
            raise ValueError("shared Serena port 9121 is excluded")
        path = self.root / f"slot-{port}.json"
        with _exclusive_guard(self.guard):
            receipt = _read_json(path)
            if receipt is None:
                return {"ok": True, "status": "already-absent", "port": port}
            if receipt.get("owner_id") not in {owner_id, None}:
                raise LeaseBusy("Serena slot belongs to another owner")
            if not _identity_matches(receipt):
                path.unlink(missing_ok=True)
                return {"ok": True, "status": "stale-receipt-removed", "port": port}
            shutdown = _stop_verified_process(receipt)
            path.unlink(missing_ok=True)
            return {
                "ok": True,
                "status": "destroyed",
                "port": port,
                "shutdown": shutdown,
            }


class _JsonLease:
    def __init__(self, path: Path, *, lease_seconds: float) -> None:
        self.path = path
        self.lease_seconds = float(lease_seconds)
        self.guard = path.with_suffix(path.suffix + ".lock")

    def acquire(self, owner_id: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not owner_id:
            raise ValueError("owner_id is required")
        now = _now()
        with _exclusive_guard(self.guard):
            current = _read_json(self.path)
            if current and current.get("owner_id") == owner_id:
                current["heartbeat_at"] = now
                current["expires_at"] = now + self.lease_seconds
                atomic_write_json(self.path, current, sort_keys=True)
                return {**current, "status": "already-owned"}
            if current and float(current.get("expires_at", 0)) > now:
                raise LeaseBusy(f"lease held by {current.get('owner_id')}")
            payload = {
                "schema_version": 1,
                "owner_id": owner_id,
                "acquired_at": now,
                "heartbeat_at": now,
                "expires_at": now + self.lease_seconds,
                **(metadata or {}),
            }
            atomic_write_json(self.path, payload, sort_keys=True)
            return {**payload, "status": "acquired" if not current else "reclaimed-stale"}

    def heartbeat(self, owner_id: str) -> dict[str, Any]:
        now = _now()
        with _exclusive_guard(self.guard):
            current = _read_json(self.path)
            if not current or current.get("owner_id") != owner_id:
                raise LeaseBusy("lease is not owned by this owner")
            current["heartbeat_at"] = now
            current["expires_at"] = now + self.lease_seconds
            atomic_write_json(self.path, current, sort_keys=True)
            return {**current, "status": "heartbeat"}

    def release(self, owner_id: str) -> dict[str, Any]:
        with _exclusive_guard(self.guard):
            current = _read_json(self.path)
            if current is None:
                return {"ok": True, "status": "already-released"}
            if current.get("owner_id") != owner_id:
                if float(current.get("expires_at", 0)) <= _now():
                    self.path.unlink(missing_ok=True)
                    return {"ok": True, "status": "stale-released"}
                raise LeaseBusy("lease belongs to another owner")
            self.path.unlink(missing_ok=True)
            return {"ok": True, "status": "released", "owner_id": owner_id}


class CodingWorkspacePolicy:
    def __init__(self, configured_workspace: str | Path, *, lease_seconds: float = _DEFAULT_LEASE_SECONDS) -> None:
        self.workspace = Path(configured_workspace).expanduser().resolve()
        self.lease_seconds = float(lease_seconds)
        self.root = ensure_state_dirs() / "concurrency" / "coding-writers"
        self.root.mkdir(parents=True, exist_ok=True)

    def assert_binding(self, requested_path: str | Path) -> Path:
        requested = Path(requested_path).expanduser().resolve()
        try:
            requested.relative_to(self.workspace)
        except ValueError as exc:
            raise BindingMismatch(
                f"requested path {requested} is outside configured workspace {self.workspace}"
            ) from exc
        return requested

    def acquire_writer(self, worktree: str | Path, owner_id: str) -> dict[str, Any]:
        worktree_path = self.assert_binding(worktree)
        identity = _key(str(worktree_path).casefold())
        lease = _JsonLease(
            self.root / f"{identity}.json",
            lease_seconds=self.lease_seconds,
        )
        return lease.acquire(
            owner_id,
            metadata={
                "kind": "coding-worktree-writer",
                "workspace": str(self.workspace),
                "worktree": str(worktree_path),
                "worktree_id": identity,
            },
        )

    def release_writer(self, worktree: str | Path, owner_id: str) -> dict[str, Any]:
        worktree_path = self.assert_binding(worktree)
        identity = _key(str(worktree_path).casefold())
        return _JsonLease(
            self.root / f"{identity}.json",
            lease_seconds=self.lease_seconds,
        ).release(owner_id)


class MachineGuiLease:
    def __init__(self, *, lease_seconds: float = 120.0) -> None:
        path = ensure_state_dirs() / "concurrency" / "gui-lease.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lease = _JsonLease(path, lease_seconds=lease_seconds)

    def acquire(self, owner_id: str, *, action: str) -> dict[str, Any]:
        return self._lease.acquire(
            owner_id,
            metadata={"kind": "machine-gui", "action": action},
        )

    def heartbeat(self, owner_id: str) -> dict[str, Any]:
        return self._lease.heartbeat(owner_id)

    def release(self, owner_id: str) -> dict[str, Any]:
        return self._lease.release(owner_id)
