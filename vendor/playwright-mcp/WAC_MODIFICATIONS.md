# WebGPT-as-Codex Playwright MCP source snapshot

Upstream: https://github.com/microsoft/playwright-mcp
Upstream tag: v0.0.81
Upstream commit: e73d72e01f162054a3d0a6b0fe8d4affffb095ee
License: Apache-2.0

This directory is the complete upstream source snapshot used by WebGPT-as-Codex for Playwright MCP deployment.
WebGPT currently does not rewrite the MCP source files in this directory directly. The WebGPT derivative behavior is applied to its pinned playwright-core dependency through src/webgpt_as_codex/playwright_hotfix.py.

The package pins:
- playwright 1.64.0-alpha-2026-09-14
- playwright-core 1.64.0-alpha-2026-09-14

The matching complete Playwright source snapshot is stored in ../playwright/.
