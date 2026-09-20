from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "docs" / "TRANSLATION-COVERAGE.json"
PROVENANCE = ROOT / "docs" / "THIRD-PARTY-PROVENANCE.json"
LICENSE_SHA256 = "1eb85fc97224598dad1852b5d6483bbcf0aa8608790dcc657a5a2a761ae9c8c6"
TEXT_SUFFIXES = {".md", ".json", ".toml", ".html", ".css", ".js", ".py"}
EXACT_TEXT = {".gitignore", "LICENSE"}


def _candidate_paths() -> set[str]:
    raw = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    result: set[str] = set()
    for value in raw.splitlines():
        path = Path(value)
        if value in EXACT_TEXT or path.suffix.lower() in TEXT_SUFFIXES:
            result.add(path.as_posix())
    return result


def _coverage() -> dict:
    return json.loads(COVERAGE.read_text(encoding="utf-8"))


def test_every_text_candidate_has_translation_disposition() -> None:
    coverage = _coverage()
    entries = {row["path"]: row for row in coverage["entries"]}
    assert len(entries) == len(coverage["entries"])
    dynamic_prefixes = tuple(coverage["dynamic_historical_prefixes"])
    dynamic_prefixes += tuple(
        row["prefix"] for row in coverage.get("dynamic_current_prefixes", [])
    )
    missing = sorted(
        path
        for path in _candidate_paths()
        if path not in entries and not path.startswith(dynamic_prefixes)
    )
    assert missing == []


def test_required_current_mirrors_exist() -> None:
    coverage = _coverage()
    for row in coverage["entries"]:
        if row["status"] == "MIRRORED_CURRENT":
            mirror = row.get("mirror_path")
            assert mirror, row["path"]
            assert (ROOT / mirror).is_file(), (row["path"], mirror)


def test_apache_original_is_byte_preserved_and_translation_is_non_binding() -> None:
    original = (ROOT / "LICENSE").read_bytes()
    assert hashlib.sha256(original).hexdigest() == LICENSE_SHA256
    translated = (ROOT / "LICENSE.zh-CN.md").read_text(encoding="utf-8")
    assert "不具有约束力" in translated
    assert "一律以英文原文为准" in translated


def test_component_provenance_matches_repository_manifests() -> None:
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in provenance["components"]}
    manifests = {}
    for path in sorted((ROOT / "components").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        manifests[data["id"]] = data
    assert set(by_id) == set(manifests)
    for component_id, manifest in manifests.items():
        row = by_id[component_id]
        assert row["source"] == f"components/{component_id}.json"
        assert row["upstream"] == manifest["upstream"]
        assert row["license"] == manifest[row["license_field"]]


def test_python_dependency_provenance_covers_pyproject() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    names = {row["name"] for row in provenance["python_dependencies"]}
    assert {"setuptools", "requests", "pytest", "ruff"} <= names
    assert project["project"]["dependencies"] == ["requests>=2.32,<3"]
    assert project["project"]["optional-dependencies"]["dev"] == [
        "pytest>=8.0",
        "ruff>=0.15",
    ]
    assert project["build-system"]["requires"] == ["setuptools>=68"]


def test_stage18_release_resources_are_declared() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    release = project["tool"]["setuptools"]["data-files"]["share/webgpt-as-codex/release"]
    assert release == [
        "README.md",
        "README.zh-CN.md",
        "LICENSE",
        "LICENSE.zh-CN.md",
        "THIRD_PARTY_NOTICES.md",
        "THIRD_PARTY_NOTICES.zh-CN.md",
        "docs/TRANSLATION-COVERAGE.json",
        "docs/TRANSLATION-COVERAGE.md",
        "docs/THIRD-PARTY-PROVENANCE.json",
    ]


def test_language_entrypoints_cross_link() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    agents_zh = (ROOT / "AGENTS.zh-CN.md").read_text(encoding="utf-8")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    notices_zh = (ROOT / "THIRD_PARTY_NOTICES.zh-CN.md").read_text(encoding="utf-8")
    assert "README.zh-CN.md" in readme and "README.md" in readme_zh
    assert "AGENTS.zh-CN.md" in agents and "AGENTS.md" in agents_zh
    assert "THIRD_PARTY_NOTICES.zh-CN.md" in notices
    assert "THIRD_PARTY_NOTICES.md" in notices_zh
