---
name: clickup-cli-reference
description: Complete command reference for the ClickUp Framework CLI (cum) with all shortcuts, options, examples, and usage patterns
tags: [clickup, cli, reference, commands]
---

# ClickUp Framework CLI Reference

Quick reference for the ClickUp Framework CLI (`cum` / `clickup`)

## Installation

### Install from GitHub (Latest)
```bash
pip install --upgrade --force-reinstall git+https://github.com/SOELexicon/clickup_framework.git
```

### Verify Installation
```bash
cum --version
# or
clickup --version
```

### Required: API Token Setup
```bash
export CLICKUP_API_TOKEN="your_token_here"
# Or add to ~/.bashrc or ~/.zshrc for persistence
```

## Command Invocation

**In Development Environment (working in the repo):**
```bash
python -m clickup_framework.cli <command> [args]
```

**In Installed Environment:**
```bash
cum <command> [args]
# or
clickup <command> [args]
```

**How to determine which to use:**
1. First check if `cum` command is available with: `which cum` or `command -v cum`
2. If NOT available (returns empty/error), use: `python -m clickup_framework.cli`
3. If available, use: `cum`

## Quick Reference: All Short Codes

**View:** `h` `ls` `l` `c` `f` `fil` `d` `st` `a`
**Context:** `set` `show` `clear`
**Tasks:** `tc` `tu` `td` `ta` `tua` `tss` `tsp` `tst` `tad` `trd` `tal` `trl`
**Comments:** `ca` `cl` `cu` `cd`
**Docs:** `dl` `dg` `dc` `du` `de` `di` `pl` `pc` `pu`

## View Commands

| Command | Short Codes | Usage | Description |
|---------|-------------|-------|-------------|
| `hierarchy` | `h` `list` `ls` `l` | `cum h <list_id\|--all>` | Hierarchical parent-child tree view |
| `clist` / `container` | `c` | `cum c <list_id>` | Container hierarchy (Space→Folder→List) |
| `flat` | `f` | `cum f <list_id>` | Flat list view |
| `filter` | `fil` | `cum fil <list_id> [--status\|--priority\|--tags\|--assignee]` | Filtered task view |
| `detail` | `d` | `cum d <task_id> [list_id]` | Detailed single task view |
| `stats` | `st` | `cum st <list_id>` | Task statistics & distribution |
| `assigned` | `a` | `cum a [--user-id UID] [--team-id TID]` | Your assigned tasks, sorted by difficulty |
| `demo` | | `cum demo [--mode MODE]` | Demo mode (no API token required) |

## Context Management

| Command | Short Codes | Usage | Description |
|---------|-------------|-------|-------------|
| `set_current` | `set` | `cum set <type> <id>` | Set current workspace/list/task/assignee |
| `show_current` | `show` | `cum show` | Display current context |
| `clear_current` | `clear` | `cum clear [type]` | Clear context (all or specific type) |
| `ansi` | | `cum ansi <enable\|disable\|status>` | Configure color output |

**Context Types**: `workspace`, `space`, `folder`, `list`, `task`, `assignee`

## Task Management

| Command | Short Codes | Usage | Description |
|---------|-------------|-------|-------------|
| `task_create` | `tc` | `cum tc "name" --list <list_id> [options]` | Create new task (name FIRST!) |
| `task_update` | `tu` | `cum tu <task_id> [options]` | Update task properties |
| `task_delete` | `td` | `cum td <task_id> [--force]` | Delete task |
| `task_assign` | `ta` | `cum ta <task_id> <user_id> [...]` | Assign users to task |
| `task_unassign` | `tua` | `cum tua <task_id> <user_id> [...]` | Remove assignees |
| `task_set_status` | `tss` | `cum tss <task_id> [...] <status>` | Change task status (validates subtasks) |
| `task_set_priority` | `tsp` | `cum tsp <task_id> <priority>` | Set priority (1-4 or name) |
| `task_set_tags` | `tst` | `cum tst <task_id> <--add\|--remove\|--set> <tags...>` | Manage task tags |
| `task_add_dependency` | `tad` | `cum tad <task_id> --waiting-on\|--blocking <task_id>` | Add dependency |
| `task_remove_dependency` | `trd` | `cum trd <task_id> --waiting-on\|--blocking <task_id>` | Remove dependency |
| `task_add_link` | `tal` | `cum tal <task_id> <linked_task_id>` | Link tasks |
| `task_remove_link` | `trl` | `cum trl <task_id> <linked_task_id>` | Unlink tasks |

