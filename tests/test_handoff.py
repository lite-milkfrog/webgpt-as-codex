from webgpt_as_codex.handoff import HandoffSpec, build_handoff_prompt, validate_handoff_prompt


def test_stable_handoff_contains_required_contract() -> None:
    spec = HandoffSpec(
        current_stage="STAGE-X",
        next_stage="STAGE-Y",
        after_next_stage="STAGE-Z",
        source_head="abc123",
        stage_objective="Build the owned subsystem.",
        required_outputs=("implementation", "closure"),
        do_not_redo=("Stage W",),
        known_risks=("one known risk",),
    )
    text = build_handoff_prompt(spec)
    assert validate_handoff_prompt(
        text,
        expected_stage="STAGE-X",
        expected_head="abc123",
    ) == []
    assert "## Recursive continuation invariant" in text
    assert "recursive continuation ends only after the planned final stage and Final Overall Acceptance" in text
    assert "## Self-evolving execution contract" in text
    assert "20-minute soft stage budget" in text
    assert "real active composer" in text
    assert "RECOVER > REUSE > CREATE" in text
    assert "SUBMIT_ATTEMPTED" in text
    assert "must never trigger a second Enter" in text
    assert "Routing decides WHICH capability" in text


def test_handoff_rejects_stale_head() -> None:
    spec = HandoffSpec(
        current_stage="STAGE-X",
        next_stage="STAGE-Y",
        after_next_stage="STAGE-Z",
        source_head="abc123",
        stage_objective="Build.",
        required_outputs=("implementation",),
        do_not_redo=("closed work",),
    )
    text = build_handoff_prompt(spec)
    errors = validate_handoff_prompt(
        text,
        expected_stage="STAGE-X",
        expected_head="different",
    )
    assert "SOURCE_HEAD mismatch" in errors
