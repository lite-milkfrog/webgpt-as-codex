from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from collections.abc import Callable
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .health import ManagerStatusService, sanitize_for_output
from .paths import repo_root


@dataclass(frozen=True)
class ActionContract:
    name: str
    label: str
    owner_stage: str
    confirmation_required: bool
    impact: str


ACTION_CONTRACTS: dict[str, ActionContract] = {
    "start_all": ActionContract(
        "start_all",
        "Start All",
        "STAGE-8-DESKTOP-LAUNCHER-AND-AUTOSTART",
        False,
        "starts repository-owned runtimes only",
    ),
    "restart": ActionContract(
        "restart",
        "Restart",
        "STAGE-8-DESKTOP-LAUNCHER-AND-AUTOSTART",
        True,
        "restarts repository-owned runtimes only",
    ),
    "doctor": ActionContract(
        "doctor",
        "Doctor",
        "STAGE-7-BOOTSTRAP-DOCTOR-REPAIR",
        False,
        "read-only diagnostics",
    ),
    "repair": ActionContract(
        "repair",
        "Repair",
        "STAGE-7-BOOTSTRAP-DOCTOR-REPAIR",
        True,
        "bounded repair of repository-owned configuration",
    ),
    "update": ActionContract(
        "update",
        "Update",
        "STAGE-11-SECURITY-RELIABILITY-HARDENING",
        True,
        "bounded update after provenance/version checks",
    ),
}


class ActionBusyError(RuntimeError):
    pass


class ActionConfirmationError(PermissionError):
    pass


ActionExecutor = Callable[[ActionContract, dict[str, Any]], dict[str, Any]]


class ActionRunner:
    def __init__(self, executors: dict[str, ActionExecutor] | None = None) -> None:
        self._executors = dict(executors or {})
        self._lock = threading.Lock()

    def contracts(self) -> list[dict[str, Any]]:
        return [
            {**asdict(contract), "available": contract.name in self._executors}
            for contract in ACTION_CONTRACTS.values()
        ]

    def run(
        self,
        name: str,
        *,
        confirm: bool = False,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        contract = ACTION_CONTRACTS.get(name)
        if contract is None:
            raise KeyError(name)
        if contract.confirmation_required and not confirm:
            raise ActionConfirmationError(name)
        executor = self._executors.get(name)
        if executor is None:
            return {
                "ok": False,
                "status": "not-available-yet",
                "action": name,
                "owner_stage": contract.owner_stage,
            }
        if not self._lock.acquire(blocking=False):
            raise ActionBusyError("another manager action is already running")
        try:
            result = executor(contract, dict(payload or {}))
        finally:
            self._lock.release()
        if not isinstance(result, dict):
            raise TypeError("action executor must return a mapping")
        return sanitize_for_output({"action": name, **result})


class ManagerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        status_service: ManagerStatusService,
        action_runner: ActionRunner,
    ) -> None:
        super().__init__(server_address, ManagerRequestHandler)
        self.status_service = status_service
        self.action_runner = action_runner


class ManagerRequestHandler(BaseHTTPRequestHandler):
    server: ManagerHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(sanitize_for_output(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, path: Path) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._html(repo_root() / "manager" / "static" / "index.html")
            return
        if self.path == "/healthz":
            self._json({"ok": True})
            return
        if self.path == "/api/status":
            self._json(self.server.status_service.snapshot())
            return
        if self.path == "/api/actions":
            self._json({"actions": self.server.action_runner.contracts()})
            return
        self.send_error(HTTPStatus.NOT_FOUND.value)

    def do_POST(self) -> None:
        if not self.path.startswith("/api/actions/"):
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        if self.headers.get("X-WebGPT-Control") != "1":
            self._json({"ok": False, "error": "control-header-required"}, HTTPStatus.FORBIDDEN)
            return
        name = self.path.rsplit("/", 1)[-1]
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 0 or length > 4096:
            self._json({"ok": False, "error": "invalid-body-size"}, HTTPStatus.BAD_REQUEST)
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json({"ok": False, "error": "invalid-json"}, HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(payload, dict):
            self._json({"ok": False, "error": "object-body-required"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            result = self.server.action_runner.run(
                name,
                confirm=payload.get("confirm") is True,
                payload=payload,
            )
        except KeyError:
            self._json({"ok": False, "error": "unknown-action"}, HTTPStatus.NOT_FOUND)
            return
        except ActionConfirmationError:
            self._json({"ok": False, "error": "confirmation-required"}, HTTPStatus.CONFLICT)
            return
        except ActionBusyError:
            self._json({"ok": False, "error": "action-busy"}, HTTPStatus.CONFLICT)
            return
        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.CONFLICT
        self.server.status_service.snapshot(force=True)
        self._json(result, status)


def build_server(
    host: str = "127.0.0.1",
    port: int = 9200,
    *,
    status_service: ManagerStatusService | None = None,
    action_runner: ActionRunner | None = None,
) -> ManagerHTTPServer:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("Manager is loopback-only")
    if action_runner is None:
        from .doctor import manager_doctor_executor
        from .repair import manager_repair_executor
        from .runtime import manager_restart_executor, manager_start_all_executor

        action_runner = ActionRunner(
            {
                "start_all": manager_start_all_executor,
                "restart": manager_restart_executor,
                "doctor": manager_doctor_executor,
                "repair": manager_repair_executor,
            }
        )
    return ManagerHTTPServer(
        (host, port),
        status_service=status_service or ManagerStatusService(),
        action_runner=action_runner,
    )


def cli_manager(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex manager")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9200)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args(argv)
    server = build_server(args.host, args.port)
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"Manager: {url}")
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
