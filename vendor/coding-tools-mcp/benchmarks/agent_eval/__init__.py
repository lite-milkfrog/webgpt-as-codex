"""Real-task evaluation harness: native developer tools versus this server.

The only artifact that can falsify "the agent spent all day and it still is not
right" is a scored run over real tasks. This package owns the scaffolding for
one: task manifests, the per-task loop, and the scoring. It deliberately owns
no model access — the agent under test is an external command — so the harness
is runnable, testable, and reviewable without a model budget.
"""

from .scoring import EvaluationReport, score_runs
from .tasks import Task, load_tasks
from .harness import ArmConfig, TaskRun, run_task

__all__ = [
    "ArmConfig",
    "EvaluationReport",
    "Task",
    "TaskRun",
    "load_tasks",
    "run_task",
    "score_runs",
]
