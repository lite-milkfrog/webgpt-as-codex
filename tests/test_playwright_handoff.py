from webgpt_as_codex.playwright_handoff import (
    _evaluation_json,
    _textbox_ref,
    prompt_sha256,
)


def test_extracts_chatgpt_textbox_ref() -> None:
    snapshot = '- textbox "Chat with ChatGPT" [ref=e131]:'
    assert _textbox_ref(snapshot) == "e131"


def test_evaluation_json_parses_result() -> None:
    text = '### Result\n{"url":"https://chatgpt.com/c/abc","users":[],"assistantCount":1}'
    assert _evaluation_json(text)["assistantCount"] == 1


def test_prompt_sha_is_stable() -> None:
    assert prompt_sha256("abc") == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )
