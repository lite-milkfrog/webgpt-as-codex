from __future__ import annotations

import difflib
import hashlib
import os
import re
import stat
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ToolFailure


PATCH_TEMP_PREFIX = ".coding-tools-patch-"
PATCH_BACKUP_PREFIX = ".coding-tools-backup-"
END_OF_FILE_MARKER = "*** End of File"

REVISION_ALGORITHM = "sha256"

# Grades are tried in order and the one that placed a hunk is reported back
# verbatim, so a caller can tell an exact placement from a whitespace-tolerant
# one instead of being told "applied" for both.
MATCH_GRADES = ("exact", "trailing_ws", "indent")
MATCH_GRADE_WARNINGS = {
    "trailing_ws": "context matched only after ignoring trailing whitespace",
    "indent": "context matched only after ignoring indentation width",
}
# Grades that may be used to decide a hunk is *already applied*. The indent
# grade is deliberately absent: stripping indentation makes a line match
# wherever it appears at any depth, which is too weak to turn a miss into a
# success.
ALREADY_APPLIED_GRADES = ("exact", "trailing_ws")

# `@@ -1,4 +1,4 @@` is a unified-diff position header, not a Codex-dialect
# scope anchor. It names line numbers this parser does not use, so it has to
# read as "no scope" rather than as text to search the file for.
_UNIFIED_HEADER = re.compile(r"^-\d+(,\d+)?\s+\+\d+(,\d+)?\s*(@@.*)?$")

# Repair data is model-facing text, so it is bounded twice: by a line count
# around the point of interest and by a byte ceiling on the rendered block.
NEARBY_CONTEXT_LINES = 6
NEARBY_TEXT_MAX_BYTES = 800
MAX_REPORTED_CANDIDATES = 8


def content_revision(text: str) -> str:
    """Return the optimistic-concurrency token for one file's UTF-8 bytes.

    The same derivation backs `apply_patch` success evidence and the
    `revision` that `read_file` publishes and `apply_changes` requires, so a
    hash observed on either tool names the same bytes.
    """

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PatchHunk:
    """One update hunk plus the scope text its `@@` header carried."""

    lines: list[str]
    scope: str | None = None


@dataclass
class PatchOperation:
    kind: str
    path: str
    add_content: str | None = None
    hunks: list[PatchHunk] = field(default_factory=list)
    move_to: str | None = None


@dataclass(frozen=True)
class ParsedHunk:
    old: list[str]
    new: list[str]
    # For every element of `new`, the index into `old` it was copied from, or
    # None when the line is an addition. A downgraded (whitespace-tolerant)
    # match reinstates context lines from the file rather than from the patch,
    # so tolerating a difference never silently rewrites it.
    new_sources: list[int | None] = field(default_factory=list)
    scope: str | None = None
    eof_anchor: bool = False


@dataclass(frozen=True)
class MatchedHunk:
    hunk_index: int
    start: int
    end: int
    new: list[str]
    quality: str = "exact"
    scope_used: bool = False
    old: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateOutcome:
    """Result of applying one file's hunks, with the evidence callers report."""

    content: str
    changed_ranges: list[dict[str, int]]
    match_quality: str
    warnings: list[str]
    already_applied_hunks: list[int]
    applied_hunks: int


@dataclass(frozen=True)
class FileBaseline:
    """Filesystem state captured while a patch is being staged."""

    data: bytes | None
    mode: int | None
    digest: str | None

    @classmethod
    def capture(cls, path: Path) -> FileBaseline:
        if not path.exists():
            return cls(data=None, mode=None, digest=None)
        if path.is_dir():
            raise ToolFailure("PATCH_FAILED", "Cannot patch a directory.", category="validation")
        data = path.read_bytes()
        return cls(data=data, mode=stat.S_IMODE(path.stat().st_mode), digest=hashlib.sha256(data).hexdigest())

    def matches(self, path: Path) -> bool:
        if self.data is None:
            return not path.exists()
        if not path.exists() or path.is_dir():
            return False
        current = path.read_bytes()
        return self.digest == hashlib.sha256(current).hexdigest() and self.mode == stat.S_IMODE(path.stat().st_mode)

    def text(self, path: str) -> str:
        if self.data is None:
            return ""
        try:
            return self.data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ToolFailure(
                "UNSUPPORTED_ENCODING",
                f"Patch target is not valid UTF-8: {path}",
                category="validation",
            ) from exc


