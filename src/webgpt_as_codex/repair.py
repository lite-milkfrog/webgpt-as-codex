from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .health import configured_public_mcp_url, sanitize_for_output
from .paths import ensure_state_dirs, state_root

REPAIR_ACTIONS = {
    "ensure-state-layout",
    "reset-invalid-manager-config",
    "remove-invalid-public-mcp-url",
}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, bool]:
    if not path.exists():
        return {}, True
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, False
    return (value, True) if isinstance(value, dict) else (None, False)


def _health_hints() -> list[dict[str, str]]:
    doctor, valid = _read_json(state_root() / "doctor" / "last-result.json")
    if not valid or not doctor:
        return [{"kind": "doctor", "message": "Run Doctor first; no valid persisted result is available."}]
    hints: list[dict[str, str]] = []
    components = doctor.get("components")
    if not isinstance(components, dict):
        return hints
    for cid, row in components.items():
        if not isinstance(row, dict):
            continue
        health = row.get("health")
        if not isinstance(health, dict):
            continue
        if health.get("listener") is False:
            hints.append(
                {
                    "kind": "runtime",
                    "message": f"{cid}: listener is down; inspect logs before Stage 8 start/restart.",
                }
            )
        if health.get("protocol") is False:
            hints.append(
                {
                    "kind": "protocol",
                    "message": f"{cid}: listener evidence is not protocol proof; inspect MCP configuration/logs.",
                }
            )
        if health.get("safe_call") is False:
            hints.append(
                {
                    "kind": "safe-call",
                    "message": f"{cid}: protocol is reachable but the declared safe call failed.",
                }
            )
        if health.get("oauth") is False:
            hints.append(
                {
                    "kind": "oauth",
                    "message": f"{cid}: inspect OAuth metadata and revalidate final acceptance over real HTTPS.",
                }
            )
        if health.get("remote") is False:
            hints.append(
                {
                    "kind": "remote",
                    "message": f"{cid}: public HTTPS edge is not healthy; inspect Funnel/edge state.",
                }
            )
    return hints


def build_repair_plan() -> dict[str, Any]:
    root = state_root()
    actions: list[dict[str, Any]] = []
    expected_dirs = (
        "logs",
        "pids",
        "downloads",
        "config",
        "secrets",
        "bin",
        "doctor",
        "bootstrap",
        "repair",
        "handoffs",
    )
    missing = [name for name in expected_dirs if not (root / name).is_dir()]
    if missing:
        actions.append(
            {
                "id": "ensure-state-layout",
                "reason": "machine-local state directories are missing",
                "targets": missing,
                "bounded": True,
                "reversible": "created empty directories can be removed",
            }
        )

    manager_path = root / "config" / "manager.json"
    manager, valid = _read_json(manager_path)
    if manager_path.exists() and not valid:
        actions.append(
            {
                "id": "reset-invalid-manager-config",
                "reason": "manager.json is not a valid JSON object",
                "bounded": True,
                "reversible": "original file is backed up before replacement",
            }
        )
    elif manager and "public_mcp_url" in manager and configured_public_mcp_url(manager) is None:
        actions.append(
            {
                "id": "remove-invalid-public-mcp-url",
                "reason": "public_mcp_url violates the credential-free public HTTPS contract",
                "bounded": True,
                "reversible": "original file is backed up before edit",
            }
        )
    return {
        "actions": actions,
        "hints": _health_hints(),
        "arbitrary_command_surface": False,
    }


def _backup(path: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_root / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, backup)
    return backup


def _ensure_state_layout() -> dict[str, Any]:
    root = state_root()
    before = {path.name for path in root.iterdir()} if root.exists() else set()
    ensure_state_dirs()
    after = {path.name for path in root.iterdir()}
    return {"created": sorted(after - before)}


def _reset_invalid_manager_config() -> dict[str, Any]:
    root = ensure_state_dirs()
    path = root / "config" / "manager.json"
    backup = _backup(path, root / "repair" / "backups")
    path.write_text("{}\n", encoding="utf-8")
    return {"backup_created": backup.is_file(), "replacement": "empty-object"}


def _remove_invalid_public_mcp_url() -> dict[str, Any]:
    root = ensure_state_dirs()
    path = root / "config" / "manager.json"
    data, valid = _read_json(path)
    if not valid or data is None:
        raise RuntimeError("manager config is not a JSON object")
    backup = _backup(path, root / "repair" / "backups")
    data.pop("public_mcp_url", None)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"backup_created": backup.is_file(), "removed": "public_mcp_url"}


_APPLIERS: dict[str, Callable[[], dict[str, Any]]] = {
    "ensure-state-layout": _ensure_state_layout,
    "reset-invalid-manager-config": _reset_invalid_manager_config,
    "remove-invalid-public-mcp-url": _remove_invalid_public_mcp_url,
}


def run_repair(
    *,
    dry_run: bool = True,
    confirm: bool = False,
    requested_actions: list[str] | None = None,
) -> dict[str, Any]:
    plan = build_repair_plan()
    planned_ids = [row["id"] for row in plan["actions"]]
    selected = requested_actions if requested_actions is not None else planned_ids
    unknown = sorted(set(selected) - REPAIR_ACTIONS)
    if unknown:
        raise ValueError("unknown repair action: " + ", ".join(unknown))
    if not dry_run and not confirm:
        raise PermissionError("repair apply requires explicit confirmation")
    results: list[dict[str, Any]] = []
    if not dry_run:
        for action_id in selected:
            if action_id not in planned_ids and requested_actions is None:
                continue
            results.append({"id": action_id, "result": _APPLIERS[action_id]()})
    receipt = sanitize_for_output(
        {
            "ok": True,
            "status": "dry-run" if dry_run else "applied",
            "selected_actions": selected,
            "results": results,
            "plan": plan,
            "completed_at": datetime.now(UTC).isoformat(),
        }
    )
    if not dry_run:
        root = ensure_state_dirs()
        (root / "repair" / "last-result.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return receipt


def manager_repair_executor(
    _contract: object,
    _payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = run_repair(dry_run=False, confirm=True)
    return {
        "ok": True,
        "status": result["status"],
        "selected_actions": result["selected_actions"],
        "results": result["results"],
        "hints": result["plan"]["hints"],
    }


def cli_repair(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex repair")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--action", action="append", choices=sorted(REPAIR_ACTIONS))
    args = parser.parse_args(argv)
    if args.apply and not args.confirm:
        parser.error("--apply requires --confirm")
    result = run_repair(
        dry_run=not args.apply,
        confirm=args.confirm,
        requested_actions=args.action,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
