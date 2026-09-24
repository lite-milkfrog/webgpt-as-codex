import json
import threading
from pathlib import Path

import pytest

from webgpt_as_codex import playwright_handoff
from webgpt_as_codex.concurrency import LeaseBusy
from webgpt_as_codex.playwright_handoff import (
    PromptSubmissionLedger,
    _ensure_pinned_chatgpt_tab,
    _evaluation_json,
    _open_and_select_chatgpt_tab,
    _pin_current_chatgpt_tab,
    _target_blank_chatgpt_tab_index,
    _target_new_chatgpt_tab_index,
    _textbox_ref,
    _wait_for_active_composer,
    prompt_sha256,
)


def test_extracts_chatgpt_textbox_ref() -> None:
    snapshot = '- textbox "Chat with ChatGPT" [ref=e131]:'
    assert _textbox_ref(snapshot) == "e131"


def test_prefers_active_composer_over_hydration_fallback() -> None:
    snapshot = (
        '- textbox "Chat with ChatGPT" [ref=e133]:\n'
        '- textbox "与 ChatGPT 聊天" [active] [ref=e716]:'
    )
    assert _textbox_ref(snapshot, require_active=True) == "e716"


def test_active_composer_is_required_when_requested() -> None:
    snapshot = '- textbox "Chat with ChatGPT" [ref=e133]:'
    try:
        _textbox_ref(snapshot, require_active=True)
    except RuntimeError as exc:
        assert "active ChatGPT composer" in str(exc)
    else:
        raise AssertionError("hidden hydration fallback must not satisfy active composer gate")


def test_wait_focuses_visible_dom_composer_before_accepting_active_ref() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def tool(self, name: str, _arguments: dict, *, request_id: int) -> dict:
            self.calls.append(name)
            if name == "browser_evaluate":
                text = '### Result\n{"value":"{\\\"focused\\\":true,\\\"tag\\\":\\\"DIV\\\"}"}'
            else:
                text = '### Snapshot\n- textbox "Chat with ChatGPT" [active] [ref=e716]:'
            return {"result": {"content": [{"type": "text", "text": text}]}}

    client = FakeClient()
    ref, next_id = _wait_for_active_composer(
        client, timeout_seconds=1.0, first_request_id=5
    )
    assert ref == "e716"
    assert next_id == 7
    assert client.calls == ["browser_evaluate", "browser_snapshot"]


def test_targets_current_blank_chatgpt_tab_when_new_action_marks_it_current() -> None:
    tabs = (
        "- 0: [Welcome](chrome-extension://example)\n"
        "- 2: (current) [ChatGPT](https://chatgpt.com/)\n"
        "- 3: [ChatGPT](https://chatgpt.com/)"
    )
    assert _target_blank_chatgpt_tab_index(tabs) == 2


def test_targets_latest_blank_chatgpt_tab_when_extension_remains_current() -> None:
    tabs = (
        "- 0: (current) [Welcome](chrome-extension://example)\n"
        "- 1: [Existing](https://chatgpt.com/c/abc)\n"
        "- 2: [ChatGPT](https://chatgpt.com/)\n"
        "- 3: [ChatGPT](https://chatgpt.com/)"
    )
    assert _target_blank_chatgpt_tab_index(tabs) == 3


def test_new_tab_selection_ignores_duplicate_browser_tabs_sections() -> None:
    before = (
        "### Result\n"
        "- 0: (current) [Welcome](chrome-extension://example)\n"
        "### Open tabs\n"
        "- 0: (current) [Welcome](chrome-extension://example)"
    )
    after = (
        "### Result\n"
        "- 0: (current) [Welcome](chrome-extension://example)\n"
        "- 2: [ChatGPT](https://chatgpt.com/)\n"
        "### Open tabs\n"
        "- 0: (current) [Welcome](chrome-extension://example)\n"
        "- 2: [ChatGPT](https://chatgpt.com/)"
    )
    assert _target_new_chatgpt_tab_index(before, after) == 2


def test_evaluation_json_parses_result() -> None:
    text = '### Result\n{"url":"https://chatgpt.com/c/abc","users":[],"assistantCount":1}'
    assert _evaluation_json(text)["assistantCount"] == 1