STAGED_ACTIONS = ("write", "delete", "verify")


@dataclass(frozen=True)
class StagedFile:
    display: str
    path: Path
    content: str | None
    baseline: FileBaseline
    mode: int | None
    action: str = ""
    """One of ``write``, ``delete``, or ``verify``.

    ``verify`` asserts the baseline still holds and writes nothing — what a
    copy source or an already-applied target needs. The default is derived
    from ``content`` so the historical ``content=None`` spelling of a delete
    keeps working for existing callers.
    """

    def __post_init__(self) -> None:
        if not self.action:
            object.__setattr__(self, "action", "delete" if self.content is None else "write")
        if self.action not in STAGED_ACTIONS:
            raise ToolFailure(
                "PATCH_FAILED",
                f"Unknown staged action: {self.action}",
                category="validation",
                details={"supported": list(STAGED_ACTIONS)},
            )
        if self.action == "write" and self.content is None:
            raise ToolFailure("PATCH_FAILED", "A write action requires content.", category="validation")


class AtomicPatchCommitter:
    """Commit staged paths with atomic renames and full-set rollback.

    Filesystems do not provide a portable transaction spanning unrelated paths.
    Every replacement here is atomic; originals are retained as same-directory
    backups until the complete set succeeds, then removed.

    ``verify`` entries take part in the baseline rechecks and in nothing else:
    they are how a caller says "this file must not have changed underneath us"
    without asking for a write.
    """

    def commit(self, changes: list[StagedFile]) -> None:
        if not changes:
            return
        self._assert_unique_paths(changes)
        mutations = [change for change in changes if change.action != "verify"]
        created_dirs: list[Path] = []
        prepared: dict[Path, Path] = {}
        backups: dict[Path, Path] = {}
        installed: set[Path] = set()
        preserve_backups = False
        try:
            for change in mutations:
                created_dirs.extend(_ensure_parent(change.path.parent))
                if change.action == "write":
                    prepared[change.path] = _prepare_file(change)

            for change in changes:
                self._assert_baseline(change)

            for change in mutations:
                # Recheck immediately before moving each original. If a later
                # path conflicts, earlier backups are restored as a set.
                self._assert_baseline(change)
                if change.path.exists():
                    backup = _reserve_backup_path(change.path.parent)
                    os.replace(change.path, backup)
                    backups[change.path] = backup
                    _fsync_directory(change.path.parent)

            for change in mutations:
                prepared_path = prepared.get(change.path)
                if prepared_path is not None:
                    # A newly-created target has no backup. Do not silently
                    # overwrite a file created after patch staging.
                    if change.path not in backups:
                        self._assert_baseline(change)
                    os.replace(prepared_path, change.path)
                    installed.add(change.path)
                    _fsync_directory(change.path.parent)

        except Exception as exc:
            rollback_errors = self._rollback(mutations, prepared, backups, installed, created_dirs)
            if rollback_errors:
                preserve_backups = True
                display_by_path = {change.path: change.display for change in changes}
                recovery_backups = {
                    display_by_path.get(path, str(path)): str(backup)
                    for path, backup in backups.items()
                    if backup.exists()
                }
                raise ToolFailure(
                    "PATCH_ROLLBACK_FAILED",
                    "Patch failed and one or more files could not be restored; recovery backups were preserved.",
                    category="internal",
                    details={
                        "rollback_errors": rollback_errors,
                        "recovery_backups": recovery_backups,
                        "cause": str(exc),
                    },
                ) from exc
            raise
        finally:
            for path in prepared.values():
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            if not preserve_backups:
                for path in backups.values():
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        # The new file is already installed (or rollback has
                        # restored the old one). A stale hidden backup is safer
                        # than turning cleanup failure into data loss.
                        continue
                    _fsync_directory(path.parent)

    @staticmethod
    def _assert_unique_paths(changes: list[StagedFile]) -> None:
        paths = [change.path for change in changes]
        if len(paths) != len(set(paths)):
            raise ToolFailure("PATCH_FAILED", "Patch staged the same path more than once.", category="validation")

    @staticmethod
    def _assert_baseline(change: StagedFile) -> None:
        if change.baseline.matches(change.path):
            return
        raise ToolFailure(
            "PATCH_CONFLICT",
            f"File changed while the patch was being prepared: {change.display}",
            category="conflict",
            retryable=True,
            details={
                "path": change.display,
                "retry_hint": "Read the current file and regenerate the patch.",
            },
        )

    @staticmethod
    def _rollback(
        changes: list[StagedFile],
        prepared: dict[Path, Path],
        backups: dict[Path, Path],
        installed: set[Path],
        created_dirs: list[Path],
    ) -> list[str]:
        errors: list[str] = []
        for path in reversed([change.path for change in changes]):
            try:
                if path in installed and path.exists() and not path.is_dir():
                    path.unlink()
                backup = backups.get(path)
                if backup is not None:
                    if not backup.exists():
                        errors.append(f"{path}: recovery backup is missing")
                        continue
                    os.replace(backup, path)
                    _fsync_directory(path.parent)
            except OSError as rollback_error:
                errors.append(f"{path}: {rollback_error}")
        for path in prepared.values():
            try:
                path.unlink(missing_ok=True)
            except OSError as cleanup_error:
                errors.append(f"{path}: {cleanup_error}")
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        return errors


