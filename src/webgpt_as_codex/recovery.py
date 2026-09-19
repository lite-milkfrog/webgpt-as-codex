from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .concurrency import _exclusive_guard
from .paths import ensure_state_dirs
from .stateio import atomic_write_json

Probe = Callable[[], dict[str, Any]]
Mutator = Callable[[], Any]


@dataclass(frozen=True)
class RecoveryRequest:
    attempt_id: str
    component_id: str
    origin_path: str
    visited: tuple[str, ...]
    hops_remaining: int

    @classmethod
    def new(
        cls,
        component_id: str,
        origin_path: str,
        *,
        attempt_id: str | None = None,
        hop_budget: int = 2,
    ) -> RecoveryRequest:
        return cls(
            attempt_id=attempt_id or uuid.uuid4().hex,
            component_id=component_id,
            origin_path=origin_path,
            visited=(origin_path,),
            hops_remaining=hop_budget,
        )

    def enter(self, path: str) -> RecoveryRequest:
        if path in self.visited:
            raise RuntimeError(f"recovery-cycle-blocked:{path}")
        if self.hops_remaining <= 0:
            raise RuntimeError("recovery-hop-budget-exhausted")
        return replace(
            self,
            visited=(*self.visited, path),
            hops_remaining=self.hops_remaining - 1,
        )


def choose_complementary_path(
    failed_path: str,
    *,
    gateway_available: bool,
    rdc_available: bool,
) -> str | None:
    if failed_path in {"gateway", "public-gateway", "gateway-backend"}:
        return "rdc" if rdc_available else None
    if failed_path == "rdc":
        return "gateway" if gateway_available else None
    return None


class RecoveryCoordinator:
    def __init__(self) -> None:
        self.root = ensure_state_dirs() / "recovery" / "attempts"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, request: RecoveryRequest) -> Path:
        key = hashlib.sha256(
            f"{request.attempt_id}:{request.component_id}".encode()
        ).hexdigest()[:32]
        return self.root / f"{key}.json"

    def _guard(self, request: RecoveryRequest) -> Path:
        return self._path(request).with_suffix(".lock")

    def _load(self, request: RecoveryRequest) -> dict[str, Any]:
        path = self._path(request)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            value = {}
        return value if isinstance(value, dict) else {}

    def _write(self, request: RecoveryRequest, state: dict[str, Any]) -> None:
        atomic_write_json(self._path(request), state, sort_keys=True)

    def claim_mutation(
        self,
        request: RecoveryRequest,
        path: str,
        *,
        lifecycle_authority: bool,
    ) -> dict[str, Any]:
        if not lifecycle_authority:
            return {
                "ok": False,
                "status": "diagnose-only-no-lifecycle-authority",
                "mutation_owner": None,
            }
        with _exclusive_guard(self._guard(request)):
            state = self._load(request)
            owner = state.get("mutation_owner")
            if owner is None:
                state.update(
                    {
                        "schema_version": 1,
                        "attempt_id": request.attempt_id,
                        "component_id": request.component_id,
                        "origin_path": request.origin_path,
                        "mutation_owner": path,
                        "claimed_at": time.time(),
                    }
                )
                self._write(request, state)
                return {"ok": True, "status": "claimed", "mutation_owner": path}
            if owner == path:
                return {"ok": True, "status": "already-claimed", "mutation_owner": path}
            return {
                "ok": False,
                "status": "mutation-owned-by-other-path",
                "mutation_owner": owner,
            }

    def execute(
        self,
        request: RecoveryRequest,
        *,
        path: str,
        lifecycle_authority: bool,
        diagnose: Probe,
        mutate: Mutator,
        post_state: Probe,
    ) -> dict[str, Any]:
        try:
            routed = request.enter(path)
        except RuntimeError as exc:
            return {
                "ok": False,
                "status": str(exc),
                "attempt_id": request.attempt_id,
                "component_id": request.component_id,
                "mutated": False,
            }

        before = diagnose()
        if before.get("healthy") is True:
            return {
                "ok": True,
                "status": "already-healthy",
                "attempt_id": request.attempt_id,
                "component_id": request.component_id,
                "path": path,
                "visited": routed.visited,
                "mutated": False,
                "post_state": before,
            }

        claim = self.claim_mutation(
            routed,
            path,
            lifecycle_authority=lifecycle_authority,
        )
        if not claim["ok"]:
            after = post_state()
            return {
                "ok": after.get("healthy") is True,
                "status": (
                    "recovered-by-other-path"
                    if after.get("healthy") is True
                    else claim["status"]
                ),
                "attempt_id": request.attempt_id,
                "component_id": request.component_id,
                "path": path,
                "visited": routed.visited,
                "mutation_owner": claim.get("mutation_owner"),
                "mutated": False,
                "post_state": after,
            }

        mutation_error: str | None = None
        mutation_result: Any = None
        try:
            mutation_result = mutate()
        except (OSError, RuntimeError, ValueError) as exc:
            # Ambiguous side-effect failures are resolved from post-state, never by blind retry.
            mutation_error = type(exc).__name__

        after = post_state()
        healthy = after.get("healthy") is True
        status = (
            "recovered"
            if healthy and mutation_error is None
            else "recovered-after-ambiguous-mutation"
            if healthy
            else "mutation-failed-post-state-unhealthy"
        )
        with _exclusive_guard(self._guard(routed)):
            state = self._load(routed)
            state.update(
                {
                    "completed_at": time.time(),
                    "status": status,
                    "post_state": after,
                    "mutation_error": mutation_error,
                }
            )
            self._write(routed, state)
        return {
            "ok": healthy,
            "status": status,
            "attempt_id": request.attempt_id,
            "component_id": request.component_id,
            "path": path,
            "visited": routed.visited,
            "mutation_owner": path,
            "mutated": True,
            "mutation_result": mutation_result,
            "mutation_error": mutation_error,
            "post_state": after,
        }
