import json
from pathlib import Path

import pytest

from webgpt_as_codex.handoff import (
    HandoffPlan,
    load_handoff_plan,
    validate_handoff_prompt,
    write_validated_prompt_from_plan,
)
from webgpt_as_codex.loop import (
    LoopStateStore,
    StageClosureState,
    StageCostEvidence,
    calibrated_closure_reserve_ratio,
    calibrated_soft_budget_seconds,
    recommend_stage_action,
)
from webgpt_as_codex.playwright_handoff import (
    AmbiguousSubmissionError,
    _open_and_select_chatgpt_tab,
    _prepare_prompt_draft,
    _submit_once_and_verify,
    _target_new_chatgpt_tab_index,
)


def _evidence(
    stage: str,
    *,
    implementation: float = 600,
    closure: float = 300,
    first_pass: bool | None = True,
    split: str = "none",
) -> StageCostEvidence:
    return StageCostEvidence(
        stage=stage,
        source_head="a" * 40,
        scope="bounded public-safe test stage",
        implementation_seconds=implementation,
        closure_seconds=closure,
        test_seconds=120,
        docs_seconds=90,
        retry_count=1,
        tool_switch_count=1,
        harness_failure_count=0,
        handoff_first_pass=first_pass,
        almost_done_incidents=0,
        split_decision=split,
        closure_verified=True,
    )


def test_stage_cost_evidence_is_public_safe_and_round_trips() -> None:
    row = _evidence("STAGE-10-TEST")
    payload = row.to_public_dict()
    assert payload["schema_version"] == 1
    assert payload["total_seconds"] == 900
    rebuilt = StageCostEvidence.from_dict(payload)
    assert rebuilt.stage == row.stage
    assert rebuilt.total_seconds == row.total_seconds


@pytest.mark.parametrize(
    "scope",
    [
        r"C:\Users\someone\private\repo",
        "Authorization: Bearer should-not-persist",
        "http://127.0.0.1:9999/private",
    ],
)
def test_stage_cost_evidence_rejects_machine_private_or_secret_scope(scope: str) -> None:
    row = _evidence("STAGE-10-PRIVATE")
    row.scope = scope
    with pytest.raises(ValueError, match="public-safe|machine-specific"):
        row.to_public_dict()


def test_stage_budget_calibrates_from_verified_first_pass_history() -> None:
    rows = [
        _evidence("STAGE-A", implementation=700, closure=300),
        _evidence("STAGE-B", implementation=720, closure=280),
        _evidence("STAGE-C", implementation=680, closure=320),
    ]
    assert calibrated_soft_budget_seconds(rows) == 1000
    assert calibrated_closure_reserve_ratio(rows) == pytest.approx(0.30)


def test_stage_budget_ignores_failed_or_split_baseline_rows() -> None:
    rows = [
        _evidence("STAGE-A", implementation=300, closure=100, first_pass=False),
        _evidence("STAGE-B", implementation=300, closure=100, split="split"),
        _evidence("STAGE-C", implementation=300, closure=100, first_pass=False),
    ]
    assert calibrated_soft_budget_seconds(rows) == 1200
    assert calibrated_closure_reserve_ratio(rows) == pytest.approx(0.35)


def test_sizing_decision_reserves_closure_and_splits_before_tail_starvation() -> None:
    decision = recommend_stage_action(
        elapsed_implementation_seconds=650,
        estimated_remaining_implementation_seconds=200,
    )
    assert decision.soft_budget_seconds == 1200
    assert decision.closure_reserve_seconds == 420
    assert decision.implementation_budget_seconds == 780
    assert decision.action == "split"


def test_sizing_decision_freezes_scope_after_bounded_split_depth() -> None:
    decision = recommend_stage_action(
        elapsed_implementation_seconds=760,
        estimated_remaining_implementation_seconds=100,
        split_depth=2,
    )
    assert decision.action == "freeze-and-close"


def test_closure_state_persists_and_cannot_regress(tmp_path: Path) -> None:
    state = StageClosureState(
        current_stage="STAGE-10-TEST",
        next_stage="STAGE-11-TEST",
        after_next_stage="STAGE-12-TEST",
        source_head="b" * 40,
        scope="dogfood durable closure state",
    )
    state.record_loop_step("execute", "ok")
    state.record_loop_step("observe", "friction", lesson_layer="stage-evidence")
    state.advance_phase("implementation-complete")
    store = LoopStateStore(tmp_path)
    path = store.save(state)

    assert path.is_file()
    loaded = store.load("STAGE-10-TEST")
    assert loaded.phase == "implementation-complete"
    assert [event.step for event in loaded.loop_events] == ["execute", "observe"]

    with pytest.raises(ValueError, match="cannot regress"):
        loaded.advance_phase("executing")


def test_closure_state_rejects_private_machine_path(tmp_path: Path) -> None:
    state = StageClosureState(
        current_stage="STAGE-10-TEST",
        next_stage="STAGE-11-TEST",
        after_next_stage="STAGE-12-TEST",
        source_head="c" * 40,
        scope=r"write D:\private\machine\state",
    )
    with pytest.raises(ValueError, match="machine-specific"):
        LoopStateStore(tmp_path).save(state)


