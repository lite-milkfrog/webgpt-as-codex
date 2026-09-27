from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .stateio import atomic_write_text

_LIFETIME_OLD = """          dispose: async () => {
            clientCount--;
            const last = !shared || !clientCount;
            if (last && sharedBrowserPromise === promise)
              sharedBrowserPromise = void 0;
            if (!last) {
              if (config.browser.isolated) {
                testDebug3("close context");
                await browserContext.close().catch(() => {
                });
              } else {
                testDebug3("disconnect from shared browser");
              }
              await browser.close().catch(() => {
              });
              return;
            }
            testDebug3("close browser");
            await browserContext.close().catch(() => {
            });
            await browser.close().catch(() => {
            });
            await shared?.browser.close().catch(() => {
            });
          }"""

_LIFETIME_NEW = """          dispose: async () => {
            clientCount--;
            const retainSharedExtension = !!shared && config.sharedBrowserContext && !!config.extension && !config.browser.isolated;
            if (retainSharedExtension) {
              testDebug3("disconnect from retained shared extension browser");
              await browser.close().catch(() => {
              });
              return;
            }
            const last = !shared || !clientCount;
            if (last && sharedBrowserPromise === promise)
              sharedBrowserPromise = void 0;
            if (!last) {
              if (config.browser.isolated) {
                testDebug3("close context");
                await browserContext.close().catch(() => {
                });
              } else {
                testDebug3("disconnect from shared browser");
              }
              await browser.close().catch(() => {
              });
              return;
            }
            testDebug3("close browser");
            await browserContext.close().catch(() => {
            });
            await browser.close().catch(() => {
            });
            await shared?.browser.close().catch(() => {
            });
          }"""

_SELECT_OLD = """      async selectTab(index) {
        const tab2 = this._tabs[index];"""
_SELECT_V1 = """      async selectTab(index) {
        await this.ensureBrowserContext();
        const tab2 = this._tabs[index];"""
_SELECT_NEW = """      async selectTab(index) {
        await this.ensureBrowserContext();
        const tab2 = this._tabs[index];
        if (tab2 && this.config.sharedBrowserContext && this.config.extension)
          globalThis.__wacPlaywrightSharedCurrentTabIndex = index;"""

_CLOSE_OLD = """      async closeTab(index) {
        const tab2 = index === void 0 ? this._currentTab : this._tabs[index];"""
_CLOSE_NEW = """      async closeTab(index) {
        await this.ensureBrowserContext();
        const tab2 = index === void 0 ? this._currentTab : this._tabs[index];"""

_NEW_TAB_OLD = """        const page = await browserContext.newPage();
        this._currentTab = this._tabs.find((t) => t.page === page);
        return this._currentTab;"""
_NEW_TAB_NEW = """        const page = await browserContext.newPage();
        this._currentTab = this._tabs.find((t) => t.page === page);
        if (this.config.sharedBrowserContext && this.config.extension && this._currentTab)
          globalThis.__wacPlaywrightSharedCurrentTabIndex = this._tabs.indexOf(this._currentTab);
        return this._currentTab;"""

_PAGE_CLOSED_OLD = """        this._tabs.splice(index, 1);
        if (this._currentTab === tab2)
          this._currentTab = this._tabs[Math.min(index, this._tabs.length - 1)];"""
_PAGE_CLOSED_NEW = """        this._tabs.splice(index, 1);
        if (this._currentTab === tab2)
          this._currentTab = this._tabs[Math.min(index, this._tabs.length - 1)];
        if (this.config.sharedBrowserContext && this.config.extension)
          globalThis.__wacPlaywrightSharedCurrentTabIndex = this._currentTab ? this._tabs.indexOf(this._currentTab) : void 0;"""

_CURRENT_TAB_OLD = """        for (const page of browserContext.pages())
          this._onPageCreated(page);
        this._disposables.push(eventsHelper.addEventListener(browserContext, "page", (page) => this._onPageCreated(page)));
        return browserContext;"""

_CURRENT_TAB_V1 = """        for (const page of browserContext.pages())
          this._onPageCreated(page);
        for (const tab2 of this._tabs) {
          const visibility = await tab2.page.evaluate(() => document.visibilityState).catch(() => void 0);
          if (visibility === "visible") {
            this._currentTab = tab2;
            break;
          }
        }
        this._disposables.push(eventsHelper.addEventListener(browserContext, "page", (page) => this._onPageCreated(page)));
        return browserContext;"""

