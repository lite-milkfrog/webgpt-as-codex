from webgpt_as_codex.playwright_handoff import (
    _evaluation_json,
    _target_blank_chatgpt_tab_index,
    _textbox_ref,
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


def test_evaluation_json_parses_result() -> None:
    text = '### Result\n{"url":"https://chatgpt.com/c/abc","users":[],"assistantCount":1}'
    assert _evaluation_json(text)["assistantCount"] == 1


def test_prompt_sha_is_stable() -> None:
    assert prompt_sha256("abc") == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )
