---
name: bmad-parallel-plan
description: |
  Turns a sequential, ready-for-dev story backlog into conflict-free CONCURRENT WAVES.
  Builds a dependency DAG from epic order, per-story dependency maps, and Owned File/Module
  Scope overlaps, then topologically sorts it into parallel waves of mutually disjoint,
  dependency-satisfied stories (capped by maxParallel), and emits a parallelization-plan.md
  with per-story git-worktree branch names and an ordered merge sequence.
  Use when the user says "plan parallel work", "which stories can run in parallel",
  "parallelize the backlog", "build the wave plan", "parallelization plan",
  "conflict-free workstreams", "what can we run concurrently", "split into worktrees",
  "dependency graph for the stories", "merge order", or "how do I fan this backlog out
  to multiple dev agents". Run AFTER stories are ready-for-dev (scrum-master) and an
  architecture exists. This skill PLANS parallelism only — it does NOT run agents, spawn
  worktrees, write code, run tests, or perform git operations.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---

# BMAD Parallel Plan

Convert a linear backlog into **waves** of stories that can be developed at the same
time without colliding — then describe exactly how to merge them back together. This
skill produces a *plan*. Your external dev tools execute it.

**Persona flavor:** Winston (Architect) reasons about isolation; the workflow does the math.

## Scope (read first)

- This skill **plans** concurrency. It NEVER spawns worktrees, runs dev agents, writes
  application code, runs tests, lints, or runs `git`.
- Inputs are planning artifacts. The only output is `parallelization-plan.md` (plus an
  optional `dependency-graph.json` / `waves.json` for traceability).
- Branch names and merge order are *recommendations* the dev tool/human carries out.

## Inputs

| Artifact | Path (under output folder) | Used for |
|----------|---------------------------|----------|
| Sprint status | `sprint-status.yaml` | story ids, epic, status, dependency lists |
| Ready stories | `stories/{epic}.{story}.{slug}.story.md` | **Owned File/Module Scope** + **Dependency Maps** |
| Architecture | `architecture.md` | semantic-conflict prevention (boundaries, shared modules) |
| Config | `userConfig.maxParallel` (default `3`) | wave width cap |

Only stories at status `ready-for-dev` (or later) are eligible for a wave.

## The four steps

1. **Lean on architecture for semantic safety.** Read `architecture.md`. Architecture is
   what makes parallelism *safe* — clean module boundaries mean two stories touching
   different components won't create a hidden semantic conflict even if the files differ.
   Note any shared/cross-cutting modules (auth, config, DB schema, shared types); stories
   that touch them are high-conflict and rarely parallelizable.

2. **Read each story's Owned File/Module Scope.** Every ready story declares the explicit
   list of paths it may touch. Collect `{story_id -> [paths]}`. A missing or empty scope
   is a **planning blocker** — flag it; do not guess.

3. **Build the dependency DAG, then topologically sort into waves.** Edges come from three
   conflict classes (see REFERENCE.md):
   - **Ordering edges** — epic order (stories within an epic are usually sequential) and
     each story's explicit Dependency Maps (`depends_on`).
   - **File-scope edges** — any two stories whose Owned File/Module Scopes intersect must
     not share a wave (an undirected conflict, resolved by lower story id first).
   - **Semantic edges** — both touch a shared/cross-cutting module from step 1.

   Topologically sort: wave *N* = all stories whose dependencies are already satisfied by
   waves `< N` AND that are pairwise file-disjoint AND pairwise semantically safe. Cap each
   wave at `maxParallel`; overflow rolls to the next wave (lowest id first).

4. **Emit `parallelization-plan.md`.** For each wave, list the ready-for-dev stories; give
   each an isolated `git-worktree` branch name and its disjoint file scope. Then give the
   **ordered merge sequence**: lowest story id first into an `integration` branch, an
   integration review checkpoint, then a single PR `integration -> main`.

## Three intents

- **Create** — first wave plan from the current backlog.
- **Update** — re-plan after stories were added/finished/re-scoped (recompute the DAG;
  exclude `done`, re-sort remaining).
- **Validate** — re-check an existing plan: confirm every wave is still file-disjoint,
  dependency-satisfied, and within `maxParallel`; report drift.

State the intent, then proceed.

## Run the helper scripts

Both scripts are deterministic and read-only. Resolve paths via `${CLAUDE_PLUGIN_ROOT}`.

```bash
# 1) Build the dependency DAG (edges + conflict class) from status + story scopes
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bmad-parallel-plan/scripts/build-dependency-graph.py" \
  --status   "<output>/sprint-status.yaml" \
  --stories  "<output>/stories" \
  --out      "<output>/dependency-graph.json"

# 2) Topologically sort into capped waves
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bmad-parallel-plan/scripts/plan-parallel-waves.py" \
  --graph        "<output>/dependency-graph.json" \
  --max-parallel 3 \
  --out          "<output>/waves.json"

# 3) (Optional) cross-check two scope lists for overlap — shared orchestrator helper
bash "${CLAUDE_PLUGIN_ROOT}/scripts/scope-conflict-check.sh" \
  "<output>/stories/2.1.foo.story.md" "<output>/stories/2.2.bar.story.md"
```

Then render `waves.json` into the human-facing plan using
[`templates/parallelization-plan.template.md`](templates/parallelization-plan.template.md)
and write it to `<output>/parallelization-plan.md`.

## Branch & merge conventions

- Branch per story: `story/{epic}.{story}-{slug}` (one worktree each, fully isolated).
- Integration branch per wave: `integration/wave-{N}`.
- Merge order **inside** a wave: ascending story id into `integration/wave-{N}`.
- After all of a wave's stories merge: integration-review checkpoint, then PR
  `integration/wave-{N}` -> `main`. Wave *N+1* branches off the merged `main`.

## Output

- `<output>/parallelization-plan.md` — the deliverable.
- `<output>/dependency-graph.json`, `<output>/waves.json` — traceability (optional).
- Append a one-line entry to `<output>/decision-log.md` noting `maxParallel`, wave count,
  and any stories deferred for missing scope.

## Guardrails

- Never place two stories with intersecting Owned File/Module Scope in the same wave.
- Never schedule a story before a story it `depends_on`.
- A story with no declared scope is **not** wave-eligible — surface it for the
  scrum-master to fix; do not invent paths.
- Honor `maxParallel`; the dev tool enforces real concurrency, the plan must not exceed it.
- Do not modify Acceptance Criteria, Dev Notes, or Testing in any story — those are LOCKED.

See [REFERENCE.md](REFERENCE.md) for the wave algorithm, conflict classes, and merge-order
rationale.

> ---
> Part of the **BMAD Planning & Orchestrator** plugin — a Claude Code harness for the **BMAD Method** by the **BMAD Code Organization** (https://github.com/bmad-code-org/BMAD-METHOD). Implements the spirit of `bmad-parallel-plan`. All methodology credit belongs to the BMAD Code Organization.
