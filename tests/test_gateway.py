
from webgpt_as_codex.gateway import mcpjungle_binary
from webgpt_as_codex.mcp import _decode


def test_sse_decode() -> None:
    assert _decode(b'data: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n')["result"]["ok"]


def test_json_decode() -> None:
    assert _decode(b'{"jsonrpc":"2.0","id":1,"result":{}}')["id"] == 1


def test_fragmented_sse_decode() -> None:
    raw = (
        b"event: message\n"
        b'data: {"jsonrpc":"2.0",\n'
        b'data: "id":1,"result":{"ok":true}}\n\n'
    )
    assert _decode(raw)["result"]["ok"] is True


def test_mcpjungle_binary_is_outside_repo() -> None:
    path = mcpjungle_binary()
    assert path.name == "mcpjungle.exe"
    assert "WebGPT-as-Codex" in str(path)
    assert ".git" not in path.parts
