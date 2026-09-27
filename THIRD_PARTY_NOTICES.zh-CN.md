# 第三方声明与上游来源（简体中文）

[English](THIRD_PARTY_NOTICES.md) | **简体中文**

本仓库包含第三方组件的集成、部署元数据或运行时互操作配置。产品 README 继续聚焦 WebGPT-as-Codex；第三方来源与许可证事实记录在本文件、`docs/THIRD-PARTY-PROVENANCE.json` 和 `components/*.json`。

> 本文件用于来源/许可信息披露，不替代任何第三方上游项目自己的许可证或 NOTICE。实际重新分发某个第三方 binary/package 时，必须遵守该具体上游版本附带的精确许可证文本与义务。

release secret scan 将 pinned 的完整 upstream source snapshot 视为有 provenance 的第三方输入；在这些 `vendor/` 树中继续扫描 WAC 实际修改的 derivative 文件与 `WAC_*` 证据。所有 `vendor/` 之外的 WAC-owned 源码仍完整扫描。

| 组件/依赖 | 上游/来源 | 许可/来源事实 | WebGPT 关系 |
|---|---|---|---|
| MCPJungle | https://github.com/mcpjungle/MCPJungle | `MPL-2.0`（来自 `components/mcpjungle.json`） | 本地 MCP 聚合/Gateway 运行依赖 |
| mcp-auth-proxy | https://github.com/sigbit/mcp-auth-proxy | `MIT`（来自 `components/mcp-auth-proxy.json`） | OAuth Edge 运行依赖 |
| Tailscale | https://github.com/tailscale/tailscale | `BSD-3-Clause core`（来自 `components/tailscale.json`） | HTTPS/Funnel 传输依赖 |
| Serena | https://github.com/oraios/serena | bundled derivative 基于完整 `v1.7.0`（最后一个 MIT Serena application release）；upstream v2+ application 为 GPL-3.0-or-later | 完整修改版源码随 `vendor/serena-agent/` 分发，并保留 upstream license 与 WAC 修改/diff 证据 |
| Coding Tools MCP | https://github.com/xyTom/coding-tools-mcp | `Apache-2.0` | 完整修改版源码随 `vendor/coding-tools-mcp/` 分发，并保留 upstream LICENSE/NOTICE 与 WAC 修改/diff 证据 |
| Playwright MCP / Playwright Core | https://github.com/microsoft/playwright-mcp / https://github.com/microsoft/playwright | `Apache-2.0` | 完整 MCP v0.0.81 与匹配的 Playwright gitHead 源码快照随 `vendor/playwright-mcp/`、`vendor/playwright/` 分发；WAC runtime 修改由 deterministic hotfix 应用，并在 vendor 中保留 exact bundle diff 证据 |
| Windows-MCP | https://github.com/CursorTouch/Windows-MCP | `MIT` | Windows 原生自动化 MCP |
| Remote Desktop Commander | https://github.com/desktop-commander/remote-desktop-commander | `hosted relay proprietary; repository docs/manifests only`（manifest license note） | 独立整机控制/救援平面 |
| requests | https://github.com/psf/requests | `Apache-2.0`；`pyproject.toml` 运行时依赖 | WebGPT Python HTTP 客户端运行依赖 |
| setuptools | https://github.com/pypa/setuptools | `MIT`；`pyproject.toml` PEP 517 build backend | 构建依赖，不是运行时 MCP |
| pytest | https://github.com/pytest-dev/pytest | `MIT`；`pyproject.toml` dev dependency | 测试依赖 |
| Ruff | https://github.com/astral-sh/ruff | `MIT`；`pyproject.toml` dev dependency | lint 依赖 |

## 分发边界

- WebGPT-as-Codex 不通过本 notices 文件声称拥有任何第三方项目。
- 默认不为了“自包含”而复制完整上游仓库；优先使用官方 package/release installer。明确例外是 WebGPT 已实质二次开发、且 fresh deployment 必须复现的组件：Coding Tools 与 Serena 完整 derivative source 保存在 `vendor/`，并保留许可证、来源和 exact diff 证据。
- 第三方 runtime artifact 的版本、来源、asset identity 与 digest 由 component metadata/install adapter 验证。
- 本仓库自己的 `LICENSE` 只约束 WebGPT-as-Codex 自身受其覆盖的内容；不会把第三方代码重新许可为 Apache-2.0。
- Git 源码树会有意 vendored `vendor/coding-tools-mcp/` 与 `vendor/serena-agent/`；当前 Python wheel 仍是 thin artifact，不能单独作为这两个 derivative 的完整 fresh-machine 部署源，canonical 部署保留已验证的 source checkout。
- secrets、账号数据、cookie、token、私有 URL 和机器特定路径不得进入本文件、provenance 数据或 Git。
