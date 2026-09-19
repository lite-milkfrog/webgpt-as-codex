
from webgpt_as_codex.edge import auth_proxy_binary, tailscale_binary


def test_edge_binaries_live_outside_repo() -> None:
    assert auth_proxy_binary().name == "mcp-auth-proxy.exe"
    assert tailscale_binary().name.lower() == "tailscale.exe"


def test_auth_proxy_machine_local_path() -> None:
    path = auth_proxy_binary()
    assert "WebGPT-as-Codex" in str(path)
    assert ".git" not in path.parts
