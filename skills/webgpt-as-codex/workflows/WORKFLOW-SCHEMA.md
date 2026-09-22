# Workflow Registry Schema

This document defines the repository-owned Workflow DSL used by WebGPT-as-Codex.

Canonical machine-readable registry:

`../workflow-registry.json`

The registry is the execution definition. The Manager UI is only a view/editor surface and must not invent a second workflow model.

## 1. Registry

```json
{
  "schema_version": 1,
  "id": "webgpt-as-codex-workflow-registry",
  "updated_at": "YYYY-MM-DD",
  "workflows": []
}
```

Required:

- `schema_version`: integer, currently `1`
- `workflows`: array

Recommended:

- `id`
- `updated_at`
- `design`

## 2. Workflow

```json
{
  "id": "web-product-build",
  "title": "Web Product Build",
  "description": "...",
  "supporting_workflows": ["coding.md", "browser.md"],
  "stages": []
}
```

Required:

- `id`: stable kebab-case identifier
- `title`
- `stages`: ordered array

A Workflow owns semantic Stage ordering. It does not own MCP transport details.

## 3. Stage

```json
{
  "id": "browser-qa",
  "title": "Browser QA",
  "when": "browser_verification_needed",
  "skills": [],
  "supporting_workflows": ["browser.md"],
  "outputs": ["browser evidence"],
  "gate": {
    "type": "validation",
    "requires": ["critical flows pass"]
  }
}
```

Supported fields:

- `id`: stable within the Workflow
- `title`
- `when`: optional context condition
- `skills`: Skill selectors
- `supporting_workflows`: WAC workflow docs needed for this Stage
- `outputs`: expected artifacts/evidence
- `gate`: exit requirements

A Stage skipped by `when` is recorded as `skipped`, not silently deleted from the run.

## 4. Skill selector

String shorthand:

```json
"frontend-design"
```

is equivalent to:

```json
{
  "name": "frontend-design",
  "required": true
}
```

Full selector:

```json
{
  "name": "brandkit",
  "required": false,
  "when": "brand_identity_needed"
}
```

Rules:

- `name` matches the Skill folder/slug discovered by the Skill Registry.
- required Skill missing => Stage planner state `blocked`.
- optional selected Skill missing => Stage planner state `degraded`.
- selector condition false => selector is not selected and does not degrade/block the Stage.
- Only current-Stage selected Skills should be loaded into execution context.

## 5. Conditions

Conditions are intentionally data-only.

Single flag:

```json
"reference_image_exists"
```

Composite:

```json
{
  "all": ["existing_product", "browser_available"],
  "any": ["brand_heavy", "visual_reference_needed"],
  "none": ["text_only"]
}
```

Semantics:

- `all`: every named context flag must be truthy
- `any`: at least one named context flag must be truthy
- `none`: every named context flag must be falsy

No `eval`, Python expression, JavaScript expression, shell expression or arbitrary callable is permitted in Workflow conditions.

## 6. Planner state

Planner states describe capability availability before/during a Stage:

- `ready`
- `degraded`
- `blocked`
- `skipped`

Runtime Stage states describe execution:

- `pending`
- `in_progress`
- `passed`
- `failed`
- `blocked`
- `skipped`

These are separate dimensions. A future Stage may be planner-`blocked` while the current Run remains `active`; the Run becomes blocked only when that Stage becomes current.

## 7. Gate

Current gate format:

```json
{
  "type": "validation",
  "requires": ["critical flows pass"]
}
```

Initial gate types are descriptive:

- `artifact`
- `review`
- `validation`
- `visual`
- `evidence`
- `runtime`

WCP v1 stores gate requirements and evidence but does not execute arbitrary gate code. Automated gate adapters must be explicit, allowlisted integrations added later.

## 8. SoT boundaries

Repository SoT owns:

- Workflow definitions
- Stage ordering
- Skill selectors
- gate semantics
- supporting workflow references

Machine-local SoT owns:

- Skill discovery paths
- logical categories/order
- Workflow run state
- execution evidence

The UI must not silently convert a machine-local Skill category drag into a repository Workflow edit.

## 9. Change discipline

A Workflow schema/semantic change requires:

1. update this file;
2. update `workflow-registry.json`;
3. update planner tests;
4. update WAC routing/SKILL rules if execution semantics changed;
5. validate backward compatibility or bump `schema_version`.

Physical Skill relocation is outside this DSL. It is a separate filesystem transaction because it may rewrite category-router references and aliases.
