from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .concurrency import MachineGuiLease
from .handoff import validate_handoff_prompt
from .mcp import _decode
from .paths import ensure_state_dirs
from .stateio import atomic_write_json

_CHATGPT_ORIGIN = "https://chatgpt.com"
_TAB_LEASE_KEY = "__webgpt_as_codex_handoff_tab_lease_v1"
_IDEMPOTENCY_STATES = {
    "PREPARED",
    "SUBMIT_ATTEMPTED",
    "SUBMITTED_VERIFIED",
    "AMBIGUOUS_AFTER_SIDE_EFFECT",
    "FAILED_BEFORE_SIDE_EFFECT",
}
_IDEMPOTENCY_TRANSITIONS = {
    None: {"PREPARED"},
    "PREPARED": {"PREPARED", "SUBMIT_ATTEMPTED", "FAILED_BEFORE_SIDE_EFFECT"},
    "FAILED_BEFORE_SIDE_EFFECT": {"FAILED_BEFORE_SIDE_EFFECT", "PREPARED"},
    "SUBMIT_ATTEMPTED": {"SUBMIT_ATTEMPTED", "SUBMITTED_VERIFIED", "AMBIGUOUS_AFTER_SIDE_EFFECT"},
    "AMBIGUOUS_AFTER_SIDE_EFFECT": {"AMBIGUOUS_AFTER_SIDE_EFFECT", "SUBMITTED_VERIFIED"},
    "SUBMITTED_VERIFIED": {"SUBMITTED_VERIFIED"},
}


@dataclass(frozen=True)
class PlaywrightHandoffResult:
    conversation_url: str
    prompt_sha256: str
    sent_user_message_verified: bool
    assistant_run_verified: bool
    handoff_first_pass: bool
    recoveries: tuple[str, ...] = ()
    owner_id: str = ""
    tab_lease_token: str = ""
    idempotency_state: str = "SUBMITTED_VERIFIED"
    submit_attempted_at: float | None = None
    verified_at: float | None = None
    reused_existing_tab: bool = False


class AmbiguousSubmissionError(RuntimeError):
    """Submission was attempted once, so retrying could duplicate the user message."""


class PromptSubmissionLedger:
    """Persistent prompt-SHA state machine for exactly-once browser handoff."""

    def __init__(self, root: Path | None = None) -> None:
        state_root = root or ensure_state_dirs()
        self.root = state_root / "handoffs" / "playwright" / "submissions"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, prompt_sha256: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", prompt_sha256):
            raise ValueError("prompt_sha256 must be a lowercase SHA-256 hex digest")
        return self.root / f"{prompt_sha256}.json"

    def read(self, prompt_sha256: str) -> dict[str, Any] | None:
        path = self._path(prompt_sha256)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"corrupt Playwright handoff ledger: {path.name}") from exc
        if not isinstance(payload, dict):
            raise TypeError(f"invalid Playwright handoff ledger: {path.name}")
        return payload

    def transition(
        self,
        prompt_sha256: str,
        state: str,
        **updates: Any,
    ) -> dict[str, Any]:
        if state not in _IDEMPOTENCY_STATES:
            raise ValueError(f"unknown idempotency state: {state}")
        current = self.read(prompt_sha256)
        previous = current.get("state") if current else None
        allowed = _IDEMPOTENCY_TRANSITIONS.get(previous, set())
        if state not in allowed:
            raise RuntimeError(
                f"illegal idempotency transition for {prompt_sha256[:12]}: "
                f"{previous!r} -> {state!r}"
            )
        now = time.time()
        payload: dict[str, Any] = {
            **(current or {}),
            "schema_version": 1,
            "prompt_sha256": prompt_sha256,
            "state": state,
            "updated_at": now,
            **updates,
        }
        payload.setdefault("created_at", now)
        atomic_write_json(self._path(prompt_sha256), payload, sort_keys=True)
        return payload


