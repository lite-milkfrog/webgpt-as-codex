from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

from .discovery import discover_component, process_health, process_markers, process_snapshot
from .health import HEALTH_LEVELS, configured_public_mcp_url, sanitize_for_output
from .mcp import initialize, rpc, session_id
from .paths import ensure_state_dirs, state_root
from .registry import Component, load_components
from .stateio import atomic_write_json

_VERSION_RE = re.compile(
    r"(?i)\b(?:version\s*[:=]?\s*|v)(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)\b"
)
_EXACT_VERSION_RE = re.compile(
    r"(?i)^v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)$"
)

_process_health = process_health
_process_markers = process_markers
_process_snapshot = process_snapshot


def _manifest_version(component: Component) -> tuple[str | None, str]:
    for key in ("verified_release", "verified_local_binary", "version"):
        value = component.raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), f"manifest:{key}"
    return None, "unknown"


def _resolved_version_command(component: Component) -> tuple[list[str] | None, str | None]:
    command = [str(value) for value in (component.raw.get("version_command") or [])]
    if not command:
        return None, "no-version-command"
    if any("@latest" in value.lower() for value in command):
        return None, "network-capable-version-command-skipped"
    executable = shutil.which(command[0])
    if executable:
        command[0] = executable
        return command, None
    try:
        if component.id == "mcpjungle":
            from .gateway import mcpjungle_binary

            candidate = mcpjungle_binary()
        elif component.id == "tailscale":
            from .edge import tailscale_binary

            candidate = tailscale_binary()
        else:
            candidate = None
    except (OSError, RuntimeError):
        candidate = None
    if candidate and candidate.is_file():
        command[0] = str(candidate)
        return command, None
    return None, "version-executable-not-found"


def _version_probe(component: Component) -> dict[str, Any]:
    fallback, source = _manifest_version(component)
    command, skipped = _resolved_version_command(component)
    if command is None:
        return {
            "value": fallback,
            "source": source,
            "probe_ok": None,
            "note": skipped,
        }
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=6,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "value": fallback,
            "source": source,
            "probe_ok": False,
            "note": type(exc).__name__,
        }
    raw_output = (result.stdout or result.stderr).strip()
    output = raw_output.splitlines()
    match = _VERSION_RE.search(raw_output)
    exact = next(
        (
            exact_match.group(1)
            for line in output
            if (exact_match := _EXACT_VERSION_RE.fullmatch(line.strip()))
        ),
        None,
    )
    parsed = match.group(1) if match else exact
    value = parsed or fallback
    return {
        "value": value,
        "source": "command" if parsed else source,
        "probe_ok": result.returncode == 0,
        "note": (
            None
            if result.returncode == 0 and parsed
            else (
                "unparseable-version-output"
                if result.returncode == 0
                else f"exit-{result.returncode}"
            )
        ),
    }


def _probe_mcp(component: Component, listener: bool | None) -> tuple[bool | None, bool | None, dict]:
    if component.transport != "streamable_http" or not component.default_endpoint:
        return None, None, {"attempted": False, "reason": "not-streamable-http"}
    if listener is not True:
        return None, None, {"attempted": False, "reason": "listener-not-ready"}
    try:
        initialized = initialize(component.default_endpoint)
        sid = session_id(initialized)
        listed = rpc(component.default_endpoint, "tools/list", request_id=2, session_id=sid)
        tools = listed.body.get("result", {}).get("tools")
        if initialized.status != 200 or listed.status != 200 or not isinstance(tools, list):
            return False, None, {"attempted": True, "initialize": False, "tools_list": False}
        safe_tool = component.raw.get("safe_tool")
        if not safe_tool:
            return True, None, {
                "attempted": True,
                "initialize": True,
                "tools_list": True,
                "tool_count": len(tools),
                "safe_call_attempted": False,
            }
        called = rpc(
            component.default_endpoint,
            "tools/call",
            {
                "name": safe_tool,
                "arguments": component.raw.get("safe_tool_args") or {},
            },
            request_id=3,
            session_id=sid,
            timeout=20,
        )
        payload = called.body.get("result", {})
        safe_ok = called.status == 200 and not payload.get("isError", False)
        return True, safe_ok, {
            "attempted": True,
            "initialize": True,
            "tools_list": True,
            "tool_count": len(tools),
            "safe_call_attempted": True,
            "safe_tool": str(safe_tool),
        }
    except (OSError, TimeoutError, TypeError, ValueError) as exc:
        return False, None, {
            "attempted": True,
            "initialize": False,
            "tools_list": False,
            "error_type": type(exc).__name__,
        }


