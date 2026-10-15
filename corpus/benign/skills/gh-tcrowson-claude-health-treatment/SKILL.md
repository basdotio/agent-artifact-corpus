---
name: treatment
description: Acts on the checkup's patient chart. Builds a triage table from the open conditions (design questions first, then serious bugs, then the rest; minor ones stay on a watch list), gets the user's approval batch by batch, including every file to be created or deleted, then fixes each item with a test and a check of sibling code, measures performance changes, re-reviews the fix diff, and marks each condition treated on the chart so the next checkup's follow-up visit can confirm the cure. Use when the user asks to treat, fix or act on checkup findings, or to work through a checkup report.
---

# Treatment

Works from the checkup's patient chart, `<data_root>/chart.json` (config `.claude/checkup/config.json`), through
`<this skill dir>/../checkup/scripts/chart.py`; the chart's format is in the checkup skill's `REFERENCE.md`
(section Chart). Each condition's latest run folder holds its full finding (findings.json) or design card
(trajectory.json). Follow the project's CLAUDE.md for tests, lint, commits and pace; commit only when the user asks.

## Talking to the user

Same rules as the checkup skill ("Talking to the user" in `<this skill dir>/../checkup/SKILL.md`): say where we
are and what you need first, in plain words; no raw files in chat; counts while working, details when done.
Refer to conditions by their chart ids and titles ("C0042, Mirror with nothing selected crashes"). For every file
to add or remove, one line on what it is and why, e.g. "`tests/test_mirror.py`: a test that fails today and passes
after the fix, so the bug can't quietly come back." Each batch ends with a short done message: what changed, the
test result in one line, and a link to the full output.

## Steps

1. **Load.** `python <checkup scripts>/chart.py status` for the vitals, then the open conditions: `open` and
   `reopened` defects, `open` improvements, and accepted design cards (`chart.py list --status ... --kind ...`
   filters them; `chart.py show <id>` prints one in full, so the JSON is never read by hand). Conditions on the `watch` list (minor bugs)
   are left out unless the user asks, or a planned fix touches the same code (then fix them in that batch).
   `documented`, `deferred` and `wontfix` stay out. Record the current head: it is the treatment's base. Re-check each
   item's file:line at HEAD; drop or re-anchor what moved, and say so.
2. **Triage table.** Batches in this order: design questions (a card and the conditions it would retire), then
   reopened conditions (a fix that did not hold), then critical and high defects, then the rest, grouped by root
   cause and directory. Per batch, one row with: ask, feasibility, effort (in agent time, see below),
   consequences, **new files** (every test, script, fixture or module it would create, by path) and **deleted
   files** (including tests made redundant).
3. **Approval.** The user approves, reorders or drops batches. The approval covers exactly the listed files: if a
   fix turns out to need a file that is not on the list, stop and ask before creating it, even a test.
4. **Fix each item.**
   - A defect gets a test that fails before the fix and passes after, where feasible (the tdd skill works for
     this). Test through the module's interface, the same one callers use.
   - **Siblings:** before calling a fix done, search for the same pattern elsewhere: the same state reset on the
     other events and paths that reach it, the other phases of the same job, the copies of the same code. Fix the
     siblings in the same batch or add them to the chart as their own conditions; the follow-up re-check tests them.
   - A performance item gets before and after numbers from the measurement plan, on the same input. A change that
     does not move the number is reverted and reported as such.
   - A structural change picks its test strategy by dependency: in-process code is tested through the new
     interface; a dependency with a local stand-in (in-memory database, temp folder) uses the stand-in; a seam with
     two real implementations gets a port with a test adapter; true externals get a mock.
   - A design card: before writing code, lay out at least two genuinely different designs and compare them on
     depth, locality and seam placement, then recommend one and get the user's pick. Migrate in steps that each
     leave the tests green.
   - Old tests made redundant by a test at the new interface are deleted only when that deletion was approved.
5. **Verify.** Run the batch's tests and the linter after each fix, and the full suite at the project's cadence.
   Show the output. Then run `/code-review` on the batch's diff and fix what it confirms. A failure that comes and
   goes (a crash in one run of several) gets a rate, not a verdict: run it ten times or more, before and after.
   Measure and bisect it in the working tree the tests normally run in, not a clean worktree: files git ignores
   (downloaded models, local settings) can change what runs, and a clean checkout may never reproduce it.
6. **Record** on the chart, never in findings.json:
   `chart.py set <id> treated --commit <sha> --base <the treatment's base> [--note ...]` for each fixed condition,
   `chart.py set <id> deferred --note "<why>"` or `wontfix --note "<why>"` for the rest. Treated is not cured: the
   next checkup's follow-up visit re-checks every treated defect and marks it cured or reopens it (treated
   improvements and design cards count as done). A bug found and fixed during the treatment that no checkup
   reported goes on the chart too: `chart.py new --title "..." --file <path> --line <n> --severity <s>
   [--evidence "..."]`, then `set <id> treated` like the others, so the follow-up re-checks it.
7. **Report** per batch: what changed, the files created and deleted, test and measurement output, and anything
   skipped and why. At the end, recommend the follow-up visit (`/checkup`, which picks it when the chart holds
   treated conditions) and give its agent count from `partition.py --visit follow-up`.

Effort is estimated as agent work (an agent writes the code and tests), plus the parts that stay slow: test suite
and benchmark wall-clock, and the user's reviews.

## Agents

Default to fixing in the main loop. Use agents only for a batch that splits cleanly by directory, one agent per
directory, each in its own worktree (`isolation: "worktree"`). State the count and model first and get a yes on
it; a skill that spawns agents (`/code-review`, a review fork) counts the same, so say its count and model
before calling it. Each brief lists the items, the only files the agent may create or delete, the project's invariants, how to
run the tests, and requires verbatim test output. Spot-check agent code on real data, not only on its own tests.
