"""Task manifests for the real-task evaluation.

A task is a repository at a known commit, a prompt, and two commands: one that
must pass when the work is done, and one that must keep passing. Keeping the
tasks as data means the 30-task run the release gate asks for is a manifest
edit rather than a code change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_S = 900
MANIFEST_DIR = Path(__file__).resolve().parent / "manifests"


class TaskError(ValueError):
    """A manifest that cannot be run as written."""


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    verify: str
    repo: str = ""
    """Git URL or local path to clone. Empty means the workspace comes from `fixture`/`setup`."""
    commit: str = ""
    fixture: str = ""
    """Directory, relative to the manifest, copied into the fresh workspace."""
    category: str = "general"
    setup: str = ""
    """Command run once in the fresh workspace, before the agent sees it."""
    regression_verify: str = ""
    """Command that already passes and must keep passing."""
    timeout_s: int = DEFAULT_TIMEOUT_S
    max_rounds: int = 3
    tags: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, raw: Any, *, source: str, base: Path | None = None) -> Task:
        if not isinstance(raw, dict):
            raise TaskError(f"{source}: every task must be an object")
        missing = [key for key in ("id", "prompt", "verify") if not raw.get(key)]
        if missing:
            raise TaskError(f"{source}: task is missing {', '.join(missing)}")
        if not any(raw.get(key) for key in ("repo", "fixture", "setup")):
            raise TaskError(f"{source}: task {raw['id']} needs a repo, a fixture, or a setup command")
        known = {item.name for item in cls.__dataclass_fields__.values()}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise TaskError(f"{source}: task {raw['id']} has unknown fields: {', '.join(unknown)}")
        fixture = str(raw.get("fixture", ""))
        if fixture:
            resolved = (base / fixture) if base is not None else Path(fixture)
            if not resolved.is_dir():
                raise TaskError(f"{source}: task {raw['id']} names a fixture that is not a directory: {resolved}")
            fixture = str(resolved)
        return cls(
            id=str(raw["id"]),
            prompt=str(raw["prompt"]),
            verify=str(raw["verify"]),
            repo=str(raw.get("repo", "")),
            commit=str(raw.get("commit", "")),
            fixture=fixture,
            category=str(raw.get("category", "general")),
            setup=str(raw.get("setup", "")),
            regression_verify=str(raw.get("regression_verify", "")),
            timeout_s=int(raw.get("timeout_s", DEFAULT_TIMEOUT_S)),
            max_rounds=int(raw.get("max_rounds", 3)),
            tags=tuple(str(tag) for tag in raw.get("tags", ())),
        )


def load_tasks(path: Path) -> list[Task]:
    """Read and validate one manifest.

    Validation is strict and happens before any task runs: a typo in task 27
    should not surface an hour into a 30-task evaluation.
    """

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskError(f"{path}: cannot be read as JSON: {exc}") from exc
    entries = raw.get("tasks") if isinstance(raw, dict) else raw
    if not isinstance(entries, list) or not entries:
        raise TaskError(f"{path}: manifest holds no tasks")
    tasks = [Task.from_mapping(entry, source=str(path), base=path.parent) for entry in entries]
    duplicates = sorted({task.id for task in tasks if [item.id for item in tasks].count(task.id) > 1})
    if duplicates:
        raise TaskError(f"{path}: duplicate task ids: {', '.join(duplicates)}")
    return tasks