_CURRENT_TAB_V2 = """        for (const page of browserContext.pages())
          this._onPageCreated(page);
        const contentTabs = this._tabs.filter((tab2) => {
          const url3 = tab2.page.url();
          return !(url3.startsWith("chrome-extension://") && url3.includes("/connect.html?mcpRelayUrl="));
        });
        let activeTab;
        for (const tab2 of contentTabs) {
          const focused = await tab2.page.evaluate(() => document.hasFocus()).catch(() => false);
          if (focused) {
            activeTab = tab2;
            break;
          }
        }
        if (!activeTab) {
          for (const tab2 of contentTabs) {
            const visibility = await tab2.page.evaluate(() => document.visibilityState).catch(() => void 0);
            if (visibility === "visible") {
              activeTab = tab2;
              break;
            }
          }
        }
        this._currentTab = activeTab ?? contentTabs[0] ?? this._currentTab;
        this._disposables.push(eventsHelper.addEventListener(browserContext, "page", (page) => this._onPageCreated(page)));
        return browserContext;"""

_CURRENT_TAB_NEW = """        for (const page of browserContext.pages())
          this._onPageCreated(page);
        const contentTabs = this._tabs.filter((tab2) => {
          const url3 = tab2.page.url();
          return !(url3.startsWith("chrome-extension://") && url3.includes("/connect.html?mcpRelayUrl="));
        });
        const rememberedIndex = this.config.sharedBrowserContext && this.config.extension ? globalThis.__wacPlaywrightSharedCurrentTabIndex : void 0;
        let activeTab = Number.isInteger(rememberedIndex) ? this._tabs[rememberedIndex] : void 0;
        if (activeTab && !contentTabs.includes(activeTab))
          activeTab = void 0;
        if (!activeTab) {
          for (const tab2 of contentTabs) {
            const focused = await tab2.page.evaluate(() => document.hasFocus()).catch(() => false);
            if (focused) {
              activeTab = tab2;
              break;
            }
          }
        }
        if (!activeTab) {
          for (const tab2 of contentTabs) {
            const visibility = await tab2.page.evaluate(() => document.visibilityState).catch(() => void 0);
            if (visibility === "visible") {
              activeTab = tab2;
              break;
            }
          }
        }
        this._currentTab = activeTab ?? contentTabs[0] ?? this._currentTab;
        if (this.config.sharedBrowserContext && this.config.extension && contentTabs.includes(this._currentTab))
          globalThis.__wacPlaywrightSharedCurrentTabIndex = this._tabs.indexOf(this._currentTab);
        this._disposables.push(eventsHelper.addEventListener(browserContext, "page", (page) => this._onPageCreated(page)));
        return browserContext;"""

_CLICK_OLD = """      handle: async (tab2, params2, response2) => {
        response2.setIncludeSnapshot();
        const { locator: locator2, selector } = await tab2.targetLocator(params2);
        const options = {
          button: params2.button,
          modifiers: params2.modifiers,
          ...tab2.actionTimeoutOptions
        };
        response2.addAction({
          name: "click",
          selector,
          button: params2.button ?? "left",
          modifiers: fromKeyboardModifiers(params2.modifiers),
          clickCount: params2.doubleClick ? 2 : 1
        });
        await tab2.waitForCompletion(async () => {
          if (params2.doubleClick)
            await locator2.dblclick(options);
          else
            await locator2.click(options);
        });
      }"""

_CLICK_NEW = """      handle: async (tab2, params2, response2, signal) => {
        const { locator: locator2, selector } = await tab2.targetLocator(params2);
        const configuredTimeout = tab2.actionTimeoutOptions?.timeout ?? 5e3;
        const preflightTimeout = Math.min(configuredTimeout, 5e3);
        const options = {
          button: params2.button,
          modifiers: params2.modifiers,
          timeout: preflightTimeout
        };
        const trialOptions = { ...options, trial: true };
        if (params2.doubleClick)
          await locator2.dblclick(trialOptions);
        else
          await locator2.click(trialOptions);
        if (signal?.aborted)
          throw new Error("Action cancelled before click commit");
        response2.addAction({
          name: "click",
          selector,
          button: params2.button ?? "left",
          modifiers: fromKeyboardModifiers(params2.modifiers),
          clickCount: params2.doubleClick ? 2 : 1
        });
        const commitOptions = {
          ...options,
          timeout: Math.min(preflightTimeout, 2e3),
          noWaitAfter: true
        };
        if (params2.doubleClick)
          await locator2.dblclick(commitOptions);
        else
          await locator2.click(commitOptions);
      }"""

