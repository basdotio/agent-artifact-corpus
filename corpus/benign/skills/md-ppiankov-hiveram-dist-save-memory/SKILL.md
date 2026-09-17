---
name: save-memory
description: Save memory files locally and push to workledger for cross-machine sync
argument-hint:
---

Save current memory state and sync to workledger. $ARGUMENTS

## Steps

1. **Update local memory** -- review the current conversation for new stable patterns, conventions, or decisions:
   - Only save patterns confirmed across multiple interactions
   - Do not save session-specific state (that belongs in context)
   - Do not duplicate existing entries -- update them instead
   - Write to `~/.claude/projects/<project-key>/memory/` using memory frontmatter format
   - Update `MEMORY.md` index if new topic files were created
   - If nothing new to save, report "No new memory to save" and skip to step 2

2. **Push to workledger** -- sync memory files using the three-tier fallback:
   - Read MEMORY.md and all topic files from the local memory directory
   - **Tier 1 (MCP):** for each file, call `workledger_memory_put(project="<project>", key="memory/<filename>", content=<file contents>)`
   - **Tier 2 (HTTP API):** if MCP is unavailable:
     - `source ~/.workledger/api-key.env`
     - `curl -s --max-time 10 -X PUT -H "Authorization: Bearer $WORKLEDGER_API_KEY" -H "Content-Type: application/octet-stream" --data-binary @<local-path> '${WORKLEDGER_URL}/api/v1/blob/<project>/memory/<filename>'`
   - **Tier 3 (local only):** if both are unavailable, report "Memory saved locally only -- workledger sync skipped"
   - Show: `Pushed N memory files to workledger`

## Rules

- This is a lightweight sync -- no commit, no push, no context save
- Use `/wrapup` instead when ending a session
- Do not save ephemeral debugging state -- that belongs in context
- Keep MEMORY.md under 200 lines -- move detail to topic files