def _ensure_parent(parent: Path) -> list[Path]:
    missing: list[Path] = []
    current = parent
    while not current.exists():
        missing.append(current)
        current = current.parent
    parent.mkdir(parents=True, exist_ok=True)
    return list(reversed(missing))


def _prepare_file(change: StagedFile) -> Path:
    assert change.content is not None
    fd, raw_path = tempfile.mkstemp(prefix=PATCH_TEMP_PREFIX, dir=change.path.parent)
    temp_path = Path(raw_path)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(change.content.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, change.mode if change.mode is not None else 0o644)
        return temp_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _reserve_backup_path(parent: Path) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=PATCH_BACKUP_PREFIX, dir=parent)
    os.close(fd)
    path = Path(raw_path)
    path.unlink()
    return path


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def parse_patch(patch: str) -> list[PatchOperation]:
    # split("\n") rather than splitlines(): a context line carrying a form feed
    # or U+2028 must stay one patch line so it can match the file line it came
    # from. The envelope closes on the last non-empty line because the patch
    # text's own trailing newline(s) become trailing empty elements here.
    lines = normalize_to_lf(patch).split("\n")
    while lines and not lines[-1]:
        lines.pop()
    if not lines or lines[0].strip() != "*** Begin Patch" or lines[-1].strip() != "*** End Patch":
        raise ToolFailure("PATCH_FAILED", "Patch must use *** Begin Patch / *** End Patch envelope.", category="validation")
    operations: list[PatchOperation] = []
    i = 1
    while i < len(lines) - 1:
        line = lines[i]
        if not line:
            i += 1
            continue
        if line.startswith("*** Add File: "):
            path = line.removeprefix("*** Add File: ").strip()
            i += 1
            content_lines: list[str] = []
            while i < len(lines) - 1 and not lines[i].startswith("*** "):
                if not lines[i].startswith("+"):
                    raise ToolFailure("PATCH_FAILED", "Add file lines must start with '+'.", category="validation")
                content_lines.append(lines[i][1:])
                i += 1
            operations.append(PatchOperation("add", path, add_content="\n".join(content_lines) + "\n"))
            continue
        if line.startswith("*** Delete File: "):
            path = line.removeprefix("*** Delete File: ").strip()
            operations.append(PatchOperation("delete", path))
            i += 1
            continue
        if line.startswith("*** Update File: "):
            path = line.removeprefix("*** Update File: ").strip()
            i += 1
            move_to: str | None = None
            if i < len(lines) - 1 and lines[i].startswith("*** Move to: "):
                move_to = lines[i].removeprefix("*** Move to: ").strip()
                i += 1
            hunks: list[PatchHunk] = []
            current: list[str] = []
            current_scope: str | None = None
            # `*** End of File` is the one `*** ` line that belongs to a hunk
            # rather than terminating the file block: it anchors the hunk at
            # EOF. Every other `*** ` line starts the next operation.
            while i < len(lines) - 1 and (
                not lines[i].startswith("*** ") or lines[i].rstrip() == END_OF_FILE_MARKER
            ):
                if lines[i].startswith("@@"):
                    if current:
                        hunks.append(PatchHunk(current, current_scope))
                    current = []
                    current_scope = _header_scope(lines[i])
                elif lines[i].rstrip() == END_OF_FILE_MARKER:
                    current.append(END_OF_FILE_MARKER)
                else:
                    current.append(lines[i])
                i += 1
            if current:
                hunks.append(PatchHunk(current, current_scope))
            operations.append(PatchOperation("update", path, hunks=hunks, move_to=move_to))
            continue
        raise ToolFailure("PATCH_FAILED", f"Unrecognized patch line: {line}", category="validation")
    return operations