class PlaywrightMcpClient:
    def __init__(self, endpoint: str, *, timeout: float = 30.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.tab_lease_token: str | None = None
        self.reused_existing_tab = False
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


def _tab_rows(tabs_text: str) -> list[tuple[int, bool, str]]:
    rows: list[tuple[int, bool, str]] = []
    seen: set[tuple[int, bool, str]] = set()
    for line in tabs_text.splitlines():
        match = re.match(
            r"- (\d+): (?:(\(current\)) )?\[[^\]]*\]\(([^)]+)\)",
            line.strip(),
        )
        if match:
            row = (int(match.group(1)), bool(match.group(2)), match.group(3))
            if row not in seen:
                seen.add(row)
                rows.append(row)
    return rows


def _target_blank_chatgpt_tab_index(tabs_text: str) -> int:
    blank = [row for row in _tab_rows(tabs_text) if row[2] == "https://chatgpt.com/"]
    if not blank:
        raise RuntimeError("new blank ChatGPT tab not found in Playwright tab list")
    current = [row for row in blank if row[1]]
    return current[0][0] if current else max(row[0] for row in blank)


def _target_new_chatgpt_tab_index(before_text: str, after_text: str) -> int:
    before = {row[0] for row in _tab_rows(before_text)}
    blank_after = [row for row in _tab_rows(after_text) if row[2] == "https://chatgpt.com/"]
    created = [row for row in blank_after if row[0] not in before]
    if len(created) == 1:
        return created[0][0]
    current = [row for row in blank_after if row[1]]
    if len(current) == 1 and (not created or current[0] in created):
        return current[0][0]
    raise RuntimeError("new ChatGPT tab selection is ambiguous after tab refresh")


def _unique_blank_chatgpt_tab_index(tabs_text: str) -> int:
    blank = [row for row in _tab_rows(tabs_text) if row[2] == "https://chatgpt.com/"]
    if len(blank) != 1:
        raise RuntimeError("unique blank ChatGPT recovery target not found")
    return blank[0][0]


def _evaluation_value_object(tool_text: str) -> dict[str, Any]:
    outer = _evaluation_json(tool_text)
    if set(outer) == {"value"} and isinstance(outer["value"], str):
        value = json.loads(outer["value"])
        if isinstance(value, dict):
            return value
    return outer


def _current_tab_lease_state(
    client: PlaywrightMcpClient,
    *,
    request_id: int,
) -> tuple[dict[str, Any], int]:
    key = json.dumps(_TAB_LEASE_KEY)
    body = client.tool(
        "browser_evaluate",
        {
            "function": (
                "() => {"
                "let lease=null;"
                f"try{{lease=sessionStorage.getItem({key});}}catch(_error){{}}"
                "return JSON.stringify({url:location.href,lease});"
                "}"
            )
        },
        request_id=request_id,
    )
    return _evaluation_value_object(_tool_text(body)), request_id + 1


def _pin_current_chatgpt_tab(
    client: PlaywrightMcpClient,
    lease_token: str,
    *,
    request_id: int,
) -> int:
    key = json.dumps(_TAB_LEASE_KEY)
    token = json.dumps(lease_token)
    origin = json.dumps(_CHATGPT_ORIGIN)
    body = client.tool(
        "browser_evaluate",
        {
            "function": (
                "() => {"
                "const url=location.href;"
                f"if(!(url==={origin} || url.startsWith({origin}+'/'))){{"
                "return JSON.stringify({url,lease:null,pinned:false});"
                "}"
                "try{"
                f"sessionStorage.setItem({key},{token});"
                f"const lease=sessionStorage.getItem({key});"
                f"return JSON.stringify({{url,lease,pinned:lease==={token}}});"
                "}catch(error){"
                "return JSON.stringify({url,lease:null,pinned:false,error:String(error)});"
                "}"
                "}"
            )
        },
        request_id=request_id,
    )
    state = _evaluation_value_object(_tool_text(body))
    if (
        not bool(state.get("pinned"))
        or state.get("lease") != lease_token
        or not str(state.get("url", "")).startswith(_CHATGPT_ORIGIN)
    ):
        raise RuntimeError(f"failed to pin ChatGPT tab lease: {state!r}")
    client.tab_lease_token = lease_token
    return request_id + 1


def _ensure_pinned_chatgpt_tab(
    client: PlaywrightMcpClient,
    *,
    first_request_id: int,
    recoveries: list[str] | None = None,
) -> int:
    lease_token = getattr(client, "tab_lease_token", None)
    if not lease_token:
        return first_request_id

    request_id = first_request_id
    state, request_id = _current_tab_lease_state(client, request_id=request_id)
    if (
        state.get("lease") == lease_token
        and str(state.get("url", "")).startswith(_CHATGPT_ORIGIN)
    ):
        return request_id

    tabs_text = _tool_text(
        client.tool("browser_tabs", {"action": "list"}, request_id=request_id)
    )
    request_id += 1
    candidates = [
        row[0]
        for row in _tab_rows(tabs_text)
        if row[2] == _CHATGPT_ORIGIN or row[2].startswith(_CHATGPT_ORIGIN + "/")
    ]
    for index in candidates:
        client.tool(
            "browser_tabs",
            {"action": "select", "index": index},
            request_id=request_id,
        )
        request_id += 1
        state, request_id = _current_tab_lease_state(client, request_id=request_id)
        if (
            state.get("lease") == lease_token
            and str(state.get("url", "")).startswith(_CHATGPT_ORIGIN)
        ):
            if recoveries is not None and "tab-lease-restored" not in recoveries:
                recoveries.append("tab-lease-restored")
            return request_id
    raise RuntimeError("pinned ChatGPT tab lease was lost")


def _open_and_select_chatgpt_tab(
    client: PlaywrightMcpClient,
    *,
    first_request_id: int = 2,
    recoveries: list[str] | None = None,
) -> int:
    request_id = first_request_id
    before = _tool_text(
        client.tool("browser_tabs", {"action": "list"}, request_id=request_id)
    )
    request_id += 1
    blank = [row for row in _tab_rows(before) if row[2] == "https://chatgpt.com/"]
    if len(blank) == 1:
        client.tool(
            "browser_tabs",
            {"action": "select", "index": blank[0][0]},
            request_id=request_id,
        )
        client.reused_existing_tab = True
        return request_id + 1

    client.tool(
        "browser_tabs",
        {"action": "new", "url": "https://chatgpt.com/"},
        request_id=request_id,
    )
    request_id += 1
    after = _tool_text(
        client.tool("browser_tabs", {"action": "list"}, request_id=request_id)
    )
    request_id += 1
    try:
        target_index = _target_new_chatgpt_tab_index(before, after)
    except RuntimeError:
        if recoveries is not None:
            recoveries.append("tab-selection-refresh")
        after = _tool_text(
            client.tool("browser_tabs", {"action": "list"}, request_id=request_id)
        )
        request_id += 1
        try:
            target_index = _target_new_chatgpt_tab_index(before, after)
        except RuntimeError:
            target_index = _unique_blank_chatgpt_tab_index(after)
            if recoveries is not None:
                recoveries.append("unique-blank-tab-reuse")
    client.tool(
        "browser_tabs",
        {"action": "select", "index": target_index},
        request_id=request_id,
    )
    return request_id + 1


def _wait_for_active_composer(
    client: PlaywrightMcpClient,
    *,
    timeout_seconds: float,
    first_request_id: int = 3,
    recoveries: list[str] | None = None,
) -> tuple[str, int]:
    deadline = time.monotonic() + timeout_seconds
    request_id = first_request_id
    last_snapshot = ""
    last_focus_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        focus_body = client.tool(
            "browser_evaluate",
            {
                "function": (
                    "() => {"
                    "const visible = el => {"
                    "const s=getComputedStyle(el), r=el.getBoundingClientRect();"
                    "return s.display!=='none' && s.visibility!=='hidden' && s.opacity!=='0' "
                    "&& r.width>1 && r.height>1 && !el.disabled "
                    "&& el.getAttribute('aria-hidden')!=='true';"
                    "};"
                    "const selectors=["
                    "'[contenteditable=\"true\"][data-lexical-editor=\"true\"]',"
                    "'[contenteditable=\"true\"][role=\"textbox\"]',"
                    "'textarea[name=\"prompt-textarea\"]',"
                    "'[contenteditable=\"true\"]','textarea'"
                    "];"
                    "const seen=new Set(), candidates=[];"
                    "for(const sel of selectors){for(const el of document.querySelectorAll(sel)){"
                    "if(!seen.has(el)){seen.add(el);candidates.push(el);}}}"
                    "const el=candidates.find(visible);"
                    "if(!el)return JSON.stringify({focused:false,reason:'no-visible-composer'});"
                    "el.focus();"
                    "return JSON.stringify({focused:document.activeElement===el,"
                    "tag:el.tagName,role:el.getAttribute('role'),"
                    "contenteditable:el.getAttribute('contenteditable')});"
                    "}"
                )
            },
            request_id=request_id,
        )
        request_id += 1
        focus_outer = _evaluation_json(_tool_text(focus_body))
        focus_value: dict[str, Any] = focus_outer
        if set(focus_outer) == {"value"} and isinstance(focus_outer["value"], str):
            parsed = json.loads(focus_outer["value"])
            if isinstance(parsed, dict):
                focus_value = parsed
        last_focus_state = focus_value
        if not bool(focus_value.get("focused")):
            if recoveries is not None and "hidden-hydration-composer" not in recoveries:
                recoveries.append("hidden-hydration-composer")
            time.sleep(0.25)
            continue
        last_snapshot = _tool_text(
            client.tool("browser_snapshot", {}, request_id=request_id)
        )
        request_id += 1
        try:
            return _textbox_ref(last_snapshot, require_active=True), request_id
        except RuntimeError:
            if recoveries is not None and "active-ref-refresh" not in recoveries:
                recoveries.append("active-ref-refresh")
            time.sleep(0.25)
    raise RuntimeError(
        "active ChatGPT composer did not hydrate before timeout; "
        f"last_focus_state={last_focus_state!r}; last_snapshot={last_snapshot[-800:]!r}"
    )


def _evaluation_json(tool_text: str) -> dict[str, Any]:
    marker = "### Result"
    if marker not in tool_text:
        raise RuntimeError("browser_evaluate result marker missing")
    tail = tool_text.split(marker, 1)[1].strip()
    if "\n### " in tail:
        tail = tail.split("\n### ", 1)[0].strip()
    try:
        value: Any = json.loads(tail)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"browser_evaluate result was not JSON: {tail[:400]}") from exc
    for _ in range(2):
        if not isinstance(value, str):
            break
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"browser_evaluate string result was not JSON: {value[:400]}"
            ) from exc
    if not isinstance(value, dict):
        raise TypeError("browser_evaluate did not return an object")
    return value


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _prepare_prompt_draft(
    client: PlaywrightMcpClient,
    prompt: str,
    *,
    timeout_seconds: float,
    first_request_id: int,
    recoveries: list[str],
    max_attempts: int = 3,
) -> int:
    request_id = first_request_id
    for attempt in range(max_attempts):
        request_id = _ensure_pinned_chatgpt_tab(
            client,
            first_request_id=request_id,
            recoveries=recoveries,
        )
        target, request_id = _wait_for_active_composer(
            client,
            timeout_seconds=timeout_seconds,
            first_request_id=request_id,
            recoveries=recoveries,
        )
        try:
            client.tool(
                "browser_type",
                {"target": target, "text": prompt, "submit": False, "slowly": False},
                request_id=request_id,
            )
            return request_id + 1
        except RuntimeError:
            if attempt + 1 >= max_attempts:
                raise
            if "stale-composer-ref" not in recoveries:
                recoveries.append("stale-composer-ref")
            request_id += 1
    raise RuntimeError("prompt draft preparation exhausted")