### Task Create Options

**IMPORTANT**: Task name comes FIRST as a positional argument!

```bash
cum tc "Task Name" --list <list_id> [options]
cum tc "Task Name" --parent <parent_id> [options]  # For subtasks

Options:
--list LIST_ID              # List to create task in (or "current")
--parent TASK_ID           # Create as subtask (no --list needed if parent provided)
--description TEXT          # Task description (text)
--description-file PATH     # Task description (from file)
--status STATUS            # Initial status
--priority {1|2|3|4|urgent|high|normal|low}
--tags TAG [...]           # Tags to add
--assignees USER_ID [...]  # Assign users (defaults to context assignee)
```

**Note**: `--description` and `--description-file` are mutually exclusive.

### Task Update Options

```bash
--name TEXT                # Update name
--description TEXT         # Update description (text)
--description-file PATH    # Update description (from file)
--status STATUS           # Update status
--priority PRIORITY       # Update priority
```

**Note**: `--description` and `--description-file` are mutually exclusive.

## Comment Management

| Command | Short Codes | Usage | Description |
|---------|-------------|-------|-------------|
| `comment_add` | `ca` | `cum ca <task_id> "text" \| --comment-file FILE` | Add comment |
| `comment_list` | `cl` | `cum cl <task_id>` | List task comments |
| `comment_update` | `cu` | `cum cu <comment_id> "text" \| --comment-file FILE` | Update comment |
| `comment_delete` | `cd` | `cum cd <comment_id>` | Delete comment |

### Comment Options

```bash
# Add/Update comments with text or file
comment_text               # Direct text input
--comment-file PATH        # Read comment text from file
```

**Note**: Comment text and `--comment-file` are mutually exclusive.

## Docs & Pages

| Command | Short Codes | Usage | Description |
|---------|-------------|-------|-------------|
| `dlist` | `dl` `doc_list` | `cum dl <workspace_id>` | List all docs |
| `doc_get` | `dg` | `cum dg <workspace_id> <doc_id>` | Show doc details |
| `doc_create` | `dc` | `cum dc <workspace_id> "name" [--pages "name:content" ...]` | Create doc |
| `doc_update` | `du` | `cum du <workspace_id> <doc_id> [options]` | Update doc |
| `doc_export` | `de` | `cum de <workspace_id> [--doc-id ID] --output-dir ./out` | Export to markdown |
| `doc_import` | `di` | `cum di <workspace_id> ./input_dir [--nested]` | Import markdown files |
| `page_list` | `pl` | `cum pl <workspace_id> <doc_id>` | List pages in doc |
| `page_create` | `pc` | `cum pc <workspace_id> <doc_id> --name "name" [--content "..."]` | Create page |
| `page_update` | `pu` | `cum pu <workspace_id> <doc_id> <page_id> [--name\|--content]` | Update page |

## Global Format Options

| Option | Description |
|--------|-------------|
| `--preset {minimal\|summary\|detailed\|full}` | Quick format preset |
| `--colorize` / `--no-colorize` | Force colors on/off |
| `--show-ids` | Display task IDs |
| `--show-tags` | Display tags (default: on) |
| `--show-descriptions` | Display descriptions |
| `--show-dates` | Display date fields |
| `--show-comments N` | Show N most recent comments per task (default: 5, set to 0 to hide) |
| `--include-completed` | Include completed tasks |
| `--no-emoji` | Hide emoji icons |

