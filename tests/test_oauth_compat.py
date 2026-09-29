import http.client
import http.server
import threading

import pytest
import requests

from webgpt_as_codex import oauth_compat


def _serve(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.mark.parametrize(
    ("failure", "expected"),
    [(requests.Timeout("slow"), 504), (requests.ConnectionError("down"), 502)],
)
def test_compat_proxy_returns_controlled_upstream_errors(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected: int,
) -> None:
    def fail(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(oauth_compat.requests, "request", fail)
    handler = oauth_compat._handler("http://127.0.0.1:9340", "https://example.test")
    server, thread = _serve(handler)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        conn.request("GET", "/.well-known/oauth-protected-resource")
        response = conn.getresponse()
        body = response.read()
        assert response.status == expected
        assert body in {b"upstream timeout", b"upstream unavailable"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def _response(status: int, body: bytes, content_type: str = "application/json") -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.headers["Content-Type"] = content_type
    return response


def test_compat_publishes_path_scoped_resource_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    upstream = _response(
        200,
        b'{"resource":"https://example.test/","authorization_servers":["https://example.test/"]}',
    )
    monkeypatch.setattr(oauth_compat.requests, "request", lambda *_a, **_kw: upstream)
    handler = oauth_compat._handler("http://127.0.0.1:9340", "https://example.test")
    server, thread = _serve(handler)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        conn.request("GET", "/.well-known/oauth-protected-resource/mcp")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        assert response.status == 200
        assert '"resource":"https://example.test/mcp"' in body
        assert '"bearer_methods_supported":["header"]' in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_compat_challenge_points_to_path_scoped_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    upstream = _response(401, b'{"error":"Unauthorized"}')
    monkeypatch.setattr(oauth_compat.requests, "request", lambda *_a, **_kw: upstream)
    handler = oauth_compat._handler("http://127.0.0.1:9340", "https://example.test")
    server, thread = _serve(handler)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        conn.request("GET", "/mcp")
        response = conn.getresponse()
        response.read()
        assert response.status == 401
        assert response.getheader("WWW-Authenticate") == (
            'Bearer resource_metadata="https://example.test/.well-known/oauth-protected-resource/mcp"'
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)



def test_compat_streams_mcp_get_without_buffering() -> None:
    release = threading.Event()

    class StreamingHandler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b"event: message\n")
            self.wfile.write(b'data: {"ok":true}\n\n')
            self.wfile.flush()
            release.wait(timeout=2)

    upstream_server, upstream_thread = _serve(StreamingHandler)
    compat = oauth_compat._handler(
        f"http://127.0.0.1:{upstream_server.server_port}",
        "https://example.test",
    )
    compat_server, compat_thread = _serve(compat)
    try:
        conn = http.client.HTTPConnection(
            "127.0.0.1",
            compat_server.server_port,
            timeout=1,
        )
        conn.request("GET", "/mcp")
        response = conn.getresponse()
        assert response.status == 200
        assert response.getheader("Content-Type") == "text/event-stream"
        assert response.readline() == b"event: message\n"
        assert response.readline() == b'data: {"ok":true}\n'
        assert response.readline() == b"\n"
    finally:
        release.set()
        upstream_server.shutdown()
        upstream_server.server_close()
        upstream_thread.join(timeout=3)
        compat_server.shutdown()
        compat_server.server_close()
        compat_thread.join(timeout=3)
