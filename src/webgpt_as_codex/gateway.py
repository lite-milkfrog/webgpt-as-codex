from __future__ import annotations

import os
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


def register_http(registry: str, name: str, url: str, description: str) -> None:
    binary = mcpjungle_binary()
    result = subprocess.run(
        [
            str(binary),
            "--registry",
            registry,
            "register",
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
