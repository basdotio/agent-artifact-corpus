---
name: running-milestone-loops
description: Use when asked to loop, keep going while the user is away, or drive a milestone, epic or ticket set to done over hours or days with a design doc and Linear (or another tracker) as the sources of truth. Also use when resuming such a loop after a context compaction, a scheduled wakeup, or a hand-off to another session or machine.
---

# Running milestone loops

## Overview
A milestone loop turns a design doc and tracker tickets into adversarially reviewed, tested PRs while the user is away. It runs for days, across compactions and machines. Two principles follow from that:
- **The loop's memory is its files, not your context.**
- **Anything that leaves your branches is governed by an authority table the user approved.**

**REQUIRED BACKGROUND:** workflow-authoring (the Workflow tool). Read the sources with the project's design-doc skill if it has one.

## Start a loop
1. **Create the loop dir.** Put it outside the repo or on a never-merged branch. Fill `LOOP.md` from `LOOP.template.md` (in this skill's directory), and the state files from `reference.md` § State files.
2. **Fill LOOP.md's Authority table.**
   - Fill in every row the user's standing instructions already answer (CLAUDE.md, memory, this conversation), citing the source.
   - Ask the user about the remaining rows once, in one message, each with a proposed default.
   - Every row is required; an unanswered row means "not allowed".
   - Don't ask about order, scope or acceptance criteria; those come from the sources.
3. **Build QUEUE.md from the milestone.** For each ticket record its done-when, its design § refs, its dependencies and the files it will touch. Choose the stack shape (§ Stack shape).
4. **Take ownership:** write `OWNER` (`reference.md` § Ownership). Then start the first unit.

## Every wakeup or resume, in this order
1. **Ownership first.** Look for another live session on this loop. Check: OWNER's heartbeat age; `ps` for another `claude` process with this loop dir in its args; tmux sessions; recent writes to other transcripts. If another session owns it, stop and tell the user.
2. **Re-read the files.** Re-read LOOP.md, QUEUE.md, PRS.md and QUESTIONS.md. The compaction summary and the wakeup prompt are hints; the files and live state win.
3. **Reconcile with reality:**
   - background workflow results;
   - each PR's state, base, review decision and checks;
   - branch tips against PRS.md;
   - new human comments;
   - the user's replies.
4. **Act and record.** Act, update the files, refresh OWNER's heartbeat, and re-arm the fallback wakeup.

## Per unit
Run `unit-pipeline.js` with the Workflow tool: `Workflow({scriptPath: "<this skill dir>/unit-pipeline.js", args: {loop, units}})`.
- **One worktree per unit**, never shared by two agents. Each worktree is branched from a freshly fetched base.
- **Pipeline:** implement → three independent read-only reviewers (conformance, breaker, tests) → fixer, only if the reviews found something → a conformance and breaker re-review if a blocker or major was fixed → PR text written from the final diff.
- **Already implemented?** If the branch already holds the change, pass `implemented: true` (and any `gates` you already ran as `[{gate, command, result}]`); the unit starts at review.
- **Scope every stage.** Name the unit's gate commands in its brief; agents run only those, not other CI tiers or extra installs. Reviewers reuse the reported gate results instead of re-running suites, spend about 15 minutes, prefer unit-level probes to real services, and report no nits; the tests reviewer runs at most 5 mutants on the changed lines against the covering test files. PR text stays under about 2 KB.
- **Keep briefs short:** the goal, the done-when, the gate commands and pointers to the sources. Agents read the tickets, design doc and code themselves, so don't paste background into the brief.
- **Bot review threads** (Greptile) on a pushed PR are fixed directly, not through this pipeline (`reference.md` § Bot review loop).
- **Done:** a unit is done only when its done-when table is MET from evidence that actually ran. Green CI, a closed ticket or "the agent said so" don't count. The table must name every limit on the proof: a slice, a mock, a skipped store, a consumer still on the released version.

## Outward actions
Before any write that leaves your branches, check its Authority row in LOOP.md. That includes:
- tracker comments, state changes and new tickets;
- chat messages;
- reviewer requests and @-mentions;
- PR comments;
- merges, deploys and prod data.

If the action isn't listed as allowed:
- add it to QUESTIONS.md and lead the next status update with it;
- keep working everything that isn't blocked on it;
- don't route around a slow reviewer or an absent user through someone else.

## Stack shape
- **Units that share files go in one linear stack**, each PR based on the branch below it. Siblings off main that share files conflict on every merge.
- **Independent units** branch from a freshly fetched main.
- **Restacking:** record every layer's tip in PRS.md first, then rebase each layer `--onto` its parent's new tip from its recorded old base. Push with `--force-with-lease`. See `reference.md` § Stacking.

## Keep going
- End a turn only while a background workflow is running; it re-invokes you when it finishes. Also schedule a 20–30 minute fallback wakeup.
- Stop only when QUEUE.md has nothing actionable. Then report what's done, what's blocked and exactly what you need from the user.
- Send a status update every few hours or at each milestone. Lead with the decisions you need, then merged, open and blocked items, with links.

## Common mistakes
| Mistake | Instead |
|---|---|
| Posting questions or progress as tracker comments by default | Check the Authority row. If it's not allowed, use QUESTIONS.md and the status update. |
| Resuming from the compaction summary | Re-read the files and reconcile with live state first. |
| Two sessions working one loop | Check ownership first on every wakeup. |
| Re-pinning goldens or snapshots to turn CI green | Account for every moved value against the unit's declared changes first. |
| A reviewer who trusts the implementer's report | Reviewers read the sources themselves; the report is a list of claims to check. |
| Hand-merging a generated fixture during a rebase | Regenerate it at that commit, then re-check what it declares. |