def test_evaluation_json_unwraps_json_string_result() -> None:
    text = '### Result\n"{\\\"focused\\\":true,\\\"tag\\\":\\\"DIV\\\"}"'
    result = _evaluation_json(text)
    assert result == {"focused": True, "tag": "DIV"}


def test_prompt_sha_is_stable() -> None:
    assert prompt_sha256("abc") == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_pins_current_chatgpt_tab_with_session_scoped_lease() -> None:
    class FakeClient:
        tab_lease_token: str | None = None

        def tool(self, name: str, _arguments: dict, *, request_id: int) -> dict:
            assert name == "browser_evaluate"
            assert request_id == 5
            payload = json.dumps(
                {
                    "url": "https://chatgpt.com/",
                    "lease": "lease-123",
                    "pinned": True,
                }
            )
            text = "### Result\n" + json.dumps({"value": payload})
            return {"result": {"content": [{"type": "text", "text": text}]}}

    client = FakeClient()
    next_id = _pin_current_chatgpt_tab(
        client,
        "lease-123",
        request_id=5,
    )
    assert next_id == 6
    assert client.tab_lease_token == "lease-123"


def test_restores_pinned_chatgpt_tab_when_another_tab_becomes_current() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.tab_lease_token = "lease-123"
            self.current = 0

        def tool(self, name: str, arguments: dict, *, request_id: int) -> dict:
            if name == "browser_tabs" and arguments["action"] == "list":
                text = (
                    "### Result\n"
                    "- 0: (current) [Welcome](chrome-extension://example)\n"
                    "- 1: [ChatGPT](https://chatgpt.com/c/old)\n"
                    "- 2: [ChatGPT](https://chatgpt.com/c/pinned)"
                )
            elif name == "browser_tabs" and arguments["action"] == "select":
                self.current = arguments["index"]
                text = "### Result\nOK"
            elif name == "browser_evaluate":
                url = {
                    0: "chrome-extension://example",
                    1: "https://chatgpt.com/c/old",
                    2: "https://chatgpt.com/c/pinned",
                }[self.current]
                lease = "lease-123" if self.current == 2 else None
                payload = json.dumps({"url": url, "lease": lease})
                text = "### Result\n" + json.dumps({"value": payload})
            else:
                raise AssertionError((name, arguments, request_id))
            return {"result": {"content": [{"type": "text", "text": text}]}}

    client = FakeClient()
    recoveries: list[str] = []
    next_id = _ensure_pinned_chatgpt_tab(
        client,
        first_request_id=10,
        recoveries=recoveries,
    )
    assert next_id == 16
    assert client.current == 2
    assert recoveries == ["tab-lease-restored"]


def test_open_prefers_unique_existing_blank_tab_over_creating_new() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []
            self.reused_existing_tab = False

        def tool(self, name: str, arguments: dict, *, request_id: int) -> dict:
            self.calls.append((name, arguments))
            if name == "browser_tabs" and arguments["action"] == "list":
                text = (
                    "### Result\n"
                    "- 0: (current) [Existing](https://chatgpt.com/c/abc)\n"
                    "- 1: [ChatGPT](https://chatgpt.com/)"
                )
            else:
                text = "### Result\nOK"
            return {"result": {"content": [{"type": "text", "text": text}]}}

    client = FakeClient()
    next_id = _open_and_select_chatgpt_tab(client, first_request_id=2)
    assert next_id == 4
    assert client.reused_existing_tab is True
    assert ("browser_tabs", {"action": "new", "url": "https://chatgpt.com/"}) not in client.calls
    assert client.calls[-1] == ("browser_tabs", {"action": "select", "index": 1})


