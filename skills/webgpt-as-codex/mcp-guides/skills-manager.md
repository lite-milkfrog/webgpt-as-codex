# Skills Manager MCP

Skills Manager is WAC's canonical local Skills + Workflow backend.

## Ownership boundary

- Skills Manager owns Skill discovery, canonical variants, recursive Router/Composite resolution, Workflow definitions, Runs, gates, evidence, and the human Manager UI.
- WAC owns process supervision, gateway registration, tool routing, browser/desktop/code tools, and cross-tool execution.
- Do not rebuild a second Workflow executor inside WAC.

## Runtime

- MCP: `http://127.0.0.1:8943/mcp`
- Manager UI: `http://127.0.0.1:8955/`
- Component ID stays `skills-control-plane` for compatibility.
- Opening the Manager UI is never required for Agent execution.

## Agent usage

Prefer the MCP backend directly:

1. `skills_search` for capability discovery.
2. `skills_resolve` when a Router/Composite Skill may contain internal routing/resources.
3. `workflow_list/search/get` to locate the current Workflow.
4. `workflow_plan` and `workflow_prompt` to compile execution context.
5. `run_create/start/block/evidence_add/resume/succeed` for durable state.

Do not flatten a Composite Skill to its top-level `SKILL.md`. Follow bounded referenced resources and child routes.

## Production Workflows

The standalone repository currently versions:

- Frontend Product Builder v4
- Creator Studio v4

Their JSON definitions live in the standalone `skills-manager/workflows/` directory, not in WAC.

## Install or update

From the WAC repository:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_skills_manager.ps1 -Update
```

The installer refuses to auto-update a dirty Skills Manager worktree.
