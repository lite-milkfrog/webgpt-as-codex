from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from .health import sanitize_for_output
from .paths import ensure_state_dirs

SOFT_BUDGET_DEFAULT_SECONDS = 20 * 60
SOFT_BUDGET_MIN_SECONDS = 15 * 60
SOFT_BUDGET_MAX_SECONDS = 25 * 60
DEFAULT_CLOSURE_RESERVE_RATIO = 0.35
MIN_CLOSURE_RESERVE_RATIO = 0.25
MAX_CLOSURE_RESERVE_RATIO = 0.55
MAX_AUTO_SPLIT_DEPTH = 2

LOOP_STEPS = (
    "execute", "observe", "diagnose", "explore", "compare",
    "improve", "verify", "record", "reuse",
)
LESSON_LAYERS = ("skill", "mcp-guide", "machine-local", "stage-evidence")
CLOSURE_PHASES = (
    "executing",
    "implementation-complete",
    "validating",
    "documenting",
    "ready-to-commit",
    "committed",
    "prompt-generated",
    "prompt-validated",
    "submitted",
    "receiving-run-verified",
    "closed",
)
SPLIT_DECISIONS = ("none", "split", "freeze-and-close")
_HEX_RE = re.compile(r"^[0-9a-f]{7,64}$", re.IGNORECASE)
_STAGE_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
_WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\")


def _public_text(name: str, value: str, *, max_length: int = 500) -> str:
    value = value.strip()
    if not value or len(value) > max_length:
        raise ValueError(f"{name} must be 1..{max_length} characters")
    if _WINDOWS_PATH_RE.search(value):
        raise ValueError(f"{name} must not contain machine-specific absolute paths")
    sanitized = sanitize_for_output(value)
    if sanitized != value or "[private-url]" in value or "[redacted" in value.lower():
        raise ValueError(f"{name} is not public-safe")
    return value


def _stage_name(value: str) -> str:
    if not _STAGE_RE.fullmatch(value):
        raise ValueError(f"invalid stage name: {value!r}")
    return value
def _source_head(value: str) -> str:
    if not _HEX_RE.fullmatch(value):
        raise ValueError("source_head must be a Git object id")
    return value.lower()


def _non_negative(name: str, value: float) -> float:
    numeric = float(value)
    if numeric < 0:
        raise ValueError(f"{name} must be non-negative")
    return numeric