_PRESS_OLD = """      handle: async (tab2, params2, response2) => {
        response2.addCode(`// Press ${params2.key}`);
        response2.addCode(`await page.keyboard.press(${escapeWithQuotes(params2.key)});`);
        if (params2.key === "Enter") {
          response2.setIncludeSnapshot();
          await tab2.waitForCompletion(async () => {
            await tab2.page.keyboard.press("Enter");
          });
        } else {
          await tab2.page.keyboard.press(params2.key);
        }
      }"""

_PRESS_NEW = """      handle: async (tab2, params2, response2, signal) => {
        response2.addCode(`// Press ${params2.key}`);
        response2.addCode(`await page.keyboard.press(${escapeWithQuotes(params2.key)});`);
        if (signal?.aborted)
          throw new Error("Action cancelled before key commit");
        await tab2.page.keyboard.press(params2.key);
      }"""

_TYPE_OLD = """      handle: async (tab2, params2, response2) => {
        const { locator: locator2, resolved, selector } = await tab2.targetLocator(params2);
        const secret = tab2.context.lookupSecret(params2.text);
        const action = async () => {
          if (params2.slowly) {
            response2.setIncludeSnapshot();
            response2.addCode(`await page.${resolved}.pressSequentially(${secret.code});`);
            await locator2.pressSequentially(secret.value, tab2.actionTimeoutOptions);
          } else {
            response2.addAction({ name: "fill", selector, text: secret.isSecret ? `SECRET_${params2.text}` : params2.text });
            await locator2.fill(secret.value, tab2.actionTimeoutOptions);
          }
          if (params2.submit) {
            response2.setIncludeSnapshot();
            response2.addAction({ name: "press", selector, key: "Enter", modifiers: 0 });
            await locator2.press("Enter", tab2.actionTimeoutOptions);
          }
        };
        if (params2.submit || params2.slowly)
          await tab2.waitForCompletion(action);
        else
          await action();
      }"""

_TYPE_NEW = """      handle: async (tab2, params2, response2, signal) => {
        const { locator: locator2, resolved, selector } = await tab2.targetLocator(params2);
        const secret = tab2.context.lookupSecret(params2.text);
        const configuredTimeout = tab2.actionTimeoutOptions?.timeout ?? 5e3;
        const safeOptions = { timeout: Math.min(configuredTimeout, 5e3) };
        const action = async () => {
          if (params2.slowly) {
            if (!params2.submit)
              response2.setIncludeSnapshot();
            response2.addCode(`await page.${resolved}.pressSequentially(${secret.code});`);
            await locator2.pressSequentially(secret.value, safeOptions);
          } else {
            response2.addAction({ name: "fill", selector, text: secret.isSecret ? `SECRET_${params2.text}` : params2.text });
            await locator2.fill(secret.value, safeOptions);
          }
          if (params2.submit) {
            if (signal?.aborted)
              throw new Error("Action cancelled before submit commit");
            response2.addAction({ name: "press", selector, key: "Enter", modifiers: 0 });
            await locator2.press("Enter", {
              timeout: Math.min(safeOptions.timeout, 2e3),
              noWaitAfter: true
            });
          }
        };
        if (params2.slowly && !params2.submit)
          await tab2.waitForCompletion(action);
        else
          await action();
      }"""

_MARKERS = (
    "disconnect from retained shared extension browser",
    "__wacPlaywrightSharedCurrentTabIndex",
    "async selectTab(index) {\n        await this.ensureBrowserContext();",
    "async closeTab(index) {\n        await this.ensureBrowserContext();",
    "document.hasFocus()",
    "/connect.html?mcpRelayUrl=",
    "Action cancelled before click commit",
    "Action cancelled before submit commit",
    "Action cancelled before key commit",
)


def _candidate_bundles() -> list[Path]:
    values: list[Path] = []
    explicit = os.getenv("WEBGPT_CODEX_PLAYWRIGHT_CORE_BUNDLE")
    if explicit:
        values.append(Path(explicit).expanduser())
    root = os.getenv("WEBGPT_CODEX_PLAYWRIGHT_MCP_ROOT")
    if root:
        values.append(
            Path(root).expanduser()
            / "node_modules"
            / "playwright-core"
            / "lib"
            / "coreBundle.js"
        )
    values.append(
        Path("D:/AgentData/10_Workspaces/coding-tools-mcp-demo")
        / ".tools"
        / "playwright-mcp"
        / "node_modules"
        / "playwright-core"
        / "lib"
        / "coreBundle.js"
    )
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in values:
        key = str(candidate).casefold()
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped


