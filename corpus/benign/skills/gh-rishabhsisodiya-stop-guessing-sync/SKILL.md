---
name: sync
allowed-tools: Bash, Read, Grep, Glob, Edit, AskUserQuestion
disable-model-invocation: true
description: "Run /sync as the last step after a change is complete, around merge, to keep the durable files honest. Reconciles AGENTS.md, the scope and spec statuses against what the repo now actually shows. Surgical edits only: it adds lines and rewrites single lines it owns, never a section, never curated prose."
---

## What this skill does

Keeps the files everything else reads from drifting away from the truth.

`AGENTS.md`, the scope and the specs are read by every other skill on every run. A stale
line in any of them is not a cosmetic problem: it is a wrong instruction that gets followed
silently. A test command that changed three weeks ago makes `/develop` and `/verify` wrong
until someone notices.

This runs at the end of a change, when the repo has moved and the files have not.

## This skill owns reconciliation

Comparing the repo against the scope, and writing the result, happens here and nowhere else.
`/scope` plans; this skill reconciles. One writer means two skills can never tick the same
box from two different readings of the same evidence, or tick it twice.

`/scope` run bare reads the reconciled state and plans forward on top of it. If the scope has
not been reconciled since the last change, it says so and recommends this skill first.

## Where the files are

The scope and specs each live where the project chose for that kind (`_shared/workflow-files.md`).
Reconcile only the kinds that are saved. If neither is, update `AGENTS.md` only, and say so.

## Evidence, never memory

Everything this skill writes comes from something it can point at: a diff, a file on disk, a
command it ran. Never from what happened earlier in the conversation, and never from what
the plan said would happen.

If the evidence is ambiguous, it is a question for the engineer, not a guess.

## Surgical edits only

This is the discipline that makes the skill safe to run often:

- **Add** a line that is now true and missing.
- **Rewrite a single line it owns**: a version, a command, a path, a status, a pointer.
- **Never rewrite a section.** Never reformat. Never reword someone's sentence.
- **Never touch human prose.** If a paragraph a person wrote is now wrong, say so in the
  report and leave it exactly as it is.

A skill that rewrites files wholesale gets run once and then avoided, which defeats it.

## What this skill refuses to do

1. **Never declares a feature `done`.** That is the engineer's call. It can report that
   everything a feature needed appears finished, and ask.
2. **Never writes a new spec, scope row or convention that has no evidence.**
3. **Never resolves a conflict on its own.** Drift is surfaced, not fixed.
4. **Never deletes.** A de-scoped row becomes `dropped`. A replaced spec becomes
   `Superseded by NNNN`. History stays.
5. **Never touches code, and never runs a command the boundary blocks.**
6. **Never marks a spec `Decided`.** Ratifying an assumption is `/architect`'s job.

## What it reconciles

### The scope

- Boxes whose work is now visibly in the repo → tick them.
- A feature whose build is clearly complete → report it and ask whether it is `done`.
- Missing pointer lines → fill in `code in <path>` where the evidence is clear.
- Code with no scope row → surface it. Something was built that was never planned.
- A row marked done with nothing in the repo → surface it.
- A feature still carrying `assumed decision (spec NNNN)` → report it as outstanding.

### `AGENTS.md`

- A command that changed → rewrite that line and name the change in the report.
- A dependency version that moved meaningfully → update it.
- A new top level directory → add its one line.
- **A convention that is now real** → add it, but only with two or more examples, the same
  evidence bar `/audit` uses. One occurrence is a sighting.
- A convention the codebase has abandoned → surface it, do not delete it. Someone wrote
  that line deliberately.
- A new workspace or service → note that it needs its own nested file via `/audit <path>`.

### Specs

- A spec whose decision the change contradicts → mark nothing, report it as stale, and say
  which part the code no longer matches.
- A spec superseded by a later one → add `Superseded by NNNN` to the old one.
- An `Assumed` spec whose assumption is now load bearing in shipped code → report it as
  owed ratification, more loudly each time.

### The Stack table in `AGENTS.md`

- A tool the repo now uses that the table does not name → add the row.
- A row the repo contradicts → the repo wins. Rewrite that row and say so.
- A change here usually means `/guard` needs re-running, because its migration rules were
  written for the old tool. Say so rather than re-running it yourself.

Never write to `_shared/stack-defaults.md`. It is a machine wide preference, read only to
skills.

## Execution

### Step 1: Gather the evidence

- `git diff` for the change, and `git log` since the files were last touched.
- The current state of the scope, the specs, and `AGENTS.md`.
- The real directory tree and the real manifests.
- Re-run the commands in `AGENTS.md` if the change plausibly affected them. A command that
  no longer works is the most valuable thing this skill can catch.

### Step 2: Compare, and sort into three piles

- **Certain and owned**: apply the edit.
- **Certain but not yours**: human prose that is now wrong, a conflict between two files,
  a convention that has quietly changed. Report it, change nothing.
- **Ambiguous**: ask, in one batched panel, or leave it and say you left it.

### Step 3: Apply

Read each file again immediately before editing it, because a teammate may have changed it
since Step 1. Make the edits, one line at a time.

### Step 4: Report

```
## /sync · <change, one line>

**<N> edits applied · <M> items surfaced for you.**
Updated: <one line per edit, e.g. "AGENTS.md test command: `npm test` → `pnpm test:unit`">
Surfaced: <drift that needs a person: stale specs, conflicting prose, unplanned code>
Outstanding: <assumed decisions still owing ratification, and which feature carries each>
Ready to close: <features that look complete, asking whether to mark them done>
Next: <usually nothing, or `/architect` to ratify an assumption>
```

Every line under `Updated` names the before and the after. A sync that says "updated
AGENTS.md" and nothing else is not reviewable, and the point of surgical edits is that each
one can be checked in a second.
