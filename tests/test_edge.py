
import pytest

from webgpt_as_codex import edge
from webgpt_as_codex.edge import auth_proxy_binary, tailscale_binary


def test_edge_binaries_live_outside_repo() -> None:
    assert auth_proxy_binary().name == "mcp-auth-proxy.exe"
    assert tailscale_binary().name.lower() == "tailscale.exe"


def test_auth_proxy_machine_local_path() -> None:
    path = auth_proxy_binary()
    assert "WebGPT-as-Codex" in str(path)
    assert ".git" not in path.parts


def test_public_https_base_omits_default_443() -> None:
    assert edge.public_https_base("node.example.ts.net", 443) == "https://node.example.ts.net"
    assert edge.public_https_base("node.example.ts.net", 8443) == "https://node.example.ts.net:8443"


def test_start_funnel_rejects_unsupported_public_port() -> None:
    with pytest.raises(ValueError, match="443, 8443, or 10000"):
        edge.start_funnel("http://127.0.0.1:9341", public_port=10003)


def test_start_funnel_refuses_existing_other_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        edge,
        "funnel_proxy_for_port",
        lambda _port: "http://127.0.0.1:9240",
    )
    with pytest.raises(RuntimeError, match="already has another target"):
        edge.start_funnel("http://127.0.0.1:9341", public_port=443)