def locate_playwright_core_bundle() -> Path | None:
    for candidate in _candidate_bundles():
        if candidate.is_file():
            return candidate.resolve()
    return None


def patch_playwright_core_bundle(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    changed: list[str] = []

    replacements = (
        ("shared-extension-lifetime", (_LIFETIME_OLD,), _LIFETIME_NEW),
        ("select-tab-reconcile", (_SELECT_V1, _SELECT_OLD), _SELECT_NEW),
        ("close-tab-reconcile", (_CLOSE_OLD,), _CLOSE_NEW),
        ("new-tab-stickiness", (_NEW_TAB_OLD,), _NEW_TAB_NEW),
        ("page-close-stickiness", (_PAGE_CLOSED_OLD,), _PAGE_CLOSED_NEW),
        ("click-exactly-once", (_CLICK_OLD,), _CLICK_NEW),
        ("press-exactly-once", (_PRESS_OLD,), _PRESS_NEW),
        ("type-submit-exactly-once", (_TYPE_OLD,), _TYPE_NEW),
        (
            "current-tab-visibility",
            (_CURRENT_TAB_V2, _CURRENT_TAB_V1, _CURRENT_TAB_OLD),
            _CURRENT_TAB_NEW,
        ),
    )
    for name, old_variants, new in replacements:
        if new in text:
            continue
        old = next((value for value in old_variants if value in text), None)
        if old is None:
            return {
                "ok": False,
                "status": "signature-mismatch",
                "path": str(path),
                "missing_patch": name,
            }
        text = text.replace(old, new, 1)
        changed.append(name)

    if changed:
        backup = path.with_name(path.name + ".pre-wac-hotfix")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
        atomic_write_text(path, text)

    verified = path.read_text(encoding="utf-8")
    if not all(marker in verified for marker in _MARKERS):
        return {
            "ok": False,
            "status": "verification-failed",
            "path": str(path),
            "changed": changed,
        }
    return {
        "ok": True,
        "status": "patched" if changed else "present",
        "path": str(path),
        "changed": changed,
    }


def ensure_playwright_hotfix() -> dict[str, Any]:
    path = locate_playwright_core_bundle()
    if path is None:
        return {"ok": False, "status": "bundle-not-found"}
    try:
        bundle = patch_playwright_core_bundle(path)
        if not bundle.get("ok"):
            return bundle
        startup = ensure_playwright_action_timeout()
        return {
            **bundle,
            "startup_timeout": startup,
            "ok": bool(startup.get("ok")),
            "status": (
                bundle.get("status")
                if startup.get("ok")
                else startup.get("status", "startup-timeout-not-ready")
            ),
        }
    except OSError as exc:
        return {
            "ok": False,
            "status": "patch-io-failed",
            "failure_type": type(exc).__name__,
        }


def _startup_script_specs() -> list[tuple[Path, str, str]]:
    return [
        (
            Path(
                "D:/AgentData/20_State/playwright-mcp-tailscale/"
                "start-playwright-remote.ps1"
            ),
            "'--output-dir',$outputPath)",
            "'--output-dir',$outputPath,'--timeout-action','15000')",
        ),
        (
            Path(
                "D:/AgentData/10_Workspaces/coding-tools-mcp-demo/"
                ".tools/playwright-mcp/start-extension.cmd"
            ),
            "--output-dir output ",
            "--output-dir output --timeout-action 15000 ",
        ),
    ]


def ensure_playwright_action_timeout() -> dict[str, Any]:
    scripts = _startup_script_specs()
    rows: list[dict[str, Any]] = []
    for path, old, new in scripts:
        if not path.is_file():
            rows.append({"path": str(path), "status": "absent"})
            continue
        text = path.read_text(encoding="utf-8-sig")
        if "--timeout-action" in text:
            rows.append({"path": str(path), "status": "present"})
            continue
        if old not in text:
            return {
                "ok": False,
                "status": "startup-timeout-signature-mismatch",
                "path": str(path),
            }
        atomic_write_text(path, text.replace(old, new, 1))
        rows.append({"path": str(path), "status": "patched"})
    return {"ok": True, "status": "ready", "scripts": rows}
