from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from webgpt_as_codex import __version__, paths


def test_release_metadata_declares_runtime_assets() -> None:
    root = paths.repo_root()
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["version"] == __version__
    data_files = data["tool"]["setuptools"]["data-files"]
    assert data_files["share/webgpt-as-codex/components"] == ["components/*.json"]
    assert data_files["share/webgpt-as-codex/manager/static"] == [
        "manager/static/index.html",
        "manager/static/index.zh-CN.html",
        "manager/static/manager.css",
        "manager/static/manager.js",
    ]
    assert data_files["share/webgpt-as-codex/release"] == [
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


def test_resource_root_falls_back_to_installed_share(
    monkeypatch, tmp_path: Path
) -> None:
    missing_source = tmp_path / "Lib"
    prefix = tmp_path / "venv"
    installed = prefix / "share" / "webgpt-as-codex"
    (installed / "components").mkdir(parents=True)
    static = installed / "manager" / "static"
    static.mkdir(parents=True)
    (static / "index.html").write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(paths, "repo_root", lambda: missing_source)
    monkeypatch.setattr(sys, "prefix", str(prefix))

    assert paths.resource_root() == installed


def test_skill_manifest_matches_skill_frontmatter() -> None:
    root = paths.repo_root() / "skills" / "webgpt-as-codex"
    manifest = (root / "manifest.json").read_text(encoding="utf-8")
    skill = (root / "SKILL.md").read_text(encoding="utf-8")

    assert '\"version\":  \"1.3.2\"' in manifest or '\"version\": \"1.3.2\"' in manifest
    assert "version: 1.3.2" in skill
