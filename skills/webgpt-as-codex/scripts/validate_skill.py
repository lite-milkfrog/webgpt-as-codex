from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[1]
REQUIRED = [
    "SKILL.md",
    "session-bootstrap.md",
    "product-contract.md",
    "routing.md",
    "permissions.md",
    "validation.md",
    "maintenance.md",
    "gpt-web-port.md",
    "experience-ledger.md",
    "add-mcp.md",
    "loop-evidence.md",
    "mcp-operating-guide.md",
    "mcp-guides/coding-tools.md",
    "mcp-guides/serena.md",
    "mcp-guides/remote-desktop-commander.md",
    "workflows/coding.md",
    "workflows/browser.md",
    "workflows/desktop.md",
    "workflows/windows-gui-visual-calibration.md",
    "workflows/files.md",
    "workflows/cross-tool.md",
    "workflows/loop-engineering.md",
    "workflows/handoff-template.md",
    "workflows/parallel-agent-orchestration.md",
    "workflows/parallel-agent-contracts.md",
    "workflows/WORKFLOW-SCHEMA.md",
    "workflow-registry.json",
    "evals/scenarios.json",
    "evals/parallel-orchestration-scenarios.json",
    "schemas/parallel-agent/stage-manifest.schema.json",
    "schemas/parallel-agent/dispatch-receipt.schema.json",
    "schemas/parallel-agent/handoff.schema.json",
    "schemas/parallel-agent/build-plan.schema.json",
    "manifest.json",
    "CHANGELOG.md",
    "scripts/mcp-http-client.mjs",
    "scripts/chatgpt-loop-handoff.mjs",
]

errors: list[str] = []

for rel in REQUIRED:
    p = ROOT / rel
    if not p.exists():
        errors.append(f"missing: {rel}")
    elif p.stat().st_size == 0:
        errors.append(f"empty: {rel}")

skill = (ROOT / "SKILL.md").read_text(encoding="utf-8") if (ROOT / "SKILL.md").exists() else ""
if not skill.startswith("---\n"):
    errors.append("SKILL.md missing YAML frontmatter")
for field in ("name:", "description:", "version:"):
    if field not in skill:
        errors.append(f"SKILL.md missing field: {field}")

# Validate local markdown links to .md files.
for md in ROOT.rglob("*.md"):
    if "state" in md.relative_to(ROOT).parts:
        continue
    if md.name in {"experience-ledger.md", "environment.local.md", "MCP-SKILLS-INVENTORY.md"}:
        # Ledger references and machine-local overlays may name project/workspace
        # resources that intentionally do not exist in the portable Skill tree.
        continue
    text = md.read_text(encoding="utf-8")
    for target in re.findall(r"`([^`]+\.md)`", text):
        if target.startswith("http"):
            continue
        if Path(target).name in {
            "environment.local.md",
            "MCP-SKILLS-INVENTORY.md",
            "MCP-SKILLS-INVENTORY.json",
        }:
            continue
        target = target.removeprefix(".skills/webgpt-as-codex/")
        candidate = (md.parent / target).resolve()
        if not candidate.exists():
            # Also allow paths relative to skill root.
            candidate = (ROOT / target).resolve()
        if not candidate.exists():
            # Local environment docs may intentionally point at workspace-local tool docs
            # such as .tools/playwright-mcp/README-local.md.
            candidate = (WORKSPACE_ROOT / target).resolve()
        if not candidate.exists():
            errors.append(f"broken md reference in {md.relative_to(ROOT)}: {target}")

