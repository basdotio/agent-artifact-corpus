---
name: git-workflow-patterns
description: Analyzes git history to identify commit patterns, branching habits, workflow inefficiencies, and collaboration opportunities. Use when users mention git workflows, commits, branches, rebasing, merge conflicts, PR strategy, force push, git aliases, or express frustration with git operations.
allowed-tools:
  - Read
  - Bash
  - Grep
---

# Git Workflow Patterns Analysis

This skill analyzes your git history to identify patterns in your workflow and suggest improvements. It learns from your past git behavior to provide personalized recommendations for efficiency, safety, and consistency.

## How to Use This Skill

When activated, analyze the user's git history to identify patterns and provide actionable insights. The analysis should be:
- **Personalized**: Based on actual patterns in their git history
- **Actionable**: Include specific commands, aliases, or workflow changes
- **Evidence-based**: Reference actual data from their history
- **Privacy-conscious**: Analyze locally, don't store raw commit messages or sensitive data

## Analysis Process

### 1. Gather Git History Data

Run these commands to collect pattern data:

```bash
# Get comprehensive commit history
git log --all --pretty=format:"%h|%an|%ae|%ai|%s" --numstat --no-merges

# Get branch information
git for-each-ref --format='%(refname:short)|%(authorname)|%(authordate:iso8601)|%(upstream:short)' refs/heads/

# Get reflog for error recovery patterns
git reflog --pretty=format:"%h|%gd|%gs" -n 500

# Get stash list
git stash list

# Get merge/rebase patterns
git log --all --merges --pretty=format:"%h|%ai|%s"

# Get remote branch information
git branch -r
```

### 2. Identify Key Patterns

Analyze the data for:

#### Commit Patterns
- **Message consistency**: Do they follow conventional commits? Consistent format?
- **Commit size**: Average lines changed per commit (small/focused vs. large batches)
- **Commit frequency**: Time between commits (batching behavior)
- **WIP/fixup commits**: Frequency of temporary commits that should be squashed
- **Test commits**: Separate test commits vs. code+test together

