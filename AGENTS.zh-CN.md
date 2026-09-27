# AGENTS.md（简体中文镜像）

[English](AGENTS.md) | **简体中文**

本仓库是 WebGPT-as-Codex 的公开安全事实源。

## WAC Session Bootstrap — 强制
- 只要当前 Agent session 准备实际使用 WAC / WAC Unified Gateway / WAC 管理的 MCP 能力，就必须在**本 session**先读取 canonical `skills/webgpt-as-codex/SKILL.md`，再开始实质工作。
- 随后执行 `skills/webgpt-as-codex/session-bootstrap.md`：读取 routing；涉及本机时读取 Inventory/environment；复杂多阶段任务先选 Workflow；只加载当前 Stage 所需的 leaf Skills/guides。
- “上一窗口已经读过 Skill”或模型记忆不能替代当前 session bootstrap。
- bootstrap 完成前只允许 liveness/source/Skill 定位等只读发现；禁止工作区修改、浏览器提交、GUI 副作用、部署/升级、发布或 push。

## 部署任务分流
- 如果用户只给了本仓库链接，再说一句“请帮我部署这个项目”之类的话，就把它当作真实部署任务，而不是写教程。
- 修改目标电脑之前，先读 `prompts/ONE-CLICK-AGENT-DEPLOY.md` 和 `docs/DEPLOYMENT.md`，然后完整执行其中的“发现 -> 部署 -> 验证 -> 收口”契约。
- fresh deploy 必须遵守 component metadata 中声明的 WAC bundled derivative source。Coding Tools 与 Serena 必须从本仓库 `vendor/` 完整修改版源码安装，不能静默退回未修改的上游包。
- 部署用户所给仓库 URL 的**当前默认分支最新 HEAD**。过期本地 checkout、旧 release、旧 tag、复制出来的旧 Prompt、旧聊天里的 HEAD 都不能冒充“最新版”。
- 已存在 checkout 时，先核对 remote，再 fetch 默认分支；只有工作树干净且可以安全 fast-forward 时才更新。不得为了追最新而执行 `reset --hard`、`clean` 或丢弃未知本地修改。
- 如果旧 checkout 已脏或已分叉、无法安全 fast-forward，应保留原目录，并在条件允许时另建安全目录，fresh clone 当前默认分支后从新目录部署。
- 最终部署结果必须记录仓库 URL、解析出的默认分支和实际部署的 source HEAD。
- 必须持续做到真实验收；只有确实需要人工账号登录/OAuth consent，或遇到明确安全冲突时才停。

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
