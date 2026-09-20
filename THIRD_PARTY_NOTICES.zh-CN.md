# 第三方声明与上游来源（简体中文）

[English](THIRD_PARTY_NOTICES.md) | **简体中文**

本仓库包含第三方组件的集成、部署元数据或运行时互操作配置。产品 README 继续聚焦 WebGPT-as-Codex；第三方来源与许可证事实记录在本文件、`docs/THIRD-PARTY-PROVENANCE.json` 和 `components/*.json`。

> 本文件用于来源/许可信息披露，不替代任何第三方上游项目自己的许可证或 NOTICE。实际重新分发某个第三方 binary/package 时，必须遵守该具体上游版本附带的精确许可证文本与义务。

| 组件/依赖 | 上游/来源 | 许可/来源事实 | WebGPT 关系 |
|---|---|---|---|
| MCPJungle | https://github.com/mcpjungle/MCPJungle | `MPL-2.0`（来自 `components/mcpjungle.json`） | 本地 MCP 聚合/Gateway 运行依赖 |
| mcp-auth-proxy | https://github.com/sigbit/mcp-auth-proxy | `MIT`（来自 `components/mcp-auth-proxy.json`） | OAuth Edge 运行依赖 |
| Tailscale | https://github.com/tailscale/tailscale | `BSD-3-Clause core`（来自 `components/tailscale.json`） | HTTPS/Funnel 传输依赖 |
| Serena | https://github.com/oraios/serena | `v1.7.0 historical release; upstream main application GPL-3.0-or-later, SolidLSP MIT`（manifest license note） | 语义代码 MCP |
| Coding Tools MCP | https://github.com/xyTom/coding-tools-mcp | `Apache-2.0` | 仓库代码 MCP |
| Playwright MCP | https://github.com/microsoft/playwright-mcp | `Apache-2.0` | 浏览器自动化 MCP |
| Windows-MCP | https://github.com/CursorTouch/Windows-MCP | `MIT` | Windows 原生自动化 MCP |
| Remote Desktop Commander | https://github.com/desktop-commander/remote-desktop-commander | `hosted relay proprietary; repository docs/manifests only`（manifest license note） | 独立整机控制/救援平面 |
| requests | https://github.com/psf/requests | `Apache-2.0`；`pyproject.toml` 运行时依赖 | WebGPT Python HTTP 客户端运行依赖 |
| setuptools | https://github.com/pypa/setuptools | `MIT`；`pyproject.toml` PEP 517 build backend | 构建依赖，不是运行时 MCP |
| pytest | https://github.com/pytest-dev/pytest | `MIT`；`pyproject.toml` dev dependency | 测试依赖 |
| Ruff | https://github.com/astral-sh/ruff | `MIT`；`pyproject.toml` dev dependency | lint 依赖 |

## 分发边界

- WebGPT-as-Codex 不通过本 notices 文件声称拥有任何第三方项目。
- 不为了“自包含”而复制完整上游仓库；优先使用官方 package/release installer。
- 第三方 runtime artifact 的版本、来源、asset identity 与 digest 由 component metadata/install adapter 验证。
- 本仓库自己的 `LICENSE` 只约束 WebGPT-as-Codex 自身受其覆盖的内容；不会把第三方代码重新许可为 Apache-2.0。
- wheel 的 Stage18 release resource 会包含本 notices 文件及其英文原文，用于让 installed artifact 保留公开 provenance；这不等于把上述第三方软件本体 vendored 进 wheel。
- secrets、账号数据、cookie、token、私有 URL 和机器特定路径不得进入本文件、provenance 数据或 Git。
