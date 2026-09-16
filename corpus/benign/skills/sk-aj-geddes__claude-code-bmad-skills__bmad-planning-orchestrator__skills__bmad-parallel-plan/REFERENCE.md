# BMAD Parallel Plan — Reference

Detailed mechanics for turning a sequential backlog into conflict-free concurrent waves.
This file documents the **conflict classes**, the **wave algorithm**, and the
**merge-order rationale**. The skill plans; it does not execute.

---

## 1. Why architecture comes first

Parallelism is only *safe* when the work items are isolated. Two kinds of collision exist:

- **Syntactic / file collision** — two stories edit the same file. Git surfaces this as a
  merge conflict. Cheap to detect (compare Owned File/Module Scopes), cheap to catch.
- **Semantic collision** — two stories edit *different* files but change the same behavior,
  contract, or shared invariant (e.g. both alter the auth flow, the DB schema, or a shared
  type). Git will **not** flag it; it surfaces as a broken integration.

A clean architecture (clear module boundaries, explicit shared modules) is what prevents
semantic collisions. So step 1 of the skill is to read `architecture.md` and enumerate the
**shared / cross-cutting modules**. Any two stories that both touch a shared module are
treated as semantically conflicting even if their file scopes are disjoint.

---

## 2. Conflict classes (edge types in the DAG)

| Class | Direction | Source | Effect |
|-------|-----------|--------|--------|
| **Ordering — epic** | directed | epic order; stories within one epic are usually sequential | story B `depends_on` the prior story in its epic unless the story explicitly marks itself epic-parallel |
| **Ordering — explicit** | directed | a story's `Dependency Maps` / `depends_on` list | B cannot start until A is done |
| **File scope** | undirected | Owned File/Module Scope intersection | A and B may not share a wave; resolved lower-id-first |
| **Semantic** | undirected | both touch a shared module from §1 | A and B may not share a wave |

**Directed edges** constrain *which wave* a story lands in (it must come after its
prerequisites). **Undirected edges** constrain *who else can be in the same wave* (mutual
exclusion within a wave) — they do not by themselves force an ordering, so the planner
breaks the tie deterministically by ascending story id.

### Epics parallel, stories sequential

The default BMAD heuristic: **stories within an epic are usually sequential** (they build on
each other), while **epics often run in parallel** (they target different components). The
graph builder encodes this by chaining stories inside an epic via ordering edges, and by
*not* adding cross-epic ordering edges unless an explicit `depends_on` says so. A story may
opt out of its intra-epic chain by declaring `epic_parallel: true` (or by having no
preceding sibling).

---

## 3. The wave algorithm

Input: a DAG `G = (V, E)` where `V` = eligible stories (`ready-for-dev`+), directed edges =
ordering constraints, plus an undirected `conflicts` set (file + semantic). Cap = `maxParallel`.

```
waves        = []
scheduled    = {}            # story_id -> wave index
remaining    = topo-eligible vertices of G

while remaining:
    # candidates whose every directed prerequisite is already scheduled
    ready = [ s for s in remaining
              if all(dep in scheduled for dep in prereqs(s)) ]
    ready.sort(by ascending story id)        # deterministic tie-break

    wave = []
    for s in ready:
        if len(wave) == maxParallel: break
        # mutual exclusion: no undirected conflict with anyone already in this wave
        if any(conflict(s, t) for t in wave): continue
        wave.append(s)

    if wave is empty:        # only happens on a dependency cycle
        raise "cycle detected among: <remaining>"

    assign wave -> next wave index in scheduled
    waves.append(wave)
    remaining -= wave
```

Properties:

- **Dependency-safe.** A story enters a wave only after all prerequisites are in earlier
  waves. (Prerequisites in the *same* generation are deferred to a later wave.)
- **Conflict-free.** No two stories in a wave have intersecting file scope or a shared
  semantic module.
- **Capped.** No wave exceeds `maxParallel`; overflow ready-stories roll forward (lowest id
  first), preserving fairness and determinism.
