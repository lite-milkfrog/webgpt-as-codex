from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from webgpt_as_codex.gateway import register_http, temporary_mcpjungle
from webgpt_as_codex.mcp import initialize, rpc, session_id
from webgpt_as_codex.paths import ensure_state_dirs, repo_root, user_home

BACKENDS = [
    ("coding", "http://127.0.0.1:8766/mcp", "Repository mutation, test and Git"),
    ("windows", "http://127.0.0.1:8001/mcp", "Native Windows GUI"),
]
SAFE_CALLS = {
    "serena__get_current_config": {},
    "coding__server_info": {},
    "windows__DisplayInventory": {},
    "playwright__browser_tabs": {"action": "list"},
}


def _serena_exe() -> Path:
    found = shutil.which("serena")
    if found:
        return Path(found)
    return user_home() / ".local" / "bin" / "serena.exe"


def _edge_exe() -> Path:
    candidates: list[Path] = []
    for env_name in ("ProgramFiles(x86)", "ProgramFiles"):
        root = os.getenv(env_name)
        if root:
            candidates.append(Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    candidates.extend(
        [
            user_home() / "AppData" / "Local" / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
            Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Microsoft Edge executable not found")


def _playwright_cli() -> Path:
    override = os.getenv("WEBGPT_CODEX_PLAYWRIGHT_CLI")
    if override:
        return Path(override)
    npm = shutil.which("npm")
    if npm:
        result = subprocess.run(
            [npm, "root", "-g"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            candidate = Path(result.stdout.strip()) / "@playwright" / "mcp" / "cli.js"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        "Playwright MCP CLI not found. Set WEBGPT_CODEX_PLAYWRIGHT_CLI to @playwright/mcp/cli.js."
    )


def _wait_mcp(url: str, process: subprocess.Popen[bytes], label: str, timeout: float = 25.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            initialize(url)
            return
        except (OSError, TimeoutError, ValueError):
            if process.poll() is not None:
                raise RuntimeError(f"{label} exited with {process.returncode}")
            time.sleep(0.4)
    raise RuntimeError(f"{label} did not become MCP-ready")


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


@contextmanager
def temporary_serena(port: int = 9129):
    exe = _serena_exe()
    if not exe.is_file():
        raise FileNotFoundError(exe)
    state = ensure_state_dirs() / "stage4" / "serena"
    state.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    home = str(user_home())
    env["HOME"] = home
    env["USERPROFILE"] = home
    process = subprocess.Popen(
        [
            str(exe),
            "start-mcp-server",
            "--project",
            str(repo_root()),
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
        ],
        cwd=state,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        _wait_mcp(url, process, "temporary Serena")
        yield url
    finally:
        _stop(process)


@contextmanager
def temporary_playwright(port: int = 8939):
    cli = _playwright_cli()
    node = shutil.which("node")
    if not node:
        raise FileNotFoundError("node")
    state = ensure_state_dirs() / "stage4" / "playwright"
    state.mkdir(parents=True, exist_ok=True)
    stdout_path = state / "stdout.log"
    stderr_path = state / "stderr.log"
    out = stdout_path.open("wb")
    err = stderr_path.open("wb")
    process = subprocess.Popen(
        [
            node,
            str(cli),
            "--headless",
            "--isolated",
            "--executable-path",
            str(_edge_exe()),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--idle-timeout",
            "0",
            "--output-dir",
            str(state),
        ],
        cwd=state,
        stdout=out,
        stderr=err,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    url = f"http://localhost:{port}/mcp"
    try:
        try:
            _wait_mcp(url, process, "temporary Playwright")
        except Exception as exc:
            out.flush()
            err.flush()
            stdout_tail = stdout_path.read_text(encoding="utf-8", errors="replace")[-3000:]
            stderr_tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-3000:]
            raise RuntimeError(
                f"{exc}\nPLAYWRIGHT_STDOUT:\n{stdout_tail}\nPLAYWRIGHT_STDERR:\n{stderr_tail}"
            ) from exc
        yield url
    finally:
        _stop(process)
        out.close()
        err.close()


def main() -> int:
    with (
        temporary_serena() as serena_url,
        temporary_playwright() as playwright_url,
        temporary_mcpjungle() as (_, registry),
    ):
        register_http(registry, "serena", serena_url, "Semantic code intelligence")
        register_http(registry, "playwright", playwright_url, "Browser automation")
        for name, url, description in BACKENDS:
            register_http(registry, name, url, description)

        gateway = registry + "/mcp"
        init = initialize(gateway)
        sid = session_id(init)
        listed = rpc(gateway, "tools/list", request_id=2, session_id=sid)
        tools = listed.body.get("result", {}).get("tools", [])
        names = {tool.get("name") for tool in tools}
        print("GATEWAY_TOOL_COUNT", len(names))
        missing = sorted(set(SAFE_CALLS) - names)
        if missing:
            print("MISSING_TOOLS", json.dumps(missing))
            return 2

        for index, (tool, arguments) in enumerate(SAFE_CALLS.items(), start=10):
            response = rpc(
                gateway,
                "tools/call",
                {"name": tool, "arguments": arguments},
                request_id=index,
                session_id=sid,
                timeout=30,
            )
            result = response.body.get("result", {})
            ok = response.status == 200 and not result.get("isError", False)
            print("SAFE_CALL", tool, "PASS" if ok else "FAIL")
            if not ok:
                print(json.dumps(response.body, ensure_ascii=False)[:2000])
                return 4

        print("STAGE4_GATEWAY_E2E_PASS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
