from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class StateWriteError(RuntimeError):
    pass


def _stage_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return temp


def atomic_write_text(path: Path, text: str) -> None:
    temp = _stage_text(path, text)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_write_json(path: Path, payload: Any, *, sort_keys: bool = False) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=sort_keys) + "\n",
    )


def atomic_write_text_bundle(entries: dict[Path, str]) -> None:
    """Stage all files first, then replace them with in-process rollback on failure."""
    if not entries:
        return
    staged: dict[Path, Path] = {}
    previous: dict[Path, bytes | None] = {}
    committed: list[Path] = []
    try:
        for path, text in entries.items():
            if path in staged:
                raise ValueError(f"duplicate state target: {path}")
            previous[path] = path.read_bytes() if path.exists() else None
            staged[path] = _stage_text(path, text)
        for path, temp in staged.items():
            os.replace(temp, path)
            committed.append(path)
    except BaseException as exc:
        rollback_failures: list[str] = []
        for path in reversed(committed):
            try:
                old = previous[path]
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    restore = _stage_text(path, old.decode("utf-8"))
                    os.replace(restore, path)
            except (OSError, UnicodeError):
                rollback_failures.append(path.name)
        suffix = (
            f"; rollback failed for: {', '.join(rollback_failures)}"
            if rollback_failures
            else ""
        )
        raise StateWriteError(f"state bundle commit failed{suffix}") from exc
    finally:
        for temp in staged.values():
            temp.unlink(missing_ok=True)


def json_text(payload: Any, *, sort_keys: bool = False) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=sort_keys) + "\n"
