---
covers: platform limits and non-obvious rules to design the machinery around
---

# Limits

Every agent has its own limits on delegation. Before a plan depends on one, check it against the agent you are running in. If you cannot confirm a limit, design as if it is lower.

## What to check

- **Can it spawn subagents at all?** If not, use separate sessions or inline passes.
- **How deep can subagents nest?** A subagent at the bottom level may not get the tool to spawn more. For multi-phase work, run each phase from the main session and read each result before the next.
- **How many agents can run at once?** Parallel work beyond this runs in sequence.

## Rules that are easy to miss

- **Plan mode vs. this plan.** If the agent has a plan mode and it is in play, it settles _what_ to change. This plan covers only the machinery and the team; do not run a second approval on the solution.
- **Send parallel agent calls together.** Most agents run delegated calls in parallel only when they go out in one message; otherwise they run in sequence.
