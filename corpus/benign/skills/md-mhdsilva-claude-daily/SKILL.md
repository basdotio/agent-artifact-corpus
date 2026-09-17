---
name: daily
description: Generate a daily summary of Claude Code sessions - activities, time spent, and cost. Use with optional date argument (YYYY-MM-DD).
user-invocable: true
---

Run the `claude-daily` CLI tool. The tool generates the full formatted report — you just run it and stop.

## Instructions

1. Determine the arguments:
   - If the user provided a date (e.g., `/daily 2026-03-15`), use that date
   - If no date was provided, use today's date
   - If the user asked for English output (e.g., `/daily --lang en`), add `--lang en`
   - Default language is Portuguese (`--lang pt`)

2. Run the command using Bash:

   ```bash
   claude-daily [DATE] [--lang pt|en]
   ```

3. If `claude-daily` is not found in PATH, try running it directly:

   ```bash
   ~/.local/bin/claude-daily [DATE] [--lang pt|en]
   ```

4. **CRITICAL**: After the Bash tool returns, you are DONE. Do NOT write ANY text after the tool output. No summary, no commentary, no "here's your report", no "would you like details?", no reformatting. The CLI output IS the response. Say absolutely nothing.
