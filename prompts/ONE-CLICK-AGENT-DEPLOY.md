# WebGPT-as-Codex — One-Click Agent Deployment Prompt

把下面整段交给一个能够操作目标 Windows 电脑的大模型 Agent。它的任务是实际完成部署，不是只写教程。

```text
# WebGPT-as-Codex — AGENT-NATIVE ONE-CLICK DEPLOY

你正在部署 WebGPT-as-Codex。不要只汇报计划；在当前授权范围内持续执行、验证和修复，直到达到完成条件，或只剩必须由人完成的账号/OAuth 授权。

REPOSITORY = <本仓库 URL 或本地路径>
TARGET = 当前 Windows 用户电脑
PRODUCT = WebGPT-as-Codex
CANONICAL_SKILL = skills/webgpt-as-codex/
CANONICAL_DEPLOYMENT_ARTIFACT = GitHub source checkout
BUNDLED_DERIVATIVES = vendor/coding-tools-mcp + vendor/serena-agent + vendor/playwright-mcp + vendor/playwright
REQUIRED_STANDALONE_COMPONENT = https://github.com/lite-milkfrog/skills-manager

## -1. Source Freshness Gate（“最新版”必须可证明）
- 如果任务起点只有 GitHub 仓库 URL，就以**用户给出的仓库**为 source of truth，先解析它的当前 default branch，再 clone/fetch；不得因为本机碰巧有旧目录就直接部署旧 HEAD。
- fresh clone 必须来自用户给出的仓库 URL 的当前 default branch；除非用户明确指定，否则不得用旧 release/tag/archive 代替 default-branch latest。
- 已存在 checkout 时，先确认其 remote 对应用户给出的仓库，再 `git fetch` 当前 default branch，并比较本地 `HEAD` 与 `origin/<default-branch>`。
- 只有工作树干净、没有未知本地修改，并且可以安全 fast-forward 时，才允许用 `git pull --ff-only`（或等价 fast-forward）更新旧 checkout。
- 如果 checkout dirty/diverged，不得用 `reset --hard` / `clean` / 覆盖未知文件来追最新；保留原目录，在可行时另建安全目录 fresh clone 最新 default branch 并从那里部署。若连安全新目录都无法建立，再明确报告阻塞。
- **实际安装 WebGPT 源码前再次 fetch 一次**，记录 `SOURCE_REPOSITORY`、`SOURCE_BRANCH`、`SOURCE_HEAD`，并确认部署源 `HEAD == origin/<default-branch>`。这三个字段进入最终验收摘要。
- 当前仓库维护 Coding Tools 与 Serena 的完整 derivative source；fresh deployment 必须保留 source checkout，不能先做一个不含 `vendor/` 的瘦 wheel 再删除 checkout。
- 后续 WebGPT lifecycle/deploy 命令必须以该 checkout 根为 cwd；如果 Agent 的执行器会改变 cwd，则为部署进程设置 `WEBGPT_CODEX_SOURCE_ROOT=<checkout-root>`，确保安装进 venv 后仍能定位 bundled derivative source。
- 旧聊天记录、旧 handoff、旧 release note 只能作为历史证据，不能覆盖当前 Git 远端真值。

## 0. 不变量
- 先发现真实环境，再安装；健康的现有服务必须 preserve，禁止为了“统一”重复安装。
- 不 reset/clean 用户仓库，不覆盖未知文件，不 kill 身份不明进程。
- Token、OAuth password、cookie、private key、浏览器登录态、公网私有机器身份不得写进 Git/Prompt/日志。
- listener/process 存活不等于 MCP/OAuth/公网健康；必须分层验证。
- 遇到普通失败先诊断、恢复、换同工具策略，再 fallback；不要把一次失败当作停工理由。
- **禁止把“继续 / 完成剩余任务 / 自动收口 / 一直做完”解释成 reboot、shutdown、sign-out、断网、重启网卡、Tailscale logout/reset 的授权。** 这些动作必须获得当前轮次针对动作本身的明确人工授权。
- 为验证 reboot recovery，默认使用服务级 stop/start、真实 Autostart 实跑、故障注入和 post-state 验证；没有同轮明确授权时，不得为了验收真实重启电脑。
- 如果目标机重启后需要人工恢复网络，远程 Agent 不得主动触发重启，除非用户明确授权且有人能在本地恢复网络。
- 任何外部账号登录、Tailscale 登录或 ChatGPT OAuth consent 需要人确认时，只暂停该交互点，其余可执行工作继续完成。

## 1. 必读顺序
1. AGENTS.md
2. README.md 或 README.zh-CN.md
3. docs/CURRENT-PROJECT-STATE.md
4. docs/DEPLOYMENT.md
5. docs/ARCHITECTURE.md
6. skills/webgpt-as-codex/SKILL.md
7. skills/webgpt-as-codex/session-bootstrap.md
8. skills/webgpt-as-codex/product-contract.md
9. skills/webgpt-as-codex/routing.md

从这一刻起，canonical WebGPT-as-Codex Skill 是整个部署 session 的强制执行合同；不得只在安装 Skill 时读一次，也不得用旧聊天记忆替代当前 session bootstrap。

## 2. 环境与安装
- 确认 Windows、Python、Git、winget、uv、Node/npm、Tailscale 的真实状态。
- 建立项目 venv 并安装 WebGPT-as-Codex；开发 checkout 可使用 editable install。
- 先运行 `webgpt-codex deploy` dry-run，检查 preserve/install/upgrade/diagnose/manual 分类。
- 无冲突后运行 `webgpt-codex deploy --apply`；只有明确采用已有 stopped external install 时才使用项目允许的 adopt 路径。
- 对 component metadata 标记为 `bundled_derivative=true` 的组件，必须从**当前 checkout 的 vendor 完整源码**安装并记录 source path/base revision；禁止为了省事改回 PyPI/npm 上游原版。当前包括：
  - `vendor/coding-tools-mcp/`：完整 Apache-2.0 Coding Tools derivative；
  - `vendor/serena-agent/`：完整 Serena v1.7.0 MIT derivative。
  - `vendor/playwright-mcp/`：完整 Playwright MCP v0.0.81 Apache-2.0 source snapshot，通过 `bundled-npm` 安装；
  - `vendor/playwright/`：与其依赖匹配的完整 Playwright / Playwright Core source baseline（gitHead `d1ead3e...`）。
- Playwright 的 WAC runtime derivative 仍由本仓库 `playwright_hotfix.py`/launcher 应用到 bundled MCP 安装出来的 pinned Core；部署后必须验证 hotfix markers / exactly-once / tab reconciliation，不能仅安装 source 就宣称已复现当前 WAC 行为。
- Skills Manager / `skills-control-plane` 是 WAC 的 required standalone component，不在 WAC 仓库内重复分发源码。部署或升级 WAC 时必须从当前 WAC checkout 执行：
  `powershell -ExecutionPolicy Bypass -File scripts/install_skills_manager.ps1 -Update`
  该脚本 fresh machine 会 clone `lite-milkfrog/skills-manager` 的 `main`，已有 clean checkout 会 fetch + `--ff-only` 更新到最新 `origin/main`，dirty worktree 必须 preserve 并阻止自动覆盖。
- 记录 `SKILLS_MANAGER_REPOSITORY / SKILLS_MANAGER_BRANCH / SKILLS_MANAGER_HEAD`；验收时必须证明实际安装的 Skills Manager HEAD 等于当次读取的远端默认分支最新 HEAD。
- Skills Manager 安装器会导入仓库中的 production Workflows 并安装 WAC integration wrapper。不得仅因为 `components/skills-control-plane.json` 已存在就跳过 standalone source 安装/更新。
- 运行 `webgpt-codex bootstrap` / 必要的 apply 路径完成 machine-local state 与系统依赖准备。
- 若 Tailscale 未登录，打开官方登录流程并把该步骤标记为 HUMAN_AUTH_REQUIRED；不要伪造成功。

## 3. MCP 与 Unified Gateway
- 对启用 MCP 做 process/listener -> initialize -> tools/list -> manifest safe call。
- 核心目标：Coding Tools、Serena、Playwright、Windows-MCP 可被 Unified Gateway 聚合；RDC 保持独立 recovery plane。
- 健康外部 MCP 不重复安装；需要 WebGPT 生命周期接管时必须先满足项目 ownership/adoption 规则。
- 启动/同步 MCPJungle routes，验证 Gateway initialize/tools/list 与代表性 safe call。
- 对 `skills-control-plane` 额外验证：8943 MCP initialize + tools/list + 代表性 `skills_status`/只读 Skill 查询；确认 WAC external-ensure wrapper 指向独立 `skills-manager` checkout，而不是历史 `skill-control-plane` 工作区。

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
- 当前 canonical Skill 必须为 `1.4.0` 或仓库中更新版本。
- 每个新的 WAC Agent session 都必须重新完成 `session-bootstrap.md`；任何 substantive WAC mutation 前都要实际读取当前 `SKILL.md` + `routing.md`，不能用上一窗口记忆替代。
- 多阶段任务先匹配 Workflow，再只加载当前 Stage 需要的 Skills；强制使用 canonical Skill 不等于一次性加载整个 Skills 库。
- 不再安装第二套 `computer-agent` Skill；如发现旧版，先归档，再迁移 machine-local overlay/experience，最后退休旧入口。
- 运行 `scripts/sync_webgpt_skill.py` 和 Skill validator；Experience Ledger、60+ regression scenarios、MCP Guides/workflows 不得因迁移丢失。

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
- 当前 session 已完成 `session-bootstrap.md`，且 portable Skill 与本机同步版本一致；
- Coding Tools / Serena / Playwright MCP 实际安装来源与 component metadata 的 bundled derivative source 一致，不是 registry-latest fallback；
- Skills Manager 独立 checkout = 当前远端默认分支最新 HEAD，`components/skills-control-plane.json` 仍为 required/enabled，8943 MCP 可用，8955 Manager 可选打开，WAC binding 指向独立 `skills-manager`；
- Serena derivative 保留 `implementation_fallback=exact-name-and-kind`；Coding Tools bundled tree 保留 upstream LICENSE/NOTICE 与 WAC 修改；Playwright bundled source/version/core gitHead 一致且 overlay 的目标 signature 验证通过；
- repository tests / Ruff / secret scan / `git diff --check` PASS（若这是源码 checkout）。

## 8. ChatGPT 最后一公里
当本机和公网全部 READY 后，给出唯一 public MCP URL，让用户在 ChatGPT 中添加 WebGPT-as-Codex，并完成真实 OAuth browser consent。若你拥有已授权的浏览器自动化，可导航到对应设置，但不要替用户猜账号授权。

只有真实 ChatGPT connector 完成 OAuth 并能进行至少一个安全 MCP 实调后，才标记 `CHATGPT_CONNECTOR_VERIFIED`。

最终输出只需要：完成状态、唯一 MCP URL 的安全展示方式、仍需人的交互（若有）、验证摘要和任何明确阻塞。不要让用户重复手工执行你已经能执行的步骤。
验证摘要必须包含 `SOURCE_REPOSITORY / SOURCE_BRANCH / SOURCE_HEAD` 和 `SKILLS_MANAGER_REPOSITORY / SKILLS_MANAGER_BRANCH / SKILLS_MANAGER_HEAD`，用于证明 WAC 与独立 Skills Manager 都来自当次解析出的最新默认分支版本。
```

这个 Prompt 不包含机器特定 URL、密码或 Token；目标 Agent 必须从目标电脑实时发现这些信息。