def _header_scope(line: str) -> str | None:
    """Return the searchable scope text a `@@` header carries, if any."""

    text = line[2:].strip()
    if text.endswith("@@"):
        # `@@ def farewell @@` — a symmetric header; the middle is the scope.
        text = text[:-2].strip()
    if not text or _UNIFIED_HEADER.match(text):
        return None
    return text


HunkInput = Sequence["PatchHunk | list[str]"]


def apply_update_hunks(content: str, hunks: HunkInput, path: str = "<patch>") -> str:
    """Apply hunks and return the new file text.

    Retained as the narrow entry point; :func:`apply_update_hunks_detailed`
    returns the same content plus the evidence callers report to the model.
    """

    return apply_update_hunks_detailed(content, hunks, path).content


def apply_update_hunks_detailed(content: str, hunks: HunkInput, path: str = "<patch>") -> UpdateOutcome:
    if not hunks:
        return UpdateOutcome(content, [], "exact", [], [], 0)
    bom, text = strip_bom(content)
    line_ending = detect_line_ending(text)
    normalized = normalize_to_lf(text)
    # split("\n") is a bijection with the text: "a\nb\n" becomes
    # ["a", "b", ""], where the final empty element *is* the trailing newline.
    # splitlines() would additionally break on \x0b \x0c \x1c \x1d \x1e \x85
    # \u2028 \u2029 and silently rewrite those to \n on rejoin, and it would
    # need a trailing-newline correction that no hunk could ever override.
    lines = normalized.split("\n")
    parsed = [parse_update_hunk(hunk) for hunk in hunks]
    matched: list[MatchedHunk] = []
    already_applied: list[int] = []
    warnings: list[str] = []
    for index, hunk in enumerate(parsed):
        placement = _locate_hunk(lines, hunk, index, path)
        if placement is None:
            already_applied.append(index)
            continue
        matched.append(placement)
        warning = MATCH_GRADE_WARNINGS.get(placement.quality)
        if warning:
            warnings.append(f"hunk {index}: {warning}")
        if placement.scope_used:
            warnings.append(f"hunk {index}: located using the @@ scope anchor")

    matched.sort(key=lambda item: item.start)
    for previous, current in zip(matched, matched[1:]):
        if previous.end > current.start:
            raise ToolFailure(
                "PATCH_HUNKS_OVERLAP",
                f"Patch hunks {previous.hunk_index} and {current.hunk_index} overlap in {path}.",
                category="validation",
                details={
                    "path": path,
                    "hunk_indexes": [previous.hunk_index, current.hunk_index],
                    "retry_hint": "Merge the overlapping hunks into one hunk.",
                },
            )

    # Splicing back to front keeps every later placement's indices valid.
    # Two placements can share a start (a hunk that only adds lines is an
    # empty span), and the one spliced last is the one whose text ends up
    # first, so the final-file order is this order reversed.
    application_order = sorted(matched, key=lambda item: item.start, reverse=True)
    updated_lines = list(lines)
    for matched_hunk in application_order:
        updated_lines = updated_lines[: matched_hunk.start] + matched_hunk.new + updated_lines[matched_hunk.end :]
    updated = "\n".join(updated_lines)
    quality = "exact"
    for item in matched:
        if MATCH_GRADES.index(item.quality) > MATCH_GRADES.index(quality):
            quality = item.quality
    if already_applied:
        warnings.append(
            "hunks already present in the file were skipped: " + ", ".join(str(index) for index in already_applied)
        )
    return UpdateOutcome(
        content=bom + restore_line_endings(updated, line_ending),
        changed_ranges=changed_ranges(list(reversed(application_order))),
        match_quality=quality,
        warnings=warnings,
        already_applied_hunks=already_applied,
        applied_hunks=len(matched),
    )


