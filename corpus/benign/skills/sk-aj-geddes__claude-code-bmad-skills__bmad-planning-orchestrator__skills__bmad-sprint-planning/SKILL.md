---
name: bmad-sprint-planning
description: |
  Orchestration handoff bridge: emits and maintains sprint-status.yaml as the project's
  sequencing system-of-record. Orders stories by epic then dependency, assigns parallel-set
  (wave) membership, and drives the status lifecycle (backlog → ready-for-dev → in-progress
  → review → done) as a view — never as a metric.

  Use when the user says "sequence the stories", "build the sprint status", "plan the waves",
  "create sprint-status.yaml", "assign parallel sets", "order stories by dependency",
  "what can run in parallel", "set up story sequencing", "initialize sprint tracking",
  "ready the backlog", or "prepare for dev handoff". Also triggers on "sprint planning"
  when the project already has epics defined.

  SCOPE: SEQUENCING AND ORCHESTRATION ONLY. No velocity, no burndown, no committed points,
  no coverage metrics. Capacity is expressed as wave width (concurrent story count), not
  points. The final artifact is a ready-for-dev handoff manifest; implementation is
  delegated to external dev tools.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---

# BMAD Sprint Planning

**Role:** Sequencing & Handoff Bridge — Phase 4 orchestration  
**System-of-record:** `bmad-output/sprint-status.yaml`

---

## What This Skill Does

1. Reads planning artifacts (PRD, architecture, epics, stories) from `bmad-output/`.
2. Derives a dependency graph across all stories.
3. Assigns each story a `parallel_set` (wave) — stories in the same wave have no mutual dependencies and can run concurrently.
4. Emits `bmad-output/sprint-status.yaml` using the canonical template.
5. Marks the first wave of stories `ready-for-dev`; all others remain `backlog`.
6. Optionally re-sequences on demand as stories are completed or new ones are added.

This skill does **not** write application code, run tests, lint, build, or review diffs.

---

## Three-Intent Operation

| Intent | Trigger phrase | Action |
|--------|---------------|--------|
| **Create** | "initialize sprint status", "first time" | Scaffold fresh `sprint-status.yaml` from template |
| **Update** | "re-sequence", "story X is done", "add story", "update wave" | Mutate existing `sprint-status.yaml` in-place |
| **Validate** | "check sequencing", "are dependencies correct", "show wave plan" | Read and report without writing |

---

## Workflow — Create

1. **Load planning artifacts**
   ```
   Glob: bmad-output/**/*.md, bmad-output/**/*.yaml
   ```
   Priority order: `epics.md` → `prd.md` → `architecture.md` → individual story files.

2. **Extract epics and stories**
   - Parse all story IDs: format `{epic}.{story}.{slug}.story.md` (e.g., `2.1.stripe-integration.story.md`)
   - Derive epic ordering from the epic list in `epics.md` or `prd.md`

3. **Build dependency graph**
   - Read `dependencies[]` from each story's frontmatter or Dev Notes section
   - Topological sort: stories with no unmet dependencies → wave 1; stories unblocked after wave 1 → wave 2; etc.

4. **Initialize sprint-status.yaml**
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/skills/bmad-sprint-planning/scripts/init-sprint-status.sh
   ```
   Then populate with sequenced data (see template).

5. **Sequence stories**
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/skills/bmad-sprint-planning/scripts/sequence-stories.sh
   ```

6. **Set initial statuses**
   - Wave 1 stories: `status: ready-for-dev`
   - All other stories: `status: backlog`
   - Epics: `status: in-progress` if any child story is ready-for-dev; else `backlog`

7. **Emit handoff summary** — list wave 1 stories by `owned_scope` for conflict-free parallel dispatch

---

## Workflow — Update

When a story moves to `done`:
1. Remove it from any `dependencies[]` lists where it appears
2. Identify newly unblocked stories (dependencies now fully satisfied)
3. Promote them to `ready-for-dev`
4. Re-evaluate parent epic status
5. Write updated `sprint-status.yaml`