#### Branch Patterns
- **Naming conventions**: Identify different formats used (feature/*, feat/JIRA-*, user/*)
- **Branch lifespan**: Average time from creation to merge
- **Abandoned branches**: Branches created but never merged
- **Branch size**: Average commits per branch
- **Long-lived branches**: Branches with 20+ commits (potential for splitting)

#### Collaboration Patterns
- **Solo vs. co-authored**: Frequency of pair programming
- **Merge strategy**: Merge commits vs. rebase preference
- **Force push frequency**: How often and to which branches
- **PR patterns**: Can infer from branch merge frequency

#### Error Recovery Patterns
- **Reflog usage**: Frequent reflog = frequent mistakes/uncertainty
- **Reset/revert**: Hard resets vs. reverts
- **Cherry-pick**: Frequency and context
- **Stash accumulation**: Unretrieved stashes indicate workflow issues

#### Workflow Efficiency
- **Repeated sequences**: Commands run together frequently (alias opportunities)
- **Manual cleanups**: Patterns suggesting missing automation
- **Conflict patterns**: Files that frequently conflict
- **Context switching**: Branch checkout frequency

### 3. Generate Report

Structure the report similarly to the shell history analysis:

```markdown
## Git Workflow Analysis Summary
[2-3 sentence overview of their git workflow patterns]

## Commit Patterns
- Total commits analyzed: X
- Average commit size: Y lines
- Commit message format: [detected pattern or inconsistency]
- Most active hours: [time patterns]

## Top Workflow Patterns
1. [Pattern 1]: Frequency and context
2. [Pattern 2]: Frequency and context
...

## Improvement Opportunities

### High Impact
**[Issue 1]**: [Description with evidence]
- **Current state**: [What they do now]
- **Impact**: [Why it's inefficient/risky]
- **Recommendation**: [Specific fix]
- **Implementation**:
  ```bash
  [Copy-pasteable commands/aliases]
  ```

### Medium Impact
[Similar structure]

### Quick Wins
1. [One-liner improvement 1]
2. [One-liner improvement 2]

## Suggested Git Aliases & Config

```bash
# Add to ~/.gitconfig

[alias]
  # [Description of what this solves]
  alias-name = "command based on their patterns"

  # [Another pattern-based alias]
  another-alias = "..."

[merge]
  # [Config to prevent common conflicts they experience]
  conflictstyle = diff3

[Other recommended configs based on patterns]
```

## Workflow Recommendations

### Branch Strategy
[Recommendations based on their branching patterns]

### Commit Strategy
[Recommendations based on commit patterns]

### Safety Improvements
[Recommendations for preventing errors they've made]
```

## Common Scenarios & Examples

### Scenario 1: Rebase Anxiety
**When to activate**: User mentions rebasing, or git history shows reflog activity after rebases

**What to analyze**:
- Frequency of `git reflog` usage after rebase operations
- Reset/revert patterns following rebases
- Success rate of interactive rebases

**What to suggest**:
- Backup branch workflow before rebasing
- Git aliases for safe rebasing
- Alternative strategies if rebasing causes consistent issues

### Scenario 2: Large PRs / Long-Lived Branches
**When to activate**: User is working on a branch with 20+ commits

**What to analyze**:
- Historical PR sizes and review times
- Correlation between PR size and merge time
- Natural logical split points in commit history

**What to suggest**:
- Breaking into smaller PRs
- Stacked PR workflow
- Commit organization strategies

### Scenario 3: Inconsistent Commit Messages
**When to activate**: User commits code, or asks about git best practices

**What to analyze**:
- Commit message formats used
- Consistency over time
- Team patterns (if multiple authors)

**What to suggest**:
- Conventional commits format
- Commit message templates
- Git hooks for enforcement

### Scenario 4: Merge Conflict Patterns
**When to activate**: User mentions merge conflicts or is resolving conflicts

**What to analyze**:
- Which files conflict most frequently
- Common conflict types (dependency files, migrations, etc.)
- Their typical resolution strategy

**What to suggest**:
- Merge strategies for specific file types
- Git configuration to auto-resolve certain conflicts
- Workflow changes to reduce conflict frequency

### Scenario 5: Stash Hoarding
**When to activate**: User says "I had some changes but lost them" or has many stashes

**What to analyze**:
- Number of stashes
- How often stashes are applied vs. abandoned
- Time stashes remain unapplied

**What to suggest**:
- Using WIP branches instead of stashes
- Stash cleanup workflow
- Better branch management

### Scenario 6: Force Push Safety
**When to activate**: User is about to force push or mentions force pushing

**What to analyze**:
- Frequency of force pushes
- Branches force-pushed to (solo vs. shared)
- Historical issues caused by force pushes

**What to suggest**:
- `--force-with-lease` instead of `--force`
- Git aliases with safety checks
- Team communication protocols

## Guidelines

### Be Specific and Evidence-Based
- Always reference actual data: "You've created 23 branches in the last month"
- Show frequency: "This happens in 73% of your commits"
- Compare to best practices with context, not judgment

### Prioritize by Impact
- Focus on patterns that waste the most time
- Address safety issues (force pushes to shared branches) with urgency
- Quick wins first, then deeper workflow changes

### Provide Working Solutions
- All suggestions should include copy-pasteable commands
- Test that aliases and configs are syntactically correct
- Include both short-term fixes and long-term improvements

### Respect Privacy
- Never include actual commit messages in analysis (just patterns)
- Don't reference specific code changes
- Focus on workflow metadata, not content
- Analyze locally, don't send git history to external services

### Encourage and Highlight Strengths
- Note good patterns: "Your commit sizes are consistently small and focused"
- Frame suggestions as optimization, not criticism
- Acknowledge learning curve for git complexity

## Technical Notes

### Performance Considerations
- Limit history analysis to last 500-1000 commits for initial analysis
- Cache pattern data to avoid re-analyzing on every activation
- Use `--no-merges` and `--no-walk` flags appropriately to reduce data

### Error Handling
- Check if in a git repository before running commands
- Handle repositories with no commits gracefully
- Account for repositories with unconventional setups (multiple remotes, submodules)

### Integration with Shell History Analysis
When both skills are available, cross-reference:
- Shell history shows git commands run frequently
- Git patterns show the results of those commands
- Combined insights reveal automation opportunities

Example:
- Shell: `git add . && git commit -m "..." && git push` (typed 200x)
- Git: Commits average 3 files, 50 lines, always pushed immediately
- Combined insight: Create single alias for the entire workflow
