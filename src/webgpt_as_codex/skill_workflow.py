from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import resource_root, state_root, user_home

_CATEGORY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_ROUTE_RE = re.compile(r"\.\./\.\./([^/\\\s]+)/REFERENCE\.md")
_RUN_STATUSES = {"pending", "in_progress", "passed", "failed", "blocked", "skipped"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _is_link_like(path: Path) -> bool:
    raw = os.path.normcase(str(path.absolute()))
    resolved = os.path.normcase(str(path.resolve(strict=False)))
    return path.is_symlink() or raw != resolved


def _read_text(path: Path, *, limit: int = 65536) -> str:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _frontmatter_value(text: str, key: str) -> str | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:80]:
        if line.strip() == "---":
            break
        prefix = key + ":"
        if line.lower().startswith(prefix.lower()):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            return value or None
    return None


def _summary_from_markdown(text: str, fallback: str) -> tuple[str, str]:
    name = _frontmatter_value(text, "name")
    description = _frontmatter_value(text, "description")
    lines = text.splitlines()
    if not name:
        for line in lines:
            if line.startswith("# "):
                name = line[2:].strip()
                break
    if not description:
        after_heading = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                after_heading = True
                continue
            if after_heading and stripped and not stripped.startswith((">", "-", "*", "\x60")):
                description = stripped
                break
    return name or fallback, description or ""