def _probe_oauth(component: Component, listener: bool | None) -> tuple[bool | None, dict]:
    if component.role != "oauth_edge" or not component.default_endpoint:
        return None, {"attempted": False, "reason": "not-oauth-edge"}
    if listener is not True:
        return None, {"attempted": False, "reason": "listener-not-ready"}
    base = component.default_endpoint.rstrip("/")
    try:
        protected = requests.get(base + "/.well-known/oauth-protected-resource", timeout=5)
        auth = requests.get(base + "/.well-known/oauth-authorization-server", timeout=5)
        protected_json = protected.json() if protected.status_code == 200 else {}
        auth_json = auth.json() if auth.status_code == 200 else {}
        metadata_ok = (
            protected.status_code == 200
            and auth.status_code == 200
            and bool(protected_json.get("resource"))
            and all(
                auth_json.get(key)
                for key in ("authorization_endpoint", "token_endpoint", "registration_endpoint")
            )
        )
        return metadata_ok, {
            "attempted": True,
            "protected_resource_status": protected.status_code,
            "authorization_server_status": auth.status_code,
            "metadata_complete": metadata_ok,
            "scope": "read-only-metadata",
            "authoritative_full_oauth_requires_real_https": True,
        }
    except (requests.RequestException, ValueError) as exc:
        return False, {
            "attempted": True,
            "metadata_complete": False,
            "error_type": type(exc).__name__,
            "authoritative_full_oauth_requires_real_https": True,
        }


def _public_mcp_url() -> str | None:
    path = state_root() / "config" / "manager.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return configured_public_mcp_url(data if isinstance(data, dict) else {})


def _remote_urls(public_mcp: str) -> tuple[str, str]:
    parts = urlsplit(public_mcp)
    path = parts.path.rstrip("/")
    if path.endswith("/mcp"):
        base_path = path[:-4]
        mcp_path = path
    else:
        base_path = path
        mcp_path = path + "/mcp"
    base = urlunsplit((parts.scheme, parts.netloc, base_path, "", "")).rstrip("/")
    mcp = urlunsplit((parts.scheme, parts.netloc, mcp_path, "", ""))
    return base, mcp


def _probe_remote(public_mcp: str | None) -> tuple[bool | None, dict]:
    if not public_mcp:
        return None, {"attempted": False, "reason": "public-mcp-not-configured"}
    base, mcp_url = _remote_urls(public_mcp)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "webgpt-as-codex-doctor", "version": "0.1.0"},
        },
    }
    try:
        metadata = requests.get(base + "/.well-known/oauth-protected-resource", timeout=8)
        unauth = requests.post(
            mcp_url,
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
            timeout=10,
            allow_redirects=False,
        )
        ok = metadata.status_code == 200 and unauth.status_code == 401
        return ok, {
            "attempted": True,
            "https": True,
            "protected_resource_status": metadata.status_code,
            "unauthenticated_mcp_status": unauth.status_code,
            "oauth_challenge_present": bool(unauth.headers.get("WWW-Authenticate")),
        }
    except requests.RequestException as exc:
        return False, {"attempted": True, "https": True, "error_type": type(exc).__name__}