---

## Parallel Set Assignment

Wave width (how many stories can run at once) is not a fixed number — it is the size of the dependency-free frontier at each topological level. There is no points budget or velocity ceiling.

```
Wave 1: all stories with no dependencies
Wave 2: all stories whose only dependencies are in wave 1
Wave N: all stories whose dependencies are fully in waves 1…(N-1)
```

Stories within a wave MUST have non-overlapping `owned_scope` to be safe for parallel dispatch. If two stories in the same wave share a file, split them into separate waves or document the conflict.

---

## Status Lifecycle (view, not metric)

```
backlog → ready-for-dev → in-progress → review → done
```

- This is a **view** of sequencing state, not a tracking instrument.
- Transitions are triggered by external signals (dev tool reports, user command).
- This skill never computes velocity, burndown, or completion rates from these statuses.

---

## Scale-Adaptive Track Guidance

| Track | Story count | Sprint-status behavior |
|-------|-------------|----------------------|
| Quick Flow | 1–15 | Single wave pass; minimal epic structure |
| BMAD Method | 10–50+ | Full wave assignment; epic grouping |
| Enterprise | 30+ | Multi-phase wave planning; dependency map documented in REFERENCE |

Track is confirmed with the user before generating the status file.

---

## Subagent Strategy

**Pattern:** Parallel dependency analysis  
**Use when:** 15+ stories across 3+ epics

| Agent | Task | Output |
|-------|------|--------|
| Agent 1 | Parse all story files, extract dependency declarations | `bmad-output/context/dependency-raw.yaml` |
| Agent 2 | Parse epic ordering from PRD/epics.md | `bmad-output/context/epic-order.yaml` |
| Agent 3 | Identify `owned_scope` conflicts within candidate waves | `bmad-output/context/scope-conflicts.md` |

Main context: merge outputs, run topological sort, write `sprint-status.yaml`.

### Example subagent prompt
```
Task: Extract dependencies from all story files
Context: Read all *.story.md files under bmad-output/stories/
Objective: For each story, output its id and its dependencies[] list
Output: Write YAML list to bmad-output/context/dependency-raw.yaml

Format:
- id: "2.1.stripe-integration"
  dependencies: ["1.3.user-auth"]
- id: "2.2.payment-webhook"
  dependencies: ["2.1.stripe-integration"]
```

---

## Scripts

### `init-sprint-status.sh`
Scaffolds `bmad-output/sprint-status.yaml` from the template if it does not exist.

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/bmad-sprint-planning/scripts/init-sprint-status.sh \
  [project-name] [output-dir]
```

### `sequence-stories.sh`
Orders stories: epics first (by epic number), then stories within each epic by dependency
(topological), then assigns `parallel_set` integers.

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/bmad-sprint-planning/scripts/sequence-stories.sh \
  [sprint-status-file]
```

---

## Template

`${CLAUDE_PLUGIN_ROOT}/skills/bmad-sprint-planning/templates/sprint-status.template.yaml`

Fields: `epics[]`, `stories[]` (with `id`, `title`, `status`, `dependencies`, `parallel_set`,
`owned_scope`). The template contains **no** velocity, burndown, or points fields.

---

## Key Guidelines

1. **Load context first** — always read existing `sprint-status.yaml` before writing
2. **Use TodoWrite** to track multi-step sequencing workflows
3. **Respect owned_scope** — flag conflicts before assigning same-wave membership
4. **No metrics** — if a field resembles velocity, points, or burndown, remove it
5. **Handoff clearly** — conclude every Create/Update with the list of `ready-for-dev` stories and their `owned_scope`
6. **Decision log** — append sequencing decisions to `bmad-output/decision-log.md`

---

> ---
> Part of the **BMAD Planning & Orchestrator** plugin — a Claude Code harness for the **BMAD Method** by the **BMAD Code Organization** (https://github.com/bmad-code-org/BMAD-METHOD). Implements the spirit of `bmad-sprint-planning`. All methodology credit belongs to the BMAD Code Organization.
