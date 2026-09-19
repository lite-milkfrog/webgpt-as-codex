# Third-Party Notices and Upstream Components

This repository includes integration, deployment metadata or runtime interoperability for third-party components. Product README content remains focused on WebGPT-as-Codex; source/provenance records live here and in `components/*.json`.

The exact license text and redistribution obligations for any redistributed binary/package must be preserved according to that upstream release.

| Component | Upstream | WebGPT relationship |
|---|---|---|
| MCPJungle | https://github.com/mcpjungle/MCPJungle | local MCP aggregation/runtime dependency |
| mcp-auth-proxy | https://github.com/sigbit/mcp-auth-proxy | OAuth edge runtime dependency |
| Tailscale | https://tailscale.com/ | HTTPS/Funnel transport dependency |
| Serena | upstream recorded in `components/serena.json` | semantic coding MCP |
| Coding Tools MCP | upstream/install metadata recorded in `components/coding-tools.json` | repository coding MCP |
| Playwright MCP | upstream/install metadata recorded in `components/playwright.json` | browser automation MCP |
| Windows-MCP | upstream/install metadata recorded in `components/windows-mcp.json` | native Windows automation MCP |
| Remote Desktop Commander | upstream/install metadata recorded in `components/remote-desktop-commander.json` | independent host control/rescue plane |

## Policy

- Do not remove upstream license/copyright notices from redistributed artifacts.
- Do not state or imply that a third-party project is authored by WebGPT-as-Codex.
- Do not copy whole upstream repositories merely to make deployment self-contained when an official package/release installer is sufficient.
- Pin/verify runtime artifacts through component metadata and install adapters.
- Keep secrets, account data and machine-specific URLs out of this file and Git.