def changed_ranges(matched: Sequence[MatchedHunk]) -> list[dict[str, int]]:
    """Map each placement onto 1-based line numbers in the *new* file.

    ``matched`` must already be ordered the way its replacement text appears
    in the new file, because each range is offset by the net line count of the
    ones before it. Sorting by ``start`` alone is not that order: placements
    that share a start are ordered by which one was spliced last, which only
    the caller doing the splicing knows.

    Context lines a hunk carried only to locate itself are trimmed off both
    ends, so the reported range names the lines that actually differ rather
    than the whole replaced window. ``end_line`` is inclusive; a hunk that
    only removes lines reports ``end_line == start_line - 1``, an empty range
    naming the position the removed lines used to occupy.
    """

    ranges: list[dict[str, int]] = []
    delta = 0
    for item in matched:
        removed = item.end - item.start
        added = len(item.new)
        prefix, suffix = _unchanged_margins(item.old, item.new)
        start = item.start + prefix + delta
        ranges.append(
            {
                "start_line": start + 1,
                "end_line": start + added - prefix - suffix,
                "added_lines": added - prefix - suffix,
                "removed_lines": removed - prefix - suffix,
            }
        )
        delta += added - removed
    return ranges


def changed_ranges_between(before: str, after: str) -> list[dict[str, int]]:
    """Describe final-file ranges changed between two complete texts.

    Sequential patch blocks locate hunks against intermediate revisions.
    Comparing the original baseline with the final staged text keeps every
    reported line in the final file's coordinate system.
    """

    def content_lines(value: str) -> list[str]:
        _bom, text = strip_bom(value)
        if not text:
            return []
        lines = normalize_to_lf(text).split("\n")
        if lines[-1] == "":
            lines.pop()
        return lines

    before_lines = content_lines(before)
    after_lines = content_lines(after)
    ranges: list[dict[str, int]] = []
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        ranges.append(
            {
                "start_line": new_start + 1,
                "end_line": new_end,
                "added_lines": new_end - new_start,
                "removed_lines": old_end - old_start,
            }
        )
    return ranges


def _unchanged_margins(old: list[str], new: list[str]) -> tuple[int, int]:
    limit = min(len(old), len(new))
    prefix = 0
    while prefix < limit and old[prefix] == new[prefix]:
        prefix += 1
    suffix = 0
    while suffix < limit - prefix and old[len(old) - 1 - suffix] == new[len(new) - 1 - suffix]:
        suffix += 1
    return prefix, suffix


def _locate_hunk(lines: list[str], hunk: ParsedHunk, index: int, path: str) -> MatchedHunk | None:
    """Place one hunk, or return None when its result is already in the file.

    Grades are tried strictly in order, and an ambiguity at the grade that
    first produced candidates is reported instead of being resolved by a
    fuzzier pass: a looser comparison can only match in more places.
    """

    if not hunk.old:
        start = _eof_insert_index(lines) if hunk.eof_anchor else 0
        return MatchedHunk(index, start, start, list(hunk.new), "exact", False, [])
    for grade in MATCH_GRADES:
        candidates = find_subsequence_all(lines, hunk.old, grade=grade)
        if not candidates:
            continue
        scoped, scope_used = _filter_by_scope(lines, candidates, hunk.scope)
        selected = _filter_by_eof(lines, scoped, hunk) if hunk.eof_anchor else scoped
        if len(selected) == 1:
            start = selected[0]
            new_lines = _rebuild_new_lines(lines, start, hunk, grade)
            if new_lines is None:
                continue
            return MatchedHunk(
                index,
                start,
                start + len(hunk.old),
                new_lines,
                grade,
                scope_used,
                lines[start : start + len(hunk.old)],
            )
        if len(selected) > 1:
            raise _ambiguous_failure(lines, selected, hunk, index, path, grade)
    if _already_applied(lines, hunk):
        return None
    raise _not_found_failure(lines, hunk, index, path)


