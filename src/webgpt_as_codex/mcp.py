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
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
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
