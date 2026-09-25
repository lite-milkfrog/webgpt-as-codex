from __future__ import annotations

import os
import re
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .paths import ensure_state_dirs


def mcpjungle_binary() -> Path:
    override = os.getenv("WEBGPT_CODEX_MCPJUNGLE")
    if override:
        return Path(override)
    return ensure_state_dirs() / "bin" / "mcpjungle" / "mcpjungle.exe"


def wait_http(url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return
        except (OSError, TimeoutError, ValueError) as exc:
            last = exc
        time.sleep(0.25)
    raise RuntimeError(f"service did not become ready: {url}: {last}")


@contextmanager
def temporary_mcpjungle(port: int = 9330) -> Iterator[tuple[subprocess.Popen[bytes], str]]:
    binary = mcpjungle_binary()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    state = ensure_state_dirs() / "gateway"
    state.mkdir(parents=True, exist_ok=True)
    db = state / "stage4-e2e.db"
    if db.exists():
        db.unlink()
    registry = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [str(binary), "start", "--port", str(port), "--sqlite-db-path", str(db)],
        cwd=state,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        wait_http(registry + "/health")
        yield process, registry
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def register_http(
    registry: str,
    name: str,
    url: str,
    description: str,
    *,
    force: bool = False,
) -> None:
    binary = mcpjungle_binary()
    result = subprocess.run(
        [
            str(binary),
            "--registry",
            registry,
            "register",
            *(["--force"] if force else []),
            "--name",
            name,
            "--description",
            description,
            "--url",
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"register {name} failed: {result.stdout}\n{result.stderr}")


def list_registered_servers(registry: str) -> dict[str, dict[str, str]]:
    binary = mcpjungle_binary()
    result = subprocess.run(
        [str(binary), "--registry", registry, "list", "servers"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"list servers failed: {result.stdout}\n{result.stderr}")
    if "There are no MCP servers in the registry" in result.stdout:
        return {}

    servers: dict[str, dict[str, str]] = {}
    current_name: str | None = None
    current: dict[str, str] = {}
    for raw in result.stdout.splitlines():
        line = raw.strip()
        match = re.fullmatch(r"\d+\.\s+(.+)", line)
        if match:
            if current_name is not None:
                servers[current_name] = current
            current_name = match.group(1).strip()
            current = {}
            continue
        if current_name is None:
            continue
        if line.startswith("Transport:"):
            current["transport"] = line.split(":", 1)[1].strip()
        elif line.startswith("URL:"):
            current["url"] = line.split(":", 1)[1].strip()
    if current_name is not None:
        servers[current_name] = current
    return servers


def sync_enabled_http_routes(registry: str) -> dict[str, object]:
    """Mirror healthy enabled HTTP MCPs into WebGPT's private gateway only."""
    from .discovery import discover_all
    from .registry import load_components

    components = load_components()
    discovery = discover_all(components)
    existing = list_registered_servers(registry)
    registered: list[str] = []
    updated: list[str] = []
    preserved: list[str] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    for component_id, component in sorted(components.items()):
        if component_id in {"mcpjungle", "mcp-auth-proxy"}:
            continue
        if component.transport != "streamable_http" or not component.enabled_by_default:
            continue
        endpoint = component.default_endpoint
        if not endpoint:
            skipped.append({"id": component_id, "reason": "no-endpoint"})
            continue
        live = discovery.get(component_id, {})
        if live.get("listener_up") is not True:
            skipped.append({"id": component_id, "reason": "listener-unavailable"})
            continue
        current = existing.get(component_id)
        same_route = (
            current is not None
            and current.get("transport") == "streamable_http"
            and current.get("url") == endpoint
        )
        refresh_registration = component.raw.get("refresh_registration") is True
        if same_route and not refresh_registration:
            preserved.append(component_id)
            continue
        try:
            register_http(
                registry,
                component_id,
                endpoint,
                f"{component.display_name} via WebGPT-as-Codex",
                force=current is not None,
            )
        except RuntimeError as exc:
            failed.append({"id": component_id, "reason": type(exc).__name__})
            continue
        if current is None:
            registered.append(component_id)
        else:
            updated.append(component_id)

    return {
        "ok": not failed,
        "registered": registered,
        "updated": updated,
        "preserved": preserved,
        "skipped": skipped,
        "failed": failed,
        "preserves_upstream_configuration": True,
    }
