from __future__ import annotations

import argparse
import json
import os
import threading
import time
import webbrowser
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import __version__
from .edge_runtime import (
    oauth_password_status,
    read_oauth_password,
    regenerate_oauth_password,
    set_oauth_password,
)
from .health import ManagerStatusService, sanitize_for_output
from .paths import resource_root
from .prerequisites import environment_report, install_tailscale_with_winget
from .registry import delete_custom_component, load_components, write_custom_component
from .skill_workflow import SkillWorkflowControlPlane


@dataclass(frozen=True)
class ActionContract:
    name: str
    label: str
    owner_stage: str
    confirmation_required: bool
    impact: str
    payload_fields: tuple[str, ...] = ("confirm",)


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
        ("confirm", "component"),
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
        ("confirm", "component"),
    ),
}


class ActionBusyError(RuntimeError):
    pass


class ActionConfirmationError(PermissionError):
    pass


class ActionPayloadError(ValueError):
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
        body = dict(payload or {})
        unknown = sorted(set(body) - set(contract.payload_fields))
        if unknown:
            raise ActionPayloadError("unsupported action fields: " + ", ".join(unknown))
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
            result = executor(contract, body)
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
        skill_workflow: SkillWorkflowControlPlane,
    ) -> None:
        super().__init__(server_address, ManagerRequestHandler)
        self.status_service = status_service
        self.action_runner = action_runner
        self.skill_workflow = skill_workflow
        self.local_mutation_lock = threading.Lock()
        self._activity_lock = threading.Lock()
        self._activity: deque[dict[str, Any]] = deque(maxlen=50)

    def record_activity(
        self,
        action: str,
        status: str,
        *,
        detail: str | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "at": time.time(),
            "action": action,
            "status": status,
        }
        if detail:
            row["detail"] = detail
        with self._activity_lock:
            self._activity.appendleft(sanitize_for_output(row))

    def recent_activity(self) -> list[dict[str, Any]]:
        with self._activity_lock:
            return list(self._activity)


