---
name: evolve-context
description: Self-evolving context protocol that captures insights, prevents repeated mistakes, and evolves project documentation through structured feedback loops.
metadata:
  version: 1.1.1
---

# Self-Evolving Context Protocol

## Basics

### Activation

- 'POST_TASK' (default) — execute post-task protocol when task warrants it
- 'ALWAYS_ON' (opt-in) — monitor every interaction; use only when explicitly requested
- 'ON_REQUEST' — full context lifecycle audit when user asks

### Paths

- '`SKILL_DIR`' — the directory containing this `SKILL.md` file (resolved by the agent at runtime)
- 'Scripts': `${SKILL_DIR}/scripts/` — skill automation scripts
- 'Detailed docs': [`${SKILL_DIR}/docs/protocols.md`](./docs/protocols.md) — adaptation rules, lifecycle management, validation checklist

### Managed Targets

- 'Root README': `README.md` — human entry point
- 'Index File': `AGENTS.md` (alternatives: `CLAUDE.md`, `CODEX.md`, `GEMINI.md`, `CONTEXT.md`)
- 'Canonical Plan File': `BACKLOG.md` / `TODO.md` / `PLAN.md` / `ROADMAP.md` — open work, epics, blocked items, next slices
- 'Docs Index': `/docs/README.md` — living index of `/docs`
- 'Project Docs': `/docs/'` — documentation files

---

## Purpose

Maintain a living knowledge system that captures insights, prevents repeated mistakes,
and evolves project documentation through structured feedback loops.

'Target format': GitHub-Flavored Markdown.
'Sweet spot': Projects with extensive documentation.
'Core guarantee': No insight is lost. No mistake is repeated. No documentation goes stale. No completed slice stays falsely open in the canonical backlog.

---

## Axioms

### A1: Reflexive Integrity

The protocol applies its own rules to itself. Process context (index file) ≠ project docs (`/docs`).

### A2: Constraint-Driven Evolution

Complexity is earned through discovered constraints, not invented upfront.

### A3: Single Source of Truth

Every piece of knowledge lives in exactly one place. Navigate via hierarchy, never duplicate.

### A4: Backlog State Truth

Documentation, changelog, and code history do not substitute for canonical open-work state. If an iteration changes what remains to be built, the plan file must be updated in the same pass.

---

## Three-Layer Architecture

```
Layer 0: README.md            ← "what is this & where to go"
Layer 1: AGENTS.md (index)    ← "how we work" (conventions, insights, mistakes)
Layer 2: /docs/README.md      ← "what docs exist"
Layer 3: /docs/'              ← "what we build"
```

Orthogonal control plane:

```text
Canonical plan file          ← "what remains open / blocked / next"
```

### Routing Decision Tree

```
About how we work?         → Layer 1 (index file)
About what we build?       → Layer 3 (/docs), then update Layer 2
About project identity?    → Layer 0 (README.md)
About what remains open?   → Canonical plan file
```

### Connectivity Invariant

README.md → /docs/README.md → /docs/'.
README.md → AGENTS.md.

Every doc reachable within 2 clicks from root. No dead ends.

---

## Activation Modes

### Mode 1: POST_TASK (Default)

'Trigger decision tree':

```
Task touched any *.md file?              → YES → run POST_TASK
                                          NO  → Changed public APIs/architecture? → YES → run POST_TASK
                                                                                   NO  → Changed canonical backlog state? → YES → run POST_TASK
                                                                                                                         NO  → skip
```

'Farmville guard': Before writing any update, ask: "Does this prevent a future mistake, capture
a non-obvious constraint, or correct stale backlog state?" If no → skip. Silence is a valid output.
Measuring documentation activity instead of prevented errors is the Farmville trap.

'Light post-task' (default — ≤3 files changed, no architectural impact):

1. EVALUATE — anything worth capturing? If no → skip
2. BACKLOG SYNC — update canonical plan state if the task changed what remains open
3. ROUTE & WRITE — update appropriate layer
4. SYNC — ensure /docs/README.md is current

