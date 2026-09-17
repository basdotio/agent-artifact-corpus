---
name: "Dangerous Operations"
description: "Complete safety protocol for handling potentially destructive operations with mandatory approval and git checkpoints"
approved: Yes
created: 2026-02-27
license: "MIT"
metadata:
  author: "Main Agent"
  version: "1.0"
  last_updated: "2026-02-27"
  tags: [safety, dangerous-operations, approval, git-checkpoint, security]
tools: [Bash]
files: []
---

# Dangerous Operations

## Overview

Mandatory safety protocol for all potentially dangerous or destructive operations. Agents **MUST NEVER** perform destructive actions without explicit user approval and git checkpoint.

**Usage Type**: EDUCATIONAL - Learn safety protocols for dangerous operations.

## When to Use

- Before deleting files/directories
- Before dropping databases or truncating tables
- Before destructive git operations
- Before system modifications
- Before any irreversible action

## Core Principle

**This is NOT optional. This is NOT negotiable. Violation is SEVERE.**

## What is Dangerous?

ANY action that:

### File & Code Deletion
- Deleting multiple files (`rm -rf`, `rm *`)
- Deleting entire directories or test files
- Removing large code sections (>50 lines)
- Deleting functions/classes
- Gutting files for rewrites
- Removing API endpoints or schemas

### Data Operations
- Dropping databases or truncating tables
- Deleting production data
- Purging caches
- Removing backups or configs

### Destructive Git Operations
- `git reset --hard`
- `git clean -fd`
- `git push --force` (especially to main/master)
- Deleting branches
- Rebasing shared branches
- Amending pushed commits

### System Operations
- Modifying system files or permissions
- Killing critical processes
- Uninstalling packages
- Modifying PATH or environment variables

### Build/Deploy Operations
- Deleting build artifacts
- Removing lock files (package-lock.json, Cargo.lock)
- Removing node_modules/vendor
- Clearing Docker images/containers
- Destroying cloud infrastructure

## Mandatory Approval Process

### 1. Detection

Check if operation is:
1. Destructive (deletes, removes, drops, truncates, force-pushes)?
2. Affects multiple files/functions/data?
3. Irreversible?
4. Could break existing functionality?

**If ANY answer is YES → MUST get user approval**

### 2. Request Approval (MANDATORY)

```
🚨 DANGEROUS OPERATION APPROVAL REQUIRED 🚨

Operation: [Exact command or action]
Reason: [Why this is needed]

What will be affected:
- [ALL files/functions/data modified/deleted]
- [Estimated impact]

Consequences:
- [What will be lost]
- [What will break]
- [What cannot be recovered]

Alternatives considered:
- [Alternative 1]
- [Alternative 2]
- [Why alternatives rejected]

Reversibility: [Can this be undone? How?]

⚠️  I CANNOT proceed without your explicit approval.

Respond: "APPROVED" | "DENIED" | "ALTERNATIVE: [suggestion]"
```

### 3. Wait for User Response

- ✅ "APPROVED" → Proceed to Git Safety Checkpoint
- ❌ "DENIED" → Do NOT proceed, find alternative
- 🔄 Alternative suggested → Implement alternative
- ⏳ No response → MUST NOT proceed, must wait

### 4. Git Safety Checkpoint (MANDATORY)

**Before executing dangerous operation (even after approval):**

```bash
# 1. Check for uncommitted changes
git status

# 2. Main Agent: Verify all sub-agents have committed

# 3. Commit ALL changes
git add .
git commit -m "Checkpoint before dangerous operation: [description]

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. Push to remote (MUST succeed)
git push

# 5. Verify push
git status  # Should show "up to date with origin"

# 6. Report checkpoint complete
```

**Why Critical:**
- Creates restore point if operation fails
- Prevents loss of uncommitted work
- Ensures remote backup exists
- Allows easy rollback: `git reset --hard origin/[branch]`

**If Git Push Fails:**
```
❌ Git Safety Checkpoint FAILED
Cannot proceed - dangerous operation BLOCKED until push succeeds.
```

**NEVER execute dangerous operation without successful git push.**

### 5. Execution with Safeguards

After approval AND successful checkpoint:
1. Create additional backup if possible
2. Document what is being done
3. Provide way to undo if feasible
4. Execute the dangerous operation
5. Report exactly what was done
6. Verify system still works

## Red Flag Commands (ALWAYS Need Approval)

```bash
# File operations
rm -rf
rm *
find . -delete
git clean -fd

# Database operations
DROP DATABASE
DROP TABLE
TRUNCATE TABLE
DELETE FROM  # (no WHERE)

# Git operations
git reset --hard
git push --force
git branch -D

# System operations
chmod -R 777
sudo rm
kill -9

# Package operations
npm uninstall  # (multiple)
rm -rf node_modules
rm package-lock.json

# Docker operations
docker system prune -a
docker rm -f $(docker ps -aq)
```