def _eof_insert_index(lines: list[str]) -> int:
    # "a\nb\n" is ["a", "b", ""]; appending before the final empty element
    # keeps the file's trailing newline where it was.
    return len(lines) - 1 if lines and lines[-1] == "" else len(lines)


def _filter_by_scope(
    lines: list[str],
    candidates: list[int],
    scope: str | None,
    *,
    strict: bool = False,
) -> tuple[list[int], bool]:
    """Narrow candidates to the region a `@@ <scope>` header names.

    A candidate belongs to the scope whose anchor line most closely precedes
    it. Candidates governed by different anchors stay ambiguous — the scope
    text itself failed to single one out, and guessing is what the caller
    asked this header to avoid.
    """

    if scope is None:
        return candidates, False
    for anchors in (_scope_anchors(lines, scope, exact=True), _scope_anchors(lines, scope, exact=False)):
        if not anchors:
            continue
        governed: dict[int, list[int]] = {}
        for candidate in candidates:
            containing = [
                anchor
                for anchor in anchors
                if anchor <= candidate < _scope_region_end(lines, anchor)
            ]
            if not containing:
                continue
            governed.setdefault(max(containing), []).append(candidate)
        if len(governed) == 1:
            selected = next(iter(governed.values()))
            return selected, len(selected) < len(candidates)
        if governed:
            selected = sorted(value for group in governed.values() for value in group)
            return selected, len(selected) < len(candidates)
        if strict:
            return [], True
    return ([], False) if strict else (candidates, False)


def _scope_region_end(lines: list[str], anchor: int) -> int:
    """Return the first nonblank line dedented out of an anchored scope."""

    anchor_line = lines[anchor]
    indentation = len(anchor_line) - len(anchor_line.lstrip())
    for index in range(anchor + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) <= indentation:
            return index
    return len(lines)


def _scope_anchors(lines: list[str], scope: str, *, exact: bool) -> list[int]:
    if exact:
        return [index for index, line in enumerate(lines) if line.strip() == scope or scope in line]
    needle = _collapse_whitespace(scope)
    return [index for index, line in enumerate(lines) if needle and needle in _collapse_whitespace(line)]


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _filter_by_eof(lines: list[str], candidates: list[int], hunk: ParsedHunk) -> list[int]:
    """Prefer the placement that reaches the end of the file.

    `*** End of File` is the dialect's way of saying "this is the tail"; used
    as a locator it disambiguates a repeated block whose last occurrence is
    the intended one.
    """

    limit = _eof_insert_index(lines)
    at_eof = [candidate for candidate in candidates if candidate + len(hunk.old) >= limit]
    return at_eof or candidates


def _rebuild_new_lines(lines: list[str], start: int, hunk: ParsedHunk, grade: str) -> list[str] | None:
    """Produce the replacement lines for a placement at ``start``.

    Context lines are taken from the file, not the patch, so a tolerated
    whitespace difference is preserved rather than quietly normalized. Added
    lines are re-indented by the block's uniform indent delta when the match
    was graded ``indent``; if the delta is not uniform the grade does not
    apply and the caller moves on.
    """

    shift: tuple[str, int] = ("", 0)
    if grade == "indent":
        delta = _indent_delta(lines[start : start + len(hunk.old)], hunk.old)
        if delta is None:
            return None
        shift = delta
    rebuilt: list[str] = []
    for value, source in zip(hunk.new, hunk.new_sources):
        if source is not None:
            rebuilt.append(lines[start + source])
        else:
            rebuilt.append(_shift_indent(value, shift))
    return rebuilt


def _indent_delta(file_lines: list[str], hunk_lines: list[str]) -> tuple[str, int] | None:
    """Return (prefix to add, leading characters to drop) for a uniform shift."""

    delta: tuple[str, int] | None = None
    for actual, expected in zip(file_lines, hunk_lines):
        if not actual.strip() and not expected.strip():
            continue
        if actual.strip() != expected.strip():
            return None
        actual_indent = actual[: len(actual) - len(actual.lstrip())]
        expected_indent = expected[: len(expected) - len(expected.lstrip())]
        if actual_indent.startswith(expected_indent):
            candidate = (actual_indent[len(expected_indent) :], 0)
        elif expected_indent.startswith(actual_indent):
            candidate = ("", len(expected_indent) - len(actual_indent))
        else:
            return None
        if delta is None:
            delta = candidate
        elif delta != candidate:
            return None
    return delta or ("", 0)