try:
    scenarios = json.loads((ROOT / "evals/scenarios.json").read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    errors.append(f"invalid scenarios.json: {exc}")
    scenarios = []

required_keys = {"id", "prompt", "should_trigger", "primary", "secondary", "permission"}
ids = set()
for item in scenarios:
    missing = required_keys - set(item)
    if missing:
        errors.append(f"scenario missing keys {sorted(missing)}: {item.get('id', '?')}")
    sid = item.get("id")
    if sid in ids:
        errors.append(f"duplicate scenario id: {sid}")
    ids.add(sid)

if len(scenarios) < 8:
    errors.append("too few eval scenarios")
if not any(not s.get("should_trigger", True) for s in scenarios):
    errors.append("no negative trigger scenario")
if not any(s.get("permission") == "P3" for s in scenarios):
    errors.append("no P3 scenario")
if not any(s.get("primary") == "Playwright" for s in scenarios):
    errors.append("no Playwright scenario")
if not any(s.get("primary") == "Windows-MCP" for s in scenarios):
    errors.append("no Windows-MCP scenario")
if not any("Loop Engineering" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no Loop Engineering scenario")
if not any("先查后态" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no post-state recovery scenario")
if not any("handoff-template.md" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no Zero-Guess handoff-template scenario")
if not any("worktree" in (s.get("expected_behavior") or "") and "writer" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no single-writer worktree scenario")

try:
    parallel_scenarios = json.loads(
        (ROOT / "evals/parallel-orchestration-scenarios.json").read_text(encoding="utf-8")
    )
except (OSError, json.JSONDecodeError) as exc:
    errors.append(f"invalid parallel-orchestration-scenarios.json: {exc}")
    parallel_scenarios = []

parallel_ids = set()
for item in parallel_scenarios:
    if not {"id", "prompt", "expected_behavior"}.issubset(item):
        errors.append(f"parallel scenario missing keys: {item.get('id', '?')}")
    sid = item.get("id")
    if sid in parallel_ids:
        errors.append(f"duplicate parallel scenario id: {sid}")
    parallel_ids.add(sid)

for required_id in ("P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"):
    if required_id not in parallel_ids:
        errors.append(f"missing parallel orchestration scenario: {required_id}")

parallel_schema_paths = (
    "schemas/parallel-agent/stage-manifest.schema.json",
    "schemas/parallel-agent/dispatch-receipt.schema.json",
    "schemas/parallel-agent/handoff.schema.json",
    "schemas/parallel-agent/build-plan.schema.json",
)
for rel in parallel_schema_paths:
    try:
        schema = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid parallel schema {rel}: {exc}")
        continue
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append(f"parallel schema missing draft marker: {rel}")
    if schema.get("type") != "object":
        errors.append(f"parallel schema root is not object: {rel}")

parallel_workflow = (
    (ROOT / "workflows/parallel-agent-orchestration.md").read_text(encoding="utf-8")
    if (ROOT / "workflows/parallel-agent-orchestration.md").exists()
    else ""
)
for marker in (
    "WAITING_FOR_CHILDREN",
    "MANUAL_FANIN_RESUME",
    "DISPATCH_ATTEMPTED",
    "B90-BUILD",
    "B99-AUDIT",
    "HANDOFF.json",
):
    if marker not in parallel_workflow:
        errors.append(f"parallel orchestration workflow missing marker: {marker}")

try:
    workflow_registry = json.loads((ROOT / "workflow-registry.json").read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    errors.append(f"invalid workflow-registry.json: {exc}")
    workflow_registry = {}
if not any(
    workflow.get("id") == "parallel-agent-orchestration"
    for workflow in workflow_registry.get("workflows", [])
):
    errors.append("workflow registry missing parallel-agent-orchestration")

try:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    errors.append(f"invalid manifest.json: {exc}")
    manifest = {}

if manifest.get("name") != "webgpt-as-codex":
    errors.append("manifest name mismatch")
if manifest.get("design") != "direct-mcp-with-soft-routing":
    errors.append("manifest design mismatch")
version_match = re.search(r"(?m)^\s*version:\s*([^\s]+)\s*$", skill)
skill_version = version_match.group(1) if version_match else None
if manifest.get("version") != skill_version:
    errors.append("manifest version mismatch")
roles = manifest.get("roles", {})
for required_role in ("code_semantics", "code_execution", "filesystem_terminal", "browser_webapp", "windows_gui"):
    if required_role not in roles:
        errors.append(f"manifest missing role: {required_role}")

capabilities = manifest.get("capabilities", {})
for required_capability in ("adaptive_recovery", "loop_engineering", "zero_guess_handoff", "experience_absorption", "single_writer_per_worktree", "local_mcp_locator_recovery", "session_scoped_mcp_reconnect", "docs_before_prompt_barrier", "active_recovery_before_pause", "visual_coordinate_calibration", "preserve_preexisting_windows", "gui_action_observer_failure_split", "native_gui_first", "multi_layer_dialog_tracking", "mcp_concurrency_state_isolation", "release_local_portable_sync", "full_experience_ledger", "rdc_four_layer_health", "handoff_prompt_hash_transaction", "durable_handoff_receipt", "handoff_write_ahead_attempt_receipt", "single_handoff_mutation_owner", "mandatory_session_skill_bootstrap", "workflow_stage_selective_skill_loading", "bundled_derivative_sources"):
    if not capabilities.get(required_capability):
        errors.append(f"manifest missing capability: {required_capability}")

if "WAC Session Bootstrap — 强制" not in skill:
    errors.append("canonical Skill does not declare mandatory WAC session bootstrap")

if not any("EXPERIENCE_ABSORPTION" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no experience absorption scenario")
if not any("NOT_EXPOSED" in (s.get("expected_behavior") or "") and "NOT_RUNNING" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no local MCP rediscovery scenario")
if not any("session-scoped" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no session-scoped MCP scenario")
if not any("SHA-256" in (s.get("expected_behavior") or "") and "DOM activation" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no long-prompt handoff recovery scenario")
if not any("ACTIVE_RECOVERY" in (s.get("expected_behavior") or "") and "PAUSED_EXTERNAL_BLOCKER" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no active-recovery-before-pause scenario")
if not any("docs" in (s.get("expected_behavior") or "").lower() and "next prompt" in (s.get("expected_behavior") or "").lower() for s in scenarios):
    errors.append("no docs-before-prompt scenario")
if not any("OBSERVER_FAILURE" in (s.get("expected_behavior") or "") and "ACTION_FAILURE" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no GUI observer-vs-action failure scenario")
if not any("原生" in (s.get("expected_behavior") or "") and "workaround" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no native-GUI-before-workaround scenario")
if not any("RDC_EXECUTION_PLANE" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no RDC execution-plane verification scenario")
if not any("release/local portable drift" in (s.get("expected_behavior") or "") for s in scenarios):
    errors.append("no release/local portable sync scenario")
if "R56" not in ids:
    errors.append("no exact-prompt handoff transaction scenario")
if not any(
    "whitespace-normalized SHA-256" in (s.get("expected_behavior") or "")
    and "SUBMITTED" in (s.get("expected_behavior") or "")
    and "single mutation owner" in (s.get("expected_behavior") or "")
    for s in scenarios
):
    errors.append("no durable exact-prompt handoff recovery scenario")

handoff_helper_path = ROOT / "scripts/chatgpt-loop-handoff.mjs"
handoff_helper = (
    handoff_helper_path.read_text(encoding="utf-8")
    if handoff_helper_path.exists()
    else ""
)
for marker in (
    "classifyPromptState",
    "lastUserHash",
    "receiptPath",
    "leaseToken",
    "SUBMIT_ATTEMPTED",
    "SUBMITTED",
):
    if marker not in handoff_helper:
        errors.append(f"handoff helper missing transaction marker: {marker}")

if "\\${" in handoff_helper:
    errors.append("handoff helper contains escaped template interpolation")
if "\\`" in handoff_helper:
    errors.append("handoff helper contains escaped template-literal delimiter")

if handoff_helper.count("replace(/\\\\s+/g, '')") < 2:
    errors.append("handoff helper browser hash normalization is over/under escaped")

if errors:
    print("VALIDATION_FAILED")
    for e in errors:
        print(f"- {e}")
    sys.exit(1)

print("VALIDATION_OK")
print(f"files={len(REQUIRED)} scenarios={len(scenarios)}")