- **Cycle-detecting.** An empty `ready`/`wave` with stories still remaining means the
  dependency maps contain a cycle — a planning bug to surface, not to silently resolve.

### Width vs. depth

A smaller `maxParallel` yields more, narrower waves (slower wall-clock, fewer integration
collisions). A larger cap yields fewer, wider waves (faster, more merge contention). The
default of `3` is a conservative balance; the user sets it via `userConfig.maxParallel`.

---

## 4. Merge-order rationale

Within a wave every branch is file-disjoint, so the branches *can* merge in any order
without textual conflict. We still impose a deterministic order for predictable review:

1. **Ascending story id into `integration/wave-{N}`.** Lower ids are typically foundational
   (earlier in the epic / earlier authored), so the integration branch grows from the most
   foundational change outward. Determinism also makes re-runs reproducible.
2. **Integration review checkpoint.** After all of a wave's branches land on
   `integration/wave-{N}`, review the *combined* result. This is the only place a hidden
   semantic interaction between same-wave stories would appear — catching it here keeps
   `main` green.
3. **Single PR `integration/wave-{N}` -> `main`.** One reviewed, integrated unit lands on
   `main` rather than N independent PRs racing each other.
4. **Wave N+1 branches off the merged `main`.** Each wave starts from a known-good base, so
   later waves automatically see earlier waves' changes and their prerequisites hold.

This skill only *describes* this sequence. Creating worktrees, merging, reviewing diffs, and
opening PRs are all carried out by external dev tools / humans.

---

## 5. Worktree & branch naming

| Thing | Pattern | Example |
|-------|---------|---------|
| Story branch (one isolated worktree each) | `story/{epic}.{story}-{slug}` | `story/2.1-stripe-integration` |
| Per-wave integration branch | `integration/wave-{N}` | `integration/wave-1` |
| Final PR | `integration/wave-{N}` -> `main` | wave-1 -> main |

One worktree per story guarantees filesystem isolation, so concurrent dev agents never share
a working tree. The plan supplies the names; it does not run `git worktree`.

---

## 6. Eligibility & blockers

A story is **wave-eligible** only if:
- status is `ready-for-dev`, `in-progress`, or `review` (not `backlog`, not `done`), and
- it declares a non-empty **Owned File/Module Scope**, and
- every id in its `depends_on` resolves to a known story.

If a story is `ready-for-dev` but has **no declared scope**, it is excluded and reported as a
planning blocker for `bmad-epics-and-stories` to fix (scope refinement). The
planner must never invent file paths to make a story schedulable.

---

## 7. Outputs

| File | Producer | Purpose |
|------|----------|---------|
| `dependency-graph.json` | `build-dependency-graph.py` | nodes + typed edges + conflict set |
| `waves.json` | `plan-parallel-waves.py` | ordered list of waves with member stories |
| `parallelization-plan.md` | the skill (from template) | the human/dev-tool deliverable |
| `decision-log.md` (append) | the skill | records cap, wave count, deferred stories |

### `dependency-graph.json` shape

```json
{
  "max_parallel": 3,
  "nodes": [
    {"id": "2.1", "slug": "stripe-integration", "epic": 2,
     "status": "ready-for-dev", "scope": ["src/payments/stripe.ts"]}
  ],
  "ordering_edges": [{"from": "2.1", "to": "2.2", "reason": "intra-epic-sequence"}],
  "conflicts": [{"a": "2.1", "b": "3.4", "class": "file",
                 "detail": "src/payments/stripe.ts"}],
  "blocked": [{"id": "4.1", "reason": "no Owned File/Module Scope declared"}]
}
```

### `waves.json` shape

```json
{
  "max_parallel": 3,
  "waves": [
    {"wave": 1, "stories": [
      {"id": "1.1", "slug": "auth-skeleton",
       "branch": "story/1.1-auth-skeleton", "scope": ["src/auth/"]}
    ],
    "integration_branch": "integration/wave-1",
    "merge_order": ["1.1"]}
  ],
  "deferred": [{"id": "4.1", "reason": "no declared scope"}]
}
```
