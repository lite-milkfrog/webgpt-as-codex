from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import repo_root

REQUIRED_MARKERS = (
    "CURRENT_STAGE =",
    "NEXT_STAGE =",
    "AFTER_NEXT_STAGE =",
    "SOURCE_HEAD =",
    "## Mandatory read order",
    "## Stage objective",
    "## Do not redo",
    "## MCP routing contract",
    "## Failure protocol",
    "## Self-evolving execution contract",
    "## Closure contract",
    "## Recursive continuation invariant",
    "## Automatic handoff contract",
)


@dataclass(frozen=True)
class HandoffSpec:
    current_stage: str
    next_stage: str
    after_next_stage: str
    source_head: str
    stage_objective: str
    required_outputs: tuple[str, ...]
    do_not_redo: tuple[str, ...]
    known_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class HandoffPlan:
    current_stage: str
    next_stage: str
    after_next_stage: str
    stage_objective: str
    required_outputs: tuple[str, ...]
    do_not_redo: tuple[str, ...]
    known_risks: tuple[str, ...] = ()

    def instantiate(self, source_head: str) -> HandoffSpec:
        return HandoffSpec(
            current_stage=self.current_stage,
            next_stage=self.next_stage,
            after_next_stage=self.after_next_stage,
            source_head=source_head,
            stage_objective=self.stage_objective,
            required_outputs=self.required_outputs,
            do_not_redo=self.do_not_redo,
            known_risks=self.known_risks,
        )


def current_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root()), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


