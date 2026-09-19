from __future__ import annotations

import json
import time

import requests

from webgpt_as_codex.edge_runtime import public_base_url, read_oauth_password
from webgpt_as_codex.mcp import initialize, rpc, session_id
from webgpt_as_codex.oauth import password_pkce_flow, refresh_access_token
from webgpt_as_codex.runtime import RuntimeSupervisor


def _wait_public(public_base: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = requests.get(
                public_base.rstrip("/") + "/.well-known/oauth-protected-resource",
                timeout=5,
            )
            if response.status_code == 200:
                return
        except requests.RequestException as exc:
            last = exc
        time.sleep(0.5)
    raise RuntimeError(f"public edge did not become ready: {type(last).__name__ if last else 'timeout'}")


def _assert_unauthenticated_gate(public_base: str) -> None:
    response = requests.post(
        public_base.rstrip("/") + "/mcp",
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "webgpt-production-unauth-probe",
                        "version": "1",
                    },
                },
            }
        ),
        timeout=20,
        allow_redirects=False,
    )
    if response.status_code != 401:
        raise RuntimeError(
            f"public unauthenticated MCP returned {response.status_code}, expected 401"
        )


def _assert_authenticated_mcp(public_base: str, access_token: str) -> int:
    headers = {"Authorization": "Bearer " + access_token}
    init = initialize(public_base.rstrip("/") + "/mcp", extra_headers=headers)
    sid = session_id(init)
    listed = rpc(
        public_base.rstrip("/") + "/mcp",
        "tools/list",
        request_id=2,
        session_id=sid,
        extra_headers=headers,
    )
    tools = listed.body.get("result", {}).get("tools", [])
    names = {str(tool.get("name")) for tool in tools if isinstance(tool, dict)}
    required = "coding-tools__server_info"
    if required not in names:
        raise RuntimeError(f"expected routed tool missing: {required}")
    called = rpc(
        public_base.rstrip("/") + "/mcp",
        "tools/call",
        {"name": required, "arguments": {}},
        request_id=3,
        session_id=sid,
        extra_headers=headers,
        timeout=30,
    )
    if called.body.get("result", {}).get("isError", False):
        raise RuntimeError("coding-tools__server_info returned isError")
    return len(tools)


def main() -> int:
    public_base = public_base_url()
    _wait_public(public_base)
    print("PUBLIC_METADATA_PASS")

    _assert_unauthenticated_gate(public_base)
    print("PUBLIC_UNAUTH_401_PASS")

    credential = read_oauth_password()
    session, tokens = password_pkce_flow(
        public_base,
        credential,
        redirect_uri="https://chatgpt.com/connector/oauth/webgpt-codex-production-probe",
    )
    print("DCR_PKCE_TOKEN_PASS")

    tool_count = _assert_authenticated_mcp(public_base, tokens.access_token)
    print(f"PUBLIC_AUTHENTICATED_MCP_PASS tools={tool_count}")

    restarted = RuntimeSupervisor().restart("mcp-auth-proxy")
    if not restarted.get("ok"):
        raise RuntimeError(
            "production edge restart failed: " + str(restarted.get("status"))
        )
    _wait_public(public_base)
    print("PRODUCTION_EDGE_RESTART_PASS")

    refreshed = refresh_access_token(session, public_base, tokens)
    print("REFRESH_AFTER_RESTART_PASS")

    post_restart_count = _assert_authenticated_mcp(public_base, refreshed)
    if post_restart_count != tool_count:
        raise RuntimeError(
            f"tool count changed across restart: {tool_count} -> {post_restart_count}"
        )
    print(f"PUBLIC_RESTARTED_MCP_PASS tools={post_restart_count}")
    print("STAGE14_PRODUCTION_EDGE_E2E_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