def _chat_state(
    client: PlaywrightMcpClient,
    *,
    request_id: int,
) -> tuple[dict[str, Any], int]:
    body = client.tool(
        "browser_evaluate",
        {
            "function": (
                "() => {"
                "const composer=document.querySelector("
                "'[contenteditable=\\\"true\\\"][data-lexical-editor=\\\"true\\\"]'"
                ") || document.querySelector('textarea[name=\\\"prompt-textarea\\\"]')"
                " || document.querySelector('[contenteditable=\\\"true\\\"][role=\\\"textbox\\\"]');"
                "const composerText=composer ? "
                "(typeof composer.value==='string' ? composer.value : (composer.innerText || composer.textContent || '')) : '';"
                "return JSON.stringify({"
                "url: location.href,"
                "users: Array.from(document.querySelectorAll('[data-message-author-role=\\\"user\\\"]')).map(x => x.innerText),"
                "assistantCount: document.querySelectorAll('[data-message-author-role=\\\"assistant\\\"]').length,"
                "composerText"
                "});"
                "}"
            )
        },
        request_id=request_id,
    )
    outer = _evaluation_json(_tool_text(body))
    value: Any = outer
    if set(outer) == {"value"} and isinstance(outer["value"], str):
        value = json.loads(outer["value"])
    if not isinstance(value, dict):
        raise TypeError("ChatGPT state probe did not return an object")
    return value, request_id + 1