def load_handoff_plan(path: Path) -> HandoffPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("handoff plan must be a JSON object")
    required = {
        "current_stage", "next_stage", "after_next_stage", "stage_objective",
        "required_outputs", "do_not_redo",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError("handoff plan missing fields: " + ", ".join(missing))
    return HandoffPlan(
        current_stage=str(data["current_stage"]),
        next_stage=str(data["next_stage"]),
        after_next_stage=str(data["after_next_stage"]),
        stage_objective=str(data["stage_objective"]),
        required_outputs=tuple(str(item) for item in data["required_outputs"]),
        do_not_redo=tuple(str(item) for item in data["do_not_redo"]),
        known_risks=tuple(str(item) for item in data.get("known_risks", [])),
    )


def build_handoff_prompt(spec: HandoffSpec) -> str:
    outputs = "\n".join(f"- {item}" for item in spec.required_outputs)
    redo = "\n".join(f"- {item}" for item in spec.do_not_redo)
    risks = "\n".join(f"- {item}" for item in spec.known_risks) or "- none beyond local SoT"
    return f"""# WebGPT-as-Codex — {spec.current_stage}

Continue the WebGPT-as-Codex project using Computer Agent Skill + Loop Engineering + MCP-routed execution.

This is an automatic continuation window. Do not stop after reporting progress if owned work remains.

CURRENT_STAGE = {spec.current_stage}
NEXT_STAGE = {spec.next_stage}
AFTER_NEXT_STAGE = {spec.after_next_stage}
SOURCE_HEAD = {spec.source_head}

## Mandatory read order
1. D:\\AgentData\\10_Workspaces\\webgpt-as-codex\\AGENTS.md
2. docs/CURRENT-PROJECT-STATE.md
3. latest previous-stage closure
4. docs/ARCHITECTURE.md
5. skills/webgpt-as-codex/SKILL.md
6. skills/webgpt-as-codex/loop-engineering.md
7. skills/webgpt-as-codex/handoff.md
8. skills/webgpt-as-codex/routing.md
9. relevant component manifests, MCP Guides/inventory when present, and tests

The local repository SoT outranks chat memory.

## Stage objective
{spec.stage_objective}

## Required outputs
{outputs}

## Do not redo
{redo}

## Known risks / evidence
{risks}

## MCP routing contract
- Serena: semantic code navigation only after confirming the active project is webgpt-as-codex.
- Coding Tools: repo writes/tests/git only when the workspace is actually bound to this repository.
- Playwright MCP: browser/Web App automation and the final next-window handoff.
- Windows-MCP: native Windows GUI fallback.
- Desktop Commander / shell: host files/processes when structured project tools do not fit.
- Prefer structured tools; diagnose preferred-tool failure before fallback.
- Routing decides WHICH capability; actual schema/Operating Guide knowledge decides HOW to use it.
- One failed call is not proof an MCP is unavailable: inspect binding, session, auth, schema, harness and real post-state first.
- Never let a temporary test instance change the shared Serena active project.

## Failure protocol
1. distinguish harness failure from target failure;
2. inspect real logs/state;
3. retry only after a root-cause hypothesis;
4. use a bounded temporary instance when production-like services must remain untouched;
5. record reusable lessons in the Experience Ledger;
6. do not broaden into closed stages without contradictory evidence.
7. explore reasonable tools/schema/environment/log/history evidence before asking the user unless the missing fact/choice is genuinely user-exclusive.

## Self-evolving execution contract
- Do not merely execute. Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse.
- Observe the full chain: SoT loading, planning, stage sizing, routing, MCP use, implementation, validation, docs, Git, prompt generation, Playwright submit and receiving-run verification.
- Treat repeated friction, premature fallback, user reminders, missing docs and almost-finished handoffs as candidate process defects.
- Classify lessons narrowly: general -> Skill; MCP-specific -> Operating Guide; machine-specific -> local inventory/config; one-off -> stage evidence.
- User guidance that reveals a reusable operating principle is valid experience input.
- Use an approximately 20-minute soft stage budget INCLUDING closure/handoff. This is a heuristic, not a platform timeout.
- If implementation expansion threatens tests/docs/commit/verified handoff, split into a bounded sub-stage while preserving CURRENT/NEXT/AFTER_NEXT and one-owner scope.
- Collect stage-cost evidence so this heuristic can self-correct instead of hardcoding an unsupported duration limit.

## Safety
- Never copy secrets, OAuth DBs, passwords, tokens, cookies, private keys or machine-specific private state into Git.
- Do not reset/clean/force-push unrelated repositories.
- Keep existing working MCP/Funnel endpoints unchanged unless this stage explicitly owns them.
- One file has one writer; use worktrees for parallel writers.

## Closure contract
Before closing this stage:
1. finish owned implementation;
2. run narrow tests, then required full gates;
3. verify post-state and Git diff;
4. update all affected docs and decision/risk/experience records;
5. write the stage closure;
6. commit the stage;
7. generate the next prompt from the new verified HEAD;
8. validate prompt required markers + SOURCE_HEAD;
9. hash the exact prompt;
10. Playwright-submit the exact prompt in the already authenticated browser context;
11. verify sent user message + /c/ conversation + new assistant run;
12. write prompt SHA-256 / handoff receipt locally.

## Recursive continuation invariant
This handoff rule is recursive and MUST be inherited by every subsequent window:
- this window closes {spec.current_stage}, then hands off {spec.next_stage};
- the {spec.next_stage} window must, after its own verified closure, generate and submit a fresh prompt for its NEXT_STAGE;
- that following window must do the same for its own NEXT_STAGE, preserving CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE;
- every prompt is regenerated from that stage's newly committed HEAD and validated before submission;
- every handoff uses Playwright MCP and is successful only after sent-message + new-assistant-run verification;
- do not stop at a stage boundary merely to report progress;
- recursive continuation ends only after the planned final stage and Final Overall Acceptance are both CLOSED_LOCAL_VERIFIED.

## Automatic handoff contract
Automatic continuation is authorized.
After closure, use Playwright MCP with the logged-in ChatGPT browser state:
1. keep one MCP session and reuse the already authenticated browser context; do not create a fresh isolated profile merely to get a new conversation;
2. open a new ChatGPT tab/page, enumerate the tabs and explicitly select that new ChatGPT tab in the same MCP session; do not assume the extension focused it;
3. reacquire fresh DOM evidence from the selected tab and wait for the real active composer; an initial hidden hydration fallback textarea is not a valid target;
4. enter the exact validated prompt file and submit once;
5. verify the prompt appears as a sent user message containing SOURCE_HEAD;
6. verify the URL is /c/... and a new assistant run/response begins;
7. only then mark the handoff successful.
A populated textbox, click, navigation, or prompt file alone is NOT proof of handoff.

Continue Loop Engineering recursively until the full project and final overall acceptance are complete.
"""


def validate_handoff_prompt(
    text: str,
    *,
    expected_stage: str,
    expected_head: str,
    expected_next_stage: str | None = None,
    expected_after_next_stage: str | None = None,
) -> list[str]:
    errors: list[str] = []
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            errors.append(f"missing marker: {marker}")
    if f"CURRENT_STAGE = {expected_stage}" not in text:
        errors.append("CURRENT_STAGE mismatch")
    if f"SOURCE_HEAD = {expected_head}" not in text:
        errors.append("SOURCE_HEAD mismatch")
    if expected_next_stage is not None and f"NEXT_STAGE = {expected_next_stage}" not in text:
        errors.append("NEXT_STAGE mismatch")
    if (
        expected_after_next_stage is not None
        and f"AFTER_NEXT_STAGE = {expected_after_next_stage}" not in text
    ):
        errors.append("AFTER_NEXT_STAGE mismatch")
    if "Do not stop after reporting progress" not in text:
        errors.append("continuous-execution rule missing")
    if "new assistant run/response begins" not in text:
        errors.append("handoff verification rule missing")
    if "Execute -> Observe -> Diagnose -> Explore -> Compare -> Improve -> Verify -> Record -> Reuse" not in text:
        errors.append("self-evolving execution rule missing")
    if "20-minute soft stage budget" not in text:
        errors.append("soft stage budget rule missing")
    if "real active composer" not in text:
        errors.append("active-composer handoff rule missing")
    if "recursive continuation ends only after the planned final stage and Final Overall Acceptance" not in text:
        errors.append("recursive continuation invariant missing")
    return errors


def write_validated_prompt(path: Path, spec: HandoffSpec) -> str:
    text = build_handoff_prompt(spec)
    errors = validate_handoff_prompt(
        text,
        expected_stage=spec.current_stage,
        expected_head=spec.source_head,
        expected_next_stage=spec.next_stage,
        expected_after_next_stage=spec.after_next_stage,
    )
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_validated_prompt_from_plan(
    path: Path,
    plan_path: Path,
    *,
    source_head: str | None = None,
) -> str:
    plan = load_handoff_plan(plan_path)
    spec = plan.instantiate(source_head or current_head())
    return write_validated_prompt(path, spec)


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--stage")
    parser.add_argument("--next")
    parser.add_argument("--after-next")
    parser.add_argument("--objective")
    args = parser.parse_args(argv)
    if args.plan is not None:
        digest = write_validated_prompt_from_plan(args.path, args.plan)
    else:
        missing = [
            name
            for name, value in (
                ("--stage", args.stage),
                ("--next", args.next),
                ("--after-next", args.after_next),
                ("--objective", args.objective),
            )
            if not value
        ]
        if missing:
            parser.error("missing arguments without --plan: " + ", ".join(missing))
        spec = HandoffSpec(
            current_stage=args.stage,
            next_stage=args.next,
            after_next_stage=args.after_next,
            source_head=current_head(),
            stage_objective=args.objective,
            required_outputs=("stage implementation", "tests", "updated docs", "stage closure"),
            do_not_redo=("closed prior stages",),
        )
        digest = write_validated_prompt(args.path, spec)
    print(digest)
    return 0
