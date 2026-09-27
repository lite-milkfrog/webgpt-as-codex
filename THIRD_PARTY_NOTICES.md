# Third-Party Notices and Upstream Components

[**English**](THIRD_PARTY_NOTICES.md) | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

This repository includes integration, deployment metadata or runtime interoperability for third-party components. Product README content remains focused on WebGPT-as-Codex; source/provenance records live here, in `docs/THIRD-PARTY-PROVENANCE.json`, and in `components/*.json`.

This file is provenance/notice metadata, not a substitute for an upstream license or NOTICE. The exact license text and redistribution obligations for a redistributed binary/package remain those shipped by the relevant upstream release.

| Component / dependency | Upstream / source | License / provenance fact | WebGPT relationship |
|---|---|---|---|
| MCPJungle | https://github.com/mcpjungle/MCPJungle | `MPL-2.0` from `components/mcpjungle.json` | local MCP aggregation / Gateway runtime dependency |
| mcp-auth-proxy | https://github.com/sigbit/mcp-auth-proxy | `MIT` from `components/mcp-auth-proxy.json` | OAuth edge runtime dependency |
| Tailscale | https://github.com/tailscale/tailscale | `BSD-3-Clause core` from `components/tailscale.json` | HTTPS/Funnel transport dependency |
| Serena | https://github.com/oraios/serena | bundled derivative is based on complete `v1.7.0`, the last MIT-licensed Serena application release; upstream v2+ application is GPL-3.0-or-later | complete modified source redistributed under `vendor/serena-agent/`; upstream license and WAC modification/diff evidence are retained there |
| Coding Tools MCP | https://github.com/xyTom/coding-tools-mcp | `Apache-2.0` | complete modified source redistributed under `vendor/coding-tools-mcp/`; upstream LICENSE/NOTICE plus WAC modification/diff evidence are retained there |
| Playwright MCP / Playwright Core | https://github.com/microsoft/playwright-mcp / https://github.com/microsoft/playwright | `Apache-2.0` | complete MCP v0.0.81 and matching Playwright gitHead source snapshots are redistributed under `vendor/playwright-mcp/` and `vendor/playwright/`; WebGPT runtime changes are applied by the deterministic hotfix layer with exact bundle-diff evidence retained in the vendor tree |
| Windows-MCP | https://github.com/CursorTouch/Windows-MCP | `MIT` | native Windows automation MCP |
| Remote Desktop Commander | https://github.com/desktop-commander/remote-desktop-commander | `hosted relay proprietary; repository docs/manifests only` from manifest license note | independent host control/rescue plane |
| requests | https://github.com/psf/requests | `Apache-2.0`; runtime dependency declared by `pyproject.toml` | Python HTTP client runtime dependency |
| setuptools | https://github.com/pypa/setuptools | `MIT`; PEP 517 build backend declared by `pyproject.toml` | build dependency, not an MCP runtime |
| pytest | https://github.com/pytest-dev/pytest | `MIT`; development dependency declared by `pyproject.toml` | test dependency |
| Ruff | https://github.com/astral-sh/ruff | `MIT`; development dependency declared by `pyproject.toml` | lint dependency |

## Distribution boundary

- Do not remove upstream license/copyright notices from redistributed artifacts.
- Do not state or imply that a third-party project is authored by WebGPT-as-Codex.
- Do not copy whole upstream repositories merely to make deployment self-contained when an official package/release installer is sufficient. The explicit exceptions are components that WebGPT itself has materially modified and must reproduce on a fresh deployment; those derivatives live under `vendor/` with license/provenance and exact-diff evidence.
- Release secret scanning treats pinned, complete upstream source snapshots as provenance-controlled third-party inputs and scans the WebGPT-owned derivative files / `WAC_*` evidence inside those trees. WAC-owned source outside `vendor/` remains fully scanned.
- Pin/verify third-party runtime artifacts through component metadata and install adapters.
- WebGPT-as-Codex's root `LICENSE` does not relicense third-party software.
- The Git source tree intentionally vendors the complete Coding Tools and Serena derivative sources under `vendor/`. The current Python wheel remains thin and is not the canonical standalone deployment artifact for those derivatives; source deployment retains the verified checkout.
- Keep secrets, account data, cookies, tokens, private URLs and machine-specific paths out of this file, provenance data and Git.
