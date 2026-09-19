from __future__ import annotations

import threading
from pathlib import Path

import pytest

from webgpt_as_codex import concurrency, recovery
from webgpt_as_codex.concurrency import (
    BindingMismatch,
    CodingWorkspacePolicy,
    LeaseBusy,
    MachineGuiLease,
    SerenaSlotPool,
)
from webgpt_as_codex.recovery import RecoveryCoordinator, RecoveryRequest


def _fake_serena(monkeypatch: pytest.MonkeyPatch) -> dict[int, dict]:
    processes: dict[int, dict] = {}
    next_pid = {"value": 50000}

    def launch(project: Path, port: int, slot_dir: Path) -> dict:
        del slot_dir
        next_pid["value"] += 1
        pid = next_pid["value"]
        row = {
            "pid": pid,
            "birth_token": f"birth-{pid}",
            "image_name": "serena.exe",
            "launch_fingerprint": f"launch-{project.name}-{port}",
            "port": port,
            "alive": True,
        }
        processes[pid] = row
        return row

    monkeypatch.setattr(concurrency, "_launch_serena", launch)
    monkeypatch.setattr(
        concurrency,
        "_process_identity",
        lambda pid: (
            {
                "pid": pid,
                "birth_token": processes[pid]["birth_token"],
                "image_name": processes[pid]["image_name"],
            }
            if pid in processes and processes[pid]["alive"]
            else None
        ),
    )
    monkeypatch.setattr(concurrency, "_wait_listener", lambda port, timeout=20.0: True)
    monkeypatch.setattr(concurrency, "_port_available", lambda port: port != 9121)
    monkeypatch.setattr(
        concurrency,
        "_bounded_stop",
        lambda pid, graceful_seconds=5.0: processes[pid].update(alive=False) or "graceful",
    )
    return processes


def test_serena_two_projects_get_different_fixed_slots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    _fake_serena(monkeypatch)
    first_project = tmp_path / "a"
    second_project = tmp_path / "b"
    first_project.mkdir()
    second_project.mkdir()
    pool = SerenaSlotPool(ports=(9410, 9411))

    first = pool.acquire(first_project, "window-a")
    second = pool.acquire(second_project, "window-b")

    assert first["port"] != second["port"]
    assert first["project_id"] != second["project_id"]
    assert first["endpoint"].endswith("/mcp")
    assert second["endpoint"].endswith("/mcp")


