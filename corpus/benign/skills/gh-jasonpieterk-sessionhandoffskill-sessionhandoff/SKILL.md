---
name: SessionHandoff
description: Split the pending work in the current conversation across N fresh sessions and write one self-contained, copy-paste handoff prompt per session, grouped easy to hard. Use when the user invokes /SessionHandoff or asks to hand off, split, or distribute work across multiple sessions or agents.
---

# SessionHandoff

Turn the work already discussed in this conversation into one handoff prompt per new session.

## Step 1: Ask how many sessions

Ask the user once: "How many sessions do you want to split the work into?" Wait for the answer. If the user already gave a number when invoking the skill, skip the question.

## Step 2: Inventory and rate the work

List every pending task from the current conversation (only this conversation). For each task note:

- a short title and what done looks like
- difficulty: **easy**, **medium** or **hard**, judged by you (scope, risk, ambiguity, files touched)
- files and areas it touches
- dependencies on other tasks

If a task is huge, split it into smaller tasks that can go in different sessions, and record the order or interface between the parts.

## Step 3: Group into N sessions

- Sort from easy to hard. Session 1 is the easiest, session N the hardest.
- With N equal to the number of difficulty tiers present, use one tier per session.
- With more sessions than tiers, split tiers further so that each session has a balanced load. Keep related tasks together.
- With fewer sessions than tiers, merge the closest tiers.
- Tasks that touch the same files or codebase area, or depend on each other, go in the same session. If they cannot be kept together, flag the overlap and give each session its own branch.
- If N is larger than the number of tasks, warn the user and cap N at the number of tasks.
- Label each session with its main difficulty and a suggested model: a fast, cheap model for easy work, a mid-tier model for medium work, and the strongest available model for hard work.

Show the proposed grouping as a short table (session, difficulty, tasks, suggested model) before writing the prompts, and mention any warnings (cap, overlaps, splits).

## Step 4: Write one prompt per session

Each prompt must be fully self-contained. The new session sees nothing of this conversation. Use this structure:

```
# Session <i>/<N> (<difficulty>): <short title>

## Summary
<What this session must achieve and why. The relevant context and decisions from the conversation.>

## Tasks
1. <task, with details>
2. ...

## Files
<Repository-relative paths to read or change. Say which are created.>

## Constraints
<Things not to touch, conventions to follow, decisions already made, other sessions working in parallel and what they own.>

## Acceptance criteria
- <Concrete, checkable conditions, including the commands to run (tests, lint, build).>

## Branch
<Branch name to use, for example handoff/session-<i>-<slug>. State whether to branch from main or from another session's branch, and whether to open a PR.>

## Report back
<Exactly what to report when finished: what changed, files touched, test results, open issues, follow-ups.>
```

Use repository-relative paths only. Never put secrets or credentials in a prompt.

## Step 5: Output

1. Save each prompt to `handoffs/session-<i>-<difficulty>.md` in the current project, creating the folder if needed. Add `handoffs/` to `.gitignore` only if the user asks.
2. Print every prompt in chat inside its own fenced code block so it can be copied in one click. Introduce each block with a line such as:

   `1st prompt (easy), saved to <absolute path of the file>`

3. End with a one-line recommendation of the order to run the sessions and whether any must wait for another.
