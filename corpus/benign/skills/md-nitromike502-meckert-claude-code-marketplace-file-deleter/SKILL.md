---
name: file-deleter
description: REQUIRED for all file and directory deletions. This system replaces rm/rmdir commands. Always use this skill instead of bash rm commands when removing any files or directories. Moves items to recoverable .deleted/ trash folder with preserved structure.
allowed-tools:
  - Bash
  - Read
  - Glob
---

# File Deleter Skill - MANDATORY DELETION METHOD

**CRITICAL**: This skill MUST be used for ALL file and directory deletion operations. The `rm` command is blocked on this system.

## System Policy

- **ALL deletions** must use this skill's `delete-file.js` script
- Direct `rm`, `rm -rf`, `rmdir` commands are BLOCKED
- This applies to cleanup, refactoring, removing old files, or any deletion operation
- No exceptions - even for temporary files or build artifacts

## When to Use

Use this skill ANY time you need to:
- Remove any file (code, config, markdown, etc.)
- Delete any directory (empty or with contents)
- Clean up temporary files
- Remove build artifacts
- Delete old/unused code
- Perform any operation that would normally use `rm` or `rmdir`

## How It Works

The skill uses a Node.js script that:
1. Finds the project root (where `.git` and `.claude` directories exist)
2. Moves specified files/directories to `.deleted/` while preserving their path structure
3. Creates a `.gitignore` in `.deleted/` that ignores all contents
4. Handles both absolute and relative paths
5. Recursively moves directories with all contents
6. Overwrites existing files/directories in `.deleted/`

## Script Location

The `delete-file.js` script is located in the scripts subdirectory of this skill.

When Claude Code loads this skill, the base directory path is provided, allowing the script to be located at `<skill-base-dir>/scripts/delete-file.js`.

## Usage

**Standard deletion syntax** - use this for all deletions:

```bash
node <skill-base-dir>/scripts/delete-file.js <path1> [path2] [path3] ...
```

**Examples:**
```bash
# Delete single file
node <skill-base-dir>/scripts/delete-file.js src/old-component.tsx

# Delete multiple files
node <skill-base-dir>/scripts/delete-file.js file1.txt file2.js dir/file3.md

# Delete entire directory
node <skill-base-dir>/scripts/delete-file.js old-features/

# Delete multiple directories and files
node <skill-base-dir>/scripts/delete-file.js temp/ build/ old-file.txt
```

## Behavior

- **Non-existent files**: Skipped with warning, script continues
- **Overwriting**: Existing files/directories in `.deleted/` are overwritten
- **Directory structure**: Preserved within `.deleted/`
  - Example: `src/components/Button.tsx` → `.deleted/src/components/Button.tsx`
- **Git ignore**: All contents of `.deleted/` are automatically git-ignored

## Recovery

Files remain recoverable in `.deleted/` and can be manually restored if needed.

## Error Handling

If you attempt to use `rm` commands, you will receive an error message directing you to use this skill instead. Always default to using this script for any deletion operation.
