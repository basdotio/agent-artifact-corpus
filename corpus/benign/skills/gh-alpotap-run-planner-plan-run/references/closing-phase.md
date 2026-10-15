# The closing phase

Every run ends with these tasks, in this order, as its last phase:

| #   | Task                       | When                                         | Size, model                            |
| --- | -------------------------- | -------------------------------------------- | -------------------------------------- |
| 1   | Regression gate            | always                                       | L, sonnet                              |
| 2   | Walkthrough (ATTENDED)     | when the run changed something a user sees   | L, sonnet; split into ~6 rows per task |
| 3   | Adversary check            | always; the task right before documentation  | L, **opus**                            |
| 4   | Documentation and screens  | only if **D1 = Y**; always the last task     | M/L, sonnet; split by area             |

## Contents

- [1. Regression gate](#1-regression-gate)
- [2. Walkthrough](#2-walkthrough)
- [3. Adversary check](#3-adversary-check)
- [4. Documentation](#4-documentation)

## 1. Regression gate

- Run the full suites, once each, with the commands from `runs/PROJECT.md`, then the linter.
- For each failure, find the task that caused it, fix it, and rerun the failing files. Then rerun each full suite once.
- **List the known failures as facts in the task**, with their reasons, so they are not "fixed" by deleting data.
- **Name the likely breakage first.** From the plan, list which test files each task is expected to break (a changed signature, a new column, a new route). The gate then starts there instead of reading every failure cold.

## 2. Walkthrough

- Use a fresh development database, if the project has a reset command.
- Walk every findings row that has a task, as a user would. Record per row: **fixed**, **partly fixed** (and what is left) or **not fixed** (and what happens instead).
- Nothing is fixed here. Leftovers become the next run's input.
- **Keep it cheap.**
  - Split it into tasks of about six rows each, grouped by screen.
  - Give each row its concrete check ("download every format from the Files view and record each file name").
  - Read page text rather than screenshots, unless the question is visual.
  - One earlier walkthrough of 17 rows ran 274 turns and re-read 58.7M context tokens in one session.

## 3. Adversary check

The run's own reviewer. It runs after everything else has been built and tested, and before documentation, so the docs describe what survived it.

```markdown
### Task <p>.<n> — Adversary check

**Size: L** · **Model: opus**

- **Scope:** everything this run committed. In each repository:
  `git diff <first>~1..HEAD`, where `<first>` is the commit of this run's first task:
  `git log --format=%H --grep="^Task <first task id>:" | Select-Object -Last 1`.
  Start from `git diff --stat`, then read the diffs file by file, plus the callers of changed functions. Do not read whole files you have no reason to doubt.
- **Look for, in this order:**
  1. Findings rows whose Accept line the code does not actually meet (the plan's findings table is the checklist).
  2. Violations of the standing rules: <copy the project's "never" rules here>.
  3. Security: authorisation on new or changed routes, input that reaches a query, a path or a shell, secrets or personal data in logs or audit records, tenant or user isolation.
  4. Regressions in callers of changed functions, and data already stored in the old shape.
  5. Tests that do not test: assertions that cannot fail, the change mocked away, In/Out examples from the plan that no test covers.
  6. Leftovers: debug code, commented-out code, TODOs added by this run, dead code that the change orphaned.
  7. "Decisions to review" in the ledger that contradict an owner decision.
- **Fix** a defect only when this run introduced it, the fix touches at most two files, and a test proves it. Run that test, and commit as `Task <p>.<n>: fix <what>`, one commit per fix.
- **Report everything else.** No refactors, no style changes, no weakening of tests.
- Write `runs/<run>/ADVERSARY.md` (with a table of contents), and commit it:
  - a table: #, severity (high / medium / low), `file:line`, what is wrong, why it matters, **fixed** (with commit) or **open**;
  - for each open finding, a one-line proposed task for the next run.

**Accept:** `ADVERSARY.md` lists every finding with its status. Every fix has a passing targeted test.
**Verify:** the targeted tests of each fix.
```

- The adversary is on Opus because its value is judgement. Everything it fixes is small, and everything else is written down.
- Copy the standing rules into the task. Do not just point to `PROJECT.md`: the task text is what the session sees first.
- If the run has more than about 40 changed files, split it into one adversary task per repository or area, each with its own path filter (`git diff ... -- <paths>`).

## 4. Documentation

Only when **D1 = Y**. Otherwise leave this task out. The tasks' `DOCS:` lines stay in the ledger for a later run.

- **The planner writes the page list.** For each page: the path, and what changes on it, taken from the findings and tasks. Example: "`docs/user-guide/downloads.md`: the five button labels from task 50.3; the file-name rule from section 7". The task must not have to discover which pages are affected.
- **Split by area.** One task per three to five pages (user guide, operator guide, developer and contract docs). Screenshots are their own task.
- **Screenshots.**
  - One capture run, with the selector file updated for every screen whose controls moved.
  - If the capture tool fails twice for a reason outside the task, record the error and finish blocked. Do not debug the pipeline inside the docs task. That is a task of its own in the next run.
- **The strict docs build** last, with the command from `runs/PROJECT.md`, and zero warnings.
- Describe the screens as they finally are, after the adversary check.
