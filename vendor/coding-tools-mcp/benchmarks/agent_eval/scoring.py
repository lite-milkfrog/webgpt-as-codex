"""Score an evaluation run against the v0.5.0 release gates.

The metrics are the ones the plan names: final pass rate, first-attempt patch
success, rounds to green, regressions introduced, and wall time. Rates are
reported with their numerators and denominators so a small sample cannot be
mistaken for a large one.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Iterable

from .harness import TaskRun

# Release-announcement gates, not merge gates: the code lands without them and
# the announcement waits for a run that clears them.
RELEASE_GATES = {
    "minimum_tasks": 30,
    "final_pass_rate": 0.80,
    "first_attempt_success_rate": 0.80,
    "max_regression_rate": 0.05,
}


@dataclass
class ArmScore:
    arm: str
    tasks: int = 0
    invalid_tasks: int = 0
    solved: int = 0
    first_attempt: int = 0
    regressions: int = 0
    rounds_to_green: list[int] = field(default_factory=list)
    wall_time_s: list[float] = field(default_factory=list)

    @property
    def scored_tasks(self) -> int:
        return self.tasks - self.invalid_tasks

    def rate(self, numerator: int) -> float | None:
        return numerator / self.scored_tasks if self.scored_tasks else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm": self.arm,
            "tasks": self.tasks,
            "invalid_tasks": self.invalid_tasks,
            "scored_tasks": self.scored_tasks,
            "solved": self.solved,
            "final_pass_rate": self.rate(self.solved),
            "first_attempt_success": self.first_attempt,
            "first_attempt_success_rate": self.rate(self.first_attempt),
            "regressions_introduced": self.regressions,
            "regression_rate": self.rate(self.regressions),
            "median_rounds_to_green": statistics.median(self.rounds_to_green) if self.rounds_to_green else None,
            "median_wall_time_s": statistics.median(self.wall_time_s) if self.wall_time_s else None,
            "total_wall_time_s": round(sum(self.wall_time_s), 3),
        }


@dataclass
class EvaluationReport:
    arms: dict[str, ArmScore]
    gate_failures: list[str]

    @property
    def meets_release_gates(self) -> bool:
        return not self.gate_failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "arms": {name: score.to_dict() for name, score in sorted(self.arms.items())},
            "release_gates": RELEASE_GATES,
            "gate_failures": self.gate_failures,
            "meets_release_gates": self.meets_release_gates,
        }


def score_runs(runs: Iterable[TaskRun], *, gated_arm: str = "mcp") -> EvaluationReport:
    arms: dict[str, ArmScore] = {}
    for run in runs:
        score = arms.setdefault(run.arm, ArmScore(run.arm))
        score.tasks += 1
        if run.started_green or not run.setup_ok:
            score.invalid_tasks += 1
            continue
        score.wall_time_s.append(run.wall_time_s)
        if run.solved:
            score.solved += 1
            rounds = run.rounds_to_green
            if rounds is not None:
                score.rounds_to_green.append(rounds)
        if run.first_attempt_success:
            score.first_attempt += 1
        if run.regression_introduced:
            score.regressions += 1
    return EvaluationReport(arms=arms, gate_failures=_gate_failures(arms.get(gated_arm)))


def _gate_failures(score: ArmScore | None) -> list[str]:
    if score is None:
        return ["no runs recorded for the gated arm"]
    failures: list[str] = []
    if score.scored_tasks < RELEASE_GATES["minimum_tasks"]:
        failures.append(
            f"{score.scored_tasks} scored tasks is below the {RELEASE_GATES['minimum_tasks']}-task minimum"
        )
    checks = (
        ("final_pass_rate", score.rate(score.solved), RELEASE_GATES["final_pass_rate"], "at least"),
        (
            "first_attempt_success_rate",
            score.rate(score.first_attempt),
            RELEASE_GATES["first_attempt_success_rate"],
            "at least",
        ),
    )
    for name, value, threshold, _ in checks:
        if value is None or value < threshold:
            failures.append(f"{name} {_format(value)} is below the {threshold:.0%} gate")
    regression_rate = score.rate(score.regressions)
    if regression_rate is not None and regression_rate > RELEASE_GATES["max_regression_rate"]:
        failures.append(
            f"regression_rate {_format(regression_rate)} exceeds the "
            f"{RELEASE_GATES['max_regression_rate']:.0%} gate"
        )
    return failures


def _format(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def render_markdown(report: EvaluationReport) -> str:
    lines = [
        "| Arm | Scored | Final pass | First attempt | Median rounds | Regressions | Median wall time |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, score in sorted(report.arms.items()):
        data = score.to_dict()
        median_time = data["median_wall_time_s"]
        lines.append(
            f"| {name} | {data['scored_tasks']} | {_format(data['final_pass_rate'])} "
            f"| {_format(data['first_attempt_success_rate'])} "
            f"| {data['median_rounds_to_green'] if data['median_rounds_to_green'] is not None else 'n/a'} "
            f"| {data['regressions_introduced']} "
            f"| {f'{median_time:.1f}s' if median_time is not None else 'n/a'} |"
        )
    lines.append("")
    if report.meets_release_gates:
        lines.append("Release gates: met.")
    else:
        lines.append("Release gates: not met.")
        lines.extend(f"- {failure}" for failure in report.gate_failures)
    return "\n".join(lines)
