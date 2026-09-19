from __future__ import annotations

import argparse
import json
import time
from typing import Any

from .discovery import discover_all
from .health import sanitize_for_output
from .paths import ensure_state_dirs
from .prerequisites import environment_report, install_tailscale_with_winget
from .provision import provision_runtime_binaries
from .registry import Component, load_components
from .stateio import atomic_write_json


def _item(component: Component, discovered: dict[str, Any]) -> dict[str, Any]:
    installed = discovered.get("installed_by_path")
    listener = discovered.get("listener_up")
    if not component.enabled_by_default:
        state, action, reason = "disabled", "skip", "disabled by manifest"
    elif listener is True:
        state, action, reason = "healthy-listener", "preserve", "healthy listener already exists"
    elif installed is True:
        state, action, reason = (
            "installed-not-listening",
            "defer-start",
            "binary is installed; Stage 8 owns runtime start/restart",
        )
    elif installed is False:
        state, action, reason = (
            "not-found-on-path",
            "manual-install",
            "installation is required before runtime start",
        )
    else:
        state, action, reason = (
            "discovery-unknown",
            "manual-verify",
            "manifest does not expose enough evidence for a safe automatic mutation",
        )
    return {
        "component_id": component.id,
        "display_name": component.display_name,
        "required": component.required,
        "state": state,
        "action": action,
        "reason": reason,
        "install_hint": component.raw.get("install_hint"),
    }


def build_bootstrap_plan(
    components: dict[str, Component] | None = None,
    discovery: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    components = components or load_components()
    discovery = discovery or discover_all(components)
    items = [_item(component, discovery.get(cid, {})) for cid, component in components.items()]
    items.sort(key=lambda row: (not row["required"], row["display_name"].lower()))
    return {
        "mode": "plan",
        "idempotent": True,
        "preserves_healthy_services": True,
        "service_mutation": False,
        "items": items,
    }


def run_bootstrap(
    *,
    apply: bool = False,
    install_missing: bool = False,
    provision_runtime: bool = False,
) -> dict[str, Any]:
    plan = build_bootstrap_plan()
    environment_before = environment_report()
    installations: list[dict[str, Any]] = []
    if install_missing and not environment_before["tailscale"]["installed"]:
        installations.append(install_tailscale_with_winget(confirm=True))
    runtime_provision = (
        provision_runtime_binaries()
        if provision_runtime
        else {"ok": True, "status": "not-requested", "results": []}
    )
    environment_after = environment_report()
    result = {
        **plan,
        "applied": apply,
        "install_missing": install_missing,
        "provision_runtime": provision_runtime,
        "runtime_provision": runtime_provision,
        "environment": environment_after,
        "environment_changed": environment_before != environment_after,
        "installations": installations,
        "generated_at": time.time(),
    }
    if apply:
        root = ensure_state_dirs()
        path = root / "bootstrap" / "last-plan.json"
        atomic_write_json(path, sanitize_for_output(result))
    return sanitize_for_output(result)


def cli_bootstrap(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex bootstrap")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="create/verify machine-local state layout and persist the plan; never starts services",
    )
    parser.add_argument(
        "--install-missing",
        action="store_true",
        help="install allowlisted missing system dependencies; currently Tailscale through winget only",
    )
    parser.add_argument(
        "--provision-runtime",
        action="store_true",
        help="download approved MCPJungle/OAuth binaries when missing; preserve existing binaries",
    )
    parser.add_argument(
        "--require-edge-ready",
        action="store_true",
        help="exit non-zero until the OAuth/Tailscale HTTPS edge prerequisites are ready",
    )
    args = parser.parse_args(argv)
    result = run_bootstrap(
        apply=args.apply,
        install_missing=args.install_missing,
        provision_runtime=args.provision_runtime,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_edge_ready and not result["environment"]["ready_for_edge"]:
        return 2
    return 0
