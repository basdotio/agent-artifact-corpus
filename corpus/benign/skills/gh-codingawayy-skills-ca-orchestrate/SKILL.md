---
name: ca-orchestrate
description: Design how to execute a task with an AI coding agent — assemble a team of contrasting personas with clear responsibilities, right-size the machinery (inline vs. subagents vs. separate sessions, effort, models, a WIP scratchpad) to the task, write the plan to a file, get approval, then run it until the key personas are proud of the result. Invoke when the user runs /ca-orchestrate, or asks for the best way to tackle a substantial multi-step or parallelizable task — to "orchestrate", "plan the approach/execution", "assemble a team", "use subagents for this", or to break a big task into a coordinated agent plan.
---

# Orchestrating a task

Design **how** to execute a task, then run it. Two ideas carry the skill:

- **Use the least machinery that fits.** Loading this skill creates a pull toward orchestration. Resist it. Inline work with full context is the default; delegate only for a concrete reason (parallel independent chunks, protecting the main context from a large read, or a fresh context for review).
- **Done means the team is proud.** The work is not done when the steps are checked off. It is done when every key persona, reviewing in a context that did not produce the work, signs off with evidence. → `reference/team.md`

## Machinery depends on your agent

Agents differ in what they can delegate. Use what yours has, and fall back in this order:

- **Subagents** (a fresh context the agent spawns itself) — best for parallel chunks and for fresh-context review.
- **A separate session** — when the agent cannot spawn subagents, start a new session with a self-contained prompt and the files it needs. It gives the same fresh context, at the cost of a manual hand-off.
- **Inline** — when neither is practical. For review, do a separate pass that reads only the result and the pride bar, not your own reasoning, and say in the report that the review was not independent.
## Procedure

1. **Size the task.** When unsure, pick the smaller size.
   - **Trivial / Small** — one area, little uncertainty. Name a one-line team (1–2 personas), do it inline, run the pride gate inline. No plan file, no approval gate.
   - **Medium / Large** — several areas, real uncertainty, parallel chunks, or real phases. Continue below.

2. **Assemble the team.** Contrasting personas, one responsibility each, a concrete pride bar each, key ones marked. → `reference/team.md`

3. **Design the plan.** Decompose only far enough to route the work: what runs inline, what goes to parallel subagents or sessions, where effort or a stronger model is needed, and which persona owns each item. Use the skills, agent types and tools your agent actually has; check its limits. → `reference/limits.md`

4. **Write the plan, then stop.** Save it to `wip/{yyyy.MM.dd}_{short-task}/plan.md` (or the project's own scratch folder) and present the tier, team, strategy and items. → `reference/plan-format.md`. Until the user approves, do not dispatch a subagent, start a session, or edit code. The user may change the team.

5. **Execute.** If your agent has a task list, mirror open items into it; the plan file wins if they drift. If the work turns out much smaller or larger than sized, stop, re-size, and note it in the plan.

6. **Run the pride gate.** → `reference/team.md`

7. **Close out.** Mark the plan `done`. Report the outcome in one line, who signed off on what evidence, the follow-ups the personas raised, and any open decision.