def test_handoff_plan_regenerates_with_new_committed_head(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "current_stage": "STAGE-11-SECURITY-RELIABILITY-HARDENING",
                "next_stage": "STAGE-12-README-RELEASE-FINAL-ACCEPTANCE",
                "after_next_stage": "FINAL-OVERALL-ACCEPTANCE",
                "stage_objective": "Harden owned security and reliability boundaries.",
                "required_outputs": ["implementation", "tests", "closure"],
                "do_not_redo": ["closed Stages 0-10"],
                "known_risks": ["Update hardening remains Stage 11 ownership."],
            }
        ),
        encoding="utf-8",
    )
    plan = load_handoff_plan(plan_path)
    assert isinstance(plan, HandoffPlan)

    prompt_path = tmp_path / "stage11.md"
    head = "d" * 40
    digest = write_validated_prompt_from_plan(prompt_path, plan_path, source_head=head)
    text = prompt_path.read_text(encoding="utf-8")
    assert len(digest) == 64
    assert validate_handoff_prompt(
        text,
        expected_stage=plan.current_stage,
        expected_head=head,
        expected_next_stage=plan.next_stage,
        expected_after_next_stage=plan.after_next_stage,
    ) == []


def test_new_tab_selection_uses_set_difference_not_highest_existing_blank() -> None:
    before = (
        "- 0: (current) [Existing](https://chatgpt.com/c/abc)\n"
        "- 5: [ChatGPT](https://chatgpt.com/)"
    )
    after = (
        "- 0: [Existing](https://chatgpt.com/c/abc)\n"
        "- 5: [ChatGPT](https://chatgpt.com/)\n"
        "- 2: (current) [ChatGPT](https://chatgpt.com/)"
    )
    assert _target_new_chatgpt_tab_index(before, after) == 2