def _wait_for_submission_verification(
    client: PlaywrightMcpClient,
    *,
    expected_head: str,
    timeout_seconds: float,
    first_request_id: int,
) -> tuple[str, int]:
    deadline = time.monotonic() + timeout_seconds
    request_id = first_request_id
    last_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            last_state, request_id = _chat_state(client, request_id=request_id)
        except (requests.RequestException, RuntimeError, ValueError, TypeError) as exc:
            raise AmbiguousSubmissionError(
                "post-submit browser state could not be recovered; refusing duplicate submit"
            ) from exc
        users = last_state.get("users", [])
        url = str(last_state.get("url", ""))
        assistant_count = int(last_state.get("assistantCount", 0))
        composer_empty = not str(last_state.get("composerText", "")).strip()
        sent = any(expected_head in str(message) for message in users)
        if sent and assistant_count >= 1 and "/c/" in url and composer_empty:
            return url, request_id
        time.sleep(0.75)
    raise AmbiguousSubmissionError(
        "submission side effect could not be verified; refusing duplicate submit; "
        f"last_state={last_state!r}"
    )


def _submit_once_and_verify(
    client: PlaywrightMcpClient,
    *,
    expected_head: str,
    timeout_seconds: float,
    first_request_id: int,
    recoveries: list[str],
    before_submit: Callable[[], None] | None = None,
    on_verified: Callable[[str], None] | None = None,
    on_ambiguous: Callable[[str], None] | None = None,
) -> tuple[str, int]:
    request_id = _ensure_pinned_chatgpt_tab(
        client,
        first_request_id=first_request_id,
        recoveries=recoveries,
    )
    if before_submit is not None:
        before_submit()
    submit_error: Exception | None = None
    try:
        client.tool(
            "browser_press_key",
            {"key": "Enter"},
            request_id=request_id,
        )
    except (requests.RequestException, RuntimeError, ValueError, TypeError) as exc:
        submit_error = exc
        if "submit-response-ambiguous" not in recoveries:
            recoveries.append("submit-response-ambiguous")
    request_id += 1
    try:
        url, request_id = _wait_for_submission_verification(
            client,
            expected_head=expected_head,
            timeout_seconds=timeout_seconds,
            first_request_id=request_id,
        )
    except AmbiguousSubmissionError as exc:
        if on_ambiguous is not None:
            on_ambiguous(str(exc))
        if submit_error is not None:
            raise AmbiguousSubmissionError(str(exc)) from submit_error
        raise
    if on_verified is not None:
        on_verified(url)
    return url, request_id


