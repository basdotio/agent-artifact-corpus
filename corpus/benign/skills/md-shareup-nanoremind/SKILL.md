---
name: nanoremind
description: Read, create, update, complete, and delete reminders with the nanoremind CLI. Use when working on a Mac where nanoremind is installed and you need Apple Reminders access from the terminal.
---

# nanoremind CLI

Use `nanoremind` directly. Always use `--json` for structured output.

## Read

```bash
nanoremind lists --json
nanoremind list --json -l "Reminders" --limit 20
nanoremind list --json -l "Reminders" --completed
nanoremind search --json "query"
nanoremind show --json --id "REMINDER-UUID"
nanoremind due --json --days 7
nanoremind today --json
nanoremind next --json
nanoremind next --json --count 5 -l "Work"
```

## Write

```bash
nanoremind create --json -l "Reminders" --title "Task" --due "2026-02-15"
nanoremind update --json --id "REMINDER-UUID" --title "Updated title"
nanoremind complete --json --id "REMINDER-UUID"
nanoremind uncomplete --json --id "REMINDER-UUID"
nanoremind delete --json --id "REMINDER-UUID"
```

## Workflow

1. Run `lists --json` first for exact list names.
2. Pull IDs from `list`, `search`, or `due` before mutation commands.
3. Use `priority` values as integers: 0=none, 1=high, 5=medium, 9=low.
4. Ask for confirmation before create, update, complete/uncomplete, or delete.

## Options

| Flag | Description |
|------|-------------|
| `--json` | Output JSON (always use this) |
| `-l <list>` | Filter by list name (case-insensitive) |
| `--limit <n>` | Max results to return |
| `--offset <n>` | Skip first N results |
