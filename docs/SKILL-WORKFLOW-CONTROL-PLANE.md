# Skill Workflow Control Plane — Source of Truth

STATUS = ACTIVE_IMPLEMENTATION

CURRENT_STAGE = WCP-03-WEB-MANAGER-UX
NEXT_STAGE = WCP-04-WEB-MANAGER-BROWSER-ACCEPTANCE
AFTER_NEXT_STAGE = WCP-05-LIVE-INTEGRATION-AND-SKILLS-CONTROL-MERGE

BASE_REPO = lite-milkfrog/webgpt-as-codex
BASE_MAIN = c3884abecbb6644fb33c353f67fc76b895d44454
WORK_BRANCH = feat/skill-workflow-control-plane-clean-20260922
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

### Logical move — implemented

Dragging/reclassifying a Skill between categories changes only the machine-local overlay.

It does not move the filesystem directory.

Reason: the current category-router design uses relative references to a flat shared Skill root. Blind physical moves can break router paths and global junctions.

### Physical relocation — implemented, host verification pending

Cross-root filesystem relocation is now a guarded two-step transaction:

1. resolve a known Skill ID and target root ID;
2. reject category routers, links/junctions, aliases and ambiguous duplicate slugs;
3. compute affected category-router references;
4. verify target root, router availability and path conflicts;
5. return a read-only relocation plan;
6. require explicit confirmation before mutation;
7. move once and patch source/target routes atomically;
8. rescan and verify entrypoint + route membership;
9. rollback routes, location and local overlay if validation fails.

No Manager endpoint accepts an arbitrary filesystem path for relocation.

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

Implemented API surfaces:

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

Implemented on the clean integration branch:

- Skill scanner + category/router discovery + duplicate/junction identity handling;
- logical category/order overlays;
- Workflow registry, schema, planner and durable run state;
- headless `webgpt-codex skill-workflow` CLI;
- loopback Manager Skills / Workflows / Runs APIs;
- safe known-Skill Explorer operation;
- relocation plan + confirmed physical relocation transaction with route patching and rollback;
- WAC routing updated to `Task -> Workflow -> Stage -> Skills -> MCP/tool -> gate`;
- targeted tests and dedicated control-plane CI workflow.

Branch recovery note:

- the original feature branch was concurrently reset to `main` and PR #1 closed;
- preserved commits were recovered without force-pushing;
- a clean branch was recreated from current `main` (`c3884ab...`) so concurrent WAC 1.3.1 / Playwright handoff work remains intact.

WCP-02 host evidence — verified on Windows without touching the live dirty WAC checkout:

- RDC execution plane recovered on device `JIAOLONG16proSeries`;
- real Skill roots scanned: `C:\\Users\\24734\\.agents\\skills`, `C:\\Users\\24734\\.codex\\skills`, and packaged WAC `skills/`;
- scanner discovered 121 Skills across 15 categories;
- `frontend-design` resolved to category `web-ui` from the category router, with workflow usage relationships attached;
- `category-web-ui` was observed in both shared and Codex roots;
- `web-product-build` planned with `blocked=false`; required `frontend-design`, `webapp-testing`, and `impeccable` were available;
- a durable run started successfully at `product-context`;
- logical move + `inherit` restore were exercised against temporary machine-local state only;
- physical relocation completed on a disposable Windows sandbox, moved the Skill once, patched source/target routes, rescanned successfully, and left the source path absent / target entrypoint present;
- isolated Manager GET `/api/skills`, GET `/api/workflows`, and POST workflow plan returned HTTP 200;
- `open_skill_location("frontend-design")` returned `opened`, and Explorer post-state showed `file:///C:/Users/24734/.agents/skills/frontend-design`;
- Control Plane CI run 30 passed the regression gate, Ruff, secret scan, and full-suite Linux compatibility evidence;
- live WAC checkout remained untouched because a concurrent local `skills_control.py` / `skills-runtime` implementation is still dirty and owned by another task.

Still pending:

- Web Manager UX implementation;
- browser acceptance of Skills / Workflows / Runs / Runtime surfaces;
- final live integration with the concurrent low-level Skill index/MCP runtime after its writer closes or provides a clean commit.

## 10. Exit criteria

WCP-01 is closed when:

- Skill scanner handles flat Skills + category router references + duplicate/junction aliases;
- logical move/category state persists machine-locally;
- Workflow registry loads and planner resolves required/optional Skills;
- run state can start, transition, persist and reload;
- targeted unit tests pass;
- full existing suite shows no regression.

WCP-02 is CLOSED: clean-branch CI is green and Manager API, real Windows Skill scan, Explorer open-folder, logical classification and sandbox relocation were verified without interrupting WAC.

WCP-03 owns the real Manager UX. It must consume the existing APIs and machine-local truth; it may not introduce a second source of truth.