## Presets

| Preset | Shows | Hides |
|--------|-------|-------|
| `minimal` | IDs, status, priority | Tags, descriptions, dates, emojis, comments |
| `summary` | Status, priority, tags | IDs, descriptions, dates, comments |
| `detailed` | Status, priority, tags, descriptions, dates | IDs, comments |
| `full` | Everything + 5 recent comments | Nothing |

## Priority Values

| Value | Alias |
|-------|-------|
| `1` | `urgent` |
| `2` | `high` |
| `3` | `normal` |
| `4` | `low` |

## Status Codes (3-Letter)

Tasks display with color-coded 3-letter status codes:

- `[CLS]` Closed/Complete
- `[OPN]` Open
- `[PRG]` In Progress
- `[REV]` In Review
- `[BLK]` Blocked
- `[TDO]` To Do
- Custom statuses use first 3 letters

## Special Keywords

- `current` - Use currently set resource from context
- Works with: task_id, list_id, workspace_id, etc.

## Common Workflows

```bash
# Set up context (using short codes!)
cum set workspace 90151898946
cum set list 901517404278
cum set assignee 68483025

# Quick task view
cum h current                                    # Hierarchy view
cum a                                            # Your assigned tasks
cum st current                                   # Task statistics

# Create and manage tasks (using short codes!)
cum tc "New feature" --list current              # Auto-assigned to default assignee
cum tc "Feature" --list current --description-file spec.md  # With description from file
cum tc "Subtask" --parent <parent_id>            # Create subtask
cum tu current --description-file updated_spec.md    # Update from file
cum tss current "in progress"                    # Set status
cum tst current --add bug critical               # Add tags
cum td <task_id>                                 # Delete task

# Add comments (using short codes!)
cum ca current "Initial thoughts"                # Add comment directly
cum ca current --comment-file notes.txt          # Comment from file
cum cl current                                   # List comments

# Filter tasks
cum fil current --status "in progress"
cum fil current --priority urgent --view-mode flat

# Work with docs (using short codes!)
cum dl 90151898946                               # List docs
cum dc 90151898946 "API Docs"                    # Create doc
cum pc 90151898946 <doc_id> --name "Overview"    # Add page
cum de 90151898946 --output-dir ./docs           # Export all docs
```

## Configuration

Settings stored in `~/.clickup_context.json`:
- Current workspace/list/task/assignee
- ANSI color preference
- Last updated timestamp

## Tips

- **Use short codes everywhere!** `cum tc` instead of `cum task_create`, `cum h` instead of `cum hierarchy`
- Set context once with `cum set`, use `current` everywhere
- Default assignee auto-assigns new tasks
- `assigned` (`cum a`) command sorts by dependency difficulty
- `demo` mode works without API token for testing
- Use `--description-file` and `--comment-file` for longer content
- Tab complete works with both full commands and short codes
- Most commands support `--help` for details

## Tab Completion

Enable tab completion for bash/zsh (if argcomplete installed):
```bash
eval "$(register-python-argcomplete cum)"
```

## Troubleshooting

### Command not found: cum
```bash
# Reinstall the package
pip install --upgrade --force-reinstall git+https://github.com/SOELexicon/clickup_framework.git

# Or use the module directly
python -m clickup_framework.cli --help
```

### API Token Issues
```bash
# Check if token is set
echo $CLICKUP_API_TOKEN

# Set it permanently in ~/.bashrc or ~/.zshrc
echo 'export CLICKUP_API_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

### Permission Errors
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install git+https://github.com/SOELexicon/clickup_framework.git
```

## Getting Help

```bash
# General help
cum --help

# Command-specific help
cum <command> --help

# Examples
cum tc --help
cum h --help
cum tss --help
```