class ManagerRequestHandler(BaseHTTPRequestHandler):
    server: ManagerHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _loopback_request_host(self) -> bool:
        raw = self.headers.get("Host", "")
        try:
            parsed = urlsplit("//" + raw)
            host = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port
        except ValueError:
            return False
        if host not in {"127.0.0.1", "::1", "localhost"}:
            return False
        return port == self.server.server_address[1]

    def _same_origin_if_present(self) -> bool:
        raw = self.headers.get("Origin")
        if not raw:
            return True
        try:
            parsed = urlsplit(raw)
            host = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port or (80 if parsed.scheme == "http" else None)
        except ValueError:
            return False
        return (
            parsed.scheme == "http"
            and host in {"127.0.0.1", "::1", "localhost"}
            and port == self.server.server_address[1]
            and not parsed.username
            and not parsed.password
        )

    def _request_origin_ok(self) -> bool:
        return self._loopback_request_host() and self._same_origin_if_present()

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(sanitize_for_output(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ActionPayloadError("invalid body size") from exc
        if length < 0 or length > 4096:
            raise ActionPayloadError("invalid body size")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ActionPayloadError("invalid json") from exc
        if not isinstance(payload, dict):
            raise ActionPayloadError("object body required")
        return payload

    @staticmethod
    def _require_fields(payload: dict[str, Any], allowed: set[str]) -> None:
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ActionPayloadError("unsupported fields")

    @staticmethod
    def _environment_summary(report: dict[str, Any]) -> dict[str, Any]:
        python = report.get("python") or {}
        windows = report.get("windows") or {}
        winget = report.get("winget") or {}
        tailscale = report.get("tailscale") or {}
        binaries = report.get("runtime_binaries") or {}
        return {
            "python": {
                key: python.get(key)
                for key in ("ok", "version", "minimum")
            },
            "windows": {
                key: windows.get(key)
                for key in ("ok", "platform", "release", "version", "reason")
            },
            "winget": {
                key: winget.get(key)
                for key in ("available", "version")
            },
            "tailscale": {
                key: tailscale.get(key)
                for key in (
                    "installed",
                    "version",
                    "minimum_version",
                    "version_ok",
                    "backend_state",
                    "online",
                    "funnel_cli_ok",
                    "funnel_policy",
                    "ready",
                    "next_action",
                )
            },
            "runtime_binaries": {
                "mcpjungle": {
                    "ready": bool((binaries.get("mcpjungle") or {}).get("ready"))
                },
                "mcp_auth_proxy": {
                    "ready": bool((binaries.get("mcp_auth_proxy") or {}).get("ready"))
                },
                "ready": bool(binaries.get("ready")),
            },
            "ready_for_local_manager": bool(report.get("ready_for_local_manager")),
            "ready_for_gateway": bool(report.get("ready_for_gateway")),
            "ready_for_edge": bool(report.get("ready_for_edge")),
            "next_steps": report.get("next_steps") or [],
        }

    def _local_config(self) -> dict[str, Any]:
        snapshot = self.server.status_service.snapshot()
        status_rows = {
            row.get("id"): row
            for row in snapshot.get("components", [])
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        }
        rows = []
        for component in load_components().values():
            if component.id == "mcpjungle":
                migration_state = "gateway"
            elif component.id == "mcp-auth-proxy":
                migration_state = "edge"
            elif component.id == "tailscale":
                migration_state = "transport"
            elif component.transport == "vendor_remote":
                migration_state = "vendor-relay"
            else:
                migration_state = "external-preserved"
            status = status_rows.get(component.id) or {}
            builtin = (resource_root() / "components" / f"{component.id}.json").exists()
            rows.append(
                {
                    "id": component.id,
                    "display_name": component.display_name,
                    "role": component.role,
                    "transport": component.transport,
                    "endpoint": component.default_endpoint,
                    "migration_state": migration_state,
                    "version": status.get("version"),
                    "custom": not builtin,
                    "lifecycle_authority": False if not builtin else None,
                    "route_applied": False if not builtin else None,
                }
            )
        password_status = oauth_password_status()
        environment = self._environment_summary(environment_report())
        return {
            "product_version": __version__,
            "manager_url": f"http://127.0.0.1:{self.server.server_address[1]}/",
            "gateway_mcp_url": "http://127.0.0.1:9330/mcp",
            "oauth_proxy_url": "http://127.0.0.1:9340",
            "oauth_compat_url": "http://127.0.0.1:9341",
            "public_mcp_url": snapshot.get("public_mcp_url"),
            "oauth_password": {"configured": bool(password_status.get("configured"))},
            "migration_mode": "preserve-external",
            "environment": environment,
            "deployment": {
                "manager_ready": environment["ready_for_local_manager"],
                "gateway_ready": environment["ready_for_gateway"],
                "edge_ready": environment["ready_for_edge"],
                "mode": "unified-gateway",
            },
            "components": rows,
        }

    def _static(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; base-uri 'none'; form-action 'self'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, path: Path) -> None:
        self._static(path, "text/html; charset=utf-8")

    def do_GET(self) -> None:
        if not self._request_origin_ok():
            self._json({"ok": False, "error": "loopback-origin-required"}, HTTPStatus.FORBIDDEN)
            return
        if self.path in {"/", "/index.html"}:
            language = os.getenv("WEBGPT_CODEX_UI_LANG", "en").lower()
            filename = "index.zh-CN.html" if language.startswith("zh") else "index.html"
            self._html(resource_root() / "manager" / "static" / filename)
            return
        if self.path in {"/zh", "/zh/"}:
            self._html(resource_root() / "manager" / "static" / "index.zh-CN.html")
            return
        if self.path in {"/en", "/en/"}:
            self._html(resource_root() / "manager" / "static" / "index.html")
            return
        if self.path == "/manager.css":
            self._static(
                resource_root() / "manager" / "static" / "manager.css",
                "text/css; charset=utf-8",
            )
            return
        if self.path == "/manager.js":
            self._static(
                resource_root() / "manager" / "static" / "manager.js",
                "text/javascript; charset=utf-8",
            )
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
        if self.path == "/api/local-config":
            self._local_json(self._local_config())
            return
        if self.path == "/api/activity":
            self._local_json({"activity": self.server.recent_activity()})
            return
        if self.path == "/api/skills":
            self._local_json(self.server.skill_workflow.skill_snapshot())
            return
        if self.path == "/api/workflows":
            self._local_json(self.server.skill_workflow.workflow_catalog())
            return
        if self.path == "/api/workflow-runs":
            self._local_json({"runs": self.server.skill_workflow.list_runs()})
            return
        self.send_error(HTTPStatus.NOT_FOUND.value)

    def _handle_local_mutation(self, payload: dict[str, Any]) -> bool:
        if self.path not in {
            "/api/environment",
            "/api/components",
            "/api/oauth-password",
            "/api/skills",
            "/api/workflow-runs",
        }:
            return False
        if not self.server.local_mutation_lock.acquire(blocking=False):
            self.server.record_activity(self.path, "blocked", detail="manager-mutation-busy")
            self._json({"ok": False, "error": "manager-mutation-busy"}, HTTPStatus.CONFLICT)
            return True
        try:
            if self.path == "/api/skills":
                self._require_fields(
                    payload,
                    {"operation", "confirm", "id", "category", "position"},
                )
                if payload.get("confirm") is not True:
                    self.server.record_activity(
                        "skills",
                        "blocked",
                        detail="confirmation-required",
                    )
                    self._json(
                        {"ok": False, "error": "confirmation-required"},
                        HTTPStatus.CONFLICT,
                    )
                    return True
                operation = payload.get("operation")
                if operation == "move":
                    result = self.server.skill_workflow.move_skill(
                        str(payload.get("id") or ""),
                        str(payload.get("category") or ""),
                        payload.get("position"),
                    )
                    self.server.record_activity(
                        "skills.move",
                        "success",
                        detail=str(result.get("skill_id") or ""),
                    )
                    self._local_json(result)
                    return True
                if operation == "open":
                    result = self.server.skill_workflow.open_skill_location(
                        str(payload.get("id") or "")
                    )
                    self.server.record_activity(
                        "skills.open",
                        "success" if result.get("ok") else "failed",
                        detail=str(result.get("skill_id") or ""),
                    )
                    status = HTTPStatus.OK if result.get("ok") else HTTPStatus.CONFLICT
                    self._local_json(result, status)
                    return True
                self.server.record_activity(
                    "skills",
                    "failed",
                    detail="unknown-operation",
                )
                self._json(
                    {"ok": False, "error": "unknown-skill-operation"},
                    HTTPStatus.BAD_REQUEST,
                )
                return True

            if self.path == "/api/workflow-runs":
                self._require_fields(
                    payload,
                    {
                        "operation",
                        "confirm",
                        "workflow_id",
                        "context",
                        "run_id",
                        "stage_id",
                        "status",
                        "evidence",
                    },
                )
                if payload.get("confirm") is not True:
                    self.server.record_activity(
                        "workflow-runs",
                        "blocked",
                        detail="confirmation-required",
                    )
                    self._json(
                        {"ok": False, "error": "confirmation-required"},
                        HTTPStatus.CONFLICT,
                    )
                    return True
                operation = payload.get("operation")
                if operation == "start":
                    context = payload.get("context")
                    if context is not None and not isinstance(context, dict):
                        raise ActionPayloadError("context must be an object")
                    result = self.server.skill_workflow.start_run(
                        str(payload.get("workflow_id") or ""),
                        context,
                    )
                    self.server.record_activity(
                        "workflow-runs.start",
                        "success",
                        detail=str(result.get("run_id") or ""),
                    )
                    self._local_json(result)
                    return True
                if operation == "transition":
                    result = self.server.skill_workflow.transition_run(
                        str(payload.get("run_id") or ""),
                        str(payload.get("stage_id") or ""),
                        str(payload.get("status") or ""),
                        str(payload.get("evidence") or "") or None,
                    )
                    self.server.record_activity(
                        "workflow-runs.transition",
                        "success",
                        detail=str(result.get("run_id") or ""),
                    )
                    self._local_json(result)
                    return True
                self.server.record_activity(
                    "workflow-runs",
                    "failed",
                    detail="unknown-operation",
                )
                self._json(
                    {"ok": False, "error": "unknown-workflow-run-operation"},
                    HTTPStatus.BAD_REQUEST,
                )
                return True

            if self.path == "/api/environment":
                self._require_fields(payload, {"operation", "confirm"})
                if payload.get("confirm") is not True:
                    self.server.record_activity("environment", "blocked", detail="confirmation-required")
                    self._json({"ok": False, "error": "confirmation-required"}, HTTPStatus.CONFLICT)
                    return True
                operation = payload.get("operation")
                if operation != "install-tailscale":
                    self.server.record_activity("environment", "failed", detail="unknown-operation")
                    self._json(
                        {"ok": False, "error": "unknown-environment-operation"},
                        HTTPStatus.BAD_REQUEST,
                    )
                    return True
                result = install_tailscale_with_winget(confirm=True)
                public_result = {
                    "ok": bool(result.get("ok")),
                    "status": result.get("status"),
                    "tailscale": self._environment_summary(
                        {"tailscale": result.get("tailscale") or {}}
                    )["tailscale"],
                }
                self.server.record_activity(
                    "environment.install-tailscale",
                    "success" if public_result["ok"] else "failed",
                    detail=str(public_result.get("status") or "unknown"),
                )
                status = HTTPStatus.OK if public_result["ok"] else HTTPStatus.CONFLICT
                self._local_json(public_result, status)
                return True

            if self.path == "/api/components":
                self._require_fields(
                    payload,
                    {"operation", "confirm", "id", "display_name", "role", "endpoint"},
                )
                if payload.get("confirm") is not True:
                    self.server.record_activity("components", "blocked", detail="confirmation-required")
                    self._json({"ok": False, "error": "confirmation-required"}, HTTPStatus.CONFLICT)
                    return True
                operation = payload.get("operation", "create")
                if operation == "create":
                    component = {
                        "id": payload.get("id"),
                        "display_name": payload.get("display_name"),
                        "role": payload.get("role") or "custom_mcp",
                        "required": False,
                        "enabled_by_default": False,
                        "transport": "streamable_http",
                        "default_endpoint": payload.get("endpoint"),
                        "safe_tool": None,
                    }
                    write_custom_component(component)
                    self.server.status_service.snapshot(force=True)
                    result = {
                        "ok": True,
                        "component_id": component["id"],
                        "lifecycle_authority": False,
                        "route_applied": False,
                    }
                    self.server.record_activity(
                        "components.create",
                        "success",
                        detail=str(component["id"]),
                    )
                    self._local_json(result)
                    return True
                if operation == "delete":
                    component_id = payload.get("id")
                    if (
                        isinstance(component_id, str)
                        and (resource_root() / "components" / f"{component_id}.json").exists()
                    ):
                        self.server.record_activity(
                            "components.delete",
                            "blocked",
                            detail="builtin-component-protected",
                        )
                        self._json(
                            {"ok": False, "error": "builtin-component-protected"},
                            HTTPStatus.CONFLICT,
                        )
                        return True
                    removed = delete_custom_component(component_id)
                    self.server.status_service.snapshot(force=True)
                    self.server.record_activity(
                        "components.delete",
                        "success",
                        detail=str(component_id),
                    )
                    self._local_json(
                        {
                            "ok": True,
                            "component_id": component_id,
                            "removed": removed,
                            "lifecycle_authority": False,
                            "route_applied": False,
                        }
                    )
                    return True
                self.server.record_activity("components", "failed", detail="unknown-operation")
                self._json(
                    {"ok": False, "error": "unknown-component-operation"},
                    HTTPStatus.BAD_REQUEST,
                )
                return True

            self._require_fields(payload, {"action", "confirm", "value"})
            if payload.get("confirm") is not True:
                self.server.record_activity("oauth-password", "blocked", detail="confirmation-required")
                self._json({"ok": False, "error": "confirmation-required"}, HTTPStatus.CONFLICT)
                return True
            action = payload.get("action")
            if action == "reveal":
                revealed_value = read_oauth_password()
                self.server.record_activity("oauth-password.reveal", "success")
                self._local_json({"ok": True, "password": revealed_value})
                return True
            if action == "generate":
                regenerate_oauth_password()
                self.server.record_activity("oauth-password.generate", "success")
                self._local_json({"ok": True, "configured": True, "restart_required": True})
                return True
            if action == "set":
                set_oauth_password(payload.get("value"))
                self.server.record_activity("oauth-password.set", "success")
                self._local_json({"ok": True, "configured": True, "restart_required": True})
                return True
            self.server.record_activity("oauth-password", "failed", detail="unknown-action")
            self._json(
                {"ok": False, "error": "unknown-oauth-password-action"},
                HTTPStatus.BAD_REQUEST,
            )
            return True
        except ActionPayloadError:
            self.server.record_activity(self.path, "failed", detail="invalid-action-payload")
            self._json({"ok": False, "error": "invalid-action-payload"}, HTTPStatus.BAD_REQUEST)
            return True
        except KeyError as exc:
            failure = (
                "skill-not-found"
                if self.path == "/api/skills"
                else "workflow-not-found"
                if self.path == "/api/workflow-runs"
                else "resource-not-found"
            )
            self.server.record_activity(self.path, "failed", detail=failure)
            self._json(
                {"ok": False, "error": failure, "resource": str(exc)},
                HTTPStatus.NOT_FOUND,
            )
            return True
        except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
            failure = (
                "component-operation-failed"
                if self.path == "/api/components"
                else "oauth-password-operation-failed"
                if self.path == "/api/oauth-password"
                else "skill-operation-failed"
                if self.path == "/api/skills"
                else "workflow-run-operation-failed"
                if self.path == "/api/workflow-runs"
                else "environment-operation-failed"
            )
            self.server.record_activity(self.path, "failed", detail=failure)
            self._json(
                {"ok": False, "error": failure, "failure_type": type(exc).__name__},
                HTTPStatus.BAD_REQUEST,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - local HTTP trust boundary fails closed
            self.server.record_activity(self.path, "failed", detail="local-operation-failed")
            self._json(
                {
                    "ok": False,
                    "error": "local-operation-failed",
                    "failure_type": type(exc).__name__,
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return True
        finally:
            self.server.local_mutation_lock.release()

    def do_POST(self) -> None:
        if not self._request_origin_ok():
            self._json({"ok": False, "error": "loopback-origin-required"}, HTTPStatus.FORBIDDEN)
            return
        if self.headers.get("X-WebGPT-Control") != "1":
            self._json({"ok": False, "error": "control-header-required"}, HTTPStatus.FORBIDDEN)
            return
        try:
            payload = self._read_json_body()
        except ActionPayloadError:
            self._json({"ok": False, "error": "invalid-action-payload"}, HTTPStatus.BAD_REQUEST)
            return

        if self._handle_local_mutation(payload):
            return

        if not self.path.startswith("/api/actions/"):
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        name = self.path.rsplit("/", 1)[-1]
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
            self.server.record_activity(f"actions.{name}", "blocked", detail="confirmation-required")
            self._json({"ok": False, "error": "confirmation-required"}, HTTPStatus.CONFLICT)
            return
        except ActionPayloadError:
            self.server.record_activity(f"actions.{name}", "failed", detail="invalid-action-payload")
            self._json({"ok": False, "error": "invalid-action-payload"}, HTTPStatus.BAD_REQUEST)
            return
        except ActionBusyError:
            self.server.record_activity(f"actions.{name}", "blocked", detail="action-busy")
            self._json({"ok": False, "error": "action-busy"}, HTTPStatus.CONFLICT)
            return
        except Exception as exc:  # noqa: BLE001 - HTTP trust boundary must fail closed
            self.server.record_activity(f"actions.{name}", "failed", detail="action-failed")
            self._json(
                {
                    "ok": False,
                    "error": "action-failed",
                    "failure_type": type(exc).__name__,
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.CONFLICT
        self.server.status_service.snapshot(force=True)
        self.server.record_activity(
            f"actions.{name}",
            "success" if result.get("ok") else "failed",
            detail=str(result.get("status") or "completed"),
        )
        self._json(result, status)


def build_server(
    host: str = "127.0.0.1",
    port: int = 9200,
    *,
    status_service: ManagerStatusService | None = None,
    action_runner: ActionRunner | None = None,
    skill_workflow: SkillWorkflowControlPlane | None = None,
) -> ManagerHTTPServer:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("Manager is loopback-only")
    if action_runner is None:
        from .doctor import manager_doctor_executor
        from .repair import manager_repair_executor
        from .runtime import manager_restart_executor, manager_start_all_executor
        from .update import manager_update_executor

        action_runner = ActionRunner(
            {
                "start_all": manager_start_all_executor,
                "restart": manager_restart_executor,
                "doctor": manager_doctor_executor,
                "repair": manager_repair_executor,
                "update": manager_update_executor,
            }
        )
    return ManagerHTTPServer(
        (host, port),
        status_service=status_service or ManagerStatusService(),
        action_runner=action_runner,
        skill_workflow=skill_workflow or SkillWorkflowControlPlane(),
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
