---
name: whats-next
description: The five highest-priority open tickets for this repo's Setlist team. Use when the user asks what's next or what to work on, or invokes /whats-next.
---

# What's next

1. **Team**: the `--team` value in `docs/agents/issue-tracker.md`. If the repo has no such file or it names no Setlist team, say so and stop.

2. **Query**, one call. Filters the user typed after the command (`"project=Solo 3.1"`, `labels=ready-for-agent`, `--search android`); add them before the `|`.

   ```sh
   setlist issue list --team TEAM status=todo status=backlog status=in-progress blocked=no \
     | jq -r '{"urgent":0,"high":1,"medium":2,"low":3} as $r
         | .issues | sort_by(.updated_at) | reverse | sort_by($r[.priority // ""] // 4)
         | .[:5][] | [.id, (.priority // "-"), .status, .title, (.assignees | join(","))] | @tsv'
   ```

   This keeps open, unblocked tickets, ordered by priority, then most recently updated.

3. **Output**: one table, `ID · Priority · Status · Title · Assignee`, titles on one line. Then one line naming the pick: an `in-progress` ticket if the list has one (finishing beats starting), otherwise the first row.

The skill only reads; ticket changes happen in the work that follows.
