---
name: plan-run
description: Plans the next unattended run for the current project and sets up the runner that executes it. Use when the user says "perform planning on this project", "plan a run", "plan the next run", "turn these requirements/issues/complaints into a run", or asks to set up run-planner in a project. Produces runs/<NNN-name>/PLAN.md (findings, owner decisions D1, D2 ..., phased tasks each sized S/M/L and assigned to Haiku, Sonnet or Opus, a closing phase with regression gate, adversary check and optional docs) plus an empty ledger, and installs tools/run-planner/*.ps1 to run it task by task in fresh headless sessions. Plans only; never implements the tasks.
---

# plan-run: turn requirements into an unattended run

This session **plans**. It does not implement anything. Its output is one run folder, `runs/<NNN-name>/` with `PLAN.md` and an empty `PROGRESS.md`, committed, plus the commands to run it. A runner script then executes every task in a fresh headless session while the owner is away, and the owner reviews the results once, at the end.

Run the planning itself on the strongest model available. Planning effort is cheap compared with a run that rediscovers the same facts in 30 sessions: spend the effort here, so every task can be short.

## Contents

- [Step 0: set up the project](#step-0-set-up-the-project)
- [Working with the owner](#working-with-the-owner)
- [The planning process](#the-planning-process)
- [Owner decisions](#owner-decisions)
- [Finalising and hand-over](#finalising-and-hand-over)
- [Reference files](#reference-files)

## Step 0: set up the project

Do this every time, before the first planning step. It is quick when the project is already set up.

1. **Runner scripts.** Compare `tools/run-planner/VERSION` in the project with `VERSION` in this skill's folder (the base directory shown when the skill loaded). If the project's file is missing or older, run the installer:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skill folder>/scripts/install.ps1" -Project .
   ```

   It copies `run_plan.ps1`, `run_task.ps1` and `new_run.ps1` to `tools/run-planner/`, creates `runs/runner.json` and `runs/PROJECT.md` from templates if they are missing, and adds `.runlogs/` to `.gitignore`. It never overwrites `runner.json` or `PROJECT.md`.

2. **Project profile.** `runs/PROJECT.md` holds everything project-specific: repositories, standing "never" rules, test, build, lint and docs commands, environment facts, known failing tests, phase numbering. Every plan copies the facts it needs from here into its tasks. If the file still holds the template, fill it by researching the project (README, CI config, test layout, package manifests, existing `runs/`), then put what you could not prove to the owner as assumptions in the first review round. The structure is in [references/project-profile.md](references/project-profile.md).

3. **`runs/runner.json`.** List sibling repositories that tasks edit in `addDirs` (relative paths, for example `"../engine"`), and tool directories that headless shells cannot find in `pathAdd`. Leave models and effort at their defaults unless the owner says otherwise.

4. **Earlier planning guides.** If the project has an older hand-written guide (for example `runs/PLANNING_GUIDE.md`), move its project-specific facts into `PROJECT.md` and replace its body with a pointer to this skill. Ask before deleting anything.

## Working with the owner

- **Style.**
  - No compliments.
  - Every decision with complex parameters gets an example: what comes in, what comes out, and why.
  - Every Markdown file you write gets a table of contents with anchor links to all its headings, `PLAN.md` included.
- **Attention.** The owner reviews once, at the very end of a run, and is often away for days. Everything the run needs from them is settled **while planning**, never during the run.
- **Asking.** Put decisions to the owner with the question tool when it is available (up to 4 questions per call, 2 to 4 options each, the recommended option first and marked "(Recommended)"), and record every answer in `PLAN.md`. Ask the rest in chat as a numbered list.
- **Iteration.** The owner answers in short numbered comments ("D3: b", "A4 correct, but ..."). Apply every answer, bump the revision in the status line, commit, and send the file again. Repeat until the owner confirms nothing is left open.

## The planning process

1. **Intake.** Restate the requirements as a numbered list, one complaint or wish per line. This becomes the findings table.

2. **Research the code, not the history.**
   - For each item, find the root cause in the code (`file:line` **and** a unique anchor string, such as a function name or a literal, because line numbers drift).
   - Check what already exists, so no task builds something twice. Settings registries, existing routes and helper functions are the usual surprises.
   - Note anything numbered that tasks will extend (migration head, contract version, API version).
   - **Do the locating work now, once.** Every coordinate you find here goes into the task. A task that has to search for what the planner already found costs turns at full context price. This is the main lever on token cost: see [references/task-writing.md](references/task-writing.md#cheap-tasks).

3. **Findings table.** One row per item: complaint, what the code does today (`file:line`), the fix, the task id(s).

4. **Problems nobody mentioned.** List them separately. The owner decides on each, the same way as on the requirements.

5. **Owner decisions** `D1`, `D2`, ... See [Owner decisions](#owner-decisions).

6. **Assumptions** `A1`, `A2`, .... Things you believe from the code but could not prove, for the owner to confirm or correct.

7. **Phases and tasks.**
   - Group the work by dependency, not by topic: contract before the code that uses it, data model before screens.
   - Write each task: [references/task-writing.md](references/task-writing.md). That file covers the template, sizes, the **model choice (Haiku, Sonnet or Opus)** and the rules that keep a task cheap.
   - End with the closing phase: [references/closing-phase.md](references/closing-phase.md). That is the regression gate, the walkthrough if users see changes, the **adversary check**, and the documentation task if D1 is yes.
   - Lay out `PLAN.md` as [references/plan-format.md](references/plan-format.md) describes.

8. **Review loop** (see [Working with the owner](#working-with-the-owner)) until the owner confirms. Only then does the status line say "ready to run".

## Owner decisions

- Number them `D1`, `D2`, `D3`, ... in the order they appear. Anchors are `#d1--<slug>`. Never use letters.
- **D1 is always:** "Update documentation when all phases are complete? Y/n".
  - Recommend **Y** when the run changes anything a user, operator or integrator sees or configures.
  - Recommend **n** for a bug-fix run whose fixes restore documented behaviour.
  - Y adds the documentation task as the run's last task. With n, there is no documentation task. Every task still reports its `DOCS:` line, so a later run can catch up.
  - Example: "Fix the CSV export dropping the last row" → n (the docs already describe a full export). "Add per-tenant export formats" → Y.
- Every other point where more than one reasonable design exists becomes a decision, with:
  - the options;
  - the recommendation;
  - an example (in → out → why).
- Nothing is left as "the task will decide" unless it truly does not matter. In that case write the default into the task.

## Finalising and hand-over

1. Run the checklist in [references/plan-format.md](references/plan-format.md#checklist-before-hand-over).
2. Create the folder, if you have not yet: `.\tools\run-planner\new_run.ps1 -Name <short-name>`. Create it by hand if the script cannot run: next free three-digit number, `PLAN.md`, and a `PROGRESS.md` holding only the header from [references/runner.md](references/runner.md#the-ledger).
3. Commit the folder (on the session's branch if there is one) and send `PLAN.md` to the owner.
4. Give the owner the commands:

   ```powershell
   git merge --no-edit <planning branch>        # only if the plan was written on a branch
   .\tools\run-planner\run_plan.ps1             # runs the newest run with open tasks, to the end
   .\tools\run-planner\run_plan.ps1 -Run <NNN-name> -From <task id>   # explicit run / start
   ```

   Also say that the run is unattended, that it waits out usage limits on its own, and that the summary at the end lists blocked tasks, attended tasks, the adversary findings, and the most expensive tasks.

## Reference files

| File                                                           | Read it when                                                                                 |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [references/task-writing.md](references/task-writing.md)       | writing tasks: template, sizes, model choice, Haiku-ready recipes, the cheap-task rules     |
| [references/closing-phase.md](references/closing-phase.md)     | writing the last phase: gate, walkthrough, adversary check, documentation                    |
| [references/plan-format.md](references/plan-format.md)         | laying out `PLAN.md`, and the hand-over checklist                                            |
| [references/runner.md](references/runner.md)                   | what the runner does, the ledger, the RESULT block, `runner.json`: what a plan must fit      |
| [references/project-profile.md](references/project-profile.md) | filling `runs/PROJECT.md` for a new project                                                  |
| [references/lessons.md](references/lessons.md)                 | before finalising: what went wrong in earlier runs and the rule each lesson produced        |
