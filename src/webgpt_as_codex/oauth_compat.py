from __future__ import annotations

import http.server
import threading
import urllib.parse
from collections.abc import Iterator
from contextlib import contextmanager

import requests


def _set_cookies(response: requests.Response) -> list[str]:
    raw = getattr(response.raw, "headers", None)
    getlist = getattr(raw, "getlist", None)
    if callable(getlist):
        return list(getlist("Set-Cookie"))
    value = response.headers.get("Set-Cookie")
    return [value] if value else []


def _cookie_pairs(set_cookie_values: list[str]) -> list[str]:
    return [value.split(";", 1)[0] for value in set_cookie_values if value]


def _handler(upstream: str, external_url: str):
    upstream = upstream.rstrip("/")
    external = external_url.rstrip("/")
    external_host = urllib.parse.urlparse(external).netloc

    class CompatHandler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0") or "0")
            return self.rfile.read(length) if length else b""

        def _headers(self, *, cookie: str | None = None) -> dict[str, str]:
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {"host", "content-length", "connection"}
            }
            headers["X-Forwarded-Proto"] = "https"
            headers["X-Forwarded-Host"] = external_host
            if cookie:
                headers["Cookie"] = cookie
            return headers

        def _write(
            self,
            status: int,
            headers: dict[str, str],
            body: bytes,
            extra_set_cookie: list[str] | None = None,
        ) -> None:
            self.send_response(status)
            skip = {"content-length", "connection", "transfer-encoding", "set-cookie"}
            for key, value in headers.items():
                if key.lower() not in skip:
                    self.send_header(key, value)
            for value in extra_set_cookie or []:
                self.send_header("Set-Cookie", value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _forward(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = ("?" + parsed.query) if parsed.query else ""
            upstream_path = (
                "/.well-known/oauth-protected-resource"
                if path == "/.well-known/oauth-protected-resource/mcp"
                else path
            )
            body = self._body()
            response = requests.request(
                self.command,
                upstream + upstream_path + query,
                headers=self._headers(),
                data=body if body else None,
                allow_redirects=False,
                timeout=20,
            )

            if (
                self.command == "POST"
                and path == "/.auth/login"
                and 300 <= response.status_code < 400
            ):
                location = response.headers.get("Location", "")
                target = urllib.parse.urlparse(location)
                if target.path.startswith("/.idp/auth/"):
                    prior = self.headers.get("Cookie", "").strip()
                    fresh_pairs = _cookie_pairs(_set_cookies(response))
                    cookie = "; ".join(part for part in [prior, *fresh_pairs] if part)
                    consent = requests.post(
                        upstream + target.path + (("?" + target.query) if target.query else ""),
                        headers=self._headers(cookie=cookie),
                        data=b"",
                        allow_redirects=False,
                        timeout=20,
                    )
                    cookies = _set_cookies(response) + _set_cookies(consent)
                    self._write(
                        consent.status_code,
                        dict(consent.headers),
                        consent.content,
                        cookies,
                    )
                    return

            headers = dict(response.headers)
            if response.status_code == 401 and path == "/mcp":
                headers["WWW-Authenticate"] = (
                    f'Bearer resource_metadata="{external}/.well-known/oauth-protected-resource"'
                )
            self._write(
                response.status_code,
                headers,
                response.content,
                _set_cookies(response),
            )

        do_GET = _forward
        do_POST = _forward
        do_HEAD = _forward

    return CompatHandler


@contextmanager
def temporary_oauth_compat(
    upstream: str,
    external_url: str,
    *,
    port: int = 9341,
) -> Iterator[str]:
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", port),
        _handler(upstream, external_url),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
