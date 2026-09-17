---
name: context-read
description: Read and display project context from CLAUDE.md and all referenced [CONTEXT] commits for session initialization or review
---

# Read Project Context

This skill guides you through reading and understanding all project context stored in [CONTEXT] commits.

## When to Use

Use this skill when:
- Starting a new Claude session with a project
- User requests to "show context" or "review project docs"
- Need to refresh understanding of project requirements
- Verifying context setup is working correctly
- Onboarding to an unfamiliar project

## Context Reading Workflow

### 1. Read CLAUDE.md

Start by reading the context index:

```bash
cat CLAUDE.md
```

This shows you:
- List of context commit references
- Session initialization instructions
- Any project-specific guidance

### 2. Extract Context References

Parse CLAUDE.md to identify:
- Commit hashes that need to be read
- Branch names (like context-progress)
- Number and description of each context entry

Example CLAUDE.md format:
```
READ THESE COMMIT MESSAGES FOR CONTEXT:
 1. [abc1234] Project requirements
 2. [def5678] TDD workflow
 3. [context-progress] Current progress
```

### 3. Read Each Context Commit

For each referenced commit, retrieve the full message:

```bash
# For commit hash references
git log [commit-hash] -1 --format=%B

# For branch references (like context-progress)
git log [branch-name] -1 --format=%B

# Example
git log abc1234 -1 --format=%B
git log context-progress -1 --format=%B
```

### 4. Organize and Summarize

After reading all context, provide a summary organized by type:

- **Requirements**: What the project needs to accomplish
- **Technical Specs**: Technologies, platforms, versions
- **Workflows**: Development processes, TDD, review practices
- **Architecture**: Design decisions, patterns, trade-offs
- **Progress**: Current status, completed work, next tasks

### 5. Acknowledge Understanding

Confirm you've read and understood the context:

"I've read all context commits and understand:
- Project goals and requirements
- Development workflow and TDD practices
- Current progress and next tasks
- [Any other key context areas]

Ready to assist with specific tasks."

## Complete Read Example

Here's a complete context reading flow:

```bash
# 1. Read the index
cat CLAUDE.md

# Output shows:
# READ THESE COMMIT MESSAGES FOR CONTEXT:
#  1. [e7b0129] Project requirements
#  2. [ae291fc] Context pattern explanation
#  3. [7cc3e39] TDD workflow
#  4. [c8da0e3] Progress tracking workflow
#  5. [context-progress] Current project progress

# 2. Read each context commit
git log e7b0129 -1 --format=%B
git log ae291fc -1 --format=%B
git log 7cc3e39 -1 --format=%B
git log c8da0e3 -1 --format=%B
git log context-progress -1 --format=%B

# 3. Summarize understanding
# (Provide organized summary to user)
```

## Batch Reading Command

To read all context at once, use this helper:

```bash
# For a CLAUDE.md with known structure
for hash in e7b0129 ae291fc 7cc3e39 c8da0e3; do
  echo "=== Context: $(git log $hash -1 --format=%s) ==="
  git log $hash -1 --format=%B
  echo ""
done

# Read progress
echo "=== Current Progress ==="
git log context-progress -1 --format=%B
```

## Automated Context Loading

Claude Code automatically reads CLAUDE.md on session start. This skill is useful for:
- Manual verification
- Re-reading during a session
- Understanding unfamiliar projects
- Debugging context setup

## Context Types and What to Extract

### From Requirements Context

Extract:
- Project goals and objectives
- Target platforms and environments
- Key features and functionality
- Technical constraints
- Success criteria

### From Workflow Context

Extract:
- Development process (TDD, reviews, etc.)
- Testing requirements
- Code quality standards
- Commit and PR conventions
- Timeline expectations

### From Architecture Context

Extract:
- Technology stack
- Design patterns in use
- Key architectural decisions
- Trade-offs and rationale
- Performance requirements

### From Progress Context

Extract:
- Completed features/tasks
- Current work in progress
- Blocking issues
- Next planned tasks
- Status metrics (tests, coverage, etc.)

## Verifying Context Integrity

Check that context setup is valid:

```bash
# 1. Verify CLAUDE.md exists
test -f CLAUDE.md && echo "✓ CLAUDE.md exists" || echo "✗ CLAUDE.md missing"

# 2. Verify referenced commits exist
git log e7b0129 -1 --oneline > /dev/null 2>&1 && echo "✓ Commit exists" || echo "✗ Commit not found"

# 3. Verify context-progress branch exists
git rev-parse --verify context-progress > /dev/null 2>&1 && echo "✓ context-progress branch exists" || echo "✗ Branch missing"

# 4. Check commit messages have [CONTEXT] prefix
git log abc1234 -1 --format=%s | grep -q "^\[CONTEXT\]" && echo "✓ Has [CONTEXT] prefix" || echo "✗ Missing [CONTEXT]"
```

## Presenting Context to User

When reading context for the user, structure the output:

```
📋 Project Context Summary

## Requirements
[Summary of project goals, features, technical specs]

## Development Workflow
[Summary of TDD, code standards, review process]

## Architecture
[Summary of design decisions, patterns, tech stack]

## Current Progress
[Summary of completed work, current tasks, next steps]

## Key Takeaways
- [Important point 1]
- [Important point 2]
- [Important point 3]

I'm ready to help with specific tasks!
```

## Common Context Reading Patterns

### Session Start Pattern

```bash
# Quick context refresh at session start
cat CLAUDE.md
git log context-progress -1 --format=%B

# Focus on progress to see where to pick up
```

### Deep Dive Pattern

```bash
# Read all context for complete understanding
cat CLAUDE.md

# Read each commit in detail
for ref in [list of all refs]; do
  git log $ref -1 --format=%B
done

# Summarize and ask clarifying questions
```

### Verification Pattern

```bash
# Check context setup is correct
cat CLAUDE.md
git log context-progress -1 --oneline
git log [each-hash] -1 --oneline

# Verify all references are valid
```

## Troubleshooting

**CLAUDE.md not found:**
```bash
# Project may not have context workflow initialized
# Recommend using context-init skill
```

**Commit hash not found:**
```bash
# Hash may be incorrect or from different repository
git log --oneline | grep CONTEXT  # Find actual context commits
```

**context-progress branch missing:**
```bash
# Check if it exists
git branch -a | grep context-progress

# May need to initialize it
# Use context-init skill
```

**Empty context commit:**
```bash
# Verify it's a [CONTEXT] commit
git log [hash] -1 --format=%s

# Check the full message
git log [hash] -1 --format=%B
```

## Quick Reference Commands

```bash
# Read index
cat CLAUDE.md

# Read specific context commit
git log [hash] -1 --format=%B

# Read progress
git log context-progress -1 --format=%B

# List all [CONTEXT] commits
git log --oneline --grep="^\[CONTEXT\]"

# Show commit subject only
git log [hash] -1 --format=%s

# Show commit body only
git log [hash] -1 --format=%b
```

## Integration with Other Skills

- **After context-init**: Read context to verify setup
- **After context-add**: Read new context commit to confirm
- **Before context-progress**: Read current progress before updating
- **Session start**: Always read to understand current state

## Summary

The context-read skill helps you:
- Efficiently load all project context
- Verify context setup is working
- Summarize and understand requirements, workflows, and progress
- Get up to speed on unfamiliar projects
- Provide clear acknowledgment of understanding to the user
