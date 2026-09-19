from __future__ import annotations

import json
import shutil
import sys
import time

import requests

from webgpt_as_codex.edge import (
    start_funnel,
    stop_funnel,
    tailscale_dns_name,
    temporary_auth_proxy,
)
from webgpt_as_codex.gateway import register_http, temporary_mcpjungle
from webgpt_as_codex.mcp import initialize, rpc, session_id
from webgpt_as_codex.oauth import password_pkce_flow, refresh_access_token
from webgpt_as_codex.oauth_compat import temporary_oauth_compat
from webgpt_as_codex.paths import ensure_state_dirs

PUBLIC_PORT = 10003


def assert_gateway_call(url: str, access_token: str, label: str) -> None:
    headers = {"Authorization": "Bearer " + access_token}
    init = initialize(url, extra_headers=headers)
    sid = session_id(init)
    listed = rpc(url, "tools/list", request_id=2, session_id=sid, extra_headers=headers)
    names = {tool.get("name") for tool in listed.body.get("result", {}).get("tools", [])}
    if "coding__server_info" not in names:
        raise RuntimeError(f"{label}: coding__server_info missing")
    called = rpc(
        url,
        "tools/call",
        {"name": "coding__server_info", "arguments": {}},
        request_id=3,
        session_id=sid,
        extra_headers=headers,
        timeout=30,
    )
    if called.body.get("result", {}).get("isError", False):
        raise RuntimeError(f"{label}: coding__server_info returned isError")
    print(label, "MCP_PASS")


def wait_public(public: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = requests.get(
                public + "/.well-known/oauth-protected-resource",
                timeout=5,
            )
            if response.status_code == 200:
                return
        except requests.RequestException as exc:
            last = exc
        time.sleep(0.5)
    raise RuntimeError(f"public Funnel did not become ready: {last}")


def main() -> int:
    stop_funnel(public_port=PUBLIC_PORT)
    public_base = f"https://{tailscale_dns_name()}:{PUBLIC_PORT}"
    state = ensure_state_dirs() / "stage5"
    data = state / "oauth-data-e2e"
    if data.exists():
        shutil.rmtree(data)

    with temporary_mcpjungle(port=9330) as (_, registry):
        register_http(
            registry,
            "coding",
            "http://127.0.0.1:8766/mcp",
            "Repository mutation, test and Git",
        )

        with (
            temporary_auth_proxy(
                registry,
                public_base,
                port=9340,
                data_path=data,
            ) as (_, raw_local, password, _),
            temporary_oauth_compat(raw_local, public_base, port=9341) as compat_local,
        ):
            public = start_funnel(compat_local, public_port=PUBLIC_PORT)
            try:
                    wait_public(public)
                    print("PUBLIC_METADATA_PASS")
                    session, tokens = password_pkce_flow(public, password)
                    print("DCR_PKCE_TOKEN_PASS")
                    assert_gateway_call(public + "/mcp", tokens.access_token, "PUBLIC_INITIAL")

                    unauth = requests.post(
                        public + "/mcp",
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
                                    "clientInfo": {"name": "unauth-probe", "version": "1"},
                                },
                            }
                        ),
                        timeout=20,
                        allow_redirects=False,
                    )
                    if unauth.status_code != 401:
                        raise RuntimeError(
                            f"public unauthenticated /mcp returned {unauth.status_code}"
                        )
                    print("PUBLIC_UNAUTH_401_PASS")
            finally:
                stop_funnel(public_port=PUBLIC_PORT)

        with (
            temporary_auth_proxy(
                registry,
                public_base,
                port=9340,
                data_path=data,
                password=password,
            ) as (_, raw_local, _, _),
            temporary_oauth_compat(raw_local, public_base, port=9341) as compat_local,
        ):
            public = start_funnel(compat_local, public_port=PUBLIC_PORT)
            try:
                    wait_public(public)
                    refreshed = refresh_access_token(session, public, tokens)
                    print("REFRESH_AFTER_RESTART_PASS")
                    assert_gateway_call(public + "/mcp", refreshed, "PUBLIC_RESTARTED")
            finally:
                stop_funnel(public_port=PUBLIC_PORT)

    print("STAGE5_EDGE_E2E_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
