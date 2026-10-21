---
covers: the plan file, with one example, and how delegated agents share state through scratchpad files
---

# Plan format

The plan lives at `wip/{yyyy.MM.dd}_{short-task}/plan.md`. It is the single source of truth for the run: approved before execution, updated as work proceeds, with dead branches pruned. `Status` moves `awaiting approval → approved → in progress → pride gate → done`.

## Example

```markdown
# Replace legacy port lookups

**Tier:** Medium
**Strategy:** explore → parallel edits per area → build → pride gate
**Status:** awaiting approval

## Team

| Persona      | Responsibility                    | Pride bar                                        | Key |
| ------------ | --------------------------------- | ------------------------------------------------ | --- |
| Maintainer   | code reads cleanly next year      | one pattern at every site; no one-call helpers   | yes |
| Breaker      | nothing that worked breaks        | build green; each changed path run once          | yes |
| Scope keeper | the least change that works       | no file touched that the task did not need       | no  |

## Items

- [ ] 1. Find every call site — explore agent → sites.md
- [ ] 2. Edit sites, 3 parallel agents by area — owner: Maintainer — reads sites.md
- [ ] 3. Build and exercise changed paths — inline, high effort — owner: Breaker
- [ ] 4. Pride gate — one fresh agent per key persona → pride-<persona>.md

## Pride gate

| Round | Maintainer | Breaker |
| ----- | ---------- | ------- |
| 1     |            |         |

## Follow-ups / open questions
```

Annotate items as loosely as is clear. The table cells in the pride gate hold `yes`/`no` and a one-line reason.

## Sharing state between agents

A delegated agent sees only its prompt and the files you name. For each one, say which file it reads, where it writes, and that every entry must stand alone.

Sequential stages may share one append-file. Parallel agents must each write a distinct file, or return the result in their final message; concurrent appends to one file corrupt it.
