from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import resource_root, state_root, user_home

_CATEGORY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_ROUTE_RE = re.compile(r"\.\./\.\./([^/\\\s]+)/(?:REFERENCE|SKILL)\.md")
_RUN_STATUSES = {"pending", "in_progress", "passed", "failed", "blocked", "skipped"}
_RUN_TRANSITION_STATUSES = {"in_progress", "passed", "failed", "blocked", "skipped"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


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
            memberships_by_root = {
                _path_key(root["path"]): self._route_memberships(root["path"])
                for root in roots
            }

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
                    root_memberships = memberships_by_root.get(_path_key(path), {})
                    local_router_categories = set(
                        root_memberships.get(child.name, set())
                    )
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
                            "router_categories": sorted(local_router_categories),
                        }
                    else:
                        combined_categories = set(
                            aggregated[identity].get("router_categories") or []
                        )
                        combined_categories.update(local_router_categories)
                        aggregated[identity]["router_categories"] = sorted(
                            combined_categories
                        )
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
            slug_counts: dict[str, int] = {}
            for skill in skills:
                slug_counts[skill["slug"]] = slug_counts.get(skill["slug"], 0) + 1
            for skill in skills:
                if slug_counts.get(skill["slug"], 0) > 1:
                    primary_root = (
                        skill["locations"][0].get("root_id")
                        if skill.get("locations")
                        else "unknown"
                    )
                    skill["id"] = f"{skill['slug']}@{primary_root}"

            usage: dict[str, list[dict[str, Any]]] = {}
            catalog = self.workflow_catalog()
            for workflow in catalog.get("workflows", []):
                if not isinstance(workflow, dict):
                    continue
                for stage in workflow.get("stages", []):
                    if not isinstance(stage, dict):
                        continue
                    for selector in stage.get("skills", []):
                        if isinstance(selector, str):
                            name = selector
                            required = True
                            condition = None
                        elif isinstance(selector, dict):
                            name = selector.get("name")
                            required = selector.get("required", True) is not False
                            condition = selector.get("when")
                        else:
                            continue
                        if not isinstance(name, str):
                            continue
                        usage.setdefault(name, []).append(
                            {
                                "workflow_id": workflow.get("id"),
                                "workflow_title": workflow.get("title"),
                                "stage_id": stage.get("id"),
                                "stage_title": stage.get("title"),
                                "required": required,
                                "when": condition,
                            }
                        )

            assignments = overlay.get("assignments") or {}
            categories: set[str] = set()
            for skill in skills:
                assignment = assignments.get(skill["id"])
                if not isinstance(assignment, dict):
                    assignment = assignments.get(skill["slug"])
                if not isinstance(assignment, dict):
                    assignment = {}
                explicit_category = assignment.get("category")
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
                skill["workflow_usage"] = usage.get(skill["slug"], [])
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
        skills = self.skill_snapshot()["skills"]
        exact = [skill for skill in skills if skill["id"] == skill_id]
        if len(exact) == 1:
            return exact[0]
        slug_matches = [skill for skill in skills if skill["slug"] == skill_id]
        if len(slug_matches) == 1:
            return slug_matches[0]
        if len(slug_matches) > 1:
            raise ValueError("ambiguous Skill slug; use stable Skill id")
        raise KeyError(skill_id)

    def move_skill(
        self,
        skill_id: str,
        category: str,
        position: int | None = None,
    ) -> dict[str, Any]:
        category = str(category or "").strip().lower()
        if category != "inherit" and not _CATEGORY_RE.fullmatch(category):
            raise ValueError("invalid category")
        if position is not None and (
            not isinstance(position, int) or position < 0 or position > 100000
        ):
            raise ValueError("invalid position")
        with self._lock:
            skill = self._require_skill(skill_id)
            overlay = self._load_overlay()
            assignments = overlay.setdefault("assignments", {})
            if category == "inherit":
                assignments.pop(skill["id"], None)
                effective_category = None
            else:
                assignments[skill["id"]] = {
                    "category": category,
                    "position": position,
                }
                effective_category = category
            self._write_overlay(overlay)
            return {
                "ok": True,
                "skill_id": skill["id"],
                "category": effective_category,
                "position": None if category == "inherit" else position,
                "move_kind": "logical-category",
                "filesystem_changed": False,
                "inherit_router_category": category == "inherit",
            }

    def _root_by_id(self, root_id: str) -> dict[str, Any]:
        matches = [root for root in self._skill_roots() if root["id"] == root_id]
        if len(matches) != 1:
            raise KeyError(root_id)
        return matches[0]

    @staticmethod
    def _route_lines_for_skill(route_file: Path, slug: str) -> list[str]:
        if not route_file.is_file():
            return []
        text = route_file.read_text(encoding="utf-8")
        marker_reference = f"../../{slug}/REFERENCE.md"
        marker_skill = f"../../{slug}/SKILL.md"
        return [
            line
            for line in text.splitlines()
            if marker_reference in line or marker_skill in line
        ]

    @staticmethod
    def _write_text_atomic(path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def plan_relocation(self, skill_id: str, target_root_id: str) -> dict[str, Any]:
        with self._lock:
            skill = self._require_skill(skill_id)
            if skill["kind"] == "category-router":
                raise ValueError("category routers cannot be physically relocated")
            if skill.get("is_link"):
                raise ValueError("linked or junction Skills cannot be physically relocated")
            if len(skill.get("locations") or []) != 1:
                raise ValueError("Skill has aliases or duplicate locations; relocation is ambiguous")

            location = skill["locations"][0]
            source_root = self._root_by_id(str(location.get("root_id") or ""))
            target_root = self._root_by_id(target_root_id)
            source_root_path = Path(source_root["path"])
            target_root_path = Path(target_root["path"])
            source = Path(skill["path"])
            destination = target_root_path / skill["slug"]

            if _path_key(source_root_path) == _path_key(target_root_path):
                raise ValueError("source and target Skill roots are the same")
            if not source.is_dir():
                raise FileNotFoundError(source)
            if not target_root_path.is_dir():
                raise FileNotFoundError(target_root_path)

            duplicates = [
                row
                for row in self.skill_snapshot()["skills"]
                if row["slug"] == skill["slug"] and row["path"] != skill["path"]
            ]
            if duplicates:
                raise ValueError("duplicate Skill slug exists; relocation is ambiguous")
            if destination.exists():
                raise FileExistsError(destination)

            route_changes: list[dict[str, Any]] = []
            for category in skill.get("router_categories") or []:
                source_route = (
                    source_root_path
                    / f"category-{category}"
                    / "references"
                    / "routes.md"
                )
                target_route = (
                    target_root_path
                    / f"category-{category}"
                    / "references"
                    / "routes.md"
                )
                lines = self._route_lines_for_skill(source_route, skill["slug"])
                if not lines:
                    continue
                if not target_route.is_file():
                    return {
                        "ok": False,
                        "status": "blocked",
                        "reason": "target-category-router-missing",
                        "skill_id": skill["id"],
                        "target_root_id": target_root_id,
                        "missing_category": category,
                        "source": str(source),
                        "destination": str(destination),
                    }
                route_changes.append(
                    {
                        "category": category,
                        "source_route": str(source_route),
                        "target_route": str(target_route),
                        "lines": lines,
                    }
                )

            return {
                "ok": True,
                "status": "ready",
                "skill_id": skill["id"],
                "slug": skill["slug"],
                "source_root_id": source_root["id"],
                "target_root_id": target_root["id"],
                "source": str(source),
                "destination": str(destination),
                "entrypoint": skill["entrypoint"],
                "route_changes": route_changes,
                "filesystem_changed": False,
            }

    def relocate_skill(self, skill_id: str, target_root_id: str) -> dict[str, Any]:
        with self._lock:
            plan = self.plan_relocation(skill_id, target_root_id)
            if not plan.get("ok"):
                return plan

            source = Path(plan["source"])
            destination = Path(plan["destination"])
            route_backups: dict[Path, str] = {}
            overlay_before = self._load_overlay()
            moved = False
            try:
                for change in plan["route_changes"]:
                    for key in ("source_route", "target_route"):
                        path = Path(change[key])
                        if path not in route_backups:
                            route_backups[path] = path.read_text(encoding="utf-8")

                shutil.move(str(source), str(destination))
                moved = True

                for change in plan["route_changes"]:
                    source_route = Path(change["source_route"])
                    target_route = Path(change["target_route"])
                    lines_to_move = set(change["lines"])

                    source_lines = source_route.read_text(encoding="utf-8").splitlines()
                    source_text = "\n".join(
                        line for line in source_lines if line not in lines_to_move
                    )
                    if source_text:
                        source_text += "\n"
                    self._write_text_atomic(source_route, source_text)

                    target_text = target_route.read_text(encoding="utf-8")
                    target_lines = target_text.splitlines()
                    for line in change["lines"]:
                        if line not in target_lines:
                            target_lines.append(line)
                    new_target = "\n".join(target_lines)
                    if new_target:
                        new_target += "\n"
                    self._write_text_atomic(target_route, new_target)

                entrypoint = destination / str(plan["entrypoint"])
                if not entrypoint.is_file():
                    raise RuntimeError("relocated Skill entrypoint missing")

                snapshot = self.skill_snapshot()
                relocated = [
                    row
                    for row in snapshot["skills"]
                    if _path_key(Path(row["path"])) == _path_key(destination)
                ]
                if len(relocated) != 1:
                    raise RuntimeError("relocated Skill not discoverable")

                routed = set(relocated[0].get("router_categories") or [])
                expected = {change["category"] for change in plan["route_changes"]}
                if not expected.issubset(routed):
                    raise RuntimeError("relocated Skill category routes did not validate")

                return {
                    **plan,
                    "ok": True,
                    "status": "relocated",
                    "skill_id": relocated[0]["id"],
                    "filesystem_changed": True,
                }
            except Exception:
                for path, text in route_backups.items():
                    try:
                        self._write_text_atomic(path, text)
                    except OSError:
                        pass
                if moved and destination.exists() and not source.exists():
                    try:
                        shutil.move(str(destination), str(source))
                    except OSError:
                        pass
                try:
                    self._write_overlay(overlay_before)
                except OSError:
                    pass
                raise

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

    @staticmethod
    def _validate_condition(condition: Any, path: str) -> list[str]:
        if condition in (None, "", []):
            return []
        if isinstance(condition, str):
            return [] if _CATEGORY_RE.fullmatch(condition) else [f"{path}: invalid flag"]
        if not isinstance(condition, dict):
            return [f"{path}: condition must be a flag or object"]
        errors: list[str] = []
        unknown = sorted(set(condition) - {"all", "any", "none"})
        if unknown:
            errors.append(f"{path}: unsupported condition keys {unknown}")
        for key in ("all", "any", "none"):
            value = condition.get(key)
            if value is None:
                continue
            if not isinstance(value, list) or not all(
                isinstance(flag, str) and _CATEGORY_RE.fullmatch(flag)
                for flag in value
            ):
                errors.append(f"{path}.{key}: expected flag list")
        return errors

    @classmethod
    def _validate_workflow_registry(cls, raw: Any) -> list[str]:
        if not isinstance(raw, dict):
            return ["registry: expected object"]
        errors: list[str] = []
        if raw.get("schema_version") != 1:
            errors.append("registry.schema_version: expected 1")
        workflows = raw.get("workflows")
        if not isinstance(workflows, list):
            return errors + ["registry.workflows: expected array"]
        seen_workflows: set[str] = set()
        for wi, workflow in enumerate(workflows):
            base = f"workflows[{wi}]"
            if not isinstance(workflow, dict):
                errors.append(f"{base}: expected object")
                continue
            workflow_id = workflow.get("id")
            if not isinstance(workflow_id, str) or not _CATEGORY_RE.fullmatch(workflow_id):
                errors.append(f"{base}.id: invalid workflow id")
            elif workflow_id in seen_workflows:
                errors.append(f"{base}.id: duplicate workflow id")
            else:
                seen_workflows.add(workflow_id)
            if not isinstance(workflow.get("title"), str) or not workflow.get("title"):
                errors.append(f"{base}.title: required")
            stages = workflow.get("stages")
            if not isinstance(stages, list) or not stages:
                errors.append(f"{base}.stages: non-empty array required")
                continue
            seen_stages: set[str] = set()
            for si, stage in enumerate(stages):
                stage_path = f"{base}.stages[{si}]"
                if not isinstance(stage, dict):
                    errors.append(f"{stage_path}: expected object")
                    continue
                stage_id = stage.get("id")
                if not isinstance(stage_id, str) or not _CATEGORY_RE.fullmatch(stage_id):
                    errors.append(f"{stage_path}.id: invalid stage id")
                elif stage_id in seen_stages:
                    errors.append(f"{stage_path}.id: duplicate stage id")
                else:
                    seen_stages.add(stage_id)
                if not isinstance(stage.get("title"), str) or not stage.get("title"):
                    errors.append(f"{stage_path}.title: required")
                errors.extend(
                    cls._validate_condition(stage.get("when"), f"{stage_path}.when")
                )
                selectors = stage.get("skills", [])
                if not isinstance(selectors, list):
                    errors.append(f"{stage_path}.skills: expected array")
                    continue
                for ki, selector in enumerate(selectors):
                    selector_path = f"{stage_path}.skills[{ki}]"
                    if isinstance(selector, str):
                        if not _CATEGORY_RE.fullmatch(selector):
                            errors.append(f"{selector_path}: invalid Skill slug")
                        continue
                    if not isinstance(selector, dict):
                        errors.append(f"{selector_path}: expected string or object")
                        continue
                    name = selector.get("name")
                    if not isinstance(name, str) or not _CATEGORY_RE.fullmatch(name):
                        errors.append(f"{selector_path}.name: invalid Skill slug")
                    required = selector.get("required", True)
                    if not isinstance(required, bool):
                        errors.append(f"{selector_path}.required: expected boolean")
                    unknown = sorted(set(selector) - {"name", "required", "when"})
                    if unknown:
                        errors.append(f"{selector_path}: unsupported keys {unknown}")
                    errors.extend(
                        cls._validate_condition(
                            selector.get("when"),
                            f"{selector_path}.when",
                        )
                    )
                gate = stage.get("gate")
                if gate is not None:
                    if not isinstance(gate, dict):
                        errors.append(f"{stage_path}.gate: expected object")
                    else:
                        gate_type = gate.get("type")
                        requires = gate.get("requires")
                        if not isinstance(gate_type, str) or not gate_type:
                            errors.append(f"{stage_path}.gate.type: required")
                        if (
                            not isinstance(requires, list)
                            or not requires
                            or not all(
                                isinstance(item, str) and item.strip()
                                for item in requires
                            )
                        ):
                            errors.append(
                                f"{stage_path}.gate.requires: expected non-empty strings"
                            )
        return errors

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
        errors = self._validate_workflow_registry(raw)
        if errors:
            return {
                "schema_version": 1,
                "workflows": [],
                "error": "workflow-registry-invalid",
                "validation_errors": errors,
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
            return not (
                isinstance(none_flags, list)
                and any(bool(context.get(flag)) for flag in none_flags)
            )
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
                datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
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

    def refresh_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            path = self._run_path(run_id)
            data = json.loads(path.read_text(encoding="utf-8"))
            plan = self.plan_workflow(
                str(data.get("workflow_id") or ""),
                data.get("context") or {},
            )
            planned_by_id = {
                row.get("id"): row
                for row in plan.get("stages", [])
                if isinstance(row, dict)
            }
            current_stage = data.get("current_stage")
            for row in data.get("stages") or []:
                stage_id = row.get("id")
                planned = planned_by_id.get(stage_id)
                if not planned:
                    continue
                row["planner_status"] = planned.get("status")
                row["skills"] = planned.get("skills") or []
                row["gate"] = planned.get("gate")
                if row.get("status") in {"passed", "failed", "skipped"}:
                    continue
                if planned.get("status") == "skipped":
                    row["status"] = "skipped"
                    continue
                if stage_id == current_stage:
                    row["status"] = (
                        "blocked"
                        if planned.get("status") == "blocked"
                        else "in_progress"
                    )
                elif row.get("status") == "blocked":
                    row["status"] = "pending"

            active = next(
                (
                    row
                    for row in data.get("stages") or []
                    if row.get("id") == current_stage
                ),
                None,
            )
            if active is None or active.get("status") in {"passed", "skipped"}:
                current_stage = None
                for row in data.get("stages") or []:
                    if row.get("status") == "pending":
                        current_stage = row.get("id")
                        row["status"] = (
                            "blocked"
                            if row.get("planner_status") == "blocked"
                            else "in_progress"
                        )
                        break
            data["current_stage"] = current_stage
            if current_stage is None:
                data["status"] = "complete"
            else:
                current = next(
                    row
                    for row in data.get("stages") or []
                    if row.get("id") == current_stage
                )
                data["status"] = (
                    "blocked"
                    if current.get("status") == "blocked"
                    else "active"
                )
            data["updated_at"] = _utc_now()
            self._write_run(data)
            return data

    def transition_run(
        self,
        run_id: str,
        stage_id: str,
        status: str,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        if status not in _RUN_TRANSITION_STATUSES:
            raise ValueError("invalid run transition status")
        with self._lock:
            path = self._run_path(run_id)
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("current_stage") != stage_id:
                raise ValueError("only the current stage can transition")
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


def _parse_context_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("context must be valid JSON") from exc
    if not isinstance(value, dict):
        raise TypeError("context must be a JSON object")
    return value


def cli_skill_workflow(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex skill-workflow")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("skills")
    sub.add_parser("workflows")

    plan = sub.add_parser("plan")
    plan.add_argument("workflow_id")
    plan.add_argument("--context", default="{}")

    move = sub.add_parser("move")
    move.add_argument("skill_id")
    move.add_argument("category")
    move.add_argument("--position", type=int)

    open_folder = sub.add_parser("open-folder")
    open_folder.add_argument("skill_id")

    relocate_plan = sub.add_parser("relocate-plan")
    relocate_plan.add_argument("skill_id")
    relocate_plan.add_argument("target_root_id")

    relocate = sub.add_parser("relocate")
    relocate.add_argument("skill_id")
    relocate.add_argument("target_root_id")

    start = sub.add_parser("run-start")
    start.add_argument("workflow_id")
    start.add_argument("--context", default="{}")

    run_list = sub.add_parser("run-list")
    run_list.add_argument("--limit", type=int, default=50)

    refresh = sub.add_parser("run-refresh")
    refresh.add_argument("run_id")

    transition = sub.add_parser("run-transition")
    transition.add_argument("run_id")
    transition.add_argument("stage_id")
    transition.add_argument(
        "status",
        choices=sorted(_RUN_TRANSITION_STATUSES),
    )
    transition.add_argument("--evidence")

    args = parser.parse_args(argv)
    control = SkillWorkflowControlPlane()

    try:
        if args.action == "skills":
            result: Any = control.skill_snapshot()
        elif args.action == "workflows":
            result = control.workflow_catalog()
        elif args.action == "plan":
            result = control.plan_workflow(
                args.workflow_id,
                _parse_context_json(args.context),
            )
        elif args.action == "move":
            result = control.move_skill(
                args.skill_id,
                args.category,
                args.position,
            )
        elif args.action == "open-folder":
            result = control.open_skill_location(args.skill_id)
        elif args.action == "relocate-plan":
            result = control.plan_relocation(
                args.skill_id,
                args.target_root_id,
            )
        elif args.action == "relocate":
            result = control.relocate_skill(
                args.skill_id,
                args.target_root_id,
            )
        elif args.action == "run-start":
            result = control.start_run(
                args.workflow_id,
                _parse_context_json(args.context),
            )
        elif args.action == "run-list":
            result = {"runs": control.list_runs(limit=args.limit)}
        elif args.action == "run-refresh":
            result = control.refresh_run(args.run_id)
        elif args.action == "run-transition":
            result = control.transition_run(
                args.run_id,
                args.stage_id,
                args.status,
                args.evidence,
            )
        else:
            parser.error("unknown action")
            return 2
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": type(exc).__name__,
                    "detail": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