'Full post-task' (>3 files changed OR architectural impact detected):

1. EVALUATE — anything worth capturing? If no → skip
2. BACKLOG SYNC — close, narrow, split, retarget, or gate plan items affected by the iteration
3. ROUTE & WRITE — update appropriate layer
4. CONSOLIDATE — deduplicate, merge overlapping content
5. SYNC — ensure /docs/README.md is current
6. EVOLVE — update index file sections, add Change History entry
7. VALIDATE — `bash "${SKILL_DIR}/scripts/validate-context"`

### Mode 2: ALWAYS_ON (Opt-in)

Only when explicitly requested by the user. Silently track during any task: surprises,
wrong assumptions, recurring patterns, stale/missing/duplicated docs, stale open backlog items,
and newly discovered next-slice tasks. Flag for post-task capture.

Cost: agent attention on every turn. Use only when task density justifies it.

### Mode 3: ON_REQUEST (Explicit)

Full context lifecycle audit + validation. See [protocols.md](./docs/protocols.md#validation-checklist-on_request-mode).

---

## Pre-Task Protocol

```
1. READ index file — scan for relevant conventions and insights
2. READ canonical plan file if one exists — understand current open work / epic framing / blocked state
3. READ /docs/README.md — understand documentation landscape
4. CHECK if similar task was done before → review past decisions
5. SCAN relevant /docs/' files
6. PROCEED with task execution
```

---

## Entry Templates

Defaults for new files. If a file already has a format — match THAT format.
Full templates: [`docs/templates.md`](./docs/templates.md)

### Quick Reference

'Index file entry':

```markdown
- '[label]': [description] | Trigger: [cause] | Action: [what to do]
```

'Change History entry':

```markdown
- `[Current]` [Task]. Impact: [what changed]. Insight: [lesson learned].
```

'Change History rotation': `[Current]` → `[Previous]` → `[Legacy-0]` → `[Legacy-1]` → `[Legacy-2]` → CHANGELOG.md

---

## Tooling: `validate-context`

Automated documentation health checker. Detects index file, validates links (skipping code blocks),
analyzes bloat heuristically, checks docs index coverage.

- 'Bootstrap': `"${SKILL_DIR}/scripts/_bootstrap"` installs `validate-context` into `~/.local/bin`
- 'Design': [`docs/validation-design.md`](./docs/validation-design.md)
- 'Usage': `bash "${SKILL_DIR}/scripts/validate-context"` from project working directory
- 'Override root': `VALIDATE_CONTEXT_ROOT=/path/to/project bash ...`
- 'Exit 0' = passed, 'Exit 1' = errors found

---

## Backlog Sync Rules

When a task changes the true state of open work, update the canonical plan file in the same pass.

Allowed plan-state operations:

- 'Close' — exit criteria now satisfied in reality
- 'Narrow' — part of the item landed; rewrite it to describe the remaining work only
- 'Split' — one vague item became multiple concrete executable slices
- 'Retarget' — the original wording no longer matches the actual remaining task
- 'Defer' — still valid, but not the best next slice anymore
- 'Gate/Block' — remaining work now depends on an external condition

Rules:

- Epics are allowed, but keep the active next slice concrete
- Do not let docs/changelog silently carry work that still appears open in the plan
- Do not keep evergreen maintenance disciplines as unchecked backlog items; move them into the index file or docs instead

## Lifecycle & Maintenance

- 'Growth control': Discovery → Active → Consolidation → Strategic Pattern → Archive
- 'GC triggers': 3+ bloat signals from validator → mandatory garbage collection
- 'Change History': Max 5 entries, rotate older to `CHANGELOG.md`
- 'Mistake escalation': Insight → Convention → Hard rule → Structural change
- 'Details': [protocols.md](./docs/protocols.md#context-lifecycle-management)