def _check_component(
    component: Component,
    process_rows: list[str] | None,
    remote_health: bool | None,
    remote_evidence: dict[str, Any],
) -> dict[str, Any]:
    discovered = discover_component(component)
    listener = discovered.get("listener_up")
    protocol, safe_call, protocol_evidence = _probe_mcp(component, listener)
    oauth, oauth_evidence = _probe_oauth(component, listener)
    relevant_remote = component.role in {"gateway", "oauth_edge", "remote_transport"}
    health = {
        "process": _process_health(component, process_rows),
        "listener": listener,
        "protocol": protocol,
        "safe_call": safe_call,
        "oauth": oauth,
        "remote": remote_health if relevant_remote else None,
    }
    version = _version_probe(component)
    return {
        "id": component.id,
        "display_name": component.display_name,
        "required": component.required,
        "version": version.get("value"),
        "version_source": version.get("source"),
        "health": health,
        "evidence": {
            "version": version,
            "process": {
                "attempted": bool(_process_markers(component)) and process_rows is not None,
                "markers_configured": bool(_process_markers(component)),
            },
            "listener": {"attempted": component.default_endpoint is not None},
            "protocol": protocol_evidence,
            "oauth": oauth_evidence,
            "remote": remote_evidence if relevant_remote else {"attempted": False, "reason": "not-edge-role"},
        },
    }


def _summarize(
    components: dict[str, Component],
    rows: dict[str, dict[str, Any]],
    *,
    remote_expected: bool,
) -> tuple[str, dict]:
    failures: list[str] = []
    warnings: list[str] = []
    for cid, component in components.items():
        health = rows[cid]["health"]
        applicable = {
            "process": bool(_process_markers(component)),
            "listener": component.default_endpoint is not None,
            "protocol": (
                component.transport == "streamable_http"
                and component.default_endpoint is not None
                and health["listener"] is True
            ),
            "safe_call": bool(component.raw.get("safe_tool")) and health["protocol"] is True,
            "oauth": component.role == "oauth_edge" and health["listener"] is True,
            "remote": (
                remote_expected
                and component.role in {"gateway", "oauth_edge", "remote_transport"}
            ),
        }
        for level in HEALTH_LEVELS:
            if not applicable[level]:
                continue
            value = health[level]
            label = f"{cid}:{level}"
            if value is False:
                (failures if component.required else warnings).append(label)
            elif value is None:
                warnings.append(label + ":unknown")
    status = "fail" if failures else ("degraded" if warnings else "pass")
    return status, {
        "required_failures": failures,
        "warnings": warnings,
        "component_count": len(rows),
    }


def persist_doctor_result(result: dict[str, Any]) -> Path:
    root = ensure_state_dirs()
    target = root / "doctor" / "last-result.json"
    cleaned = sanitize_for_output(result)
    atomic_write_json(target, cleaned)
    return target


def run_doctor(*, include_remote: bool = True, persist: bool = True) -> dict[str, Any]:
    components = load_components()
    process_rows = _process_snapshot()
    public_mcp = _public_mcp_url() if include_remote else None
    remote_health, remote_evidence = _probe_remote(public_mcp) if include_remote else (
        None,
        {"attempted": False, "reason": "remote-check-disabled"},
    )
    rows = {
        cid: _check_component(component, process_rows, remote_health, remote_evidence)
        for cid, component in components.items()
    }
    status, summary = _summarize(
        components,
        rows,
        remote_expected=include_remote and public_mcp is not None,
    )
    result = sanitize_for_output(
        {
            "status": status,
            "completed_at": datetime.now(UTC).isoformat(),
            "summary": summary,
            "checks": {
                "process_snapshot_available": process_rows is not None,
                "public_remote_configured": public_mcp is not None,
                "remote": remote_evidence,
                "persistence": "machine-local-sanitized",
            },
            "components": rows,
            "health_levels": list(HEALTH_LEVELS),
        }
    )
    if persist:
        persist_doctor_result(result)
    return result


def manager_doctor_executor(
    _contract: object,
    _payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = run_doctor(include_remote=True, persist=True)
    return {
        "ok": True,
        "status": result["status"],
        "completed_at": result["completed_at"],
        "summary": result["summary"],
    }


def cli_doctor(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex doctor")
    parser.add_argument("--no-remote", action="store_true")
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args(argv)
    result = run_doctor(include_remote=not args.no_remote, persist=not args.no_persist)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "fail" else 2
