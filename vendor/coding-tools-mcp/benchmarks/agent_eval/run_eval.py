#!/usr/bin/env python3
"""Run the real-task evaluation: native developer tools versus this server.

The agent under test is an external command, so this runner needs no model
access and no API key of its own. Supply one `--arm` per side of the
comparison; the MCP arm gets a server bound to the task workspace and its URL
in `CODING_TOOLS_MCP_URL`.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.agent_eval.harness import ArmConfig, TaskRun, run_task, write_runs  # noqa: E402
from benchmarks.agent_eval.scoring import render_markdown, score_runs  # noqa: E402
from benchmarks.agent_eval.tasks import TaskError, load_tasks  # noqa: E402

DEFAULT_MANIFEST = Path(__file__).resolve().parent / "manifests" / "starter.json"


def parse_arm(raw: str) -> ArmConfig:
    """Parse ``name=command`` or ``name:mcp=command``."""

    label, separator, command = raw.partition("=")
    if not separator or not command.strip():
        raise argparse.ArgumentTypeError(f"--arm needs name=command, got {raw!r}")
    name, _, transport = label.partition(":")
    if transport and transport != "mcp":
        raise argparse.ArgumentTypeError(f"unknown arm transport {transport!r}; use name:mcp=command")
    return ArmConfig(name=name.strip(), agent_command=command.strip(), serve_mcp=transport == "mcp")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="task manifest JSON")
    parser.add_argument(
        "--arm",
        action="append",
        type=parse_arm,
        default=None,
        metavar="NAME[:mcp]=COMMAND",
        help="one side of the comparison; repeat it. Append :mcp to serve this repo's MCP server",
    )
    parser.add_argument("--task", action="append", default=None, help="run only these task ids")
    parser.add_argument("--workdir", type=Path, default=None, help="where checkouts go; a temp dir by default")
    parser.add_argument("--runs-out", type=Path, default=None, help="write the per-task runs as JSON")
    parser.add_argument("--report-out", type=Path, default=None, help="write the scored report as JSON")
    parser.add_argument("--gated-arm", default="mcp", help="arm the release gates apply to")
    parser.add_argument("--validate-only", action="store_true", help="check the manifest and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tasks = load_tasks(args.manifest)
    except TaskError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.task:
        wanted = set(args.task)
        unknown = sorted(wanted - {task.id for task in tasks})
        if unknown:
            print(f"ERROR: unknown task ids: {', '.join(unknown)}", file=sys.stderr)
            return 2
        tasks = [task for task in tasks if task.id in wanted]
    if args.validate_only:
        print(f"{args.manifest}: {len(tasks)} tasks validated")
        return 0
    if not args.arm:
        print("ERROR: at least one --arm is required", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as scratch:
        workdir = args.workdir or Path(scratch)
        workdir.mkdir(parents=True, exist_ok=True)
        runs: list[TaskRun] = []
        for task in tasks:
            for arm in args.arm:
                run = run_task(task, arm, workdir)
                runs.append(run)
                status = "solved" if run.solved else (run.error or "failed")
                print(f"{task.id} [{arm.name}] {status} in {run.wall_time_s:.1f}s", flush=True)

    report = score_runs(runs, gated_arm=args.gated_arm)
    if args.runs_out:
        write_runs(runs, args.runs_out)
    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    print()
    print(render_markdown(report))
    return 0 if report.meets_release_gates else 1


if __name__ == "__main__":
    raise SystemExit(main())
