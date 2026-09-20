# Third-Party Notices and Upstream Components

[**English**](THIRD_PARTY_NOTICES.md) | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

This repository includes integration, deployment metadata or runtime interoperability for third-party components. Product README content remains focused on WebGPT-as-Codex; source/provenance records live here, in `docs/THIRD-PARTY-PROVENANCE.json`, and in `components/*.json`.

This file is provenance/notice metadata, not a substitute for an upstream license or NOTICE. The exact license text and redistribution obligations for a redistributed binary/package remain those shipped by the relevant upstream release.

| Component / dependency | Upstream / source | License / provenance fact | WebGPT relationship |
|---|---|---|---|
| MCPJungle | https://github.com/mcpjungle/MCPJungle | `MPL-2.0` from `components/mcpjungle.json` | local MCP aggregation / Gateway runtime dependency |
| mcp-auth-proxy | https://github.com/sigbit/mcp-auth-proxy | `MIT` from `components/mcp-auth-proxy.json` | OAuth edge runtime dependency |
| Tailscale | https://github.com/tailscale/tailscale | `BSD-3-Clause core` from `components/tailscale.json` | HTTPS/Funnel transport dependency |
| Serena | https://github.com/oraios/serena | `v1.7.0 historical release; upstream main application GPL-3.0-or-later, SolidLSP MIT` from manifest license note | semantic coding MCP |
| Coding Tools MCP | https://github.com/xyTom/coding-tools-mcp | `Apache-2.0` | repository coding MCP |
| Playwright MCP | https://github.com/microsoft/playwright-mcp | `Apache-2.0` | browser automation MCP |
| Windows-MCP | https://github.com/CursorTouch/Windows-MCP | `MIT` | native Windows automation MCP |
| Remote Desktop Commander | https://github.com/desktop-commander/remote-desktop-commander | `hosted relay proprietary; repository docs/manifests only` from manifest license note | independent host control/rescue plane |
| requests | https://github.com/psf/requests | `Apache-2.0`; runtime dependency declared by `pyproject.toml` | Python HTTP client runtime dependency |
| setuptools | https://github.com/pypa/setuptools | `MIT`; PEP 517 build backend declared by `pyproject.toml` | build dependency, not an MCP runtime |
| pytest | https://github.com/pytest-dev/pytest | `MIT`; development dependency declared by `pyproject.toml` | test dependency |
| Ruff | https://github.com/astral-sh/ruff | `MIT`; development dependency declared by `pyproject.toml` | lint dependency |

## Distribution boundary

- Do not remove upstream license/copyright notices from redistributed artifacts.
- Do not state or imply that a third-party project is authored by WebGPT-as-Codex.
- Do not copy whole upstream repositories merely to make deployment self-contained when an official package/release installer is sufficient.
- Pin/verify third-party runtime artifacts through component metadata and install adapters.
- WebGPT-as-Codex's root `LICENSE` does not relicense third-party software.
- Stage18 release resources include this notice and its Chinese reading counterpart so an installed artifact retains public provenance; that does not vendor the listed third-party software into the wheel.
- Keep secrets, account data, cookies, tokens, private URLs and machine-specific paths out of this file, provenance data and Git.