def _shift_indent(value: str, shift: tuple[str, int]) -> str:
    prefix, drop = shift
    if not value.strip():
        return value
    if drop:
        indent = value[: len(value) - len(value.lstrip())]
        value = indent[drop:] + value.lstrip() if len(indent) >= drop else value.lstrip()
    return prefix + value


def _already_applied(lines: list[str], hunk: ParsedHunk) -> bool:
    """Report whether this hunk's result is already present in the file.

    "Already applied" turns a miss into a success, so the evidence for it is
    held to a higher standard than the evidence for a placement:

    - Only the ``exact`` and ``trailing_ws`` grades count. An indent-stripped
      comparison finds ``return None`` under any indentation anywhere in the
      file, which is not evidence that this hunk ran.
    - The result has to be locatable. A hunk that carries a context line has
      it inside ``new``, so finding that whole block finds the place the hunk
      belonged. A hunk with no context at all has no location to check, so it
      needs a multi-line ``new`` block to be evidence of anything; a single
      line such as ``pass`` or ``x = 2`` occurring somewhere in the file is a
      coincidence, not a completed edit.
    - The result must be unique inside the same ``@@`` scope and EOF locator
      constraints as the edit. A matching block elsewhere is not evidence.
    - A pure-context hunk has identical old and new text, so "already applied"
      would be indistinguishable from "never applied" and is not claimed.
    """

    if hunk.old == hunk.new or not hunk.new:
        return False
    # A blank line is present in every newline-terminated file because
    # split("\n") retains the trailing empty element. It cannot prove that a
    # deletion whose result contains only blank context ever happened.
    if not any(line.strip() for line in hunk.new):
        return False
    anchored = any(source is not None for source in hunk.new_sources)
    if not anchored and len(hunk.new) < 2:
        return False
    for grade in ALREADY_APPLIED_GRADES:
        candidates = find_subsequence_all(lines, hunk.new, grade=grade)
        if not candidates:
            continue
        selected, _scope_used = _filter_by_scope(lines, candidates, hunk.scope, strict=True)
        if hunk.eof_anchor:
            eof = _eof_insert_index(lines)
            selected = [
                candidate for candidate in selected if candidate + len(hunk.new) >= eof
            ]
        if len(selected) == 1:
            return True
        if selected:
            # A looser grade can only add candidates, never make this result
            # unique.
            return False
    return False


def _ambiguous_failure(
    lines: list[str], candidates: list[int], hunk: ParsedHunk, index: int, path: str, grade: str
) -> ToolFailure:
    reported = candidates[:MAX_REPORTED_CANDIDATES]
    hint = "Include additional unchanged context lines to make this hunk unique."
    if hunk.scope is None:
        hint += " A `@@ <enclosing scope>` header also narrows the search."
    return ToolFailure(
        "PATCH_CONTEXT_AMBIGUOUS",
        f"Patch context matched {len(candidates)} locations in {path}; add more context.",
        category="validation",
        retryable=True,
        details={
            "path": path,
            "hunk_index": index,
            "match_count": len(candidates),
            "match_quality": grade,
            "scope": hunk.scope,
            "candidate_lines": [candidate + 1 for candidate in reported],
            "candidates": [
                {
                    "line": candidate + 1,
                    "text": _numbered_excerpt(lines, candidate, len(hunk.old)),
                }
                for candidate in reported
            ],
            "retry_hint": hint,
        },
    )


def _not_found_failure(lines: list[str], hunk: ParsedHunk, index: int, path: str) -> ToolFailure:
    near = _best_near_miss(lines, hunk.old)
    details: dict[str, object] = {
        "path": path,
        "hunk_index": index,
        "match_count": 0,
        "match_quality": None,
        "scope": hunk.scope,
        "total_lines": len(lines),
        "retry_hint": "Read the current file and regenerate this hunk with current context.",
    }
    if near is not None:
        position, score = near
        details["nearest_line"] = position + 1
        details["nearest_matching_lines"] = score
    else:
        # Nothing in the file resembled the context. The head of the file is
        # still the most useful thing to hand back: it tells the model whether
        # it is even looking at the file it thinks it is.
        position = 0
    details["nearby_text"] = _numbered_excerpt(lines, position, len(hunk.old))
    return ToolFailure(
        "PATCH_CONTEXT_NOT_FOUND",
        f"Patch context did not match in {path}.",
        category="validation",
        retryable=True,
        details=details,
    )