@dataclass
class StageCostEvidence:
    stage: str
    source_head: str
    scope: str
    implementation_seconds: float = 0.0
    closure_seconds: float = 0.0
    test_seconds: float = 0.0
    docs_seconds: float = 0.0
    retry_count: int = 0
    tool_switch_count: int = 0
    harness_failure_count: int = 0
    handoff_first_pass: bool | None = None
    almost_done_incidents: int = 0
    split_decision: str = "none"
    split_depth: int = 0
    split_reason: str | None = None
    closure_verified: bool = False

    def validate(self) -> None:
        self.stage = _stage_name(self.stage)
        self.source_head = _source_head(self.source_head)
        self.scope = _public_text("scope", self.scope)
        for name in (
            "implementation_seconds", "closure_seconds", "test_seconds", "docs_seconds"
        ):
            setattr(self, name, _non_negative(name, getattr(self, name)))
        for name in (
            "retry_count", "tool_switch_count", "harness_failure_count",
            "almost_done_incidents", "split_depth",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
            setattr(self, name, value)
        if self.split_decision not in SPLIT_DECISIONS:
            raise ValueError(f"invalid split_decision: {self.split_decision}")
        if self.split_reason is not None:
            self.split_reason = _public_text("split_reason", self.split_reason, max_length=300)

    @property
    def total_seconds(self) -> float:
        return self.implementation_seconds + self.closure_seconds

    def to_public_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["schema_version"] = 1
        payload["total_seconds"] = self.total_seconds
        return sanitize_for_output(payload)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageCostEvidence:
        known = {item.name for item in fields(cls)}
        item = cls(**{key: value for key, value in data.items() if key in known})
        item.validate()
        return item


@dataclass(frozen=True)
class StageSizingDecision:
    action: str
    reason: str
    soft_budget_seconds: int
    closure_reserve_seconds: int
    implementation_budget_seconds: int
    projected_implementation_seconds: int
    split_depth: int


def _successful_baseline(records: Iterable[StageCostEvidence]) -> list[StageCostEvidence]:
    return [
        row for row in records
        if row.closure_verified
        and row.total_seconds > 0
        and row.handoff_first_pass is True
        and row.split_decision == "none"
    ]


def calibrated_soft_budget_seconds(records: Iterable[StageCostEvidence]) -> int:
    baseline = _successful_baseline(records)
    if len(baseline) < 3:
        return SOFT_BUDGET_DEFAULT_SECONDS
    observed = statistics.median(row.total_seconds for row in baseline)
    return int(max(SOFT_BUDGET_MIN_SECONDS, min(SOFT_BUDGET_MAX_SECONDS, observed)))


def calibrated_closure_reserve_ratio(records: Iterable[StageCostEvidence]) -> float:
    baseline = _successful_baseline(records)
    ratios = [row.closure_seconds / row.total_seconds for row in baseline if row.closure_seconds > 0]
    if len(ratios) < 3:
        return DEFAULT_CLOSURE_RESERVE_RATIO
    observed = statistics.median(ratios)
    return max(MIN_CLOSURE_RESERVE_RATIO, min(MAX_CLOSURE_RESERVE_RATIO, observed))


def recommend_stage_action(
    *,
    elapsed_implementation_seconds: float,
    estimated_remaining_implementation_seconds: float,
    records: Iterable[StageCostEvidence] = (),
    split_depth: int = 0,
    closure_at_risk: bool = False,
) -> StageSizingDecision:
    rows = list(records)
    soft_budget = calibrated_soft_budget_seconds(rows)
    reserve = round(soft_budget * calibrated_closure_reserve_ratio(rows))
    implementation_budget = soft_budget - reserve
    projected = round(
        _non_negative("elapsed_implementation_seconds", elapsed_implementation_seconds)
        + _non_negative("estimated_remaining_implementation_seconds", estimated_remaining_implementation_seconds)
    )
    threatened = closure_at_risk or projected > implementation_budget
    if not threatened:
        action, reason = "continue", "projected implementation fits reserved closure budget"
    elif split_depth < MAX_AUTO_SPLIT_DEPTH:
        action, reason = "split", "implementation expansion threatens owned closure budget"
    else:
        action, reason = "freeze-and-close", "automatic split depth exhausted; freeze scope and close"
    return StageSizingDecision(
        action=action,
        reason=reason,
        soft_budget_seconds=soft_budget,
        closure_reserve_seconds=reserve,
        implementation_budget_seconds=implementation_budget,
        projected_implementation_seconds=projected,
        split_depth=split_depth,
    )


@dataclass
class LoopEvent:
    step: str
    result: str
    lesson_layer: str | None = None

    def validate(self) -> None:
        if self.step not in LOOP_STEPS:
            raise ValueError(f"invalid loop step: {self.step}")
        if self.result not in {"ok", "friction", "changed", "verified", "reused"}:
            raise ValueError(f"invalid loop result: {self.result}")
        if self.lesson_layer is not None and self.lesson_layer not in LESSON_LAYERS:
            raise ValueError(f"invalid lesson layer: {self.lesson_layer}")


@dataclass
class StageClosureState:
    current_stage: str
    next_stage: str
    after_next_stage: str
    source_head: str
    scope: str
    phase: str = "executing"
    loop_events: list[LoopEvent] = field(default_factory=list)
    prompt_sha256: str | None = None
    handoff_first_pass: bool | None = None
    handoff_recoveries: list[str] = field(default_factory=list)
    reopen_count: int = 0
    reopen_reasons: list[str] = field(default_factory=list)
    cost: StageCostEvidence | None = None
    updated_at: float = field(default_factory=time.time)

    def validate(self) -> None:
        self.current_stage = _stage_name(self.current_stage)
        self.next_stage = _stage_name(self.next_stage)
        self.after_next_stage = _stage_name(self.after_next_stage)
        self.source_head = _source_head(self.source_head)
        self.scope = _public_text("scope", self.scope)
        if self.phase not in CLOSURE_PHASES:
            raise ValueError(f"invalid closure phase: {self.phase}")
        if self.prompt_sha256 is not None and not _HEX_RE.fullmatch(self.prompt_sha256):
            raise ValueError("prompt_sha256 must be hexadecimal")
        self.handoff_recoveries = [
            _public_text("handoff_recovery", item, max_length=120)
            for item in self.handoff_recoveries
        ]
        if self.reopen_count < 0:
            raise ValueError("reopen_count must be non-negative")
        self.reopen_reasons = [
            _public_text("reopen_reason", item, max_length=300)
            for item in self.reopen_reasons
        ]
        for event in self.loop_events:
            event.validate()
        if self.cost is not None:
            self.cost.validate()

    def advance_phase(self, phase: str) -> None:
        if phase not in CLOSURE_PHASES:
            raise ValueError(f"invalid closure phase: {phase}")
        if CLOSURE_PHASES.index(phase) < CLOSURE_PHASES.index(self.phase):
            raise ValueError(f"closure phase cannot regress from {self.phase} to {phase}")
        self.phase = phase
        self.updated_at = time.time()

    def record_loop_step(
        self, step: str, result: str, *, lesson_layer: str | None = None
    ) -> None:
        event = LoopEvent(step=step, result=result, lesson_layer=lesson_layer)
        event.validate()
        self.loop_events.append(event)
        self.updated_at = time.time()

    def reopen(
        self,
        reason: str,
        *,
        phase: str = "implementation-complete",
    ) -> None:
        if CLOSURE_PHASES.index(self.phase) < CLOSURE_PHASES.index("committed"):
            raise ValueError("stage may reopen only after commit-time contradictory evidence")
        if phase not in {
            "implementation-complete",
            "validating",
            "documenting",
            "ready-to-commit",
        }:
            raise ValueError("invalid reopen phase")
        public_reason = _public_text("reopen_reason", reason, max_length=300)
        self.phase = phase
        self.reopen_count += 1
        self.reopen_reasons.append(public_reason)
        self.prompt_sha256 = None
        self.handoff_first_pass = None
        self.handoff_recoveries = []
        if self.cost is not None:
            self.cost.handoff_first_pass = None
            self.cost.closure_verified = False
            self.cost.almost_done_incidents += 1
        self.updated_at = time.time()
        self.validate()

    def record_cost(self, evidence: StageCostEvidence) -> None:
        evidence.validate()
        if evidence.stage != self.current_stage:
            raise ValueError("cost evidence stage does not match closure state")
        if evidence.source_head != self.source_head:
            raise ValueError("cost evidence source_head does not match closure state")
        self.cost = evidence
        self.updated_at = time.time()

    def record_handoff(
        self,
        *,
        prompt_sha256: str,
        first_pass: bool,
        recoveries: list[str],
    ) -> None:
        if not _HEX_RE.fullmatch(prompt_sha256):
            raise ValueError("prompt_sha256 must be hexadecimal")
        self.prompt_sha256 = prompt_sha256.lower()
        self.handoff_first_pass = bool(first_pass)
        self.handoff_recoveries = list(recoveries)
        self.updated_at = time.time()
        self.validate()

    def to_public_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["schema_version"] = 1
        return sanitize_for_output(payload)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageClosureState:
        events = [LoopEvent(**item) for item in data.get("loop_events", [])]
        cost_data = data.get("cost")
        cost = StageCostEvidence.from_dict(cost_data) if isinstance(cost_data, dict) else None
        item = cls(
            current_stage=data["current_stage"],
            next_stage=data["next_stage"],
            after_next_stage=data["after_next_stage"],
            source_head=data["source_head"],
            scope=data["scope"],
            phase=data.get("phase", "executing"),
            loop_events=events,
            prompt_sha256=data.get("prompt_sha256"),
            handoff_first_pass=data.get("handoff_first_pass"),
            handoff_recoveries=list(data.get("handoff_recoveries", [])),
            reopen_count=int(data.get("reopen_count", 0)),
            reopen_reasons=list(data.get("reopen_reasons", [])),
            cost=cost,
            updated_at=float(data.get("updated_at", time.time())),
        )
        item.validate()
        return item


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temp.replace(path)


class LoopStateStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (ensure_state_dirs() / "loop")

    def path_for(self, stage: str) -> Path:
        safe_stage = _stage_name(stage)
        return self.root / "stages" / f"{safe_stage}.json"

    def save(self, state: StageClosureState) -> Path:
        path = self.path_for(state.current_stage)
        _atomic_json(path, state.to_public_dict())
        return path

    def load(self, stage: str) -> StageClosureState:
        path = self.path_for(stage)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("loop state must be a JSON object")
        return StageClosureState.from_dict(data)


def write_public_stage_cost(path: Path, evidence: StageCostEvidence) -> None:
    _atomic_json(path, evidence.to_public_dict())


def load_stage_costs(directory: Path) -> list[StageCostEvidence]:
    rows: list[StageCostEvidence] = []
    if not directory.exists():
        return rows
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            rows.append(StageCostEvidence.from_dict(data))
    return rows
def cli_loop(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex loop")
    sub = parser.add_subparsers(dest="action", required=True)

    start = sub.add_parser("start")
    start.add_argument("--stage", required=True)
    start.add_argument("--next", required=True)
    start.add_argument("--after-next", required=True)
    start.add_argument("--head", required=True)
    start.add_argument("--scope", required=True)

    show = sub.add_parser("show")
    show.add_argument("--stage", required=True)

    step = sub.add_parser("step")
    step.add_argument("--stage", required=True)
    step.add_argument("--step", choices=LOOP_STEPS, required=True)
    step.add_argument(
        "--result",
        choices=("ok", "friction", "changed", "verified", "reused"),
        required=True,
    )
    step.add_argument("--lesson-layer", choices=LESSON_LAYERS)

    phase = sub.add_parser("phase")
    phase.add_argument("--stage", required=True)
    phase.add_argument("--phase", choices=CLOSURE_PHASES, required=True)

    reopen = sub.add_parser("reopen")
    reopen.add_argument("--stage", required=True)
    reopen.add_argument("--reason", required=True)
    reopen.add_argument(
        "--phase",
        choices=("implementation-complete", "validating", "documenting", "ready-to-commit"),
        default="implementation-complete",
    )

    cost = sub.add_parser("cost")
    cost.add_argument("--stage", required=True)
    cost.add_argument("--implementation-seconds", type=float, required=True)
    cost.add_argument("--closure-seconds", type=float, required=True)
    cost.add_argument("--test-seconds", type=float, default=0)
    cost.add_argument("--docs-seconds", type=float, default=0)
    cost.add_argument("--retry-count", type=int, default=0)
    cost.add_argument("--tool-switch-count", type=int, default=0)
    cost.add_argument("--harness-failure-count", type=int, default=0)
    cost.add_argument("--almost-done-incidents", type=int, default=0)
    cost.add_argument("--split-decision", choices=SPLIT_DECISIONS, default="none")
    cost.add_argument("--split-depth", type=int, default=0)
    cost.add_argument("--split-reason")
    cost.add_argument("--closure-verified", action="store_true")

    handoff = sub.add_parser("handoff")
    handoff.add_argument("--stage", required=True)
    handoff.add_argument("--sha256", required=True)
    handoff.add_argument("--first-pass", choices=("true", "false"), required=True)
    handoff.add_argument("--recovery", action="append", default=[])

    args = parser.parse_args(argv)
    store = LoopStateStore()

    if args.action == "start":
        state = StageClosureState(
            args.stage,
            args.next,
            args.after_next,
            args.head,
            args.scope,
        )
        store.save(state)
    else:
        state = store.load(args.stage)
        if args.action == "step":
            state.record_loop_step(args.step, args.result, lesson_layer=args.lesson_layer)
            store.save(state)
        elif args.action == "phase":
            state.advance_phase(args.phase)
            store.save(state)
        elif args.action == "reopen":
            state.reopen(args.reason, phase=args.phase)
            store.save(state)
        elif args.action == "cost":
            state.record_cost(
                StageCostEvidence(
                    stage=state.current_stage,
                    source_head=state.source_head,
                    scope=state.scope,
                    implementation_seconds=args.implementation_seconds,
                    closure_seconds=args.closure_seconds,
                    test_seconds=args.test_seconds,
                    docs_seconds=args.docs_seconds,
                    retry_count=args.retry_count,
                    tool_switch_count=args.tool_switch_count,
                    harness_failure_count=args.harness_failure_count,
                    handoff_first_pass=state.handoff_first_pass,
                    almost_done_incidents=args.almost_done_incidents,
                    split_decision=args.split_decision,
                    split_depth=args.split_depth,
                    split_reason=args.split_reason,
                    closure_verified=args.closure_verified,
                )
            )
            store.save(state)
        elif args.action == "handoff":
            state.record_handoff(
                prompt_sha256=args.sha256,
                first_pass=args.first_pass == "true",
                recoveries=args.recovery,
            )
            if state.cost is not None:
                state.cost.handoff_first_pass = state.handoff_first_pass
            store.save(state)

    print(json.dumps(state.to_public_dict(), ensure_ascii=False, indent=2))
    return 0
