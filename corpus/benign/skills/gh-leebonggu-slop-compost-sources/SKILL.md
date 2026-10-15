---
name: sources
description: Manage the external source list that slop-compost's Track B reads (failure cases, trends, revenue, Korean communities, your own scraper output) - list sources with citation stats, add, remove, edit, enable, or disable one. Use when the user wants to see or change where slop-compost looks for outside signals - e.g. "slop-compost sources", "add a source", "disable failory", "which sources get cited", "출처 목록", "출처 추가", "출처 끄기", "소스 관리".
argument-hint: "list | add [id] | remove <id> | edit <id> | enable <id> | disable <id>"
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../compost/scripts/ledger.py *)
---

# sources (slop-compost source list)

Arguments: `$ARGUMENTS`

This skill shares its script with the `compost` skill. **The two skill folders must be siblings** (`.../skills/compost` and `.../skills/sources`), as they are in the plugin and in a manual install that links both folders into `~/.claude/skills/`.

- `<CLI>` means exactly `python3 ${CLAUDE_SKILL_DIR}/../compost/scripts/ledger.py` (write it like this so the pre-approved permission rule matches). Each call prints one JSON line; `{"error": ...}` means show the message and stop or ask again as below.
- If the script is missing (`No such file`), stop and tell the user: "The `sources` skill needs the `compost` skill next to it: install the slop-compost plugin, or link both `skills/compost` and `skills/sources` into `~/.claude/skills/`."
- The list is `<ledger>/sources.md` (ledger = `SLOP_COMPOST_HOME`, default `~/.slop-compost`). The script seeds it from the shipped defaults if it does not exist and never overwrites it.
- Write user-facing text in the user's language (`SLOP_COMPOST_LANG` if set). Ids, field names, and enum values stay in English.

## Do

1. **New defaults first.** Run `<CLI> sources list`. If it reports `new_default_sources`, ask once in one line: "N new default sources (ids) - add them? (yes / no)", then `<CLI> sources sync-defaults yes|no`. Then handle the command.
2. Handle the command (rules: [sources.md](../compost/references/sources.md), section "`sources` subcommand"):

| user command | do |
|---|---|
| `list` (or no arguments) | Show the `list` result as a table: id, category, type, enabled, removed/restored, cited, cited in adopted (`-` = no runs yet). |
| `add [id]` | Ask once, one line: `type, how, category` (e.g. `fetch, https://example.com/rss, trend`). Then `<CLI> sources add [id] --type "<type>" --how "<how>" --category <category>`. On an `error` listing allowed values, show them and ask again. |
| `remove <id>` | `<CLI> sources remove <id>` (marks `removed`, sets `enabled: false`; nothing is deleted). |
| `edit <id>` | `<CLI> sources edit <id>` shows the entry. Ask once for `field=value` pairs on one line, then `<CLI> sources edit <id> 'field=value' 'field=value' ...` (one quoted argument per pair). `id` cannot change: suggest `remove` + `add`. |
| `enable <id>` / `disable <id>` | `<CLI> sources enable <id>` / `<CLI> sources disable <id>` (`enable` on a removed entry restores it). |

3. An `error` with the usage line (unknown verb, missing or unknown id): show the usage and the listed ids, then stop.
4. After a change, show the changed entry and stop. Never edit `sources.md` by hand and never touch files under the skill folders.