def test_prepare_prompt_draft_retries_stale_ref_before_submission(monkeypatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.type_calls = 0

        def tool(self, name: str, arguments: dict, *, request_id: int) -> dict:
            assert name == "browser_type"
            assert arguments["submit"] is False
            self.type_calls += 1
            if self.type_calls == 1:
                raise RuntimeError("stale ref")
            return {"result": {"content": []}}

    refs = iter([("e1", 4), ("e2", 6)])
    monkeypatch.setattr(
        "webgpt_as_codex.playwright_handoff._wait_for_active_composer",
        lambda *_args, **_kwargs: next(refs),
    )
    recoveries: list[str] = []
    next_id = _prepare_prompt_draft(
        FakeClient(),
        "prompt",
        timeout_seconds=1,
        first_request_id=2,
        recoveries=recoveries,
    )
    assert next_id == 7
    assert recoveries == ["stale-composer-ref"]


def test_submit_once_never_retries_enter_after_ambiguous_response(monkeypatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.press_count = 0

        def tool(self, name: str, _arguments: dict, *, request_id: int) -> dict:
            assert name == "browser_press_key"
            self.press_count += 1
            raise RuntimeError("transport response lost after submit")

    client = FakeClient()
    states = iter(
        [
            ({"url": "https://chatgpt.com/", "users": [], "assistantCount": 0}, 11),
            (
                {
                    "url": "https://chatgpt.com/c/abc",
                    "users": ["SOURCE_HEAD = deadbeef"],
                    "assistantCount": 1,
                },
                12,
            ),
        ]
    )
    monkeypatch.setattr(
        "webgpt_as_codex.playwright_handoff._chat_state",
        lambda *_args, **_kwargs: next(states),
    )
    monkeypatch.setattr("webgpt_as_codex.playwright_handoff.time.sleep", lambda *_: None)
    recoveries: list[str] = []
    url, _ = _submit_once_and_verify(
        client,
        expected_head="deadbeef",
        timeout_seconds=1,
        first_request_id=9,
        recoveries=recoveries,
    )
    assert url.endswith("/c/abc")
    assert client.press_count == 1
    assert recoveries == ["submit-response-ambiguous"]


def test_submit_once_refuses_duplicate_when_post_state_stays_ambiguous(monkeypatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.press_count = 0

        def tool(self, name: str, _arguments: dict, *, request_id: int) -> dict:
            assert name == "browser_press_key"
            self.press_count += 1
            raise RuntimeError("lost response")

    client = FakeClient()
    monkeypatch.setattr(
        "webgpt_as_codex.playwright_handoff._chat_state",
        lambda *_args, **_kwargs: (
            {"url": "https://chatgpt.com/", "users": [], "assistantCount": 0},
            11,
        ),
    )

    class FakeClock:
        def __init__(self) -> None:
            self.value = 0.0

        def monotonic(self) -> float:
            self.value += 0.6
            return self.value

    clock = FakeClock()
    monkeypatch.setattr("webgpt_as_codex.playwright_handoff.time.monotonic", clock.monotonic)
    monkeypatch.setattr("webgpt_as_codex.playwright_handoff.time.sleep", lambda *_: None)

    with pytest.raises(AmbiguousSubmissionError, match="refusing duplicate submit"):
        _submit_once_and_verify(
            client,
            expected_head="deadbeef",
            timeout_seconds=1,
            first_request_id=9,
            recoveries=[],
        )
    assert client.press_count == 1


def test_closure_state_records_cost_and_handoff_result() -> None:
    state = StageClosureState(
        current_stage="STAGE-10-TEST",
        next_stage="STAGE-11-TEST",
        after_next_stage="STAGE-12-TEST",
        source_head="e" * 40,
        scope="durable cost and handoff result",
    )
    cost = StageCostEvidence(
        stage=state.current_stage,
        source_head=state.source_head,
        scope=state.scope,
        implementation_seconds=600,
        closure_seconds=300,
    )
    state.record_cost(cost)
    state.record_handoff(
        prompt_sha256="f" * 64,
        first_pass=False,
        recoveries=["stale-composer-ref"],
    )
    assert state.cost is cost
    assert state.prompt_sha256 == "f" * 64
    assert state.handoff_first_pass is False
    assert state.handoff_recoveries == ["stale-composer-ref"]


def test_closure_state_rejects_cost_for_other_stage_or_head() -> None:
    state = StageClosureState(
        current_stage="STAGE-10-TEST",
        next_stage="STAGE-11-TEST",
        after_next_stage="STAGE-12-TEST",
        source_head="a" * 40,
        scope="durable cost mismatch guard",
    )
    wrong = StageCostEvidence(
        stage="STAGE-99-OTHER",
        source_head="b" * 40,
        scope=state.scope,
    )
    with pytest.raises(ValueError, match="stage does not match"):
        state.record_cost(wrong)


def test_open_tab_reuses_unique_blank_after_pre_submit_recovery() -> None:
    before = (
        "### Result\n"
        "- 0: (current) [Welcome](chrome-extension://example)\n"
        "- 1: [ChatGPT](https://chatgpt.com/)"
    )
    same = before

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []
            self.list_count = 0

        def tool(self, name: str, arguments: dict, *, request_id: int) -> dict:
            self.calls.append((name, arguments))
            if name == "browser_tabs" and arguments["action"] == "list":
                self.list_count += 1
                text = before if self.list_count == 1 else same
            else:
                text = "### Result\nOK"
            return {"result": {"content": [{"type": "text", "text": text}]}}

    client = FakeClient()
    recoveries: list[str] = []
    next_id = _open_and_select_chatgpt_tab(
        client,
        first_request_id=2,
        recoveries=recoveries,
    )
    assert next_id == 7
    assert client.calls[-1] == ("browser_tabs", {"action": "select", "index": 1})
    assert recoveries == ["tab-selection-refresh", "unique-blank-tab-reuse"]


def test_closure_state_reopen_invalidates_stale_prompt() -> None:
    state = StageClosureState(
        current_stage="STAGE-10-TEST",
        next_stage="STAGE-11-TEST",
        after_next_stage="STAGE-12-TEST",
        source_head="a" * 40,
        scope="post commit contradictory handoff evidence",
        phase="prompt-validated",
        prompt_sha256="b" * 64,
        handoff_first_pass=False,
        handoff_recoveries=["tab-selection-refresh"],
        cost=StageCostEvidence(
            stage="STAGE-10-TEST",
            source_head="a" * 40,
            scope="post commit contradictory handoff evidence",
            almost_done_incidents=1,
            handoff_first_pass=False,
            closure_verified=True,
        ),
    )
    state.reopen(
        "real pre-submit tab evidence contradicted the handoff recovery assumption"
    )
    assert state.phase == "implementation-complete"
    assert state.reopen_count == 1
    assert state.prompt_sha256 is None
    assert state.handoff_first_pass is None
    assert state.handoff_recoveries == []
    assert state.cost is not None
    assert state.cost.closure_verified is False
    assert state.cost.handoff_first_pass is None
    assert state.cost.almost_done_incidents == 2


def test_closure_state_reopen_requires_commit_time_evidence() -> None:
    state = StageClosureState(
        current_stage="STAGE-10-TEST",
        next_stage="STAGE-11-TEST",
        after_next_stage="STAGE-12-TEST",
        source_head="a" * 40,
        scope="pre commit state",
        phase="ready-to-commit",
    )
    with pytest.raises(ValueError, match="only after commit-time"):
        state.reopen("too early")


def test_closure_state_reopen_reason_must_be_public_safe() -> None:
    state = StageClosureState(
        current_stage="STAGE-10-TEST",
        next_stage="STAGE-11-TEST",
        after_next_stage="STAGE-12-TEST",
        source_head="a" * 40,
        scope="post commit state",
        phase="committed",
    )
    with pytest.raises(ValueError, match="machine-specific"):
        state.reopen(r"evidence at C:\private\machine")
