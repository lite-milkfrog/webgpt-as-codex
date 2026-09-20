# Add MCP Workflow

[**English**](add-mcp.md) | [简体中文](zh-CN/add-mcp.md)

Stage 9 turns Add MCP into a discovery-first onboarding workflow. The workflow is bounded: it learns capabilities, builds operating knowledge and attaches routing/inventory evidence, but it does not acquire arbitrary lifecycle authority.

## Default contract

`webgpt-codex add-mcp NAME URL [--role ROLE]` is a **dry-run**.

Dry-run:
1. constructs and validates a public-safe manifest candidate;
2. rejects credential-bearing literals;
3. performs real MCP initialize;
4. reuses the returned session when required;
5. performs tools/list;
6. classifies evidence as success / unavailable / failed / unattempted;
7. preserves actual exposed tool names/descriptions/input schemas;
8. builds and validates an MCP Operating Guide;
9. derives a routing recommendation from actual capability evidence;
10. reports the plan without persisting it.

Mutation requires explicit `--apply`.

## Apply contract

`--apply` writes only to the machine-local WebGPT-as-Codex state directory:
- `config/components/<id>.json` — machine-local component manifest;
- `config/mcp-guides/<id>.json` — machine-readable Operating Guide;
- `config/mcp-onboarding/<id>.json` — routing/inventory attachment and capability status.

Apply is idempotent for the same manifest. Reusing the same component id with a different manifest fails closed. A custom component may not shadow an existing repository component id.

Manager and Doctor see an applied component through the existing registry. This does **not** add the component to Stage 8 runtime ownership or Manager Restart authority.

## Capability discovery semantics

Never infer capability from component/server/tool names.

- `success`: initialize and tools/list are both structurally valid.
- `unavailable`: the service/session/transport cannot currently be reached.
- `failed`: the service was reached but returned malformed/contradictory protocol or schema evidence.
- `unattempted`: the probe is intentionally not applicable or a prerequisite is absent.

Unavailable is not failed. One failed invocation is not proof that the MCP itself is unavailable.

## Operating Guide

See `mcp-operating-guide.md`.

The Guide covers:
- mental model;
- best and poor use cases;
- actual exposed tools/schema;
- goal-oriented patterns;
- common mistakes;
- failure diagnosis;
- verification signals;
- performance/context/cost notes;
- accumulated lessons;
- better alternatives.

Routing decides **which** capability should own an intent. The Guide teaches **how** to use that capability correctly.

## Public-safe versus machine-local state

Repository component manifests and portable Guide documents may reference only reusable public-safe facts.

Do not commit:
- local endpoint/port overrides;
- process/PID/health receipts;
- workspace bindings or local paths;
- private URLs;
- credentials, OAuth state, cookies, tokens or private keys.

Representative repository Guide attachments currently exist for Serena and Coding Tools. Their live Stage 9 validation came from real initialize/tools/list evidence; transient live status remains stage/local evidence rather than portable truth.

## Lifecycle boundary

Onboarding is not runtime supervision.

A newly added MCP:
- can appear in registry/Manager/Doctor;
- can have a Guide and routing recommendation;
- cannot be started/killed/restarted merely because it was discovered;
- does not enter `MANAGER_RESTARTABLE` or a runtime adapter automatically.

Stage 8 ownership rules remain authoritative.

## Failure protocol

1. classify manifest/schema validation separately from transport/protocol failure;
2. inspect initialize and tools/list evidence;
3. distinguish unavailable from malformed/failed;
4. check binding/session/auth/harness before fallback;
5. do not restart healthy external services for discovery convenience;
6. record reusable MCP-specific lessons in the Guide and general lessons in the Experience Ledger/Skill.
