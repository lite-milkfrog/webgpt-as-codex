from pathlib import Path

from webgpt_as_codex.paths import repo_root, state_root


def test_repo_root_has_agents_file() -> None:
    assert (repo_root() / "AGENTS.md").is_file()


def test_state_is_outside_repo_by_default() -> None:
    assert repo_root() not in state_root().parents
    assert state_root() != repo_root()


def test_private_patterns_are_gitignored() -> None:
    text = (repo_root() / ".gitignore").read_text(encoding="utf-8")
    for marker in ("*.pem", "*secret*", "*password*", "*token*"):
        assert marker in text
