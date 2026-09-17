---
name: init
description: Initialize a new feature workflow with git worktree. Use when the user wants to start a new feature, create an isolated development branch, says "init worktree", or needs to set up a feature branch for compounder workflow.
---

# Init Skill

Initializes an isolated git worktree for feature development, enabling parallel work without affecting the main branch.

## When to Use

- User says "initialize a worktree for X"
- User says "use compounder to init"
- User wants to start a new feature branch
- User needs isolated development environment

## Quick Start

```bash
# Via skill (if permissions are configured)
/compounder:init "my-feature"

# Direct script call (always works)
scripts/init-worktree.sh "my-feature"
```

## What Gets Created

| Item | Location | Description |
|------|----------|-------------|
| Worktree | `../compounder-{feature}` | Sibling directory to main repo |
| Branch | `feat/{feature}` | Based on current HEAD |

## Invocation Methods

### Method 1: Skill Tool (May Require Permission)

```
Skill: compounder:init
Args: "feature-name"
```

**Note:** This may fail with permission error if bash command isn't pre-approved.

### Method 2: Direct Script Call (Recommended)

```bash
/path/to/scripts/init-worktree.sh "feature-name"
```

The script is located at:
```
$CLAUDE_PLUGIN_ROOT/scripts/init-worktree.sh
```

Or in cached plugins:
```
~/.claude/plugins/cache/jero2rome-compounder/compounder/*/scripts/init-worktree.sh
```

## Debugging Journey (Reference for Claude)

This section documents the trial-and-error process that led to successful invocation:

### Attempt 1: Skill Tool
```
Tool: Skill
skill: "compounder:init"
```
**Result:** FAILED
```
Error: Bash command permission check failed for pattern...
This command requires approval
```
**Lesson:** The Skill tool internally runs a bash script that wasn't in the allowed permissions list.

### Attempt 2: Ask User for Feature Name
```
Tool: AskUserQuestion
questions: [{"question": "What feature?", "options": [{"label": "Enter custom"}]}]
```
**Result:** FAILED
```
Error: Array must contain at least 2 element(s)
```
**Lesson:** AskUserQuestion requires at least 2 options. Can't use it for single free-text input.

### Attempt 3: Direct Script Without Argument
```
Tool: Bash
command: /path/to/scripts/init-worktree.sh
```
**Result:** FAILED
```
Error: Feature name required
Usage: /compounder:init "my-feature"
```
**Lesson:** The script requires a positional argument for the feature name.

### Attempt 4: Direct Script With Argument (SUCCESS)
```
Tool: Bash
command: /path/to/scripts/init-worktree.sh "test-comp"
```
**Result:** SUCCESS
```
Creating worktree and branch...
HEAD is now at ad08615 ...
Worktree created: ../compounder-test-comp
Branch created: feat/test-comp
```

## Key Learnings

1. **Skill tool limitation:** Underlying bash commands need explicit permission approval
2. **Workaround:** Call the script directly via Bash tool with full path
3. **Script location:** `$CLAUDE_PLUGIN_ROOT/scripts/init-worktree.sh` or cached path
4. **Required argument:** Feature name MUST be passed as positional argument
5. **AskUserQuestion:** Requires 2+ options; can't use for single text input

## Required Permission

To auto-approve the init script, add to `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(*/scripts/init-worktree.sh:*)"
    ]
  }
}
```

## After Initialization

1. **Switch to worktree:**
   ```bash
   cd ../compounder-{feature} && claude
   ```

2. **Start workflow:**
   - "Let's ideate [feature]" -> feature description
   - "Create a spec" -> spec.md
   - "Create a plan" -> plan.md
   - "Create tasks" -> tasks.md
   - "Execute the tasks" -> implementation

3. **Cleanup after merge:**
   ```bash
   git worktree remove ../compounder-{feature}
   ```

## Handoff

After init completes, guide user to:
1. Open new terminal in worktree directory
2. Start Claude Code in that directory
3. Begin with `ideate` skill for the feature