## Safe Operations (No Approval Needed)

- Creating new files
- Adding code to existing files
- Modifying small code sections (<50 lines)
- Running tests, building project
- Installing dependencies (with initial consent)
- Reading files
- Git: commit, pull, push (to non-protected branches)
- Formatting code
- Adding comments/documentation
- Creating backups

⚠️ **When in doubt: ASK FOR APPROVAL**

## Safer Alternatives

### Archive Instead of Delete

```bash
mkdir archive/
mv old_code/ archive/old_code_$(date +%Y%m%d)
```

### Git-based Cleanup

```bash
git add tests/old_*.test.ts
git commit -m "Remove old tests (can revert if needed)"
```

### Gradual Removal

Remove in phases, verify each phase works

### Feature Flags

Keep both implementations, toggle with flag, remove later

## Special Cases

### User Explicitly Requests Dangerous Operation

Still confirm with brief summary:

```
Confirming dangerous operation:

You've requested: Delete all tests in tests/auth/
This will delete:
- tests/auth/jwt.test.ts
- tests/auth/session.test.ts
- tests/auth/password.test.ts
(3 files, 450 lines)

Cannot be easily undone.

Type "CONFIRM" to proceed, or "CANCEL" to reconsider.
```

### Emergency Situations

Even in emergencies, agent MUST:
1. Briefly explain dangerous operation needed
2. Request quick approval
3. **Complete Git Safety Checkpoint** (commit and push)
4. Only then proceed after approval

**No exceptions for git checkpoint - even in emergencies.**

## Agent Responsibilities

### Main Agent
- Monitor all sub-agents for dangerous operations
- Block any sub-agent attempting dangerous operation without approval
- Report to user if sub-agent tries to bypass
- **Coordinate Git Safety Checkpoint across ALL agents**
- **Verify all sub-agents committed and pushed**
- **Block dangerous operation if git push fails**

### Sub-Agent
- Check every operation against dangerous operations list
- Report to Main Agent before any dangerous operation
- NEVER execute without user approval
- **Commit all work before dangerous operation**
- **Report to Main Agent when changes committed and pushed**
- **Wait for Main Agent coordination**

## Critical Violations

1. Performing dangerous operation without user approval
2. Performing dangerous operation without git checkpoint (commit + push)
3. Executing dangerous operation with uncommitted changes
4. Proceeding when git push fails

**If violation occurs:**
1. Immediately stop all operations
2. Report violation to user
3. Undo operation if possible
4. User must manually review all changes
5. Agent session may be terminated

## Examples

### Example: Deleting Test Files

❌ **WRONG:**
```bash
rm -rf tests/  # FORBIDDEN - immediate violation
```

✅ **CORRECT:**
```
🚨 DANGEROUS OPERATION APPROVAL REQUIRED 🚨

Operation: Delete entire tests/ directory (rm -rf tests/)
Reason: User asked to "remove old tests"

What will be affected:
- tests/ directory containing 47 test files
- Test coverage for auth, API, database modules
- All test fixtures and mocks

Consequences:
- Complete loss of test suite
- CI/CD pipeline will fail
- Test coverage drops to 0%

Alternatives considered:
- Archive tests to tests_archive/
- Selectively remove only outdated tests
- Refactor tests instead of deleting

Reversibility: NOT EASILY REVERSIBLE
- If not committed: PERMANENT DATA LOSS
- If committed: Recoverable from git history

⚠️  I CANNOT proceed without your explicit approval.
```

## Workflow Summary

**Mandatory Workflow:**
1. Detect dangerous operation
2. Request user approval with detailed analysis
3. Wait for explicit "APPROVED"
4. **Complete Git Safety Checkpoint (ALL agents commit and push)**
5. Verify git push succeeded
6. Execute dangerous operation
7. Report completion

**Key Points:**
- Dangerous = Deletion, removal, dropping, truncating, force operations
- ALWAYS get user approval BEFORE executing
- **ALWAYS complete Git Safety Checkpoint BEFORE executing**
- **NEVER execute with uncommitted changes or failed git push**
- Provide detailed impact analysis and alternatives
- When in doubt, ask for approval
- Better to over-communicate than cause data loss

**This rule is absolute. No exceptions.**

## Summary

**Dangerous Operations Checklist:**
1. ✅ Detect if operation is dangerous
2. ✅ Request user approval with full details
3. ✅ Wait for explicit "APPROVED"
4. ✅ Complete git checkpoint (commit + push ALL changes)
5. ✅ Verify git push succeeded
6. ✅ Execute dangerous operation
7. ✅ Report what was done

**Key Principles:**
- User approval MANDATORY
- Git checkpoint MANDATORY (even after approval)
- No uncommitted changes before dangerous operation
- Provide alternatives
- Document consequences
- When in doubt, ask

---

_Version: 1.0 - Last Updated: 2026-02-27_
