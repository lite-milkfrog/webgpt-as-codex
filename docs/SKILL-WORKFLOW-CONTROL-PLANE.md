# Skill Workflow Control Plane — Source of Truth

STATUS = ACTIVE_IMPLEMENTATION

CURRENT_STAGE = WCP-01-REGISTRY-PLANNER-AND-RUN-STATE
NEXT_STAGE = WCP-02-MANAGER-API-AND-HOST-INTEGRATION
AFTER_NEXT_STAGE = WCP-03-WEB-MANAGER-UX

BASE_REPO = lite-milkfrog/webgpt-as-codex
BASE_MAIN = 33b5bec3ca93204529172974cba77324bdeeae9c
WORK_BRANCH = feat/skill-workflow-control-plane-20260922
START_DATE = 2026-09-22

## 1. Product goal

Build the layer above individual Skills.

The system must answer, from durable truth rather than chat memory:

1. Which Skills exist on this machine?
2. Which categories do they belong to?
3. Where are their real filesystem locations?
4. Which category router currently references them?
5. Which Workflow applies to a task?
6. Which Stage is active?
7. Which Skills are required or optional in that Stage?
8. What evidence/gate is required before advancing?
9. What state survives restart or a new ChatGPT window?
10. How can the local Manager inspect and control the system without becoming the source of truth?

The web UI is intentionally last. It must read this system, not define it.

## 2. SoT model

Two layers are mandatory.

### Repository SoT

Repository-owned, versioned and reviewable:

- workflow registry and schema;
- workflow stage/skill/gate definitions;
- routing policy;
- safety boundaries;
- control-plane implementation;
- tests and release behavior.

Canonical files:

- `skills/webgpt-as-codex/workflow-registry.json`
- `skills/webgpt-as-codex/workflows/*.md`
- `src/webgpt_as_codex/skill_workflow.py`
- this document.

### Machine-local SoT

Machine-local and never copied into public Git history:

- discovered Skill roots and real paths;
- logical category/order overrides;
- workflow run state and evidence;
- host-specific open-folder operations.

Canonical state root:

`state_root()/skills/control-plane.json`

Workflow runs:

`state_root()/workflow-runs/*.json`

Machine-local paths are exposed only through loopback Manager APIs.

## 3. Skill model

A Skill record has:

- stable local ID;
- slug/folder name;
- display name and description;
- kind: category-router / skill / reference-skill;
- entrypoint: SKILL.md or REFERENCE.md;
- logical category;
- category source;
- order position;
- route-derived category memberships;
- primary path and resolved path;
- all visible root locations/aliases;
- link/junction evidence.

Default discovery roots:

- `~/.agents/skills`
- `~/.codex/skills`
- packaged WebGPT `skills/`

`WEBGPT_CODEX_SKILL_ROOTS` may override discovery for local deployment/testing.

## 4. Classification and movement policy

"Move" is split into two different operations.

### Logical move — allowed in WCP-01

Dragging/reclassifying a Skill between categories changes only the machine-local overlay.

It does not move the filesystem directory.

Reason: the current category-router design uses relative references to a flat shared Skill root. Blind physical moves can break router paths and global junctions.

### Physical relocation — not yet authorized

Cross-root filesystem relocation requires its own later transaction:

1. inspect source and aliases;
2. compute affected category-router references;
3. verify target root and conflicts;
4. move once;
5. patch routes;
6. verify every route resolves;
7. validate Skill pack;
8. rollback on failure.

No Manager endpoint may accept an arbitrary filesystem path for relocation.

## 5. Workflow model

A Workflow is repository-owned and contains ordered Stages.

Each Stage can define:

- id/title;
- optional context condition;
- required/optional Skill selectors;
- outputs;
- supporting WAC workflow docs;
- gate requirements.

Context conditions are declarative booleans only. No arbitrary code/eval expression is allowed.

Planner states:

- `ready`: all required and selected optional Skills available;
- `degraded`: required Skills available but at least one selected optional Skill missing;
- `blocked`: at least one selected required Skill missing;
- `skipped`: Stage condition not active.

Seed workflows:

- `web-product-build`
- `screenshot-to-frontend`
- `existing-ui-redesign`
- `long-running-engineering`

The registry is intentionally extensible to research, writing, PPT, image/video, Obsidian, CAD and other domains.

## 6. Run state

Workflow runs are machine-local durable evidence.

Each run records:

- run ID;
- workflow ID;
- context;
- created/updated timestamps;
- current Stage;
- run status;
- planner result per Stage;
- selected Skills;
- gate;
- evidence list.

Stage status vocabulary:

`pending / in_progress / passed / failed / blocked / skipped`

Run state must survive Manager/browser closure and ChatGPT conversation changes.

## 7. Manager integration contract

The existing WAC Manager remains loopback-only.

Planned API surfaces:

- `GET /api/skills`
- `POST /api/skills`
- `GET /api/workflows`
- `GET /api/workflow-runs`
- `POST /api/workflow-runs`

Manager mutations must retain the existing:

- loopback host/origin gate;
- `X-WebGPT-Control: 1` header;
- bounded JSON body;
- fixed allowed fields;
- explicit confirmation for local mutations;
- mutation lock;
- activity record.

Opening Explorer must resolve a known Skill ID to a discovered path. The browser must never supply an arbitrary path.

## 8. Frontend order

Do not implement the new visual Manager first.

Required sequence:

1. control-plane schema and SoT;
2. Skill discovery/classification;
3. Workflow registry/planner;
4. durable run state;
5. Manager API;
6. automated tests;
7. real-host verification against the user's shared Skills;
8. only then design the UI;
9. implement Skill browser + categories + drag/reclassify + location/open;
10. implement Workflow graph/run UI;
11. browser acceptance.

The frontend will use the installed Web/UI Skill pack only after Stage 1-7 are stable.

## 9. Current evidence

Implemented on feature branch so far:

- core module created:
  `src/webgpt_as_codex/skill_workflow.py`
- canonical workflow registry created:
  `skills/webgpt-as-codex/workflow-registry.json`

Not yet claimed verified:

- repository tests have not yet run in the user's Windows checkout;
- WAC direct local MCP is unavailable in this chat session;
- RDC device is currently offline;
- Manager API wiring is not yet complete;
- real scan of the current host through this new module is not yet complete;
- frontend has not started.

## 10. Exit criteria

WCP-01 closes only when:

- Skill scanner handles flat Skills + category router references + duplicate/junction aliases;
- logical move/category state persists machine-locally;
- Workflow registry loads and planner resolves required/optional Skills;
- run state can start, transition, persist and reload;
- targeted unit tests pass;
- full existing suite shows no regression.

WCP-02 closes only when Manager API exposes these capabilities with the existing safety contract and host opening is verified.

WCP-03 starts only after WCP-01 and WCP-02 are verified.