class SkillWorkflowControlPlane:
    """Machine-local Skill inventory plus repository-owned Workflow registry.

    Repository SoT owns schemas and workflow definitions. Machine-local state owns
    classification/order overlays and workflow run evidence. Filesystem paths are
    never accepted directly from Manager requests; mutations resolve a known Skill
    ID to a previously discovered path.
    """

    def __init__(
        self,
        *,
        skill_roots: list[Path] | None = None,
        workflow_registry_path: Path | None = None,
        local_state_dir: Path | None = None,
    ) -> None:
        self._explicit_skill_roots = skill_roots
        self.workflow_registry_path = workflow_registry_path or (
            resource_root() / "skills" / "webgpt-as-codex" / "workflow-registry.json"
        )
        self.local_state_dir = local_state_dir or (state_root() / "skills")
        self.run_dir = (
            local_state_dir.parent / "workflow-runs"
            if local_state_dir
            else state_root() / "workflow-runs"
        )
        self._lock = threading.RLock()

    def _skill_roots(self) -> list[dict[str, Any]]:
        if self._explicit_skill_roots is not None:
            paths = list(self._explicit_skill_roots)
        else:
            override = os.getenv("WEBGPT_CODEX_SKILL_ROOTS")
            if override:
                paths = [
                    Path(item).expanduser()
                    for item in override.split(os.pathsep)
                    if item.strip()
                ]
            else:
                home = user_home()
                paths = [
                    home / ".agents" / "skills",
                    home / ".codex" / "skills",
                    resource_root() / "skills",
                ]
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for index, raw in enumerate(paths):
            path = raw.expanduser().resolve(strict=False)
            key = _path_key(path)
            if key in seen:
                continue
            seen.add(key)
            label = (
                "shared"
                if path.name == "skills" and path.parent.name == ".agents"
                else "codex"
                if path.name == "skills" and path.parent.name == ".codex"
                else "product"
                if _path_key(path) == _path_key(resource_root() / "skills")
                else f"custom-{index + 1}"
            )
            rows.append({"id": label, "path": path, "exists": path.is_dir()})
        return rows

    def _overlay_path(self) -> Path:
        return self.local_state_dir / "control-plane.json"

    def _load_overlay(self) -> dict[str, Any]:
        path = self._overlay_path()
        if not path.is_file():
            return {"schema_version": 1, "updated_at": None, "assignments": {}}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 1, "updated_at": None, "assignments": {}}
        if not isinstance(raw, dict):
            return {"schema_version": 1, "updated_at": None, "assignments": {}}
        assignments = raw.get("assignments")
        if not isinstance(assignments, dict):
            assignments = {}
        return {
            "schema_version": 1,
            "updated_at": raw.get("updated_at"),
            "assignments": assignments,
        }

    def _write_overlay(self, overlay: dict[str, Any]) -> None:
        self.local_state_dir.mkdir(parents=True, exist_ok=True)
        overlay = {
            "schema_version": 1,
            "updated_at": _utc_now(),
            "assignments": overlay.get("assignments") or {},
        }
        path = self._overlay_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(overlay, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)

    @staticmethod
    def _route_memberships(root: Path) -> dict[str, set[str]]:
        memberships: dict[str, set[str]] = {}
        if not root.is_dir():
            return memberships
        try:
            children = list(root.iterdir())
        except OSError:
            return memberships
        for child in children:
            route_file = child / "references" / "routes.md"
            if (
                not child.is_dir()
                or not child.name.startswith("category-")
                or not route_file.is_file()
            ):
                continue
            category = child.name.removeprefix("category-")
            text = _read_text(route_file)
            for match in _ROUTE_RE.finditer(text):
                memberships.setdefault(match.group(1), set()).add(category)
        return memberships

    def skill_snapshot(self) -> dict[str, Any]:
        with self._lock:
            roots = self._skill_roots()
            overlay = self._load_overlay()
            memberships: dict[str, set[str]] = {}
            for root in roots:
                for name, categories in self._route_memberships(root["path"]).items():
                    memberships.setdefault(name, set()).update(categories)

            aggregated: dict[str, dict[str, Any]] = {}
            duplicate_counts: dict[str, int] = {}
            for root in roots:
                path: Path = root["path"]
                if not path.is_dir():
                    continue
                try:
                    children = sorted(
                        path.iterdir(),
                        key=lambda item: item.name.lower(),
                    )
                except OSError:
                    continue
                for child in children:
                    if not child.is_dir():
                        continue
                    skill_md = child / "SKILL.md"
                    reference_md = child / "REFERENCE.md"
                    if not skill_md.is_file() and not reference_md.is_file():
                        continue
                    resolved = child.resolve(strict=False)
                    identity = _path_key(resolved)
                    entry = skill_md if skill_md.is_file() else reference_md
                    markdown = _read_text(entry, limit=32768)
                    display_name, description = _summary_from_markdown(
                        markdown,
                        child.name,
                    )
                    if identity not in aggregated:
                        base_id = child.name
                        count = duplicate_counts.get(base_id, 0)
                        duplicate_counts[base_id] = count + 1
                        skill_id = (
                            base_id
                            if count == 0
                            else f"{base_id}@{root['id']}"
                        )
                        kind = (
                            "category-router"
                            if child.name.startswith("category-") and skill_md.is_file()
                            else "reference-skill"
                            if reference_md.is_file() and not skill_md.is_file()
                            else "skill"
                        )
                        aggregated[identity] = {
                            "id": skill_id,
                            "slug": child.name,
                            "name": display_name,
                            "description": description,
                            "kind": kind,
                            "entrypoint": entry.name,
                            "path": str(child),
                            "resolved_path": str(resolved),
                            "is_link": _is_link_like(child),
                            "locations": [],
                            "router_categories": sorted(
                                memberships.get(child.name, set())
                            ),
                        }
                    aggregated[identity]["locations"].append(
                        {
                            "root_id": root["id"],
                            "path": str(child),
                            "exists": child.exists(),
                            "is_link": child.is_symlink()
                            or _path_key(child) != identity,
                        }
                    )

            skills = list(aggregated.values())
            assignments = overlay.get("assignments") or {}
            categories: set[str] = set()
            for skill in skills:
                assignment = assignments.get(skill["id"])
                if not isinstance(assignment, dict):
                    assignment = assignments.get(skill["slug"])
                if not isinstance(assignment, dict):
                    assignment = {}
                explicit_category = assignment.get("category")
                if explicit_category == "unclassified":
                    explicit_category = None
                routed = skill.get("router_categories") or []
                if explicit_category:
                    category = explicit_category
                    category_source = "machine-overlay"
                elif len(routed) == 1:
                    category = routed[0]
                    category_source = "category-router"
                elif skill["kind"] == "category-router":
                    category = skill["slug"].removeprefix("category-")
                    category_source = "self-router"
                else:
                    category = "unclassified"
                    category_source = "unclassified"
                position = assignment.get("position")
                skill["category"] = category
                skill["category_source"] = category_source
                skill["position"] = (
                    position
                    if isinstance(position, int) and position >= 0
                    else None
                )
                categories.add(category)

            skills.sort(
                key=lambda row: (
                    row["category"],
                    row["position"]
                    if row["position"] is not None
                    else 1_000_000,
                    row["name"].lower(),
                )
            )
            root_rows = [
                {
                    "id": row["id"],
                    "path": str(row["path"]),
                    "exists": row["exists"],
                }
                for row in roots
            ]
            return {
                "schema_version": 1,
                "updated_at": overlay.get("updated_at"),
                "roots": root_rows,
                "categories": sorted(categories),
                "skills": skills,
            }

    def _require_skill(self, skill_id: str) -> dict[str, Any]:
        if not isinstance(skill_id, str) or not skill_id.strip():
            raise ValueError("skill id required")
        for skill in self.skill_snapshot()["skills"]:
            if skill["id"] == skill_id or skill["slug"] == skill_id:
                return skill
        raise KeyError(skill_id)

    def move_skill(
        self,
        skill_id: str,
        category: str,
        position: int | None = None,
    ) -> dict[str, Any]:
        category = str(category or "").strip().lower()
        if category != "unclassified" and not _CATEGORY_RE.fullmatch(category):
            raise ValueError("invalid category")
        if position is not None and (
            not isinstance(position, int) or position < 0 or position > 100000
        ):
            raise ValueError("invalid position")
        with self._lock:
            skill = self._require_skill(skill_id)
            overlay = self._load_overlay()
            assignments = overlay.setdefault("assignments", {})
            assignments[skill["id"]] = {
                "category": category,
                "position": position,
            }
            self._write_overlay(overlay)
            return {
                "ok": True,
                "skill_id": skill["id"],
                "category": category,
                "position": position,
                "move_kind": "logical-category",
                "filesystem_changed": False,
            }

    def open_skill_location(self, skill_id: str) -> dict[str, Any]:
        skill = self._require_skill(skill_id)
        path = Path(skill["path"])
        if not path.is_dir():
            raise FileNotFoundError(path)
        if os.name != "nt":
            return {
                "ok": False,
                "status": "unsupported-platform",
                "skill_id": skill["id"],
            }
        subprocess.Popen(
            ["explorer.exe", str(path)],
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return {
            "ok": True,
            "status": "opened",
            "skill_id": skill["id"],
        }

    def workflow_catalog(self) -> dict[str, Any]:
        try:
            raw = json.loads(
                self.workflow_registry_path.read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            return {
                "schema_version": 1,
                "workflows": [],
                "error": "workflow-registry-missing",
            }
        except (OSError, json.JSONDecodeError):
            return {
                "schema_version": 1,
                "workflows": [],
                "error": "workflow-registry-invalid",
            }
        if not isinstance(raw, dict) or not isinstance(raw.get("workflows"), list):
            return {
                "schema_version": 1,
                "workflows": [],
                "error": "workflow-registry-invalid",
            }
        return raw

    @staticmethod
    def _condition_matches(
        condition: Any,
        context: dict[str, Any],
    ) -> bool:
        if condition in (None, "", []):
            return True
        if isinstance(condition, str):
            return bool(context.get(condition))
        if isinstance(condition, dict):
            any_flags = condition.get("any")
            all_flags = condition.get("all")
            none_flags = condition.get("none")
            if (
                isinstance(any_flags, list)
                and any_flags
                and not any(bool(context.get(flag)) for flag in any_flags)
            ):
                return False
            if (
                isinstance(all_flags, list)
                and not all(bool(context.get(flag)) for flag in all_flags)
            ):
                return False
            if (
                isinstance(none_flags, list)
                and any(bool(context.get(flag)) for flag in none_flags)
            ):
                return False
            return True
        return False

    def plan_workflow(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = dict(context or {})
        catalog = self.workflow_catalog()
        workflow = next(
            (
                item
                for item in catalog.get("workflows", [])
                if item.get("id") == workflow_id
            ),
            None,
        )
        if workflow is None:
            raise KeyError(workflow_id)

        snapshot = self.skill_snapshot()
        by_slug = {skill["slug"]: skill for skill in snapshot["skills"]}
        stages: list[dict[str, Any]] = []
        for raw_stage in workflow.get("stages", []):
            if not isinstance(raw_stage, dict):
                continue
            if not self._condition_matches(raw_stage.get("when"), context):
                stages.append(
                    {
                        "id": raw_stage.get("id"),
                        "title": raw_stage.get("title"),
                        "status": "skipped",
                        "skills": [],
                        "gate": raw_stage.get("gate"),
                    }
                )
                continue

            resolved_skills: list[dict[str, Any]] = []
            missing_required = False
            missing_optional = False
            for selector in raw_stage.get("skills", []):
                if isinstance(selector, str):
                    selector = {"name": selector, "required": True}
                if not isinstance(selector, dict):
                    continue
                if not self._condition_matches(
                    selector.get("when"),
                    context,
                ):
                    continue
                name = selector.get("name")
                required = selector.get("required", True) is not False
                skill = by_slug.get(name)
                available = skill is not None
                if required and not available:
                    missing_required = True
                if not required and not available:
                    missing_optional = True
                resolved_skills.append(
                    {
                        "name": name,
                        "required": required,
                        "available": available,
                        "skill_id": skill.get("id") if skill else None,
                        "category": skill.get("category") if skill else None,
                    }
                )
            status = (
                "blocked"
                if missing_required
                else "degraded"
                if missing_optional
                else "ready"
            )
            stages.append(
                {
                    "id": raw_stage.get("id"),
                    "title": raw_stage.get("title"),
                    "status": status,
                    "skills": resolved_skills,
                    "outputs": raw_stage.get("outputs") or [],
                    "gate": raw_stage.get("gate"),
                    "supporting_workflows": raw_stage.get(
                        "supporting_workflows"
                    )
                    or [],
                }
            )
        return {
            "workflow_id": workflow_id,
            "title": workflow.get("title"),
            "description": workflow.get("description"),
            "context": context,
            "stages": stages,
            "blocked": any(
                stage["status"] == "blocked"
                for stage in stages
            ),
            "generated_at": _utc_now(),
        }

    def _run_path(self, run_id: str) -> Path:
        if not isinstance(run_id, str) or not re.fullmatch(
            r"[A-Za-z0-9._-]{1,96}",
            run_id,
        ):
            raise ValueError("invalid run id")
        return self.run_dir / f"{run_id}.json"

    def _write_run(self, payload: dict[str, Any]) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        path = self._run_path(payload["run_id"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)

    def start_run(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            plan = self.plan_workflow(workflow_id, context)
            run_id = (
                datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                + "-"
                + secrets.token_hex(4)
            )
            stages = []
            current_stage = None
            run_status = "active"
            for planned in plan["stages"]:
                status = (
                    "skipped"
                    if planned["status"] == "skipped"
                    else "pending"
                )
                if current_stage is None and status == "pending":
                    current_stage = planned["id"]
                    if planned["status"] == "blocked":
                        status = "blocked"
                        run_status = "blocked"
                    else:
                        status = "in_progress"
                stages.append(
                    {
                        "id": planned["id"],
                        "title": planned.get("title"),
                        "planner_status": planned["status"],
                        "status": status,
                        "skills": planned.get("skills") or [],
                        "gate": planned.get("gate"),
                        "evidence": [],
                    }
                )
            if current_stage is None:
                run_status = "complete"
            payload = {
                "schema_version": 1,
                "run_id": run_id,
                "workflow_id": workflow_id,
                "title": plan.get("title"),
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
                "current_stage": current_stage,
                "status": run_status,
                "context": plan["context"],
                "stages": stages,
            }
            self._write_run(payload)
            return payload

    def list_runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self.run_dir.is_dir():
            return []
        rows: list[dict[str, Any]] = []
        paths = sorted(
            self.run_dir.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in paths:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                rows.append(data)
            if len(rows) >= max(1, min(limit, 200)):
                break
        return rows

    def transition_run(
        self,
        run_id: str,
        stage_id: str,
        status: str,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        if status not in _RUN_STATUSES:
            raise ValueError("invalid run status")
        with self._lock:
            path = self._run_path(run_id)
            data = json.loads(path.read_text(encoding="utf-8"))
            stages = data.get("stages") or []
            index = next(
                (
                    i
                    for i, row in enumerate(stages)
                    if row.get("id") == stage_id
                ),
                None,
            )
            if index is None:
                raise KeyError(stage_id)
            row = stages[index]
            row["status"] = status
            if evidence:
                current_evidence = row.setdefault("evidence", [])
                current_evidence.append(
                    {
                        "at": _utc_now(),
                        "text": str(evidence)[:2000],
                    }
                )
            current_stage = stage_id
            run_status = "active"
            if status in {"passed", "skipped"}:
                current_stage = None
                for next_row in stages[index + 1 :]:
                    if next_row.get("status") == "pending":
                        current_stage = next_row.get("id")
                        if next_row.get("planner_status") == "blocked":
                            next_row["status"] = "blocked"
                            run_status = "blocked"
                        else:
                            next_row["status"] = "in_progress"
                        break
                if current_stage is None:
                    run_status = "complete"
            elif status in {"failed", "blocked"}:
                run_status = status
            data["current_stage"] = current_stage
            data["status"] = run_status
            data["updated_at"] = _utc_now()
            self._write_run(data)
            return data
