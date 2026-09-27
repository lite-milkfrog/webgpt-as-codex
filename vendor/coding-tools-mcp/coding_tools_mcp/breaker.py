"""Refuse the third verbatim retry of a call that already failed the same way.

A deterministic failure repeated with byte-identical arguments cannot start
succeeding: nothing about the request changed, and the error said so
(``retryable: false``). Before v0.5.0 nothing stopped that loop — the protocol
carries no task identity, so a model that decided to retry could retry forever.

The breaker is keyed on ``(tool, normalized arguments)`` and, within that, on
the error code, so two clients doing different work in one runtime cannot trip
each other's breaker, and a call that starts failing a *different* way is a
different failure rather than a continuation of the old one.

Only deterministic failures count. A ``PATCH_CONFLICT`` or a
``COMMAND_LIMIT_REACHED`` is the server saying "the same call may win next
time", and blocking those would turn advice into a dead end.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from collections.abc import Mapping
from typing import Any

# The first and second identical failures are answered normally; the third
# attempt is refused. Two is enough to establish "this is not transient" and
# leaves room for one honest retry.
REPEAT_FAILURE_LIMIT = 2
BREAKER_CAPACITY = 256
# Arguments that name the call rather than the work. A model that varies only
# these has not changed anything the failure depended on.
FINGERPRINT_IGNORED_ARGUMENTS = frozenset({"idempotency_key"})
# This error's prescribed repair is changing an ignored naming argument. It
# must not consume the shared work fingerprint's budget, or two collisions
# under one key would block the same work under the fresh key the error asks
# the caller to use.
BREAKER_EXCLUDED_ERROR_CODES = frozenset({"IDEMPOTENCY_KEY_REUSED"})
# `retryable: true` normally means "a retry can work" — but for these codes the
# retry has to carry different arguments, and the fingerprint proves it did
# not. A byte-identical repeat of one of these is as deterministic as a
# non-retryable failure. Codes outside this set that stay retryable
# (PATCH_CONFLICT, COMMAND_LIMIT_REACHED) depend on time rather than on the
# arguments and are never counted.
RETRY_MEANS_CHANGING_THE_CALL = frozenset(
    {
        "PATCH_CONTEXT_NOT_FOUND",
        "PATCH_CONTEXT_AMBIGUOUS",
        "REVISION_MISMATCH",
        "REVISION_REQUIRED",
    }
)


def argument_fingerprint(arguments: Mapping[str, Any]) -> str:
    """A stable short hash of one call's arguments.

    Serialized with sorted keys so key order never makes two identical calls
    look different, and truncated because the fingerprint only ever has to
    distinguish calls within one runtime.
    """

    normalized = {
        key: value for key, value in sorted(arguments.items()) if key not in FINGERPRINT_IGNORED_ARGUMENTS
    }
    try:
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=repr)
    except (TypeError, ValueError):
        encoded = repr(sorted(normalized.items()))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:32]


class RepeatFailureBreaker:
    """Bounded LRU of ``(tool, fingerprint) -> {error_code: consecutive count}``."""

    def __init__(self, *, limit: int = REPEAT_FAILURE_LIMIT, capacity: int = BREAKER_CAPACITY) -> None:
        self._limit = limit
        self._capacity = capacity
        self._lock = threading.Lock()
        self._entries: OrderedDict[tuple[str, str], dict[str, int]] = OrderedDict()
        self._generation = 0

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def generation(self) -> int:
        """Return the current workspace-verdict generation."""

        with self._lock:
            return self._generation

    def blocked_error_code(self, tool: str, fingerprint: str) -> str | None:
        """Return the error code this exact call has already exhausted, if any."""

        with self._lock:
            counts = self._entries.get((tool, fingerprint))
            if not counts:
                return None
            self._entries.move_to_end((tool, fingerprint))
            for code, count in counts.items():
                if count >= self._limit:
                    return code
        return None

    def record_failure(
        self,
        tool: str,
        fingerprint: str,
        *,
        error_code: str,
        retryable: bool,
        generation: int | None = None,
    ) -> int:
        """Count one failure and return the new consecutive count for its code."""

        if error_code in BREAKER_EXCLUDED_ERROR_CODES:
            return 0
        if retryable and error_code not in RETRY_MEANS_CHANGING_THE_CALL:
            return 0
        with self._lock:
            if generation is not None and generation != self._generation:
                # The call began against a tree whose verdicts have since been
                # invalidated. Let the caller observe its real failure, but do
                # not seed the fresh generation with stale evidence.
                return 0
            counts = self._entries.setdefault((tool, fingerprint), {})
            self._entries.move_to_end((tool, fingerprint))
            count = counts.get(error_code, 0) + 1
            counts[error_code] = count
            while len(self._entries) > self._capacity:
                self._entries.popitem(last=False)
            return count

    def record_success(
        self, tool: str, fingerprint: str, *, generation: int | None = None
    ) -> None:
        """Forget this call's history: the same arguments just worked."""

        with self._lock:
            if generation is not None and generation != self._generation:
                return
            self._entries.pop((tool, fingerprint), None)

    def reset(self) -> None:
        """Forget everything: the workspace changed, so every verdict is stale.

        A deterministic failure is only deterministic against a fixed tree. Once
        a write lands, "this call can never succeed" is no longer something the
        breaker knows.
        """

        with self._lock:
            self._entries.clear()
            self._generation += 1
