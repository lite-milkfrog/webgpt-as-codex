"""Declarative, line-addressed file changes for the ``apply_changes`` tool.

``apply_patch`` locates its edits by matching context, which fails whenever the
model's memory of a file has drifted. ``apply_changes`` addresses lines by
number instead and pairs every change with the `revision` of the bytes those
numbers were read from, so a stale request is refused rather than misapplied.

This module owns the parsing and the pure text transformation. Path
resolution, revision checking, staging, and committing stay in the runtime,
which is where workspace policy lives.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .errors import ToolFailure
from .patching import (
    MatchedHunk,
    UpdateOutcome,
    changed_ranges,
    detect_line_ending,
    normalize_to_lf,
    restore_line_endings,
    strip_bom,
)

# `write` is an upsert and `create` insists the file is new: the difference is
# the whole point of keeping both, so a caller who means "this file does not
# exist yet" can say it and be told when they are wrong.
CHANGE_ACTIONS = ("create", "write", "edit", "delete", "move", "copy")
# Actions whose result depends on bytes the caller claims to have read.
REVISION_ACTIONS = frozenset({"write", "edit", "delete", "move", "copy"})
EDIT_OPERATIONS = ("replace", "delete", "insert_after", "insert_before")
CONTENT_OPERATIONS = frozenset({"replace", "insert_after", "insert_before"})
MAX_CHANGES_PER_CALL = 100
MAX_EDITS_PER_CHANGE = 200


@dataclass(frozen=True)
class LineEdit:
    """One line-addressed operation, normalized to a half-open span.

    ``start`` and ``end`` are 0-based indices into the file's line list, so an
    insertion is the empty span at its insertion point and every operation
    reduces to "replace lines[start:end] with these lines".
    """

    op: str
    start: int
    end: int
    lines: list[str]
    index: int
    requested: dict[str, int]
    """The line numbers exactly as the caller wrote them, for error text."""


@dataclass(frozen=True)
class ChangeRequest:
    """One validated entry of the ``changes`` array."""

    index: int
    action: str
    path: str
    revision: str | None
    content: str | None
    destination: str | None
    edits: tuple[LineEdit, ...]
    raw_edits: tuple[dict[str, Any], ...]


def parse_changes(raw: Any) -> list[ChangeRequest]:
    """Validate the request array before a single path is touched.

    Everything that can be judged from the request alone is judged here, so a
    malformed change never reaches the filesystem and a partially valid array
    never half-applies.
    """

    if not isinstance(raw, list):
        raise ToolFailure("INVALID_ARGUMENT", "changes must be an array.", category="validation")
    if not raw:
        # The same verdict apply_patch returns for an empty envelope: asking
        # for nothing is a mistake in the caller, not a successful no-op.
        raise ToolFailure("PATCH_FAILED", "No files were modified.", category="validation")
    if len(raw) > MAX_CHANGES_PER_CALL:
        raise ToolFailure(
            "INVALID_ARGUMENT",
            f"changes holds more than {MAX_CHANGES_PER_CALL} entries.",
            category="validation",
            details={"max_changes": MAX_CHANGES_PER_CALL, "received": len(raw)},
        )
    return [_parse_change(entry, index) for index, entry in enumerate(raw)]


def _parse_change(entry: Any, index: int) -> ChangeRequest:
    where = f"changes[{index}]"
    if not isinstance(entry, dict):
        raise ToolFailure("INVALID_ARGUMENT", f"{where} must be an object.", category="validation")
    action = entry.get("action")
    if action not in CHANGE_ACTIONS:
        raise ToolFailure(
            "INVALID_ARGUMENT",
            f"{where}.action must be one of {', '.join(CHANGE_ACTIONS)}.",
            category="validation",
            details={"supported_actions": list(CHANGE_ACTIONS)},
        )
    path = entry.get("path")
    if not isinstance(path, str) or not path:
        raise ToolFailure("INVALID_ARGUMENT", f"{where}.path is required.", category="validation")
    revision = entry.get("revision")
    if revision is not None and not isinstance(revision, str):
        raise ToolFailure("INVALID_ARGUMENT", f"{where}.revision must be a string.", category="validation")
    if action == "create" and revision is not None:
        raise ToolFailure(
            "INVALID_ARGUMENT",
            f"{where}.revision is not accepted for create; a file that does not exist yet has no revision.",
            category="validation",
        )
    content = entry.get("content")
    if content is not None and not isinstance(content, str):
        raise ToolFailure("INVALID_ARGUMENT", f"{where}.content must be a string.", category="validation")
    destination = entry.get("destination")
    if destination is not None and not isinstance(destination, str):
        raise ToolFailure("INVALID_ARGUMENT", f"{where}.destination must be a string.", category="validation")
    raw_edits = entry.get("edits")

    if action in {"create", "write"}:
        if content is None:
            raise ToolFailure("INVALID_ARGUMENT", f"{where}.content is required for {action}.", category="validation")
        _reject_field(where, "edits", raw_edits, action)
        _reject_field(where, "destination", destination, action)
    elif action == "edit":
        _reject_field(where, "content", content, action, hint="use edits[].content")
        _reject_field(where, "destination", destination, action)
    elif action == "delete":
        _reject_field(where, "content", content, action)
        _reject_field(where, "edits", raw_edits, action)
        _reject_field(where, "destination", destination, action)
    else:
        if not isinstance(destination, str) or not destination:
            raise ToolFailure(
                "INVALID_ARGUMENT", f"{where}.destination is required for {action}.", category="validation"
            )
        _reject_field(where, "content", content, action)
        _reject_field(where, "edits", raw_edits, action)

    edits: tuple[LineEdit, ...] = ()
    normalized_raw: tuple[dict[str, Any], ...] = ()
    if action == "edit":
        if not isinstance(raw_edits, list) or not raw_edits:
            raise ToolFailure("INVALID_ARGUMENT", f"{where}.edits must be a non-empty array.", category="validation")
        if len(raw_edits) > MAX_EDITS_PER_CHANGE:
            raise ToolFailure(
                "INVALID_ARGUMENT",
                f"{where}.edits holds more than {MAX_EDITS_PER_CHANGE} entries.",
                category="validation",
                details={"max_edits": MAX_EDITS_PER_CHANGE, "received": len(raw_edits)},
            )
        normalized_raw = tuple(item for item in raw_edits if isinstance(item, dict))
        if len(normalized_raw) != len(raw_edits):
            raise ToolFailure("INVALID_ARGUMENT", f"{where}.edits entries must be objects.", category="validation")
        edits = tuple(_parse_edit(item, where, position) for position, item in enumerate(normalized_raw))
    return ChangeRequest(
        index=index,
        action=action,
        path=path,
        revision=revision,
        content=content,
        destination=destination,
        edits=edits,
        raw_edits=normalized_raw,
    )


def _reject_field(where: str, field: str, value: Any, action: str, *, hint: str = "") -> None:
    if value is None:
        return
    suffix = f" ({hint})" if hint else ""
    raise ToolFailure(
        "INVALID_ARGUMENT",
        f"{where}.{field} is not accepted for {action}{suffix}.",
        category="validation",
    )


def _parse_edit(entry: dict[str, Any], where: str, position: int) -> LineEdit:
    location = f"{where}.edits[{position}]"
    op = entry.get("op")
    if op not in EDIT_OPERATIONS:
        raise ToolFailure(
            "INVALID_ARGUMENT",
            f"{location}.op must be one of {', '.join(EDIT_OPERATIONS)}.",
            category="validation",
            details={"supported_operations": list(EDIT_OPERATIONS)},
        )
    content = entry.get("content")
    if op in CONTENT_OPERATIONS:
        if not isinstance(content, str):
            raise ToolFailure(
                "INVALID_ARGUMENT", f"{location}.content is required for {op}.", category="validation"
            )
    elif content is not None:
        raise ToolFailure("INVALID_ARGUMENT", f"{location}.content is not accepted for delete.", category="validation")
    lines = content_lines(content) if isinstance(content, str) else []

    if op in {"replace", "delete"}:
        start_line = _require_int(entry, "start_line", location)
        end_line = entry.get("end_line")
        end_value = start_line if end_line is None else _require_int(entry, "end_line", location)
        if start_line < 1:
            raise ToolFailure("INVALID_ARGUMENT", f"{location}.start_line must be >= 1.", category="validation")
        if end_value < start_line:
            raise ToolFailure(
                "INVALID_ARGUMENT",
                f"{location}.end_line must be >= start_line.",
                category="validation",
            )
        _reject_field(location, "line", entry.get("line"), op)
        return LineEdit(
            op=op,
            start=start_line - 1,
            end=end_value,
            lines=lines,
            index=position,
            requested={"start_line": start_line, "end_line": end_value},
        )

    line = _require_int(entry, "line", location)
    _reject_field(location, "start_line", entry.get("start_line"), op)
    _reject_field(location, "end_line", entry.get("end_line"), op)
    if op == "insert_after":
        if line < 0:
            raise ToolFailure(
                "INVALID_ARGUMENT",
                f"{location}.line must be >= 0 for insert_after; 0 inserts at the beginning.",
                category="validation",
            )
        return LineEdit(op=op, start=line, end=line, lines=lines, index=position, requested={"line": line})
    if line < 1:
        raise ToolFailure(
            "INVALID_ARGUMENT",
            f"{location}.line must be >= 1 for insert_before; total_lines + 1 appends.",
            category="validation",
        )
    return LineEdit(
        op=op, start=line - 1, end=line - 1, lines=lines, index=position, requested={"line": line}
    )


def _require_int(entry: dict[str, Any], field: str, location: str) -> int:
    value = entry.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ToolFailure(
            "INVALID_ARGUMENT", f"{location}.{field} must be an integer.", category="validation"
        )
    return value


def reject_duplicate_paths(targets: Sequence[tuple[int, str]]) -> None:
    """One path, one change.

    apply_changes is declarative: two entries naming one path describe two
    states for it, and the line numbers in the second were read before the
    first existed. apply_patch is the tool that chains edits to one file.

    Each entry pairs the index of the change with the *resolved* display path
    it names, because that is the key the staging map uses. Comparing the raw
    request strings instead would let ``a.txt`` and ``./a.txt`` through as two
    changes and let the second silently overwrite the first.
    """

    seen: dict[str, int] = {}
    for index, path in targets:
        if path in seen:
            raise ToolFailure(
                "INVALID_ARGUMENT",
                f"changes[{index}] names {path}, which changes[{seen[path]}] already names. "
                "Combine them into one change, or use apply_patch to chain edits to one file.",
                category="validation",
                details={"path": path, "change_indexes": [seen[path], index]},
            )
        seen[path] = index


def content_lines(content: str) -> list[str]:
    """Split replacement text into whole lines.

    ``""`` is zero lines, which is what makes ``replace`` with empty content a
    deletion. Python would otherwise report ``"".split("\\n") == [""]`` — one
    empty line — and every emptied range would keep a stray blank line. A
    trailing newline does add a blank line: ``"a\\n"`` is ``["a", ""]``.
    """

    return content.split("\n") if content else []


def split_lines(text: str) -> tuple[list[str], bool]:
    """Return the file's lines and whether it ends with a newline.

    Line *n* here is line *n* as ``read_file`` counts it, so the numbers a
    model reads back are the numbers it can edit with.
    """

    if not text:
        return [], False
    parts = text.split("\n")
    if parts[-1] == "":
        return parts[:-1], True
    return parts, False


def join_lines(lines: list[str], trailing_newline: bool) -> str:
    if not lines:
        return ""
    return "\n".join(lines) + ("\n" if trailing_newline else "")


def apply_line_edits(content: str, edits: tuple[LineEdit, ...], path: str) -> UpdateOutcome:
    """Apply line-addressed edits, all resolved against the original numbering.

    Every edit names lines in the file as it was read, never as an earlier
    edit in the same call left it. That is what makes the array declarative:
    the caller does not have to track how its own edits shift the line numbers
    of the ones that follow.
    """

    bom, text = strip_bom(content)
    line_ending = detect_line_ending(text)
    lines, trailing_newline = split_lines(normalize_to_lf(text))
    total_lines = len(lines)
    placements = [_placement(edit, lines, total_lines, path) for edit in edits]
    _reject_overlaps(placements, path)

    # Splicing back to front keeps every later placement's indices valid. An
    # insertion is an empty span, so it can share a start with the replacement
    # it sits in front of; the one spliced last is the one whose text ends up
    # first, and reversing this order is therefore the order the new lines
    # appear in the result.
    application_order = sorted(placements, key=lambda item: (item.start, item.end), reverse=True)
    updated = list(lines)
    for placement in application_order:
        updated = updated[: placement.start] + placement.new + updated[placement.end :]
    # A file that gained content but never ended with a newline keeps that
    # shape; POSIX-style text stays POSIX-style.
    ends_with_newline = trailing_newline if lines else bool(updated)
    rebuilt = bom + restore_line_endings(join_lines(updated, ends_with_newline), line_ending)
    changed = [item for item in reversed(application_order) if item.old != item.new]
    return UpdateOutcome(
        content=rebuilt,
        changed_ranges=changed_ranges(changed),
        match_quality="exact",
        warnings=[],
        already_applied_hunks=[item.hunk_index for item in placements if item.old == item.new],
        applied_hunks=len(changed),
    )


def _placement(edit: LineEdit, lines: list[str], total_lines: int, path: str) -> MatchedHunk:
    # Every operation reduces to a span in [0, total_lines]: an edit may end at
    # the last line, and an insertion may sit just past it, but nothing may
    # address a line that is not there.
    if edit.end > total_lines or edit.start > total_lines:
        raise ToolFailure(
            "INVALID_ARGUMENT",
            f"{path} has {total_lines} lines; edit {edit.index} ({edit.op}) addresses past the end. "
            "Re-read the file and use the line numbers it reports.",
            category="validation",
            retryable=True,
            details={
                "path": path,
                "total_lines": total_lines,
                "edit_index": edit.index,
                "operation": edit.op,
                "requested": dict(edit.requested),
            },
        )
    return MatchedHunk(
        hunk_index=edit.index,
        start=edit.start,
        end=edit.end,
        new=list(edit.lines),
        quality="exact",
        scope_used=False,
        old=lines[edit.start : edit.end],
    )


def _reject_overlaps(placements: list[MatchedHunk], path: str) -> None:
    ordered = sorted(placements, key=lambda item: (item.start, item.end))
    for previous, current in zip(ordered, ordered[1:]):
        empty_pair = previous.start == previous.end and current.start == current.end
        collides = current.start < previous.end or (empty_pair and current.start == previous.start)
        if not collides:
            continue
        raise ToolFailure(
            "PATCH_HUNKS_OVERLAP",
            f"Edits {previous.hunk_index} and {current.hunk_index} address the same lines of {path}.",
            category="validation",
            details={
                "path": path,
                "edit_indexes": [previous.hunk_index, current.hunk_index],
                "retry_hint": "Merge the overlapping edits into one edit.",
            },
        )
