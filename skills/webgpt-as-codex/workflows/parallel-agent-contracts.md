# Parallel Agent File Contracts

本文件定义 Parallel Agent Orchestration 的固定命名、文件职责和 machine-readable schema 映射。

## 1. Agent ID

\`\`\`text
<STAGE>00-ORCH
<STAGE><NN>-RESEARCH-<slug>
<STAGE><NN>-DEV-<slug>
<STAGE><NN>-REVIEW-<slug>
<STAGE>90-BUILD
<STAGE>99-AUDIT
\`\`\`

- Stage 前缀保持项目原 Stage ID；
- \`NN\` 为两位数字；
- role 大写；
- slug 使用小写 kebab-case；
- 一旦 dispatch，AGENT_ID 不得复用给另一任务。

## 2. 父目录文件

### STAGE-MANIFEST.json

冻结本次并行 Stage 的 program/stage/base HEAD、Orchestrator、child 列表、角色、依赖、ownership 与状态。

Schema：\`schemas/parallel-agent/stage-manifest.schema.json\`

### FANOUT-PLAN.md

面向人类的并行拆分说明。至少写：

- 为什么值得并行；
- 每个 child 的任务边界；
- 哪些任务只读，哪些会写代码；
- DEV worktree/branch 计划；
- dependencies；
- dispatch 顺序；
- manual fan-in barrier；
- 哪些失败允许 partial continue，哪些是 mandatory blocker。

### CHILD-STATUS.json

父 Agent 的派发/回收索引。它是缓存，不是 child 完成事实的唯一来源；恢复时必须以各 child receipt/handoff + Git 后态重新校准。

### FANIN-SUMMARY.md

人工恢复后的 fresh rescan 汇总。必须区分：

- VERIFIED；
- CONFLICT；
- MISSING；
- BLOCKED；
- HYPOTHESIS；
- REJECTED。

### BUILD-PLAN.json

Build Agent 的结构化输入。

Schema：\`schemas/parallel-agent/build-plan.schema.json\`

## 3. Child 文件

### TASK.md

稳定任务合同，不包含浏览器 transport 细节。

### PROMPT.md

实际提交到 ChatGPT 子 Agent 的自包含提示词。任何重新生成都必须产生新的 prompt SHA-256 与 receipt transaction。

### DISPATCH-RECEIPT.json

Exactly-once transport 记录。

Schema：\`schemas/parallel-agent/dispatch-receipt.schema.json\`

### HANDOFF.json

Child 的 machine-readable 最终回传。

Schema：\`schemas/parallel-agent/handoff.schema.json\`

### REPORT.md / EVIDENCE.md

Research Agent 使用。

### DIFF-SUMMARY.md / TESTS.md

DEV Agent 使用。

## 4. Build 与 Audit

\`<STAGE>90-BUILD/BUILD-RESULT.md\` 记录实际 merge order、冲突处理、integration commit、tests 与剩余风险。

\`<STAGE>99-AUDIT/AUDIT-RESULT.md\` 必须由独立 audit 上下文产生，并明确 PASS / FAIL / BLOCKED 及证据。

## 5. 不允许的替代

- 聊天回复不能替代 HANDOFF.json；
- “我做完了”不能替代 commit/test evidence；
- Parent 的旧记忆不能替代 Fan-in rescan；
- 一个共享 worktree 不能替代多个 DEV Agent 的独立 worktree；
- Build summary 不能替代 independent audit。

