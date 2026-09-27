from __future__ import annotations

from pathlib import Path

import pytest

from webgpt_as_codex import playwright_hotfix as hotfix


def _vendor_fixture() -> str:
    return (
        f"{hotfix._LIFETIME_OLD}\n\n"
        f"{hotfix._SELECT_OLD}\n\n"
        f"{hotfix._CLOSE_OLD}\n\n"
        f"{hotfix._NEW_TAB_OLD}\n\n"
        f"{hotfix._PAGE_CLOSED_OLD}\n\n"
        f"{hotfix._CLICK_OLD}\n\n"
        f"{hotfix._PRESS_OLD}\n\n"
        f"{hotfix._TYPE_OLD}\n\n"
        f"{hotfix._CURRENT_TAB_OLD}"
    )


def test_playwright_hotfix_patches_all_short_client_failures(tmp_path: Path) -> None:
    bundle = tmp_path / "coreBundle.js"
    bundle.write_text(_vendor_fixture(), encoding="utf-8")

    first = hotfix.patch_playwright_core_bundle(bundle)
    patched = bundle.read_text(encoding="utf-8")

    assert first["ok"] is True
    assert first["status"] == "patched"
    assert first["changed"] == [
        "shared-extension-lifetime",
        "select-tab-reconcile",
        "close-tab-reconcile",
        "new-tab-stickiness",
        "page-close-stickiness",
        "click-exactly-once",
        "press-exactly-once",
        "type-submit-exactly-once",
        "current-tab-visibility",
    ]
    assert "disconnect from retained shared extension browser" in patched
    assert hotfix._SELECT_NEW in patched
    assert hotfix._CLOSE_NEW in patched
    assert hotfix._NEW_TAB_NEW in patched
    assert hotfix._PAGE_CLOSED_NEW in patched
    assert hotfix._CLICK_NEW in patched
    assert hotfix._PRESS_NEW in patched
    assert hotfix._TYPE_NEW in patched
    assert hotfix._CURRENT_TAB_NEW in patched
    assert "__wacPlaywrightSharedCurrentTabIndex" in patched
    assert bundle.with_name("coreBundle.js.pre-wac-hotfix").is_file()

    second = hotfix.patch_playwright_core_bundle(bundle)
    assert second["ok"] is True
    assert second["status"] == "present"
    assert second["changed"] == []


def test_playwright_hotfix_fails_closed_on_unknown_vendor_shape(tmp_path: Path) -> None:
    bundle = tmp_path / "coreBundle.js"
    bundle.write_text("unexpected bundle\n", encoding="utf-8")

    result = hotfix.patch_playwright_core_bundle(bundle)

    assert result["ok"] is False
    assert result["status"] == "signature-mismatch"
    assert result["missing_patch"] == "shared-extension-lifetime"


def test_playwright_hotfix_upgrades_v2_current_tab_selection(tmp_path: Path) -> None:
    bundle = tmp_path / "coreBundle.js"
    bundle.write_text(
        f"{hotfix._LIFETIME_NEW}\n\n"
        f"{hotfix._SELECT_NEW}\n\n"
        f"{hotfix._CLOSE_NEW}\n\n"
        f"{hotfix._NEW_TAB_NEW}\n\n"
        f"{hotfix._PAGE_CLOSED_NEW}\n\n"
        f"{hotfix._CLICK_NEW}\n\n"
        f"{hotfix._PRESS_NEW}\n\n"
        f"{hotfix._TYPE_NEW}\n\n"
        f"{hotfix._CURRENT_TAB_V2}",
        encoding="utf-8",
    )

    result = hotfix.patch_playwright_core_bundle(bundle)
    patched = bundle.read_text(encoding="utf-8")

    assert result["ok"] is True
    assert result["status"] == "patched"
    assert result["changed"] == ["current-tab-visibility"]
    assert "__wacPlaywrightSharedCurrentTabIndex" in patched


def test_playwright_hotfix_locator_honors_explicit_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "coreBundle.js"
    bundle.write_text(_vendor_fixture(), encoding="utf-8")
    monkeypatch.setenv("WEBGPT_CODEX_PLAYWRIGHT_CORE_BUNDLE", str(bundle))
    monkeypatch.setattr(
        hotfix,
        "ensure_playwright_action_timeout",
        lambda: {"ok": True, "status": "ready", "scripts": []},
    )

    assert hotfix.locate_playwright_core_bundle() == bundle.resolve()
    result = hotfix.ensure_playwright_hotfix()
    assert result["ok"] is True


def test_playwright_hotfix_locator_supports_nested_bundled_npm_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "playwright-root"
    bundle = (
        root
        / "node_modules"
        / "@playwright"
        / "mcp"
        / "node_modules"
        / "playwright-core"
        / "lib"
        / "coreBundle.js"
    )
    bundle.parent.mkdir(parents=True)
    bundle.write_text(_vendor_fixture(), encoding="utf-8")
    monkeypatch.delenv("WEBGPT_CODEX_PLAYWRIGHT_CORE_BUNDLE", raising=False)
    monkeypatch.setenv("WEBGPT_CODEX_PLAYWRIGHT_MCP_ROOT", str(root))
    monkeypatch.setattr(hotfix, "_npm_global_node_modules", lambda: None)

    assert hotfix.locate_playwright_core_bundle() == bundle.resolve()


def test_playwright_hotfix_locator_discovers_nested_global_npm_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_modules = tmp_path / "global-node-modules"
    bundle = (
        node_modules
        / "@playwright"
        / "mcp"
        / "node_modules"
        / "playwright-core"
        / "lib"
        / "coreBundle.js"
    )
    bundle.parent.mkdir(parents=True)
    bundle.write_text(_vendor_fixture(), encoding="utf-8")
    monkeypatch.delenv("WEBGPT_CODEX_PLAYWRIGHT_CORE_BUNDLE", raising=False)
    monkeypatch.delenv("WEBGPT_CODEX_PLAYWRIGHT_MCP_ROOT", raising=False)
    monkeypatch.setattr(hotfix, "_npm_global_node_modules", lambda: node_modules)

    assert hotfix.locate_playwright_core_bundle() == bundle.resolve()


def test_playwright_action_timeout_is_patched_idempotently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = tmp_path / "start-playwright-remote.ps1"
    local = tmp_path / "start-extension.cmd"
    remote.write_text(
        "$args=@($cli,'--output-dir',$outputPath)\n",
        encoding="utf-8",
    )
    local.write_text(
        "playwright-mcp --output-dir output --shared-browser-context\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        hotfix,
        "_startup_script_specs",
        lambda: [
            (
                remote,
                "'--output-dir',$outputPath)",
                "'--output-dir',$outputPath,'--timeout-action','15000')",
            ),
            (
                local,
                "--output-dir output ",
                "--output-dir output --timeout-action 15000 ",
            ),
        ],
    )

    first = hotfix.ensure_playwright_action_timeout()
    second = hotfix.ensure_playwright_action_timeout()

    assert first["ok"] is True
    assert [row["status"] for row in first["scripts"]] == ["patched", "patched"]
    assert second["ok"] is True
    assert [row["status"] for row in second["scripts"]] == ["present", "present"]
    assert "--timeout-action','15000" in remote.read_text(encoding="utf-8")
    assert "--timeout-action 15000" in local.read_text(encoding="utf-8")