def test_prompt_submission_ledger_persists_side_effect_states(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    sha = prompt_sha256("same prompt")
    ledger = PromptSubmissionLedger()
    prepared = ledger.transition(
        sha,
        "PREPARED",
        owner_id="owner-a",
        stage="stage-a",
        source_head="head-a",
        tab_lease_token="lease-a",
    )
    assert prepared["state"] == "PREPARED"
    attempted = ledger.transition(
        sha,
        "SUBMIT_ATTEMPTED",
        owner_id="owner-a",
        submit_attempted_at=123.0,
    )
    assert attempted["state"] == "SUBMIT_ATTEMPTED"
    assert PromptSubmissionLedger().read(sha)["submit_attempted_at"] == 123.0


def test_prompt_submission_ledger_rejects_state_regression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    sha = prompt_sha256("already submitted")
    ledger = PromptSubmissionLedger()
    ledger.transition(sha, "PREPARED", owner_id="owner-a")
    ledger.transition(sha, "SUBMIT_ATTEMPTED", owner_id="owner-a")
    ledger.transition(
        sha,
        "SUBMITTED_VERIFIED",
        owner_id="owner-a",
        conversation_url="https://chatgpt.com/c/abc",
    )
    with pytest.raises(RuntimeError, match="illegal idempotency transition"):
        ledger.transition(sha, "PREPARED", owner_id="owner-b")


def test_submit_barrier_runs_before_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class FakeClient:
        tab_lease_token = None

        def tool(self, name: str, _arguments: dict, *, request_id: int) -> dict:
            assert name == "browser_press_key"
            assert events == ["barrier"]
            events.append("enter")
            return {"result": {"content": []}}

    monkeypatch.setattr(
        playwright_handoff,
        "_wait_for_submission_verification",
        lambda *_args, **_kwargs: ("https://chatgpt.com/c/abc", 11),
    )
    playwright_handoff._submit_once_and_verify(
        FakeClient(),
        expected_head="head",
        timeout_seconds=1,
        first_request_id=9,
        recoveries=[],
        before_submit=lambda: events.append("barrier"),
    )
    assert events == ["barrier", "enter"]


def test_verified_duplicate_returns_without_browser_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("same prompt", encoding="utf-8")
    sha = prompt_sha256("same prompt")
    ledger = PromptSubmissionLedger()
    ledger.transition(sha, "PREPARED", owner_id="owner-a")
    ledger.transition(sha, "SUBMIT_ATTEMPTED", owner_id="owner-a", tab_lease_token="lease-a")
    ledger.transition(
        sha,
        "SUBMITTED_VERIFIED",
        owner_id="owner-a",
        conversation_url="https://chatgpt.com/c/already",
        verified_at=123.0,
    )
    monkeypatch.setattr(playwright_handoff, "validate_handoff_prompt", lambda *_args, **_kwargs: [])

    class BrowserMustNotStart:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("duplicate verified prompt must not touch the browser")

    monkeypatch.setattr(playwright_handoff, "PlaywrightMcpClient", BrowserMustNotStart)
    result = playwright_handoff.handoff_via_playwright(
        "http://127.0.0.1:8931/mcp",
        prompt_path,
        expected_sha256=sha,
        expected_stage="stage-a",
        expected_head="head-a",
    )
    assert result.conversation_url.endswith("/c/already")
    assert result.idempotency_state == "SUBMITTED_VERIFIED"
    assert result.recoveries == ("duplicate-suppressed",)


def test_pending_recovery_never_presses_enter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    sha = prompt_sha256("pending prompt")
    ledger = PromptSubmissionLedger()
    ledger.transition(sha, "PREPARED", owner_id="owner-a", tab_lease_token="lease-a")
    pending = ledger.transition(
        sha,
        "SUBMIT_ATTEMPTED",
        owner_id="owner-a",
        tab_lease_token="lease-a",
        submit_attempted_at=123.0,
    )

    class FakeClient:
        def __init__(self, *_args, **_kwargs) -> None:
            self.tab_lease_token = None
            self.reused_existing_tab = False

        def tool(self, name: str, _arguments: dict, *, request_id: int) -> dict:
            if name == "browser_press_key":
                raise AssertionError("recovery path must never press Enter")
            return {"result": {"content": []}}

    monkeypatch.setattr(playwright_handoff, "PlaywrightMcpClient", FakeClient)
    monkeypatch.setattr(
        playwright_handoff,
        "_ensure_pinned_chatgpt_tab",
        lambda *_args, **_kwargs: 7,
    )
    monkeypatch.setattr(
        playwright_handoff,
        "_wait_for_submission_verification",
        lambda *_args, **_kwargs: ("https://chatgpt.com/c/recovered", 8),
    )
    result = playwright_handoff._recover_pending_submission(
        "http://127.0.0.1:8931/mcp",
        prompt_sha=sha,
        record=pending,
        expected_head="head-a",
        timeout_seconds=1,
        owner_id="owner-b",
        ledger=ledger,
    )
    assert result.conversation_url.endswith("/c/recovered")
    assert PromptSubmissionLedger().read(sha)["state"] == "SUBMITTED_VERIFIED"


def test_handoff_cannot_construct_browser_client_without_machine_gui_lease(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("blocked prompt", encoding="utf-8")
    sha = prompt_sha256("blocked prompt")
    monkeypatch.setattr(playwright_handoff, "validate_handoff_prompt", lambda *_args, **_kwargs: [])

    class BusyGuiLease:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def acquire(self, _owner_id: str, *, action: str) -> dict:
            assert action == "chatgpt-handoff"
            raise LeaseBusy("held by another handoff")

        def release(self, _owner_id: str) -> dict:
            raise AssertionError("unacquired lease must not be released")

    class BrowserMustNotStart:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("browser mutation path started without GUI ownership")

    monkeypatch.setattr(playwright_handoff, "MachineGuiLease", BusyGuiLease)
    monkeypatch.setattr(playwright_handoff, "PlaywrightMcpClient", BrowserMustNotStart)
    with pytest.raises(LeaseBusy, match="another handoff"):
        playwright_handoff.handoff_via_playwright(
            "http://127.0.0.1:8931/mcp",
            prompt_path,
            expected_sha256=sha,
            expected_stage="stage-a",
            expected_head="head-a",
        )


def test_same_prompt_concurrent_owners_have_one_browser_writer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("same concurrent prompt", encoding="utf-8")
    sha = prompt_sha256("same concurrent prompt")
    monkeypatch.setattr(playwright_handoff, "validate_handoff_prompt", lambda *_args, **_kwargs: [])

    first_inside = threading.Event()
    release_first = threading.Event()
    browser_starts: list[str] = []
    outcomes: list[str] = []

    class FakeClient:
        def __init__(self, *_args, **_kwargs) -> None:
            self.tab_lease_token = None
            self.reused_existing_tab = True
            browser_starts.append(threading.current_thread().name)
            first_inside.set()
            release_first.wait(timeout=2)

    monkeypatch.setattr(playwright_handoff, "PlaywrightMcpClient", FakeClient)
    monkeypatch.setattr(playwright_handoff, "_open_and_select_chatgpt_tab", lambda *_a, **_k: 2)
    monkeypatch.setattr(playwright_handoff, "_pin_current_chatgpt_tab", lambda *_a, **_k: 3)
    monkeypatch.setattr(playwright_handoff, "_prepare_prompt_draft", lambda *_a, **_k: 4)
    def fake_submit(_client, **kwargs):
        kwargs["before_submit"]()
        kwargs["on_verified"]("https://chatgpt.com/c/one")
        return "https://chatgpt.com/c/one", 5

    monkeypatch.setattr(playwright_handoff, "_submit_once_and_verify", fake_submit)

    def worker() -> None:
        try:
            playwright_handoff.handoff_via_playwright(
                "http://127.0.0.1:8931/mcp",
                prompt_path,
                expected_sha256=sha,
                expected_stage="stage-a",
                expected_head="head-a",
            )
        except LeaseBusy:
            outcomes.append("busy")
        else:
            outcomes.append("ok")

    first = threading.Thread(target=worker, name="owner-a")
    second = threading.Thread(target=worker, name="owner-b")
    first.start()
    assert first_inside.wait(timeout=1)
    second.start()
    second.join(timeout=2)
    release_first.set()
    first.join(timeout=2)

    assert sorted(outcomes) == ["busy", "ok"]
    assert len(browser_starts) == 1
    assert PromptSubmissionLedger().read(sha)["state"] == "SUBMITTED_VERIFIED"