def _result_from_record(
    prompt_sha: str,
    record: dict[str, Any],
    *,
    recoveries: list[str],
) -> PlaywrightHandoffResult:
    conversation_url = str(record.get("conversation_url") or "")
    if record.get("state") == "SUBMITTED_VERIFIED" and not conversation_url:
        raise RuntimeError("verified Playwright handoff ledger is missing conversation_url")
    return PlaywrightHandoffResult(
        conversation_url=conversation_url,
        prompt_sha256=prompt_sha,
        sent_user_message_verified=record.get("state") == "SUBMITTED_VERIFIED",
        assistant_run_verified=record.get("state") == "SUBMITTED_VERIFIED",
        handoff_first_pass=not recoveries,
        recoveries=tuple(recoveries),
        owner_id=str(record.get("owner_id") or ""),
        tab_lease_token=str(record.get("tab_lease_token") or ""),
        idempotency_state=str(record.get("state") or ""),
        submit_attempted_at=record.get("submit_attempted_at"),
        verified_at=record.get("verified_at"),
        reused_existing_tab=bool(record.get("reused_existing_tab")),
    )


def _recover_pending_submission(
    endpoint: str,
    *,
    prompt_sha: str,
    record: dict[str, Any],
    expected_head: str,
    timeout_seconds: float,
    owner_id: str,
    ledger: PromptSubmissionLedger,
) -> PlaywrightHandoffResult:
    recoveries = ["idempotency-recovery"]
    token = str(record.get("tab_lease_token") or "")
    if not token:
        ledger.transition(
            prompt_sha,
            "AMBIGUOUS_AFTER_SIDE_EFFECT",
            owner_id=owner_id,
            last_error="pending submission has no tab lease token",
        )
        raise AmbiguousSubmissionError(
            "pending submission has no recoverable tab lease; refusing duplicate submit"
        )

    client = PlaywrightMcpClient(endpoint)
    client.tab_lease_token = token
    client.reused_existing_tab = True
    try:
        request_id = _ensure_pinned_chatgpt_tab(
            client,
            first_request_id=2,
            recoveries=recoveries,
        )
        conversation_url, _ = _wait_for_submission_verification(
            client,
            expected_head=expected_head,
            timeout_seconds=timeout_seconds,
            first_request_id=request_id,
        )
    except (AmbiguousSubmissionError, RuntimeError, requests.RequestException) as exc:
        ledger.transition(
            prompt_sha,
            "AMBIGUOUS_AFTER_SIDE_EFFECT",
            owner_id=owner_id,
            last_error=str(exc)[:500],
        )
        raise AmbiguousSubmissionError(
            "existing submission remains ambiguous; refusing duplicate submit"
        ) from exc

    final = ledger.transition(
        prompt_sha,
        "SUBMITTED_VERIFIED",
        owner_id=owner_id,
        conversation_url=conversation_url,
        verified_at=time.time(),
        reused_existing_tab=True,
    )
    return _result_from_record(prompt_sha, final, recoveries=recoveries)


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

    owner_id = f"playwright-handoff:{os.getpid()}:{uuid.uuid4().hex}"
    gui_lease = MachineGuiLease(lease_seconds=max(600.0, timeout_seconds * 4.0))
    ledger = PromptSubmissionLedger()
    gui_lease.acquire(owner_id, action="chatgpt-handoff")
    try:
        existing = ledger.read(actual_sha)
        if existing and existing.get("state") == "SUBMITTED_VERIFIED":
            return _result_from_record(
                actual_sha,
                {**existing, "owner_id": owner_id},
                recoveries=["duplicate-suppressed"],
            )
        if existing and existing.get("state") in {
            "SUBMIT_ATTEMPTED",
            "AMBIGUOUS_AFTER_SIDE_EFFECT",
        }:
            return _recover_pending_submission(
                endpoint,
                prompt_sha=actual_sha,
                record=existing,
                expected_head=expected_head,
                timeout_seconds=timeout_seconds,
                owner_id=owner_id,
                ledger=ledger,
            )

        prepared = ledger.transition(
            actual_sha,
            "PREPARED",
            owner_id=owner_id,
            stage=expected_stage,
            source_head=expected_head,
            prompt_path=str(prompt_path),
        )
        recoveries: list[str] = []
        client = PlaywrightMcpClient(endpoint)
        request_id = 2
        tab_lease_token = str(prepared.get("tab_lease_token") or "")
        if tab_lease_token:
            client.tab_lease_token = tab_lease_token
            try:
                request_id = _ensure_pinned_chatgpt_tab(
                    client,
                    first_request_id=request_id,
                    recoveries=recoveries,
                )
                client.reused_existing_tab = True
                recoveries.append("prepared-tab-recovered")
            except RuntimeError:
                client.tab_lease_token = None
                tab_lease_token = ""

        if not tab_lease_token:
            try:
                request_id = _open_and_select_chatgpt_tab(
                    client,
                    first_request_id=request_id,
                    recoveries=recoveries,
                )
                tab_lease_token = uuid.uuid4().hex
                request_id = _pin_current_chatgpt_tab(
                    client,
                    tab_lease_token,
                    request_id=request_id,
                )
            except Exception as exc:
                ledger.transition(
                    actual_sha,
                    "FAILED_BEFORE_SIDE_EFFECT",
                    owner_id=owner_id,
                    last_error=str(exc)[:500],
                )
                raise

        ledger.transition(
            actual_sha,
            "PREPARED",
            owner_id=owner_id,
            tab_lease_token=tab_lease_token,
            reused_existing_tab=client.reused_existing_tab,
        )
        try:
            request_id = _prepare_prompt_draft(
                client,
                prompt,
                timeout_seconds=min(15.0, timeout_seconds),
                first_request_id=request_id,
                recoveries=recoveries,
            )
        except Exception as exc:
            ledger.transition(
                actual_sha,
                "FAILED_BEFORE_SIDE_EFFECT",
                owner_id=owner_id,
                last_error=str(exc)[:500],
            )
            raise

        def before_submit() -> None:
            ledger.transition(
                actual_sha,
                "SUBMIT_ATTEMPTED",
                owner_id=owner_id,
                tab_lease_token=tab_lease_token,
                submit_attempted_at=time.time(),
                reused_existing_tab=client.reused_existing_tab,
            )

        def on_verified(conversation_url: str) -> None:
            ledger.transition(
                actual_sha,
                "SUBMITTED_VERIFIED",
                owner_id=owner_id,
                conversation_url=conversation_url,
                verified_at=time.time(),
                reused_existing_tab=client.reused_existing_tab,
            )

        def on_ambiguous(detail: str) -> None:
            ledger.transition(
                actual_sha,
                "AMBIGUOUS_AFTER_SIDE_EFFECT",
                owner_id=owner_id,
                last_error=detail[:500],
                reused_existing_tab=client.reused_existing_tab,
            )

        _submit_once_and_verify(
            client,
            expected_head=expected_head,
            timeout_seconds=timeout_seconds,
            first_request_id=request_id,
            recoveries=recoveries,
            before_submit=before_submit,
            on_verified=on_verified,
            on_ambiguous=on_ambiguous,
        )
        final = ledger.read(actual_sha)
        if final is None:
            raise RuntimeError("Playwright handoff ledger vanished after verification")
        return _result_from_record(actual_sha, final, recoveries=recoveries)
    finally:
        gui_lease.release(owner_id)

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
        "handoff_first_pass": result.handoff_first_pass,
        "recoveries": list(result.recoveries),
        "owner_id": result.owner_id,
        "tab_lease_token": result.tab_lease_token,
        "idempotency_state": result.idempotency_state,
        "submit_attempted_at": result.submit_attempted_at,
        "verified_at": result.verified_at,
        "reused_existing_tab": result.reused_existing_tab,
        "source_head": args.head,
        "stage": args.stage,
        "prompt_path": str(args.prompt),
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(args.receipt, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
