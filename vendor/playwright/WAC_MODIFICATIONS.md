# WebGPT-as-Codex Playwright Core derivative source baseline

Upstream: https://github.com/microsoft/playwright
Upstream gitHead: d1ead3ecca23182f2d06d761c28e3d4edafb6595
Package version: playwright-core 1.64.0-alpha-2026-09-14
License: Apache-2.0

This directory is the complete upstream source snapshot corresponding to the playwright-core package used by @playwright/mcp 0.0.81.

WebGPT-as-Codex applies a runtime derivative patch through:
- src/webgpt_as_codex/playwright_hotfix.py

Derivative behavior:
- retain shared Extension browser lifecycle correctly across MCP calls;
- reconcile/select/close/new tab state without drifting back to the extension Welcome page;
- remember the selected shared-context tab;
- harden click, key press, and type+submit commit boundaries for exactly-once behavior;
- use bounded action timeouts and avoid blind duplicate side effects.

WAC_RUNTIME_BUNDLE_DIFF.patch is the exact no-index diff between the pre-hotfix and accepted patched playwright-core/lib/coreBundle.js from the validated runtime.
The patch implementation itself remains repository-owned Python source so a fresh deployment can reproduce the derivative from this complete upstream source/package baseline.
