---
name: plan-refinement
description: Documentation-only. Refines plans for AI execution; output = plan markdown only. No code.
context: fork
agent: Plan
---

# Plan Refinement

Plan → checklist → gaps → **on any feedback: validate + verification loop** → only when user confident to write → write **new** file.

## Scope

- **Output:** Plan markdown in `./docs/plan/`. No code, tests, or config.
- **No code:** No blocks/snippets; no source edits.
- **Flow:** Read → Review → Refine → Gaps → Iterate → **on feedback: re-validate + "correct or more changes?" loop** → "Confident to write?" loop → Write new file.

## Before starting

**Do not infer the plan.** Always ask the user explicitly:

- **Which plan to use?** (path to existing plan in `./docs/plan/`), or
- **Start a new plan from scratch?**

Do not read, guess, or infer from context. Wait for the user's answer before proceeding.

---

## Feedback and verification (mandatory)

**On every feedback** (gap answers, task/plan changes):

1. Incorporate feedback into plan.
2. **Re-run validation** (Parameters to Review).
3. Present updated plan. Ask: **"Is this correct or more changes?"**
4. If more changes → go to 1. If user accepts → continue (or ask "Confident to go to writing?" if that step applies).

**Do not write** until user has accepted in this loop and (for final write) said confident to go to writing.

---

## Iteration and writing

| Step | Action                                                                                                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | Present plan (full or summary).                                                                                                                                                            |
| 2    | **Gaps:** Run **Gap analysis** (below). List in **Gaps**. Agnostic phrasing. Ask fill/confirm.                                                                                             |
| 3    | "Accomplish your requirements? Fill/confirm Gaps first if any; then changes or confirm."                                                                                                   |
| 4    | On feedback (gaps or tasks): incorporate → **re-validate** → present → **"Correct or more changes?"** → loop until accepted.                                                               |
| 5    | When accepted: **"Confident to go to writing, or more changes?"** If more → step 4. Loop until confident.                                                                                  |
| 6    | **Only when confident to write:** Write. **New** file: `./docs/plan/{plan-name}-YYYY-MM-DD-HHmm.md` with **current** date-time. If path exists → different timestamp. **Never overwrite.** |

---

## Workflow: Existing plan

1. Read plan.
2. Review vs Parameters to Review. Report: pass/fail; table Parameter | Status | Reason.
3. Refine plan to satisfy parameters. No code.
4. **Gaps:** Run Gap analysis. List in Gaps. Present; user fill/confirm.
5. **On any feedback:** Incorporate → re-run Parameters to Review → present → **"Correct or more changes?"** → loop until accepted.
6. **"Confident to go to writing?"** If no → step 5. Loop until yes.
7. **Write.** New file only. Current date-time; never overwrite. Front matter = allowed keys. Include Agent Execution Rules + Gaps (resolved).

---

## Workflow: Create from zero

1. Intent (problem + solution); scope In/Out.
2. Codebase: Files to Reference **grouped by folder** (per folder: table File | Purpose; paths relative to folder).
3. Design: UI? Ask Figma/refs. External resources = bullets or "N/A".
4. Decisions: defaults, data, errors, dialogs. Bullets; infer or "TBD".
5. Draft: front matter (allowed keys); Title & Overview; Context (Files by folder, Technical Decisions, External resources); Implementation Plan (tasks `- [ ]`: Title, File, Action, Notes; AC Given/When/Then); Additional Context if needed; Summary.
6. Self-review: Parameters to Review; Writing Guidelines.
7. **Gaps:** Run Gap analysis. List in Gaps. Present; user fill/confirm.
8. **On any feedback:** Incorporate → re-validate → present → **"Correct or more changes?"** → loop until accepted.
9. **"Confident to go to writing?"** If no → step 8. Loop until yes.
10. **Write.** New file only. Same as Existing step 7. Create `./docs/plan/` if needed.

---

## Parameters to Review

