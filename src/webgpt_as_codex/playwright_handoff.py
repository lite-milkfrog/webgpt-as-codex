from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .handoff import validate_handoff_prompt
from .mcp import _decode


@dataclass(frozen=True)
class PlaywrightHandoffResult:
    conversation_url: str
    prompt_sha256: str
    sent_user_message_verified: bool
    assistant_run_verified: bool


class PlaywrightMcpClient:
    def __init__(self, endpoint: str, *, timeout: float = 30.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "webgpt-as-codex-handoff", "version": "0.1.0"},
                },
            }
        )
        session_id = response.headers.get("Mcp-Session-Id")
        if session_id:
            self.headers["Mcp-Session-Id"] = session_id

    def _post(self, payload: dict[str, Any]) -> requests.Response:
        response = requests.post(
            self.endpoint,
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def tool(self, name: str, arguments: dict[str, Any], *, request_id: int) -> dict[str, Any]:
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        body = _decode(response.content)
        result = body.get("result", {})
        if result.get("isError", False):
            raise RuntimeError(_tool_text(body) or f"{name} returned isError")
        return body


def _tool_text(body: dict[str, Any]) -> str:
    content = body.get("result", {}).get("content", [])
    return "\n".join(
        str(item.get("text", ""))
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    )


def _textbox_ref(snapshot_text: str, *, require_active: bool = False) -> str:
    active_patterns = (
        r"textbox .*?\[active\].*?\[ref=(e\d+)\]",
        r"textbox .*?\[ref=(e\d+)\].*?\[active\]",
    )
    for pattern in active_patterns:
        match = re.search(pattern, snapshot_text)
        if match:
            return match.group(1)
    if require_active:
        raise RuntimeError("active ChatGPT composer textbox not found in Playwright snapshot")
    match = re.search(r"textbox .*?\[ref=(e\d+)\]", snapshot_text)
    if not match:
        raise RuntimeError("ChatGPT composer textbox not found in Playwright snapshot")
    return match.group(1)


def _wait_for_active_composer(
    client: PlaywrightMcpClient,
    *,
    timeout_seconds: float,
    first_request_id: int = 3,
) -> tuple[str, int]:
    deadline = time.monotonic() + timeout_seconds
    request_id = first_request_id
    last_snapshot = ""
    while time.monotonic() < deadline:
        last_snapshot = _tool_text(
            client.tool("browser_snapshot", {}, request_id=request_id)
        )
        request_id += 1
        try:
            return _textbox_ref(last_snapshot, require_active=True), request_id
        except RuntimeError:
            time.sleep(0.25)
    raise RuntimeError(
        "active ChatGPT composer did not hydrate before timeout; "
        f"last_snapshot={last_snapshot[-800:]!r}"
    )


def _evaluation_json(tool_text: str) -> dict[str, Any]:
    marker = "### Result"
    if marker not in tool_text:
        raise RuntimeError("browser_evaluate result marker missing")
    tail = tool_text.split(marker, 1)[1].strip()
    if "\n### " in tail:
        tail = tail.split("\n### ", 1)[0].strip()
    try:
        value = json.loads(tail)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"browser_evaluate result was not JSON: {tail[:400]}") from exc
    if not isinstance(value, dict):
        raise TypeError("browser_evaluate did not return an object")
    return value


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def handoff_via_playwright(
    endpoint: str,
    prompt_path: Path,
    *,
    expected_sha256: str,
    expected_stage: str,
    expected_head: str,
    timeout_seconds: float = 45.0,
) -> PlaywrightHandoffResult:
    prompt = prompt_path.read_text(encoding="utf-8")
    actual_sha = prompt_sha256(prompt)
    if actual_sha != expected_sha256:
        raise RuntimeError(f"prompt SHA-256 mismatch: {actual_sha}")
    errors = validate_handoff_prompt(
        prompt,
        expected_stage=expected_stage,
        expected_head=expected_head,
    )
    if errors:
        raise RuntimeError("handoff prompt validation failed: " + "; ".join(errors))

    client = PlaywrightMcpClient(endpoint)
    client.tool(
        "browser_tabs",
        {"action": "new", "url": "https://chatgpt.com/"},
        request_id=2,
    )
    target, request_id = _wait_for_active_composer(
        client,
        timeout_seconds=min(15.0, timeout_seconds),
    )

    client.tool(
        "browser_type",
        {
            "target": target,
            "text": prompt,
            "submit": True,
            "slowly": False,
        },
        request_id=request_id,
    )

    deadline = time.monotonic() + timeout_seconds
    request_id += 1
    last_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state_body = client.tool(
            "browser_evaluate",
            {
                "function": (
                    "() => JSON.stringify({"
                    "url: location.href,"
                    "users: Array.from(document.querySelectorAll('[data-message-author-role=\"user\"]')).map(x => x.innerText),"
                    "assistantCount: document.querySelectorAll('[data-message-author-role=\"assistant\"]').length"
                    "})"
                )
            },
            request_id=request_id,
        )
        request_id += 1
        raw = _tool_text(state_body)
        outer = _evaluation_json(raw)
        value = outer
        if set(outer) == {"value"} and isinstance(outer["value"], str):
            value = json.loads(outer["value"])
        last_state = value
        users = value.get("users", []) if isinstance(value, dict) else []
        url = str(value.get("url", "")) if isinstance(value, dict) else ""
        assistant_count = int(value.get("assistantCount", 0)) if isinstance(value, dict) else 0
        sent = any(expected_head in str(message) for message in users)
        started = assistant_count >= 1
        if sent and started and "/c/" in url:
            return PlaywrightHandoffResult(
                conversation_url=url,
                prompt_sha256=actual_sha,
                sent_user_message_verified=True,
                assistant_run_verified=True,
            )
        time.sleep(0.75)

    raise RuntimeError(f"handoff verification timed out; last_state={last_state!r}")

def cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m webgpt_as_codex.playwright_handoff")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8931/mcp")
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    result = handoff_via_playwright(
        args.endpoint,
        args.prompt,
        expected_sha256=args.sha256,
        expected_stage=args.stage,
        expected_head=args.head,
    )
    payload = {
        "conversation_url": result.conversation_url,
        "prompt_sha256": result.prompt_sha256,
        "sent_user_message_verified": result.sent_user_message_verified,
        "assistant_run_verified": result.assistant_run_verified,
        "source_head": args.head,
        "stage": args.stage,
        "prompt_path": str(args.prompt),
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
