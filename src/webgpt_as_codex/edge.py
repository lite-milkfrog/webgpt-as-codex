from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import requests

from .paths import ensure_state_dirs


def auth_proxy_binary() -> Path:
    override = os.getenv("WEBGPT_CODEX_AUTH_PROXY")
    if override:
        return Path(override)
    return ensure_state_dirs() / "bin" / "mcp-auth-proxy" / "mcp-auth-proxy.exe"


def tailscale_binary() -> Path:
    override = os.getenv("WEBGPT_CODEX_TAILSCALE")
    if override:
        return Path(override)
    found = shutil.which("tailscale")
    if found:
        return Path(found)
    candidate = Path("C:/Program Files/Tailscale/tailscale.exe")
    if candidate.is_file():
        return candidate
    raise FileNotFoundError("tailscale executable not found")


def tailscale_dns_name() -> str:
    result = subprocess.run(
        [str(tailscale_binary()), "status", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    data = json.loads(result.stdout)
    dns = str(data.get("Self", {}).get("DNSName", "")).rstrip(".")
    if not dns:
        raise RuntimeError("Tailscale DNS name unavailable")
    if not data.get("Self", {}).get("Online", False):
        raise RuntimeError("Tailscale is not online")
    return dns


def wait_http(
    url: str,
    *,
    expected: set[int] | None = None,
    timeout: float = 20.0,
) -> None:
    expected = expected or {200, 401}
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=2, allow_redirects=False)
            if response.status_code in expected:
                return
        except requests.RequestException as exc:
            last = exc
        time.sleep(0.3)
    raise RuntimeError(f"edge did not become ready: {url}: {last}")


@contextmanager
def temporary_auth_proxy(
    backend_root: str,
    external_url: str,
    *,
    port: int = 9340,
    data_path: Path | None = None,
    password: str | None = None,
) -> Iterator[tuple[subprocess.Popen[bytes], str, str, Path]]:
    binary = auth_proxy_binary()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    state = ensure_state_dirs() / "stage5"
    state.mkdir(parents=True, exist_ok=True)
    data = data_path or (state / "oauth-data")
    data.mkdir(parents=True, exist_ok=True)
    secret = password or secrets.token_urlsafe(32)
    env = os.environ.copy()
    env["PASSWORD"] = secret
    process = subprocess.Popen(
        [
            str(binary),
            "--external-url",
            external_url.rstrip("/"),
            "--no-auto-tls",
            "--listen",
            f"127.0.0.1:{port}",
            "--data-path",
            str(data),
            backend_root.rstrip("/"),
        ],
        cwd=state,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    local = f"http://127.0.0.1:{port}"
    try:
        wait_http(local + "/.well-known/oauth-protected-resource", expected={200})
        yield process, local, secret, data
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def start_funnel(local_url: str, *, public_port: int = 10003) -> str:
    dns = tailscale_dns_name()
    result = subprocess.run(
        [
            str(tailscale_binary()),
            "funnel",
            "--bg",
            "--yes",
            "--https",
            str(public_port),
            local_url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return f"https://{dns}:{public_port}"


def stop_funnel(*, public_port: int = 10003) -> None:
    result = subprocess.run(
        [
            str(tailscale_binary()),
            "funnel",
            "--yes",
            "--https",
            str(public_port),
            "off",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode:
        message = (result.stderr or result.stdout).lower()
        if "handler does not exist" not in message:
            raise RuntimeError(result.stderr or result.stdout)
