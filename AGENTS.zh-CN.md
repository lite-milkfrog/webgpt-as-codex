# AGENTS.md（简体中文镜像）

[English](AGENTS.md) | **简体中文**

本仓库是 WebGPT-as-Codex 的公开安全事实源。

## 不变量
- 开始实质性工作前先读 `docs/CURRENT-PROJECT-STATE.md`。
- 一个 Stage 只拥有一个连贯关注点；没有矛盾证据不得重新打开已关闭 Stage。
- 机器本地状态和 secrets 永不进入 Git。
- 收口前先验证；handoff 前先更新文档。
- 保留 `CURRENT_STAGE / NEXT_STAGE / AFTER_NEXT_STAGE`。
- 自动 handoff 是递归的：每个窗口在自身完成验证收口后，都必须通过 Playwright 提交下一窗口；只有 Final Overall Acceptance 才能结束链条。
- 首选工具失败时先诊断，再 fallback。
- 同一文件同一时间只有一个 writer。
- 并行 writer 使用 worktree。
- 不修改无关仓库或健康服务。
- 优先使用 component manifests/adapters，而不是机器特定硬编码。
- process alive、listener alive、MCP protocol healthy、OAuth healthy、remote reachable 是彼此独立的状态。
- test harness failure 不自动等于目标组件 failure。
- 面向 Windows 的 CLI 输出必须 UTF-8 safe。

## 安全
- 永不提交 OAuth database、password、private key、browser token、cookie、pairing data 或与私有机器绑定的 public URL。
- 外部发布和破坏性操作必须有明确 Stage ownership。
- 现有 production-like MCP/Funnel endpoint 是证据和 fallback，不是可以随意处置的测试 fixture。
