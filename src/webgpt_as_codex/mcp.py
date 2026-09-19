from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class McpResponse:
    status: int
    headers: dict[str, str]
    body: dict[str, Any]


def _decode(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("empty MCP response")

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
        raise TypeError("MCP JSON response was not an object")
    except json.JSONDecodeError:
        pass

    events: list[list[str]] = []
    current: list[str] = []
    in_data = False

    for line in text.splitlines():
        if line.startswith("data:"):
            current.append(line[5:].lstrip())
            in_data = True
            continue
        if in_data and not line.strip():
            if current:
                events.append(current)
            current = []
            in_data = False
            continue
        if in_data and not line.startswith(("event:", "id:", "retry:", ":")):
            # Tolerate transport/proxy line wrapping inside one SSE data payload.
            current.append(line)

    if current:
        events.append(current)

    for parts in events:
        for payload in ("".join(parts), "\n".join(parts)):
            try:
                value = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value

    raise ValueError(f"unrecognized MCP response: {text[:500]}")


def rpc(
    url: str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: int = 1,
    session_id: str | None = None,
    timeout: float = 20.0,
    extra_headers: dict[str, str] | None = None,
) -> McpResponse:
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return McpResponse(
            status=response.status,
            headers={k: v for k, v in response.headers.items()},
            body=_decode(response.read()),
        )


def initialize(url: str, *, extra_headers: dict[str, str] | None = None) -> McpResponse:
    return rpc(
        url,
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "webgpt-as-codex-doctor", "version": "0.1.0"},
        },
        extra_headers=extra_headers,
    )


def session_id(response: McpResponse) -> str | None:
    for key, value in response.headers.items():
        if key.lower() == "mcp-session-id":
            return value
    return None
