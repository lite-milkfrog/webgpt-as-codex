from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .discovery import discover_component
from .paths import ensure_state_dirs, state_root
from .registry import Component, load_components
from .stateio import atomic_write_json

MANAGER_UPDATEABLE = frozenset({"mcpjungle"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")


@dataclass(frozen=True)
class ApprovedUpdate:
    component_id: str
    version: str
    artifact: str
    sha256: str
    source_url: str
    destination: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_relative_path(value: str, *, field: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"{field} must be a bounded relative path")
    return path


def approved_update_for(component: Component) -> ApprovedUpdate | None:
    raw = component.raw.get("approved_update")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError("approved_update must be an object")
    required = {"version", "artifact", "sha256", "source_url"}
    missing = sorted(required - raw.keys())
    if missing:
        raise ValueError("approved_update missing: " + ", ".join(missing))
    version = str(raw["version"])
    artifact = str(raw["artifact"])
    digest = str(raw["sha256"]).lower()
    source_url = str(raw["source_url"])
    destination = component.raw.get("machine_binary")
    upstream = component.raw.get("upstream")
    if not _VERSION_RE.fullmatch(version):
        raise ValueError("approved update version is invalid")
    if Path(artifact).name != artifact or not artifact:
        raise ValueError("approved update artifact must be a file name")
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError("approved update sha256 is invalid")
    if not isinstance(destination, str):
        raise TypeError("approved update target has no machine_binary")
    _validated_relative_path(destination, field="machine_binary")
    if not isinstance(upstream, str):
        raise TypeError("approved update target has no upstream")
    source = urlsplit(source_url)
    origin = urlsplit(upstream)
    if (
        source.scheme != "https"
        or source.username
        or source.password
        or source.query
        or source.fragment
        or source.hostname != origin.hostname
        or not source.path.startswith(origin.path.rstrip("/") + "/releases/")
    ):
        raise ValueError("approved update source is outside the component release origin")
    return ApprovedUpdate(
        component_id=component.id,
        version=version,
        artifact=artifact,
        sha256=digest,
        source_url=source_url,
        destination=destination,
    )


def _candidate_path(update: ApprovedUpdate) -> Path:
    return (
        ensure_state_dirs()
        / "downloads"
        / "approved-updates"
        / update.component_id
        / update.version
        / update.artifact
    )


def _destination_path(update: ApprovedUpdate) -> Path:
    relative = _validated_relative_path(update.destination, field="machine_binary")
    root = state_root().resolve()
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ValueError("approved update destination escapes state root")
    return target


def _copy_verified(candidate: Path, destination: Path, expected_sha256: str) -> Path | None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError("refusing to replace symlink update destination")
    backup: Path | None = None
    if destination.exists():
        backup_root = ensure_state_dirs() / "runtime" / "update-backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / (
            f"{destination.name}.{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.bak"
        )
        shutil.copy2(destination, backup)

    fd, raw_temp = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".update",
        dir=destination.parent,
    )
    os.close(fd)
    temp = Path(raw_temp)
    try:
        shutil.copyfile(candidate, temp)
        if _sha256(temp) != expected_sha256:
            raise RuntimeError("staged update digest changed during copy")
        os.replace(temp, destination)
        if _sha256(destination) != expected_sha256:
            if backup is not None:
                os.replace(backup, destination)
            else:
                destination.unlink(missing_ok=True)
            raise RuntimeError("updated artifact failed post-write verification")
    finally:
        temp.unlink(missing_ok=True)
    return backup


def run_update(component_id: str = "mcpjungle") -> dict[str, Any]:
    if component_id not in MANAGER_UPDATEABLE:
        return {
            "ok": False,
            "status": "invalid-component-scope",
            "allowed_components": sorted(MANAGER_UPDATEABLE),
        }
    component = load_components().get(component_id)
    if component is None:
        return {"ok": False, "status": "component-not-registered"}
    try:
        update = approved_update_for(component)
    except ValueError as exc:
        return {"ok": False, "status": "invalid-approved-update", "reason": str(exc)}
    if update is None:
        return {
            "ok": True,
            "status": "no-approved-update",
            "component_id": component_id,
            "mutation": False,
        }
    discovery = discover_component(component)
    from .runtime import RuntimeSupervisor

    runtime_state = RuntimeSupervisor().status(component_id)
    if discovery.get("listener_up") or runtime_state.get("state") != "stopped":
        return {
            "ok": False,
            "status": "component-running-stop-first",
            "component_id": component_id,
        }
    candidate = _candidate_path(update)
    if not candidate.is_file() or candidate.is_symlink():
        return {
            "ok": False,
            "status": "approved-artifact-not-staged",
            "component_id": component_id,
            "version": update.version,
        }
    if _sha256(candidate) != update.sha256:
        return {
            "ok": False,
            "status": "approved-artifact-digest-mismatch",
            "component_id": component_id,
            "version": update.version,
        }
    destination = _destination_path(update)
    if destination.is_file() and not destination.is_symlink() and _sha256(destination) == update.sha256:
        return {
            "ok": True,
            "status": "already-current",
            "component_id": component_id,
            "version": update.version,
            "mutation": False,
        }
    backup = _copy_verified(candidate, destination, update.sha256)
    receipt = {
        "schema_version": 1,
        "component_id": component_id,
        "version": update.version,
        "sha256": update.sha256,
        "source_origin": urlsplit(update.source_url).hostname,
        "destination": update.destination,
        "backup_created": backup is not None,
        "completed_at": datetime.now(UTC).isoformat(),
    }
    atomic_write_json(
        ensure_state_dirs() / "runtime" / "last-update.json",
        receipt,
        sort_keys=True,
    )
    return {
        "ok": True,
        "status": "updated",
        "component_id": component_id,
        "version": update.version,
        "mutation": True,
        "backup_created": backup is not None,
    }


def manager_update_executor(_contract: object, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"confirm", "component"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        return {"ok": False, "status": "invalid-update-fields", "fields": unknown}
    component = payload.get("component", "mcpjungle")
    if not isinstance(component, str):
        return {"ok": False, "status": "invalid-component-scope"}
    return run_update(component)
