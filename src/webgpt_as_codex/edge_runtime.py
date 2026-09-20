from __future__ import annotations

import argparse
import http.server
import json
import os
import secrets
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import requests

from .edge import (
    auth_proxy_binary,
    public_https_base,
    start_funnel,
    stop_funnel,
    tailscale_dns_name,
    wait_http,
)
from .gateway import sync_enabled_http_routes
from .oauth_compat import _handler
from .paths import ensure_state_dirs
from .stateio import atomic_write_json, atomic_write_text

GATEWAY_ROOT = "http://127.0.0.1:9330"
AUTH_PORT = 9340
COMPAT_PORT = 9341
PUBLIC_PORT = 443


def oauth_password_path() -> Path:
    return ensure_state_dirs() / "secrets" / "oauth-password.txt"


def oauth_password_status() -> dict[str, Any]:
    path = oauth_password_path()
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        value = ""
    return {"configured": bool(value), "path": str(path)}


def ensure_oauth_password() -> str:
    path = oauth_password_path()
    try:
        current = path.read_text(encoding="utf-8").strip()
    except OSError:
        current = ""
    if current:
        return current
    value = secrets.token_urlsafe(32)
    atomic_write_text(path, value + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return value


def regenerate_oauth_password() -> str:
    value = secrets.token_urlsafe(32)
    set_oauth_password(value)
    return value


def read_oauth_password() -> str:
    value = oauth_password_path().read_text(encoding="utf-8").strip()
    if not value:
        raise FileNotFoundError("OAuth password is not configured")
    return value


def set_oauth_password(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("OAuth password must be text")
    if not (12 <= len(value) <= 256) or "\n" in value or "\r" in value:
        raise ValueError("OAuth password must be 12-256 characters without newlines")
    path = oauth_password_path()
    atomic_write_text(path, value + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def public_base_url(public_port: int = PUBLIC_PORT) -> str:
    return public_https_base(tailscale_dns_name(), public_port)


def _manager_config_path() -> Path:
    return ensure_state_dirs() / "config" / "manager.json"


def _edge_state_path() -> Path:
    return ensure_state_dirs() / "runtime" / "edge.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _persist_public_url(public_base: str) -> None:
    path = _manager_config_path()
    data = _read_json(path)
    data["public_mcp_url"] = public_base.rstrip("/") + "/mcp"
    data["edge_public_port"] = PUBLIC_PORT
    atomic_write_json(path, data)


def _write_edge_state(
    *, status: str, public_base: str | None, detail: str | None = None,
    auth_pid: int | None = None,
) -> None:
    from .runtime import _process_birth_token

    atomic_write_json(
        _edge_state_path(),
        {
            "status": status,
            "public_mcp_url": public_base.rstrip("/") + "/mcp" if public_base else None,
            "gateway": GATEWAY_ROOT + "/mcp",
            "oauth_proxy": f"http://127.0.0.1:{AUTH_PORT}",
            "compat": f"http://127.0.0.1:{COMPAT_PORT}",
            "public_port": PUBLIC_PORT,
            "edge_pid": os.getpid(),
            "oauth_pid": auth_pid,
            "oauth_birth_token": _process_birth_token(auth_pid) if auth_pid else None,
            "detail": detail,
            "updated_at": time.time(),
        },
    )


def _start_auth_proxy(public_base: str, password: str) -> subprocess.Popen[bytes]:
    binary = auth_proxy_binary()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    state = ensure_state_dirs()
    data = state / "oauth-data"
    data.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PASSWORD"] = password
    log_path = state / "logs" / "runtime" / "oauth-edge-child.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("ab")
    try:
        process = subprocess.Popen(
            [
                str(binary),
                "--external-url",
                public_base.rstrip("/"),
                "--no-auto-tls",
                "--listen",
                f"127.0.0.1:{AUTH_PORT}",
                "--data-path",
                str(data),
                GATEWAY_ROOT,
            ],
            cwd=state,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    finally:
        log.close()
    return process


def _wait_auth_proxy_contract(
    process: subprocess.Popen[bytes],
    public_base: str,
    *,
    timeout: float = 20.0,
) -> None:
    url = f"http://127.0.0.1:{AUTH_PORT}/.well-known/oauth-authorization-server"
    expected = public_base.rstrip("/")
    deadline = time.monotonic() + timeout
    last_detail = "unreachable"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"OAuth proxy exited before readiness with code {process.returncode}"
            )
        owner = _auth_listener_pid()
        if owner is not None and owner != process.pid:
            raise RuntimeError("OAuth port is served by a different process generation")
        try:
            response = requests.get(url, timeout=2, allow_redirects=False)
            if response.status_code == 200:
                issuer = str(response.json().get("issuer", "")).rstrip("/")
                if issuer == expected and (os.name != "nt" or owner == process.pid):
                    return
                last_detail = "issuer-mismatch"
            else:
                last_detail = f"http-{response.status_code}"
        except (requests.RequestException, ValueError, TypeError):
            last_detail = "request-failed"
        time.sleep(0.3)
    raise RuntimeError(
        "OAuth proxy did not expose the expected public issuer "
        f"before timeout ({last_detail})"
    )


def _auth_listener_pid() -> int | None:
    from .runtime import _listener_pid

    return _listener_pid(f"http://127.0.0.1:{AUTH_PORT}")


def _existing_auth_proxy_matches(public_base: str, pid: int) -> bool:
    from .runtime import _webgpt_auth_listener_pid

    if _auth_listener_pid() != pid or _webgpt_auth_listener_pid() != pid:
        return False
    url = f"http://127.0.0.1:{AUTH_PORT}/.well-known/oauth-authorization-server"
    try:
        response = requests.get(url, timeout=2, allow_redirects=False)
        issuer = str(response.json().get("issuer", "")).rstrip("/")
    except (requests.RequestException, ValueError, TypeError):
        return False
    return response.status_code == 200 and issuer == public_base.rstrip("/")


def _stop_child(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def run_edge_runtime() -> int:
    public_base: str | None = None
    auth_process: subprocess.Popen[bytes] | None = None
    auth_pid: int | None = None
    compat_server: http.server.ThreadingHTTPServer | None = None
    compat_thread: threading.Thread | None = None
    funnel_started = False
    cleanup_error: str | None = None
    stopping = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stopping.set()

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, request_stop)
            except (OSError, ValueError):
                pass

    try:
        wait_http(GATEWAY_ROOT + "/health", expected={200})
        route_sync = sync_enabled_http_routes(GATEWAY_ROOT)
        if not route_sync["ok"]:
            raise RuntimeError("one or more gateway routes failed to synchronize")
        public_base = public_base_url()
        credential = ensure_oauth_password()

        existing_auth_pid = _auth_listener_pid()
        if existing_auth_pid is not None:
            if not _existing_auth_proxy_matches(public_base, existing_auth_pid):
                raise RuntimeError("OAuth port is occupied by an incompatible process generation")
            auth_pid = existing_auth_pid
        else:
            auth_process = _start_auth_proxy(public_base, credential)
            _wait_auth_proxy_contract(auth_process, public_base)
            auth_pid = auth_process.pid

        compat_server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", COMPAT_PORT),
            _handler(f"http://127.0.0.1:{AUTH_PORT}", public_base),
        )
        compat_server.daemon_threads = True
        compat_thread = threading.Thread(target=compat_server.serve_forever, daemon=True)
        compat_thread.start()
        wait_http(
            f"http://127.0.0.1:{COMPAT_PORT}/.well-known/oauth-protected-resource",
            expected={200},
        )

        actual_public = start_funnel(
            f"http://127.0.0.1:{COMPAT_PORT}",
            public_port=PUBLIC_PORT,
        )
        funnel_started = True
        if actual_public.rstrip("/") != public_base.rstrip("/"):
            public_base = actual_public
        _persist_public_url(public_base)
        _write_edge_state(status="running", public_base=public_base, auth_pid=auth_pid)

        while not stopping.wait(0.5):
            if auth_process is not None and auth_process.poll() is not None:
                raise RuntimeError(
                    f"OAuth proxy exited unexpectedly with code {auth_process.returncode}"
                )
            if auth_process is None and (
                auth_pid is None or not _existing_auth_proxy_matches(public_base, auth_pid)
            ):
                raise RuntimeError("adopted OAuth proxy became unavailable or changed identity")
        return 0
    except Exception as exc:
        _write_edge_state(
            status="failed",
            public_base=public_base,
            detail=type(exc).__name__,
        )
        raise
    finally:
        if funnel_started:
            try:
                stop_funnel(public_port=PUBLIC_PORT)
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                cleanup_error = type(exc).__name__
        if compat_server is not None:
            compat_server.shutdown()
            compat_server.server_close()
        if compat_thread is not None:
            compat_thread.join(timeout=5)
        _stop_child(auth_process)
        if stopping.is_set():
            _write_edge_state(
                status="stopped" if cleanup_error is None else "stopped-with-cleanup-error",
                public_base=public_base,
                detail=cleanup_error,
            )


def cli_edge_runtime(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex edge-runtime")
    parser.parse_args(argv)
    return run_edge_runtime()
