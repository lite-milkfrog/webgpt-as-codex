# Parallel Agent Orchestration

## 目的

用于用户明确要求通过 Playwright 打开多个独立 ChatGPT 对话，让多个子 Agent 并行调研或开发，再由父 Agent 在人工恢复后统一扫描、汇总、构建与审计的任务。

它不是“多个窗口同时随意工作”，而是一个持久化 Fan-out / Manual Fan-in 协议：

\`Parent Orchestrator -> child contracts -> exactly-once Playwright dispatch -> STOP/WAIT -> manual resume -> filesystem/Git rescan -> synthesis -> Build -> independent audit\`

浏览器窗口是可替换 worker；文件、Git refs、测试证据和 durable receipt 才是 Source of Truth。

## 1. 什么时候启用

满足任一条件即可启用：

- 用户明确要求“子 Agent / 多 Agent / 多窗口并行 / Playwright 开多个窗口”；
- 一个 Stage 可以拆成多个互不依赖的调研问题；
- 一个 Stage 可以拆成多个具有明确 ownership 的独立开发 slice；
- 用户希望先 Fan-out，等自己确认子 Agent 全部完成后，再回父窗口触发统一汇总；
- 需要多个独立观点后再由 Build / Integration Agent 合并。

以下情况默认不要启用：

- 单任务很短，拆分成本高于收益；
- 多个开发任务必然修改同一热点文件且无法安全隔离；
- 用户只要求普通 Loop Engineering 串行接力；
- 并行会扩大未授权外部副作用。

## 2. 角色和 ID

每个并行 Stage 使用固定角色模型：

- \`<STAGE>00-ORCH\`：父 Agent / Orchestrator / Synthesizer。第一次运行只负责任务冻结、拆分、合同生成和 dispatch；人工恢复后负责全量 rescan 与汇总。
- \`<STAGE><NN>-RESEARCH-<slug>\`：只读调研子 Agent。
- \`<STAGE><NN>-DEV-<slug>\`：开发子 Agent。必须独立 branch + worktree + ownership。
- \`<STAGE><NN>-REVIEW-<slug>\`：可选独立复核子 Agent。
- \`<STAGE>90-BUILD\`：Build / Integration Agent。只消费已验证 handoff，负责 merge/cherry-pick、冲突处理、integration tests。
- \`<STAGE>99-AUDIT\`：独立最终审计。不能把 Build Agent 的“已通过”当事实继承。

\`NN\` 默认从 01 开始递增。角色单词大写，slug 使用小写 kebab-case。

## 3. 状态根与目录合同

portable Skill 只定义逻辑根 \`<PARALLEL_STATE_ROOT>\`。真实机器路径必须来自 \`environment.local.md\`，不得把机器专属绝对路径写进 portable Skill。

目录固定为：

\`\`\`text
<PARALLEL_STATE_ROOT>/
  <PROGRAM_ID>/
    <STAGE_ID>/
      B00-ORCH/
        STAGE-MANIFEST.json
        FANOUT-PLAN.md
        CHILD-STATUS.json
        FANIN-SUMMARY.md
        BUILD-PLAN.json
      B01-RESEARCH-cache/
        TASK.md
        PROMPT.md
        DISPATCH-RECEIPT.json
        HANDOFF.json
        REPORT.md
        EVIDENCE.md
      B02-DEV-cache/
        TASK.md
        PROMPT.md
        DISPATCH-RECEIPT.json
        HANDOFF.json
        DIFF-SUMMARY.md
        TESTS.md
      B90-BUILD/
        TASK.md
        BUILD-RESULT.md
      B99-AUDIT/
        TASK.md
        AUDIT-RESULT.md
\`\`\`

示例里的 \`B\` 仅表示 Stage ID。实际目录必须使用真实 Stage 前缀。

Machine-readable 合同见：

- \`schemas/parallel-agent/stage-manifest.schema.json\`
- \`schemas/parallel-agent/dispatch-receipt.schema.json\`
- \`schemas/parallel-agent/handoff.schema.json\`
- \`schemas/parallel-agent/build-plan.schema.json\`

## 4. 父 Agent 第一次运行：只编排，不吞子任务

\`<STAGE>00-ORCH\` 第一次进入时默认不得直接完成任何已分配给子 Agent 的研究或开发任务。

必须按顺序：

1. Bootstrap 当前 WAC Skill、Workflow、项目 SoT、Git 和工具状态；
2. 冻结本 Stage 唯一主目标与 out-of-scope；
3. 判断哪些 slice 适合并行，哪些必须串行；
4. 为每个子 Agent 明确 task、role、ownership、dependencies、expected outputs、exit criteria；
5. 生成 \`STAGE-MANIFEST.json\`、\`FANOUT-PLAN.md\` 与每个 child 的 \`TASK.md\`；
6. 为每个 child 生成自包含 \`PROMPT.md\`；
7. 逐个通过 Playwright exactly-once dispatch；
8. 每个 child 建立 durable \`DISPATCH-RECEIPT.json\`；
9. 所有计划内 child 完成 dispatch/takeover 检查后，父 Agent 写入 \`WAITING_FOR_CHILDREN\` 并停止。

父 Agent不后台等待、不轮询 ChatGPT、不假装异步工作。

## 5. 子 Agent 分类

### 5.1 Research Agent

Research Agent 默认只读：

- 可以共享同一 repo 读取源码、SoT 与测试；
- 可以 Web research；
- 不修改产品代码；
- 不创建产品 commit；
- 结束时至少生成 \`HANDOFF.json + REPORT.md + EVIDENCE.md\`。

如果调研过程中必须做实验性修改，必须升级为 DEV role 并分配独立 worktree/branch，不能偷偷变成第二 writer。

### 5.2 Development Agent

DEV Agent 必须：

- 独立 Git branch；
- 独立 Git worktree；
- 明确 ownership scope；
- 从 manifest 固定的 \`base_head\` 或明确 dependency commit 开始；
- 只在自己的 worktree 写入；
- 运行 targeted tests；
- 形成 path-scoped commit；
- 结束时生成 \`HANDOFF.json + DIFF-SUMMARY.md + TESTS.md\`；
- 不 merge 主分支，不修改别的 child worktree，不删除其它 Agent 产物。

多个 DEV Agent 不得共享同一 worktree。

## 6. Child Prompt 合同

每个 \`PROMPT.md\` 必须自包含：

- PROGRAM_ID / STAGE_ID / AGENT_ID / ROLE；
- Parent Orchestrator ID；
- 唯一任务；
- out-of-scope；
- project/repo/source/tests/SoT 精确路径；
- base HEAD；
- branch/worktree（DEV 必填）；
- ownership scope；
- dependencies；
- WAC Skill 根与必须读取的 workflow；
- 工具执行图；
- 输入文件；
- 输出文件及 schema；
- tests/gates；
- failure recovery；
- forbidden actions；
- exit criteria；
- 最终必须写 \`HANDOFF.json\`，聊天回复不是 handoff 真源。

如果关键路径、writer ownership 或输出位置仍需要 child 猜测，则 prompt 不合格，不得 dispatch。

## 7. Playwright Exactly-once Fan-out

Playwright 只承担 Agent transport，不承担 Workflow 真源。

每个 child 使用独立 transaction：

\`PROMPT_READY -> DISPATCH_ATTEMPTED -> DISPATCHED -> TAKEOVER_CONFIRMED\`

规则：

1. 先把完整 prompt 落盘；
2. 对 whitespace-normalized prompt 计算 SHA-256；
3. 写 \`DISPATCH-RECEIPT.json\`，包含 AGENT_ID、prompt path、hash 和 transaction state；
4. 在任何真实 submit primitive 前先持久化 \`DISPATCH_ATTEMPTED\`；
5. 一个 child 对应一个目标 ChatGPT conversation；
6. submit 报错/超时先查后态；
7. receipt 已到 \`DISPATCH_ATTEMPTED\` 或更后状态时，禁止 blind resubmit；
8. exact user prompt、conversation URL、composer/post-state、assistant generating/response 能证明后，升级为 \`DISPATCHED / TAKEOVER_CONFIRMED\`；
9. 不允许没有 receipt 地批量开一堆空白 tab；
10. 只清理由当前 Orchestrator 创建且确认未使用的重复/空白 tab，不动用户原有窗口。

## 8. Manual Fan-in Barrier

Fan-out 完成后，父 Agent 必须停止在：

\`WAITING_FOR_CHILDREN\`

用户之后重新唤醒父窗口时，才进入：

\`MANUAL_FANIN_RESUME -> FULL_RESCAN\`

这不是“继续回忆之前聊天”，而是一次 fresh-state reconstruction。

## 9. Fan-in Rescan

父 Agent恢复后必须重新扫描：

1. \`STAGE-MANIFEST.json\`；
2. 每个 child 的 \`DISPATCH-RECEIPT.json\`；
3. 每个 child 的 \`HANDOFF.json\`；
4. Research 的 REPORT/EVIDENCE；
5. DEV 的 branch/worktree/commit 是否真实存在；
6. DEV 的 diff/test evidence；
7. dependencies 是否满足；
8. ownership 是否越界；
9. child 之间是否产生冲突或互斥结论；
10. 是否有 child 缺失、FAILED、BLOCKED、stale 或只在聊天里说“完成”但未落盘。

聊天记忆只可作为线索，不能替代上述证据。

父 Agent生成：

- \`FANIN-SUMMARY.md\`
- \`BUILD-PLAN.json\`

只有文件/Git 后态满足条件的 child 才能进入 Build。

## 10. Build / Integration

\`<STAGE>90-BUILD\` 必须使用专用 integration branch/worktree。

Build 前：

- 读取所有 ready handoff；
- 建 dependency DAG；
- 预测同文件/同 symbol 冲突；
- 固定 merge/cherry-pick 顺序；
- 明确哪些 handoff 仅提供研究结论、不包含代码；
- 对 base drift 做检查。

Build 期间：

- 只从 \`ready_for_build=true\` 的 DEV handoff 消费 commit；
- 冲突不能用“最后写入覆盖”解决；
- 需要根据原任务和 handoff evidence 重新判断语义；
- 合并后运行 integration targeted tests 与 broader gate；
- 形成 \`BUILD-RESULT.md\` 和 integration commit。

子 Agent 永远不自行 merge 主分支。

## 11. Independent Audit

\`<STAGE>99-AUDIT\` 独立读取：

- 原始 Stage contract；
- child handoffs；
- FANIN-SUMMARY；
- BUILD-PLAN；
- integration diff；
- tests/runtime evidence。

Audit 不得只读 Build summary 后签字。

至少检查：

- 所有 mandatory child 是否有真实 handoff；
- 并行 ownership 是否被违反；
- 合并是否丢掉 child 结论；
- conflict resolution 是否合理；
- tests/gates 是否覆盖 Stage exit criteria；
- 是否存在未报告 RED/BLOCKED；
- 是否可以进入下一主 Stage。

## 12. 状态定义

Orchestrator 状态至少支持：

- \`ORCHESTRATOR_BOOTSTRAP\`
- \`FANOUT_PLANNED\`
- \`DISPATCHING\`
- \`WAITING_FOR_CHILDREN\`
- \`MANUAL_FANIN_RESUME\`
- \`FANIN_RESCAN\`
- \`FANIN_READY\`
- \`BUILDING\`
- \`AUDITING\`
- \`STAGE_COMPLETE\`
- \`PARTIAL_CHILD_FAILURE\`
- \`PAUSED_EXTERNAL_BLOCKER\`
- \`USER_STOPPED\`

Child 状态至少支持：

- \`PLANNED\`
- \`PROMPT_READY\`
- \`DISPATCH_ATTEMPTED\`
- \`DISPATCHED\`
- \`TAKEOVER_CONFIRMED\`
- \`HANDOFF_READY\`
- \`FAILED\`
- \`BLOCKED\`
- \`SKIPPED\`

## 13. 与 Loop Engineering 的关系

Parallel Agent Orchestration 是 Loop Engineering 的上层编排能力，不替代单 Agent 执行协议。

- child 内部仍按 WAC bootstrap / routing / bounded execution / validation / docs-before-handoff 工作；
- parent 管理 fan-out/fan-in，不替 child 做已经分配的工作；
- Build 是新的单 writer；
- Audit 与 Build 分离；
- 当前并行 Stage 完成后，再回到 canonical 主 Program 的 NEXT_STAGE。

## 14. 完成定义

只有满足全部条件才允许 \`STAGE_COMPLETE\`：

- 所有 mandatory child 均为 \`HANDOFF_READY\`，或 manifest 中有明确且获准的 skip/waiver；
- 所有 DEV child 的 branch/worktree/commit 与 tests 均已复核；
- FANIN-SUMMARY 与 BUILD-PLAN 已基于 fresh rescan 生成；
- Build 已完成且 integration gates 通过；
- Independent Audit PASS；
- Stage SoT/进度已更新；
- 下一主 Stage 或 Loop handoff 已明确。

Fan-out 完成只代表 \`WAITING_FOR_CHILDREN\`，不代表 Stage 完成。