| Parameter                 | Requirement                                                                                                                                                                                                      |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Output file**           | New file only. `./docs/plan/{plan-name}-YYYY-MM-DD-HHmm.md`; **current** date-time at write. Never overwrite plan-you-read or existing path; if exists → different timestamp.                                    |
| **Front matter**          | YAML `---`. Only: `title`, `slug`, `created`, `updated`, `status`, `stepsCompleted`; optional `epic`, `stories`. No other keys.                                                                                  |
| **Title & Overview**      | Problem (short), Solution (one para), Scope (In/Out). No code.                                                                                                                                                   |
| **Files to Reference**    | **Group by folder:** one subsection per folder (base path). Per folder: table **File** \| **Purpose**. File = path relative to that folder. No single flat table with full paths.                                |
| **Technical Decisions**   | Bullets: defaults, data, errors, dialogs.                                                                                                                                                                        |
| **External resources**    | Bullets. UI? Ask Figma/refs; none → inferred. No UI → "N/A".                                                                                                                                                     |
| **Implementation Plan**   | Tasks `- [ ]`. Each: Title, File, Action, Notes. AC Given/When/Then.                                                                                                                                             |
| **Additional Context**    | Optional. If absent, ask. If yes: bullets (deps, testing, notes).                                                                                                                                                |
| **Agent Execution Rules** | Per task, mandatory order: (1) Dev context first. (2) **TDD — no exceptions:** add/extend tests → run (or scope) → implement until green → then mark complete. (3) Plan metadata. Skip = invalid. |
| **Summary**               | End: what it delivers + work (scope, tasks, outcome).                                                                                                                                                            |
| **Gaps**                  | Run Gap analysis. List in Gaps; agnostic. User fill/confirm before write.                                                                                                                                        |

---

## Gap analysis

Before listing Gaps, run; add each finding to **Gaps** (agnostic phrasing).

**1. Designs (if plan has UI)**  
Figma/visuals in External resources? No → gap: request or confirm inferred. Yes → cover empty/error/loading for task-relevant states? No → gap.

**2. Task list**  
Per task (Title, File, Action, Notes): what is unspecified? (error handling, loading, empty state, validation, navigation, dependency, edge case). One gap per undefined aspect.

**3. Dimensions**

- **Architecture:** Where does X live? Which provider/notifier? Data flow?
- **Functionality:** Validation, retry/offline, errors (where/recover?), loading (skeleton vs spinner).
- **Product/UX:** Empty/error state (copy, CTA, retry?). Navigation from/to. Confirmations. Copy/labels.

**4. Dev / Additional Context**  
Plan missing Additional Context or dev refs (MCP, design, codebase) and tasks need it → gap: provide or confirm not needed.

---

## Agent Execution Rules (in every written plan)

Place after Context, before Implementation Plan. **Order is mandatory for every implementation task. Never skip 1 or 2.**

**Per implementation task (mandatory):**

1. **Dev context first - always.** Fetch required context (MCP, Figma, codebase) before implementation.
2. **TDD - mandatory, no exceptions.** Add/extend tests → run (or scoped path) → implement until pass → then mark complete. Applies to every task (UI, refactors, bug fixes, all). Skipping is invalid.
3. **Plan metadata - mandatory.** `status: implementing`; append to `stepsCompleted`; on done → `status: completed`.

**In every written plan,** include this block in Agent Execution Rules:

> **Mandatory for every implementation task: 1) Dev context first. 2) TDD:** tests → run → implement until green → mark complete. **Never skip. Not optional.**

---

## Writing Guidelines

- One intent per item; one action per task. Explicit: file path, symbol. Verbs: Add, Replace, Move, Delete, Rename.
- Tables/bullets over prose. No implicit context; cite paths.
- Concrete: "Add `X` in `path/file.dart`" not "Add a method." Task = file + action + notes. AC = one-sentence testable.

---

## Output format (report)

Summary (Parameters N/M, actions). Per parameter: ✅/❌ + comment. Optional: proposed changes. After present: Gaps → fill/confirm; "Accomplish requirements?" **On any feedback:** re-validate → present → "Correct or more changes?" → loop until accepted. Then "Confident to go to writing?" → loop until yes. **Only then** write new file (current date-time; never overwrite).

Project-specific params → Parameters to Review or linked ref.