def _best_near_miss(lines: list[str], needle: list[str]) -> tuple[int, int] | None:
    """Locate where the context came closest to matching.

    Scored on stripped-line equality so an indentation or trailing-whitespace
    drift still points at the right region instead of at the top of the file.
    """

    if not needle or not lines:
        return None
    wanted = [line.strip() for line in needle]
    best_position = -1
    best_score = 0
    for position in range(max(1, len(lines) - len(needle) + 1)):
        window = lines[position : position + len(needle)]
        score = sum(1 for actual, expected in zip(window, wanted) if actual.strip() == expected)
        if score > best_score:
            best_position, best_score = position, score
    if best_position < 0 or best_score == 0:
        return None
    return best_position, best_score


def _numbered_excerpt(lines: list[str], position: int, span: int) -> str:
    start = max(0, position - NEARBY_CONTEXT_LINES)
    end = min(len(lines), position + max(1, span) + NEARBY_CONTEXT_LINES)
    rendered: list[str] = []
    budget = NEARBY_TEXT_MAX_BYTES
    for number in range(start, end):
        entry = f"{number + 1}: {lines[number]}"
        cost = len(entry.encode("utf-8")) + 1
        if cost > budget:
            rendered.append("…")
            break
        budget -= cost
        rendered.append(entry)
    return "\n".join(rendered)


def parse_update_hunk(hunk: PatchHunk | list[str]) -> ParsedHunk:
    raw_lines = hunk.lines if isinstance(hunk, PatchHunk) else list(hunk)
    scope = hunk.scope if isinstance(hunk, PatchHunk) else None
    old: list[str] = []
    new: list[str] = []
    new_sources: list[int | None] = []
    eof_anchor = False
    for raw in raw_lines:
        if raw == END_OF_FILE_MARKER:
            eof_anchor = True
            continue
        if not raw:
            # V4A spells an empty context line as a single space, which model
            # output and intermediate layers routinely strip to "".
            new_sources.append(len(old))
            old.append("")
            new.append("")
            continue
        marker = raw[0]
        value = raw[1:] if marker in {" ", "-", "+"} else raw
        if marker == " ":
            new_sources.append(len(old))
            old.append(value)
            new.append(value)
        elif marker == "-":
            old.append(value)
        elif marker == "+":
            new_sources.append(None)
            new.append(value)
        else:
            raise ToolFailure("PATCH_FAILED", "Update lines must start with space, '-' or '+'.", category="validation")
    return ParsedHunk(old=old, new=new, new_sources=new_sources, scope=scope, eof_anchor=eof_anchor)


def _grade_key(grade: str) -> Callable[[str], str]:
    if grade == "trailing_ws":
        return str.rstrip
    if grade == "indent":
        return str.strip
    return lambda line: line


def find_subsequence_all(lines: list[str], needle: list[str], *, grade: str = "exact") -> list[int]:
    if not needle:
        return [0]
    key = _grade_key(grade)
    keyed_lines = [key(line) for line in lines] if grade != "exact" else lines
    keyed_needle = [key(line) for line in needle] if grade != "exact" else needle
    limit = len(keyed_lines) - len(keyed_needle) + 1
    first = keyed_needle[0]
    return [
        index
        for index in range(max(0, limit))
        if keyed_lines[index] == first and keyed_lines[index : index + len(keyed_needle)] == keyed_needle
    ]


def strip_bom(text: str) -> tuple[str, str]:
    return ("\ufeff", text[1:]) if text.startswith("\ufeff") else ("", text)


def detect_line_ending(text: str) -> str:
    crlf = text.find("\r\n")
    lf = text.find("\n")
    if lf < 0 or crlf < 0:
        return "\n"
    return "\r\n" if crlf <= lf else "\n"


def normalize_to_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def restore_line_endings(text: str, ending: str) -> str:
    return text.replace("\n", "\r\n") if ending == "\r\n" else text


def read_text_preserve_newlines(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()
