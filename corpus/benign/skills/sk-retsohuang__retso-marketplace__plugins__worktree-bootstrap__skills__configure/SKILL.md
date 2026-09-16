---
name: configure
description: Create or update .worktreeinclude.yaml configuration for worktree-bootstrap. Use when user says "set up worktree config", "configure worktree bootstrap", "add files to worktree include", "worktree bootstrap config", or provides file paths to include in worktree bootstrap.
license: MIT
allowed-tools: Bash Read Write
metadata:
  author: Retso Huang
  version: "1.0"
---

# Worktree Bootstrap Config

Create or update `.worktreeinclude.yaml` to configure which ignored files get copied to new worktrees.

## Input

Arguments after the skill invocation are treated as file or directory paths to add (e.g., `/worktree-bootstrap:configure .env .env.local`). If no arguments are provided, check the user's message for file/directory references.

## Steps

### Step 1: Determine mode

Check whether file/directory paths were provided (as arguments or mentioned in the user's message).

- **Paths provided** → go to Step 3 (Add entries)
- **No paths provided** → go to Step 2 (Scaffold or show)

### Step 2: Scaffold or show existing config

Check if `.worktreeinclude.yaml` exists in the project root:

```bash
cat .worktreeinclude.yaml 2>/dev/null
```

**If the file exists**: Show its current contents to the user, then scan for additional ignored files not yet in the config:

```bash
git ls-files --others --ignored --exclude-standard
```

Compare against entries already in the config. If there are new candidates, present them and ask the user which to add. If no new candidates, inform the user the config is up to date.

**If the file does not exist**: Scan for all ignored files:

```bash
git ls-files --others --ignored --exclude-standard
```

Present the discovered files to the user and ask which ones to include. Then write `.worktreeinclude.yaml`:

```yaml
files:
  - .env
  - .env.local
```

If no ignored files are found, create the file with an empty list and explain the format:

```yaml
# List files to copy to new worktrees (must be gitignored)
# Supports glob patterns (e.g., .env.*)
files: []
```

### Step 3: Add specific entries

For each provided path, verify it is ignored:

```bash
git check-ignore -q <path>
```

- **Ignored (exit code 0)**: Add to `.worktreeinclude.yaml`
- **Not ignored (non-zero exit)**: Warn the user and skip

If `.worktreeinclude.yaml` does not exist, create it with the valid entries. If it exists, read the current contents, append new entries (avoiding duplicates), and write back.

After adding, show the updated config to the user.
