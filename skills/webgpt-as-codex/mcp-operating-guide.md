# MCP Operating Guide Contract

[**English**](mcp-operating-guide.md) | [简体中文](zh-CN/mcp-operating-guide.md)

Stage 9 makes MCP operating knowledge a first-class, public-safe artifact.

## Scope boundary

A Guide explains **how to use a capability correctly**. It is not a machine inventory.

Portable Guide content may include:
- mental model and capability boundaries;
- best and poor use cases;
- actual exposed tool names and input-schema facts;
- goal-oriented usage patterns;
- common mistakes;
- failure diagnosis;
- verification signals;
- performance/context/cost notes;
- accumulated reusable lessons;
- better alternatives and justified fallback conditions.

Portable Guide content must not include:
- machine-local endpoints, ports or private hostnames;
- workspace bindings, install paths, PID/process state or transient health;
- OAuth databases, tokens, cookies, passwords, private keys or credential literals;
- user-specific browser/account state.

Machine-local availability and onboarding receipts belong under the external state directory.

## Machine-readable schema

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

## Evidence semantics

- `success`: initialize and tools/list both returned structurally valid evidence.
- `unavailable`: transport/listener/session could not be reached; capability is not disproven.
- `failed`: a reached MCP returned malformed or contradictory protocol/schema evidence.
- `unattempted`: the probe was intentionally not applicable or prerequisite evidence was absent.

Do not collapse unavailable, failed and unattempted into one boolean.

## Guide construction

1. Validate the component manifest and reject credential-bearing literals.
2. Perform MCP initialize.
3. Reuse the returned MCP session when required.
4. Perform tools/list.
5. Preserve actual tool names, descriptions and input schemas; do not infer missing capability from names.
6. Build the Guide with machine-specific endpoint/state removed.
7. Validate the Guide for required sections and secret-bearing values.
8. Derive a routing recommendation from actual capability evidence.
9. Keep dry-run as the default.
10. On explicit apply, persist component/config, Guide and routing/inventory attachment only in machine-local state unless the component is intentionally promoted to the public registry through normal repository review.

## Updating a Guide

Guide changes require evidence. Prefer:
- a changed tools/list schema;
- a repeated operating failure with a verified better method;
- a stable performance/context lesson;
- a verified capability replacement or narrower alternative.

One-off local outages belong in stage evidence or machine-local state, not the portable Guide.
