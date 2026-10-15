# PLAN.md structure

## Contents

- [Layout](#layout)
- [The rules section](#the-rules-section)
- [Run layout on disk](#run-layout-on-disk)
- [Checklist before hand-over](#checklist-before-hand-over)

## Layout

Use this order. Sections that do not apply may be dropped, except the status line, section 1, the rules section and the phases.

```markdown
# <Run title>

Source: <issue link or "owner's message of <date>">. Status: **revision N: <what changed>.**

## Table of contents
...

## 1. How this run is run          the commands, where the ledger is, what is attended
## 2. Guiding rules                e.g. parity with a reference app, if screens change
## 3. Findings                     one row per requirement: complaint, code today (file:line), fix, task id
## 4. Problems not mentioned       each with the owner's decision
## 5. Owner decisions              D1 (documentation Y/n), D2, D3 ... each with options, choice, example
## 6. Confirmed assumptions        A1, A2 ...
## 7+. Reference sections          settings tables, permission models, naming rules: whatever
                                   several tasks share. Tasks cite them by number.
## N. Phases and order             table: phase, repo, depends on, task count, models; numbered artefacts
## N+1. Rules for every task       the runner sends this section with every task (exact heading text)
## Phase <p>: <title>
### Task <p>.<n> — <title>
...
## Phase <last>: closing           gate, walkthrough?, adversary, documentation if D1 = Y
## Risks
```

- **Decision headings:** `### D1 — <title>`, `### D2 — <title>`. Link to them as `#d1--<slug>`.
- **Phases table:** add a column with the task count per model (for example `2 haiku, 3 sonnet, 1 opus`), so the owner sees the cost profile at a glance.
- **Phase numbers** continue from the previous run (see `runs/PROJECT.md`). A project's first run starts at phase 1. That way commit messages (`Task 19.3: ...`) stay unambiguous across runs.

## The rules section

The heading must contain **`Rules for every task`**, for example `## 12. Rules for every task`. The runner finds it by that text and sends it with every task, so keep it short: about 15 lines. It restates, for this run:

- the standing "never" rules from `runs/PROJECT.md` that any task could trip over;
- cross-repo conventions (commit in the sibling repo as `Task <id>: ...`);
- known failing tests, stated as facts, with "do not make them pass by deleting data";
- the UI verification rule (a browser check; which files need a reload and which need a rebuild);
- the documentation rule: no task edits docs, and every task reports `DOCS:`;
- any brand or style rule;
- environment facts a headless shell needs (a tool at a full path, the credentials file to sign in with).

Rules that only one task needs go in that task, not here.

## Run layout on disk

```text
runs/
  PROJECT.md                   the project profile (see project-profile.md)
  runner.json                  runner settings: sibling repos, models, effort, tools
  <NNN>-<name>/                one folder per run
    PLAN.md                    the plan
    PROGRESS.md                that run's ledger, written by the runner
    ADVERSARY.md               written by the adversary check
tools/run-planner/             run_plan.ps1, run_task.ps1, new_run.ps1, VERSION
.runlogs/<NNN>-<name>/         per-task prompt, event stream and usage.csv (gitignored)
```

- **One run, one ledger.** A run's `PROGRESS.md` starts empty and holds only that run's rows.
- **History is not context.** Tasks do not read earlier runs' plans or ledgers, and do not dig through git history. When a fact from an earlier run matters, the plan states it inside the task.
- **The planner may read the archive** sparingly and by search, to find such facts. It never pastes ledger text into a plan.
- **Archived runs are never run.** A ledger whose first lines contain `Archived run` is skipped. To retire a run, add `> **Archived run.** <what it was>.` as its ledger's first line.

## Checklist before hand-over

- [ ] Table of contents at the top, linking every heading.
- [ ] Status line says "ready to run", with the revision number.
- [ ] Every requirement appears in the findings table, with a task id.
- [ ] Decisions are numbered D1, D2, ...; D1 is the documentation question and is answered; every other decision is answered; every assumption is confirmed. No task says "ask the owner" without a default.
- [ ] Every task has its heading in the exact format, `Size`, `Model`, Files with anchors, Accept and one targeted Verify.
- [ ] Every Haiku task is a recipe: exact places, exact new text or rule, the test place, nothing to decide.
- [ ] Every S task really is local. Nothing marked S or M needs more than about 100K tokens of context. Heavy tasks are split by area.
- [ ] Tool-dependent tasks say what to do when the tool fails twice.
- [ ] Numbered artefacts (migrations, versions) are assigned from the current head.
- [ ] Facts from earlier runs are written into the tasks, not referenced.
- [ ] The rules section's heading contains "Rules for every task", and it is short.
- [ ] Closing phase: gate, walkthrough if users see changes, adversary check, documentation as the last task if D1 = Y.
- [ ] The run folder has `PLAN.md` and an empty `PROGRESS.md`, and is committed.
