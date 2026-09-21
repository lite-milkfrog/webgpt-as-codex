# WebGPT-as-Codex — One-Click Agent Deployment Prompt

把下面整段交给一个能够操作目标 Windows 电脑的大模型 Agent。它的任务是实际完成部署，不是只写教程。

```text
# WebGPT-as-Codex — AGENT-NATIVE ONE-CLICK DEPLOY

你正在部署 WebGPT-as-Codex。不要只汇报计划；在当前授权范围内持续执行、验证和修复，直到达到完成条件，或只剩必须由人完成的账号/OAuth 授权。

REPOSITORY = <本仓库 URL 或本地路径>
TARGET = 当前 Windows 用户电脑
PRODUCT = WebGPT-as-Codex
CANONICAL_SKILL = skills/webgpt-as-codex/

## 0. 不变量
- 先发现真实环境，再安装；健康的现有服务必须 preserve，禁止为了“统一”重复安装。
- 不 reset/clean 用户仓库，不覆盖未知文件，不 kill 身份不明进程。
- Token、OAuth password、cookie、private key、浏览器登录态、公网私有机器身份不得写进 Git/Prompt/日志。
- listener/process 存活不等于 MCP/OAuth/公网健康；必须分层验证。
- 遇到普通失败先诊断、恢复、换同工具策略，再 fallback；不要把一次失败当作停工理由。
- 任何外部账号登录、Tailscale 登录或 ChatGPT OAuth consent 需要人确认时，只暂停该交互点，其余可执行工作继续完成。

## 1. 必读顺序
1. AGENTS.md
2. README.md 或 README.zh-CN.md
3. docs/CURRENT-PROJECT-STATE.md
4. docs/DEPLOYMENT.md
5. docs/ARCHITECTURE.md
6. skills/webgpt-as-codex/SKILL.md
7. skills/webgpt-as-codex/product-contract.md
8. skills/webgpt-as-codex/routing.md

## 2. 环境与安装
- 确认 Windows、Python、Git、winget、uv、Node/npm、Tailscale 的真实状态。
- 建立项目 venv 并安装 WebGPT-as-Codex；开发 checkout 可使用 editable install。
- 先运行 `webgpt-codex deploy` dry-run，检查 preserve/install/upgrade/diagnose/manual 分类。
- 无冲突后运行 `webgpt-codex deploy --apply`；只有明确采用已有 stopped external install 时才使用项目允许的 adopt 路径。
- 运行 `webgpt-codex bootstrap` / 必要的 apply 路径完成 machine-local state 与系统依赖准备。
- 若 Tailscale 未登录，打开官方登录流程并把该步骤标记为 HUMAN_AUTH_REQUIRED；不要伪造成功。

## 3. MCP 与 Unified Gateway
- 对启用 MCP 做 process/listener -> initialize -> tools/list -> manifest safe call。
- 核心目标：Coding Tools、Serena、Playwright、Windows-MCP 可被 Unified Gateway 聚合；RDC 保持独立 recovery plane。
- 健康外部 MCP 不重复安装；需要 WebGPT 生命周期接管时必须先满足项目 ownership/adoption 规则。
- 启动/同步 MCPJungle routes，验证 Gateway initialize/tools/list 与代表性 safe call。

## 4. OAuth / HTTPS Edge
- 公网正式身份使用稳定的 Tailscale HTTPS 443，不给 Unified Gateway 使用临时随机公网 URL。
- READY 必须同时满足：Gateway、9340 OAuth child、9341 compatibility edge、正确 issuer、Funnel 443 -> 9341。
- 验证 public OAuth metadata、protected-resource metadata、未授权 `/mcp` = 401 + Bearer challenge。
- 完成 DCR + PKCE + token + refresh + authenticated MCP acceptance；不能只看 OAuth 页面能打开。
- 如果 443 被未知服务占用，fail closed 并报告冲突；不要擅自覆盖未知公网入口。

## 5. 一键启动与本机外部后端
- 安装/升级 `webgpt-codex desktop-launcher install` 与 `webgpt-codex autostart install`。
- 如果保留了 WebGPT 不拥有生命周期的现有外部 MCP，而它们重启后不会自动起来：发现它们真实、无 secret 的本地启动器，并写入 `%LOCALAPPDATA%\WebGPT-as-Codex\local-prestart.cmd`。
- `local-prestart.cmd` 只能启动已验证本机后端，不允许写 token/password，不允许抢占 WebGPT 的公网 443。
- 删除/禁用与 WebGPT autostart 重复的旧启动入口前，必须先验证新 launcher 可安全接管；保留可回退备份。
- 连续运行两次 `webgpt-codex launcher --no-open --start-all` 或真实 Autostart，第二次必须幂等且 `fully_ready=true`。

## 6. Skill
- 唯一正式 Skill 名为 `webgpt-as-codex`。
- 不再安装第二套 `computer-agent` Skill；如发现旧版，先归档，再迁移 machine-local overlay/experience，最后退休旧入口。
- 运行 `scripts/sync_webgpt_skill.py` 和 Skill validator；Experience Ledger、53+ regression scenarios、MCP Guides/workflows 不得因迁移丢失。

## 7. 最终验收
必须实际验证并报告：
- `webgpt-codex doctor` 无 required failure；
- `launcher --no-open --start-all` = `fully_ready=true`；
- required unmanaged missing = []；
- Funnel 443 的真实 target 是 managed 9341 edge；
- public OAuth metadata 正确，public `/mcp` 未授权返回 401；
- Unified Gateway 暴露预期核心 MCP 工具；
- desktop launcher 与 autostart = installed + managed；
- 唯一 canonical Skill = WebGPT-as-Codex，validator PASS；
- repository tests / Ruff / secret scan / `git diff --check` PASS（若这是源码 checkout）。

## 8. ChatGPT 最后一公里
当本机和公网全部 READY 后，给出唯一 public MCP URL，让用户在 ChatGPT 中添加 WebGPT-as-Codex，并完成真实 OAuth browser consent。若你拥有已授权的浏览器自动化，可导航到对应设置，但不要替用户猜账号授权。

只有真实 ChatGPT connector 完成 OAuth 并能进行至少一个安全 MCP 实调后，才标记 `CHATGPT_CONNECTOR_VERIFIED`。

最终输出只需要：完成状态、唯一 MCP URL 的安全展示方式、仍需人的交互（若有）、验证摘要和任何明确阻塞。不要让用户重复手工执行你已经能执行的步骤。
```

这个 Prompt 不包含机器特定 URL、密码或 Token；目标 Agent 必须从目标电脑实时发现这些信息。
