# MCP Operating Guide Contract — 简体中文

[English](../mcp-operating-guide.md) | **简体中文**

Stage9 把 MCP operating knowledge 作为 first-class public-safe artifact。

## Scope
Guide 解释 **how to use a capability correctly**，不是 machine inventory。

可以包含 mental model/boundary、best/poor use、real tool/schema、goal pattern、mistake、diagnosis、verification、performance/context/cost、reusable lesson、alternative/fallback。

禁止包含 machine-local endpoint/port/private hostname、workspace/install path/PID/health、OAuth DB/token/cookie/password/private key、user browser/account state。

## Machine-readable schema
以下 schema key/enum 是协议，保持原样：

```json
{
  "schema_version": 1,
  "component_id": "stable-component-id",
  "mental_model": "...",
  "best_use_cases": [],
  "poor_use_cases": [],
  "capability_evidence": {
    "status": "success|unavailable|failed|unattempted",
    "initialize": "ok|unavailable|failed|unattempted",
    "tools_list": "ok|unavailable|failed|unattempted",
    "tool_count": 0,
    "server_info": {},
    "tools": [
      {
        "name": "actual-tool-name",
        "description": "actual exposed description when present",
        "input_schema": {}
      }
    ],
    "reason": null
  },
  "goal_oriented_patterns": [],
  "common_mistakes": [],
  "failure_diagnosis": [],
  "verification_signals": [],
  "performance_cost_notes": [],
  "accumulated_lessons": [],
  "better_alternatives": []
}
```

## Evidence
- `success`：initialize + tools/list valid；
- `unavailable`：transport/listener/session 不可达；
- `failed`：reached MCP 返回 malformed/contradictory evidence；
- `unattempted`：不适用或 prerequisite 缺失。

不可压成 boolean。

## Guide construction
1. validate manifest + reject credential literal；
2. initialize；
3. reuse session；
4. tools/list；
5. preserve real tool name/description/schema，不从 name 猜 capability；
6. 去除 machine-specific data 后 build Guide；
7. validate required section + secret-bearing value；
8. derive routing recommendation；
9. dry-run default；
10. explicit apply 后仅 machine-local persist，除非正常 repo review 后 intentionally promote。

## Updating
Guide change 要 evidence：changed tools/list schema、重复 operating failure + verified better method、stable performance/context lesson、verified replacement/narrower alternative。one-off local outage 留 stage/machine-local。