def test_serena_same_project_reuses_only_after_release(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    _fake_serena(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    pool = SerenaSlotPool(ports=(9410, 9411))

    first = pool.acquire(project, "one")
    concurrent = pool.acquire(project, "two")
    assert concurrent["port"] != first["port"]

    pool.release(first["port"], "one")
    reused = pool.acquire(project, "three")
    assert reused["port"] == first["port"]
    assert reused["status"] == "reused"


def test_serena_stale_receipt_is_reclaimed_without_killing_unowned_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    processes = _fake_serena(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    pool = SerenaSlotPool(ports=(9410,))
    slot = pool.acquire(project, "one")
    processes[slot["pid"]]["alive"] = False

    replacement = pool.acquire(project, "two")

    assert replacement["pid"] != slot["pid"]
    assert replacement["port"] == 9410


def test_serena_occupied_port_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    _fake_serena(monkeypatch)
    monkeypatch.setattr(concurrency, "_port_available", lambda _port: False)
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(LeaseBusy):
        SerenaSlotPool(ports=(9410,)).acquire(project, "one")


def test_serena_shared_9121_is_explicitly_excluded() -> None:
    with pytest.raises(ValueError):
        SerenaSlotPool(ports=(9121,))


def test_serena_destroy_checks_post_state_after_shutdown_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    processes = _fake_serena(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    pool = SerenaSlotPool(ports=(9410,))
    slot = pool.acquire(project, "one")

    def ambiguous_stop(pid: int, graceful_seconds: float = 5.0) -> str:
        del graceful_seconds
        processes[pid]["alive"] = False
        raise RuntimeError("shutdown confirmation timed out")

    monkeypatch.setattr(concurrency, "_bounded_stop", ambiguous_stop)
    result = pool.destroy(slot["port"], "one")

    assert result["status"] == "destroyed"
    assert result["shutdown"] == "post-state-exited"


def test_serena_destroy_waits_for_delayed_post_state_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    processes = _fake_serena(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    pool = SerenaSlotPool(ports=(9410,))
    slot = pool.acquire(project, "one")
    original_identity = concurrency._process_identity
    checks = {"count": 0}

    def delayed_identity(pid: int):
        checks["count"] += 1
        if checks["count"] >= 3:
            processes[pid]["alive"] = False
        return original_identity(pid)

    monkeypatch.setattr(concurrency, "_process_identity", delayed_identity)
    monkeypatch.setattr(
        concurrency,
        "_bounded_stop",
        lambda _pid, graceful_seconds=5.0: (_ for _ in ()).throw(
            RuntimeError("shutdown confirmation timed out")
        ),
    )

    result = pool.destroy(slot["port"], "one")

    assert result["shutdown"] == "post-state-exited"
    assert checks["count"] >= 3


def test_coding_tools_binding_and_single_writer_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    workspace = tmp_path / "workspace"
    tree = workspace / "repo"
    other = workspace / "repo-worktree"
    outside = tmp_path / "outside"
    tree.mkdir(parents=True)
    other.mkdir()
    outside.mkdir()
    policy = CodingWorkspacePolicy(workspace)

    first = policy.acquire_writer(tree, "writer-a")
    assert first["status"] == "acquired"
    with pytest.raises(LeaseBusy):
        policy.acquire_writer(tree, "writer-b")
    second = policy.acquire_writer(other, "writer-b")
    assert second["worktree_id"] != first["worktree_id"]
    with pytest.raises(BindingMismatch):
        policy.assert_binding(outside)


def test_coding_tools_reads_do_not_take_writer_lease(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    workspace = tmp_path / "workspace"
    tree = workspace / "repo"
    tree.mkdir(parents=True)
    policy = CodingWorkspacePolicy(workspace)

    assert policy.assert_binding(tree) == tree.resolve()
    assert policy.assert_binding(tree) == tree.resolve()
    assert list(policy.root.glob("*.json")) == []


def test_gui_lease_allows_only_one_owner_and_reclaims_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    clock = {"now": 100.0}
    monkeypatch.setattr(concurrency, "_now", lambda: clock["now"])
    lease = MachineGuiLease(lease_seconds=5)

    assert lease.acquire("rdc", action="focus-window")["status"] == "acquired"
    with pytest.raises(LeaseBusy):
        lease.acquire("windows-mcp", action="click")
    clock["now"] = 106.0
    reclaimed = lease.acquire("windows-mcp", action="click")
    assert reclaimed["status"] == "reclaimed-stale"
    assert lease.release("windows-mcp")["status"] == "released"
    assert lease.release("windows-mcp")["status"] == "already-released"


def test_gui_simultaneous_acquire_has_single_winner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    lease = MachineGuiLease(lease_seconds=30)
    barrier = threading.Barrier(2)
    results: list[str] = []

    def worker(owner: str) -> None:
        barrier.wait()
        try:
            lease.acquire(owner, action="native-dialog")
            results.append(owner)
        except LeaseBusy:
            pass

    threads = [threading.Thread(target=worker, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 1


@pytest.mark.parametrize(
    ("failed", "gateway", "rdc", "expected"),
    [
        ("gateway", True, True, "rdc"),
        ("public-gateway", False, True, "rdc"),
        ("rdc", True, False, "gateway"),
        ("gateway", True, False, None),
    ],
)
def test_complementary_recovery_path_selection(
    failed: str, gateway: bool, rdc: bool, expected: str | None
) -> None:
    assert recovery.choose_complementary_path(
        failed,
        gateway_available=gateway,
        rdc_available=rdc,
    ) == expected


def test_recovery_gateway_to_rdc_and_rdc_to_gateway(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    coordinator = RecoveryCoordinator()
    calls: list[str] = []

    gateway_request = RecoveryRequest.new("mcpjungle", "gateway")
    result = coordinator.execute(
        gateway_request,
        path="rdc",
        lifecycle_authority=True,
        diagnose=lambda: {"healthy": False},
        mutate=lambda: calls.append("rdc-restart") or {"ok": True},
        post_state=lambda: {"healthy": True},
    )
    assert result["ok"] is True
    assert calls == ["rdc-restart"]

    rdc_request = RecoveryRequest.new("remote-desktop-commander", "rdc")
    result = coordinator.execute(
        rdc_request,
        path="gateway",
        lifecycle_authority=True,
        diagnose=lambda: {"healthy": False},
        mutate=lambda: calls.append("gateway-restart") or {"ok": True},
        post_state=lambda: {"healthy": True},
    )
    assert result["ok"] is True
    assert calls[-1] == "gateway-restart"


def test_same_attempt_has_one_mutation_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    coordinator = RecoveryCoordinator()
    request = RecoveryRequest.new("mcpjungle", "agent")
    calls: list[str] = []

    first = coordinator.execute(
        request,
        path="rdc",
        lifecycle_authority=True,
        diagnose=lambda: {"healthy": False},
        mutate=lambda: calls.append("rdc") or {"ok": False},
        post_state=lambda: {"healthy": False},
    )
    second = coordinator.execute(
        request,
        path="gateway",
        lifecycle_authority=True,
        diagnose=lambda: {"healthy": False},
        mutate=lambda: calls.append("gateway") or {"ok": True},
        post_state=lambda: {"healthy": False},
    )

    assert first["mutation_owner"] == "rdc"
    assert second["status"] == "mutation-owned-by-other-path"
    assert calls == ["rdc"]


def test_recovery_cycle_is_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    coordinator = RecoveryCoordinator()
    request = RecoveryRequest.new("mcpjungle", "gateway")
    calls: list[str] = []

    blocked = coordinator.execute(
        request,
        path="gateway",
        lifecycle_authority=True,
        diagnose=lambda: {"healthy": False},
        mutate=lambda: calls.append("bad"),
        post_state=lambda: {"healthy": False},
    )

    assert blocked["status"].startswith("recovery-cycle-blocked")
    assert calls == []


def test_recovery_hop_budget_is_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    coordinator = RecoveryCoordinator()
    request = RecoveryRequest.new("mcpjungle", "agent", hop_budget=0)
    calls: list[str] = []

    blocked = coordinator.execute(
        request,
        path="rdc",
        lifecycle_authority=True,
        diagnose=lambda: {"healthy": False},
        mutate=lambda: calls.append("bad"),
        post_state=lambda: {"healthy": False},
    )

    assert blocked["status"] == "recovery-hop-budget-exhausted"
    assert calls == []


def test_ambiguous_mutation_checks_post_state_and_does_not_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    coordinator = RecoveryCoordinator()
    request = RecoveryRequest.new("mcpjungle", "gateway")
    calls = {"count": 0}

    def mutate() -> None:
        calls["count"] += 1
        raise TimeoutError("response lost")

    result = coordinator.execute(
        request,
        path="rdc",
        lifecycle_authority=True,
        diagnose=lambda: {"healthy": False},
        mutate=mutate,
        post_state=lambda: {"healthy": True, "listener": "up"},
    )

    assert result["ok"] is True
    assert result["status"] == "recovered-after-ambiguous-mutation"
    assert calls["count"] == 1


def test_no_lifecycle_authority_is_diagnose_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEBGPT_CODEX_STATE_DIR", str(tmp_path / "state"))
    coordinator = RecoveryCoordinator()
    request = RecoveryRequest.new("serena", "gateway")
    calls: list[str] = []

    result = coordinator.execute(
        request,
        path="rdc",
        lifecycle_authority=False,
        diagnose=lambda: {"healthy": False},
        mutate=lambda: calls.append("must-not-run"),
        post_state=lambda: {"healthy": False},
    )

    assert result["status"] == "diagnose-only-no-lifecycle-authority"
    assert result["mutated"] is False
    assert calls == []
