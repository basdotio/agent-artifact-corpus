---
name: parallel-worktree-orchestrator
description: Orchestrate parallel Claude Code agents across git worktrees for large implementations
---

# Parallel Worktree Orchestrator

Spawn multiple Claude Code agents in separate git worktrees to parallelize large implementations, continuously monitor their progress, handle input requirements, and merge results.

## When to Use

- "Launch team to implement X"
- "Parallel implementation of Y"
- "Spawn worktrees for Z"
- "Multi-agent implementation"
- "Orchestrate agents to complete"
- "Set up worktree config" (triggers Phase 0 only)
- "Resume sessions" or "Resume interrupted" (triggers Phase 5)
- "Sync session IDs" (capture IDs from running sessions)

## Prerequisites

- `wt` (worktrunk) CLI installed
- `tmux` available at `/usr/bin/tmux`
- Git repository with clean working state

**Quick check:** Run `~/.claude/skills/parallel-worktree-orchestrator/scripts/check-wt-config.sh` to verify prerequisites.

## Process

### Phase 0: Setup (if needed)

Before launching worktrees, verify wt config exists:

```bash
# Check for project config
if [ -f ".config/wt.toml" ]; then
  echo "✓ Project config exists"
  wt config show 2>&1 | head -10
else
  echo "✗ No project config found"
fi
```

**If no config exists**, use AskUserQuestion to gather project info:

```
AskUserQuestion({
  questions: [{
    question: "What type of project is this?",
    header: "Project Type",
    options: [
      { label: "Node.js/TypeScript", description: "npm/yarn/pnpm project with package.json" },
      { label: "Rust/Cargo", description: "Cargo.toml based project" },
      { label: "Python", description: "pyproject.toml or requirements.txt" },
      { label: "Research/Docs", description: "Documentation or research repository" }
    ],
    multiSelect: false
  }, {
    question: "Which hooks do you need?",
    header: "Hooks",
    options: [
      { label: "post-create (Recommended)", description: "Run after worktree creation (deps, setup)" },
      { label: "pre-merge", description: "Validate before merging (tests, lint)" },
      { label: "post-switch", description: "Run when switching worktrees" },
      { label: "post-merge", description: "Run after successful merge" }
    ],
    multiSelect: true
  }]
})
```

**Generate config based on answers:**

```toml
# Node.js example
[post-create]
install = "npm install"

[pre-merge]
lint = "npm run lint"
test = "npm test"

# Rust example
[post-create]
build = "cargo build"

[pre-merge]
check = "cargo clippy && cargo test"

# Research/Docs example
[post-create]
setup = '''
echo "=== Initializing worktree: {{ branch }} ==="
mkdir -p "{{ worktree_path }}/thoughts/ledgers"
'''

[pre-merge]
validate = '''
# Check for UNCONFIRMED items
grep -r "UNCONFIRMED" thoughts/ledgers/*.md 2>/dev/null && echo "Review UNCONFIRMED items"
'''
```

**Create the config using helper script:**

```bash
# Use the helper script based on user's answers
SKILL_DIR=~/.claude/skills/parallel-worktree-orchestrator/scripts

# For Node.js projects
$SKILL_DIR/generate-wt-config.sh nodejs post-create pre-merge

# For Rust projects
$SKILL_DIR/generate-wt-config.sh rust post-create pre-merge

# For Research/Docs projects
$SKILL_DIR/generate-wt-config.sh research post-create pre-merge post-switch post-merge
```

Or manually create:

```bash
mkdir -p .config
cat > .config/wt.toml << 'EOF'
# Generated wt config
# See: https://worktrunk.dev/config/

[post-create]
# Add setup commands here

[pre-merge]
# Add validation commands here
EOF
```

**Template variables available:**
- `{{ branch }}` - Current branch name
- `{{ worktree_path }}` - Path to the worktree
- `{{ repo }}` - Repository root path

### Phase 1: Analysis

When given an implementation goal:

1. **Analyze scope** - Explore codebase to understand what needs to change
2. **Decompose into workstreams** - Break into 3-8 parallel, non-overlapping tasks
3. **Define clear boundaries** - Each workstream should touch different files
4. **Present plan and gather feedback**:

```markdown
| Branch | Task | Files Affected | Effort |
|--------|------|----------------|--------|
| feature/auth | Implement JWT auth | auth/*.rs | 2-3 days |
| feature/api | Add REST endpoints | api/*.rs | 2-3 days |
```

**Use AskUserQuestion for plan approval:**

```
AskUserQuestion({
  questions: [{
    question: "Does this workstream decomposition look correct?",
    header: "Plan Review",
    options: [
      { label: "Approve all (Recommended)", description: "Launch all workstreams as proposed" },
      { label: "Modify workstreams", description: "I want to adjust the task breakdown" },
      { label: "Add more workstreams", description: "There are additional tasks to parallelize" },
      { label: "Reduce scope", description: "Remove some workstreams for now" }
    ],
    multiSelect: false
  }, {
    question: "Any workstreams that should start first?",
    header: "Priority",
    options: [
      { label: "Launch all together (Recommended)", description: "Start all workstreams simultaneously" },
      { label: "Core first", description: "Start foundational workstreams, then dependent ones" },
      { label: "Quick wins first", description: "Start smaller tasks to build momentum" }
    ],
    multiSelect: false
  }]
})
```

**If user selects "Modify workstreams"**, gather specifics:

```
AskUserQuestion({
  questions: [{
    question: "What changes do you want to make?",
    header: "Modifications",
    options: [
      { label: "Split a workstream", description: "Break one task into smaller pieces" },
      { label: "Merge workstreams", description: "Combine related tasks" },
      { label: "Change file boundaries", description: "Adjust which files each workstream touches" },
      { label: "Rename branches", description: "Use different branch naming" }
    ],
    multiSelect: true
  }]
})
```

### Phase 2: Launch Worktrees

**Pre-launch confirmation:**

```
AskUserQuestion({
  questions: [{
    question: "Ready to create worktrees and launch agents?",
    header: "Launch",
    options: [
      { label: "Launch all now (Recommended)", description: "Create all worktrees and start all agents" },
      { label: "Launch in batches", description: "Start a few at a time to manage resources" },
      { label: "Review prompts first", description: "Show me the agent prompts before launching" },
      { label: "Wait", description: "I need to do something first" }
    ],
    multiSelect: false
  }]
})
```

**If "Launch in batches" selected:**

```
AskUserQuestion({
  questions: [{
    question: "How many agents to launch per batch?",
    header: "Batch Size",
    options: [
      { label: "2 agents", description: "Conservative - easier to monitor" },
      { label: "3 agents (Recommended)", description: "Balanced parallelism" },
      { label: "4 agents", description: "Higher parallelism" }
    ],
    multiSelect: false
  }]
})
```

**For each approved workstream:**

```bash
# 1. Create worktree
wt switch --create <branch-name>

# 2. Launch tmux session with Claude Code
/usr/bin/tmux new-session -d -s <session-name> -c "<worktree-path>" \
  "claude --dangerously-skip-permissions '<detailed-task-prompt>'"

# 3. Verify running
/usr/bin/tmux list-sessions
```

### Phase 3: Monitor Loop

Continuously check all sessions until complete:

```bash
# Check session output
/usr/bin/tmux capture-pane -t <session> -p -S -50 | tail -30
```

**Detect and handle states:**

| Pattern | State | Action |
|---------|-------|--------|
| "Shall I proceed?" | WAITING | Send `yes` |
| "Do you want to" | WAITING | Send confirmation |
| "Error:", "Failed:" | ERROR | Investigate, possibly restart |
| Session ended | COMPLETE | Ready to merge |
| Working/thinking | ACTIVE | Wait and check again |

**When sessions are WAITING, ask user:**

```
AskUserQuestion({
  questions: [{
    question: "Sessions are waiting for input. How should I respond?",
    header: "Input Action",
    options: [
      { label: "Send 'yes' to all (Recommended)", description: "Approve all pending confirmations" },
      { label: "Send 'yes' selectively", description: "Choose which sessions to approve" },
      { label: "Check details first", description: "Show me what each session is asking" },
      { label: "Send custom response", description: "I'll provide a specific response" }
    ],
    multiSelect: false
  }]
})
```

**When a session has ERROR:**

```
AskUserQuestion({
  questions: [{
    question: "Session '<session-name>' encountered an error. What should I do?",
    header: "Error Action",
    options: [
      { label: "Show error details", description: "Display the full error output" },
      { label: "Restart session", description: "Kill and relaunch with same task" },
      { label: "Restart with modified task", description: "Relaunch with adjusted instructions" },
      { label: "Skip this workstream", description: "Continue without this session" },
      { label: "Pause all", description: "Stop monitoring until I investigate" }
    ],
    multiSelect: false
  }]
})
```

**Send input when needed:**
```bash
# IMPORTANT: Send text and Enter separately for reliability
/usr/bin/tmux send-keys -t <session> "yes"
sleep 0.3
/usr/bin/tmux send-keys -t <session> Enter
```

**Batch send to multiple sessions:**
```bash
for session in session1 session2 session3; do
  /usr/bin/tmux send-keys -t $session "yes"
  sleep 0.2
  /usr/bin/tmux send-keys -t $session Enter
  sleep 0.3
done
```

**Known Issue:** Using `"yes" Enter` in a single send-keys command may only type "yes" without pressing Enter. Always send Enter as a separate command or verify the input was processed.

**Monitor interval:**
- Initial check: 2-3 minutes after launch
- Subsequent: Every 3-5 minutes
- Input response: Immediate

### Phase 4: Merge & Cleanup

When all sessions complete, gather merge preferences:

```
AskUserQuestion({
  questions: [{
    question: "All sessions complete. Ready to merge?",
    header: "Merge",
    options: [
      { label: "Merge all now (Recommended)", description: "Merge all branches in sequence" },
      { label: "Review changes first", description: "Show me what each branch changed" },
      { label: "Merge selectively", description: "Choose which branches to merge" },
      { label: "Wait", description: "I need to check something first" }
    ],
    multiSelect: false
  }, {
    question: "What to do after merging?",
    header: "Post-Merge",
    options: [
      { label: "Push and cleanup (Recommended)", description: "Push to remote, delete worktrees" },
      { label: "Push only", description: "Push but keep worktrees" },
      { label: "Cleanup only", description: "Delete worktrees but don't push" },
      { label: "Nothing", description: "Just merge, I'll handle the rest" }
    ],
    multiSelect: false
  }]
})
```

**If conflicts occur during merge:**

```
AskUserQuestion({
  questions: [{
    question: "Merge conflict in '<branch>'. How should I handle it?",
    header: "Conflict",
    options: [
      { label: "Show conflicts", description: "Display conflicting files and content" },
      { label: "Abort this merge", description: "Skip this branch, continue with others" },
      { label: "Pause for manual resolution", description: "I'll resolve conflicts myself" },
      { label: "Abort all merges", description: "Stop merging entirely" }
    ],
    multiSelect: false
  }]
})
```

**Execute merge:**

```bash
# 1. Verify each branch has commits
git -C <worktree> log --oneline -3

# 2. Merge each branch
wt merge <branch-name>

# 3. Resolve any conflicts
# 4. Run alignment/verification checks
# 5. Push to remote
git push origin main
```

**Cleanup confirmation:**

```
AskUserQuestion({
  questions: [{
    question: "Delete worktrees and tmux sessions?",
    header: "Cleanup",
    options: [
      { label: "Full cleanup (Recommended)", description: "Delete worktrees and kill tmux sessions" },
      { label: "Worktrees only", description: "Delete worktrees, keep tmux sessions" },
      { label: "Sessions only", description: "Kill tmux sessions, keep worktrees" },
      { label: "Keep all", description: "Don't clean up anything" }
    ],
    multiSelect: false
  }]
})
```

### Phase 5: Resume Interrupted Sessions

When sessions are interrupted (rate limit, user termination, system crash), use this phase to resume.

**Check for interrupted sessions:**

```bash
$SKILL_DIR/list-saved-sessions.sh
```

**Use AskUserQuestion to confirm resumption:**

```
AskUserQuestion({
  questions: [{
    question: "Found interrupted sessions. How should I handle them?",
    header: "Resume",
    options: [
      { label: "Resume all (Recommended)", description: "Resume all interrupted sessions with 'continue' message" },
      { label: "Resume selectively", description: "Choose which sessions to resume" },
      { label: "Show details first", description: "Display session details before resuming" },
      { label: "Skip resumption", description: "Don't resume - start fresh if needed" }
    ],
    multiSelect: false
  }]
})
```

**Resume all interrupted sessions:**

```bash
# Dry run first to see what will be resumed
$SKILL_DIR/resume-all.sh --dry-run

# Resume all with default "continue" message
$SKILL_DIR/resume-all.sh

# Resume with custom message
$SKILL_DIR/resume-all.sh --continue-message "Please continue from where you left off"
```

**Resume a specific session:**

```bash
$SKILL_DIR/resume-session.sh <session-name>

# With custom continue message
$SKILL_DIR/resume-session.sh <session-name> --continue-message "Continue implementing the auth module"

# Without sending a continue message (just attach)
$SKILL_DIR/resume-session.sh <session-name> --no-continue
```

**Sync session IDs from running sessions:**

If you have running sessions that weren't tracked (launched before persistence was added), sync them:

```bash
# Sync all running sessions
$SKILL_DIR/sync-session-ids.sh

# Sync a specific session
$SKILL_DIR/sync-session-ids.sh <session-name>
```

**Session state file location:**

```
~/.claude/skills/parallel-worktree-orchestrator/state/sessions.json
```

**Session statuses:**

| Status | Description |
|--------|-------------|
| `running` | Session is active in tmux |
| `interrupted` | Session died unexpectedly (rate limit, crash, user kill) |
| `completed` | Session finished successfully |
| `error` | Session encountered an error |

## Task Prompt Template

Each agent prompt should be self-contained:

```
<clear-task-description>

Context:
- Repository: <what-this-repo-is>
- Related files: <key-files-to-read-first>
- Patterns to follow: <conventions-from-CLAUDE.md>

Deliverables:
1. <specific-file-or-change>
2. <specific-file-or-change>
3. <specific-file-or-change>

When done, commit changes with descriptive message.
```

## Session Naming

Keep session names short (tmux limit):

| Branch | Session Name |
|--------|--------------|
| `research/confidence-scoring` | `confidence-scoring` |
| `specs/detector-impl` | `detector-impl` |
| `fix/auth-bug` | `fix-auth-bug` |

## Status Report Format

Provide clear status updates:

```markdown
## Parallel Implementation Status

| Session | Branch | Progress | Context | Action |
|---------|--------|----------|---------|--------|
| jwt | auth/jwt | 🔄 Working | 45% | - |
| sessions | auth/sess | ⏸️ WAITING | 60% | Sent "yes" |
| rbac | auth/rbac | ✅ Complete | - | Ready to merge |
| middleware | auth/mid | ❌ Error | 30% | Restarting |
```

## Input Verification

After sending input, always verify it was processed:

```bash
# Send input
/usr/bin/tmux send-keys -t <session> "yes"
sleep 0.2
/usr/bin/tmux send-keys -t <session> Enter

# Wait and verify processing started
sleep 2
/usr/bin/tmux capture-pane -t <session> -p -S -10 | tail -8
```

**Signs input was processed:**
- Status changed from "Shall I proceed?" to "Sprouting/Working/Cogitating..."
- New tool calls appearing (Bash, git commands)
- Progress indicator changed

**Signs input is stuck:**
- "yes" still visible in input line with no activity
- Same prompt still showing after several seconds

**Fix for stuck input:**
```bash
# Resend Enter explicitly
/usr/bin/tmux send-keys -t <session> Enter
```

## Error Recovery

If a session crashes or gets stuck:

```bash
# Check if session exists
/usr/bin/tmux has-session -t <name> 2>/dev/null && echo "alive" || echo "dead"

# If dead, check worktree state
git -C <worktree-path> status
git -C <worktree-path> log --oneline -3

# Relaunch if needed
/usr/bin/tmux new-session -d -s <name> -c "<path>" "claude --dangerously-skip-permissions '<remaining-task>'"
```

## Merge Checklist

Before merging:
- [ ] All sessions completed successfully
- [ ] Each branch has meaningful commits
- [ ] Files don't overlap (no merge conflicts expected)
- [ ] Tests pass (if applicable)

After merging:
- [ ] Run alignment/consistency checks
- [ ] Verify cross-references still valid
- [ ] Push to remote

## Example: Full Workflow

**User:** "Launch team to implement authentication with JWT, sessions, and RBAC"

**Phase 1 - Analysis Output:**
```markdown
| Branch | Task | Effort |
|--------|------|--------|
| auth/jwt-tokens | JWT generation/validation | 2-3h |
| auth/sessions | Session management | 2-3h |
| auth/rbac | Role-based access control | 3-4h |
| auth/middleware | Auth middleware integration | 2-3h |
```

**Phase 2 - Launch:**
```bash
wt switch --create auth/jwt-tokens
/usr/bin/tmux new-session -d -s jwt -c "..." "claude --dangerously-skip-permissions '...'"
# ... repeat for all 4
```

**Phase 3 - Monitor:**
```markdown
| Session | Status | Action |
|---------|--------|--------|
| jwt | ⏸️ WAITING | Sent "yes" |
| sessions | 🔄 Working | - |
| rbac | 🔄 Working | - |
| middleware | ✅ Complete | Ready |
```

**Phase 4 - Merge:**
```bash
wt merge auth/jwt-tokens
wt merge auth/sessions
wt merge auth/rbac
wt merge auth/middleware
git push origin main
```

## Helper: Reliable Input Sender

Use this pattern to send confirmations reliably:

```bash
# Function to send input and verify
send_confirm() {
  local session=$1
  local response=${2:-"yes"}

  /usr/bin/tmux send-keys -t "$session" "$response"
  sleep 0.2
  /usr/bin/tmux send-keys -t "$session" Enter
  sleep 1

  # Check if processing started
  if /usr/bin/tmux capture-pane -t "$session" -p -S -5 | grep -qE "(Sprouting|Working|Cogitat|Bash\(|git )"; then
    echo "$session: ✓ Processing"
  else
    echo "$session: ⚠ May need retry"
    /usr/bin/tmux send-keys -t "$session" Enter  # Retry Enter
  fi
}

# Usage
send_confirm "confidence-scoring" "yes"
send_confirm "websocket-security" "yes"
```

## Important Notes

- **Non-overlapping files**: Ensure workstreams don't edit the same files
- **Self-contained prompts**: Each agent has no context from main session
- **Frequent monitoring**: Check every few minutes to unblock waiting agents
- **Clean merges**: Parallel work should merge without conflicts if decomposed well

## Dependency Management

When sessions depend on each other (e.g., `sqlite-backend` depends on `storage-traits`), use tiered launching.

### Manifest File Format

Create a manifest JSON to define sessions and their dependencies:

```json
{
  "project": "my-project",
  "base_path": "/path/to/repo",
  "sessions": {
    "core-traits": {
      "branch": "impl/core-traits",
      "depends_on": [],
      "prompt": "Implement core traits..."
    },
    "sqlite-impl": {
      "branch": "impl/sqlite",
      "depends_on": ["core-traits"],
      "prompt": "Implement SQLite backend..."
    },
    "postgres-impl": {
      "branch": "impl/postgres",
      "depends_on": ["core-traits"],
      "prompt": "Implement PostgreSQL backend..."
    },
    "integration": {
      "branch": "impl/integration",
      "depends_on": ["sqlite-impl", "postgres-impl"],
      "prompt": "Add integration tests..."
    }
  }
}
```

### Launch with Dependencies

```bash
SKILL_DIR=~/.claude/skills/parallel-worktree-orchestrator/scripts

# Launch all sessions in dependency order (tier by tier)
$SKILL_DIR/launch-with-deps.sh manifest.json

# Launch only a specific tier
$SKILL_DIR/launch-with-deps.sh manifest.json --tier 0
$SKILL_DIR/launch-with-deps.sh manifest.json --tier 1
```

The script automatically:
1. Computes dependency tiers (Tier 0 = no deps, Tier 1 = depends on Tier 0, etc.)
2. Launches Tier 0 sessions first
3. Prompts before launching dependent tiers

### Session Manifest Commands

```bash
# Initialize manifest tracking
$SKILL_DIR/session-manifest.sh init my-project

# Add session with dependencies
$SKILL_DIR/session-manifest.sh add sqlite-impl core-traits
$SKILL_DIR/session-manifest.sh add integration sqlite-impl postgres-impl

# Update session status
$SKILL_DIR/session-manifest.sh status sqlite-impl running /path/to/worktree impl/sqlite
$SKILL_DIR/session-manifest.sh status sqlite-impl completed

# Check if dependencies are ready
$SKILL_DIR/session-manifest.sh ready integration

# List all sessions
$SKILL_DIR/session-manifest.sh list
```

## Inter-Session Communication

Sessions can check on their siblings via tmux. Include this in your prompts:

### Check Sibling Commands (For Agents)

```bash
SKILL_DIR=~/.claude/skills/parallel-worktree-orchestrator/scripts

# Check all sibling sessions
$SKILL_DIR/check-sibling.sh --all

# Check specific sibling status
$SKILL_DIR/check-sibling.sh storage-traits

# View sibling's recent output (last 30 lines)
$SKILL_DIR/check-sibling.sh --output storage-traits 30

# Wait for a dependency to complete (with timeout)
$SKILL_DIR/check-sibling.sh --wait storage-traits 300

# Check if my dependencies are ready
MY_SESSION=sqlite-impl $SKILL_DIR/check-sibling.sh --deps
```

### Enhanced Prompt Template with Sibling Awareness

When launching dependent sessions, include sibling awareness:

```
<task-description>

## Sibling Sessions
You are part of a parallel implementation team. Check on siblings when needed:

### Check All Siblings
~/.claude/skills/parallel-worktree-orchestrator/scripts/check-sibling.sh --all

### Check Specific Sibling
~/.claude/skills/parallel-worktree-orchestrator/scripts/check-sibling.sh <session-name>

### View Sibling Output
~/.claude/skills/parallel-worktree-orchestrator/scripts/check-sibling.sh --output <session-name>

### Your Dependencies
You depend on: storage-traits
Check its status before using types it defines.
```

### Status Indicators

| Symbol | Status | Meaning |
|--------|--------|---------|
| 🔄 | WORKING | Session is actively processing |
| ⏸️ | WAITING | Session needs input |
| ✅ | COMPLETE | Session finished successfully |
| ❌ | ERROR | Session encountered an error |
| ❓ | UNKNOWN | Cannot determine state |

## Helper Scripts

The skill includes helper scripts in `~/.claude/skills/parallel-worktree-orchestrator/scripts/`:

### Core Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `check-wt-config.sh` | Verify prerequisites and config | `./check-wt-config.sh [project-dir]` |
| `generate-wt-config.sh` | Generate wt.toml from project type | `./generate-wt-config.sh <type> [hooks...]` |
| `launch-agent.sh` | Create worktree and launch agent | `./launch-agent.sh <branch> <session> <prompt>` |
| `launch-with-deps.sh` | Launch sessions in dependency order | `./launch-with-deps.sh manifest.json` |
| `monitor-sessions.sh` | Check status of all sessions | `./monitor-sessions.sh [filter]` |
| `send-input.sh` | Reliably send input to sessions | `./send-input.sh <session> <input>` |
| `session-details.sh` | View detailed session output | `./session-details.sh <session> [lines]` |
| `cleanup.sh` | Remove sessions and worktrees | `./cleanup.sh [--sessions-only] [--worktrees-only]` |

### Dependency & Communication Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `session-manifest.sh` | Manage shared session manifest | `./session-manifest.sh {init\|add\|status\|list}` |
| `check-sibling.sh` | Check sibling session status | `./check-sibling.sh <session> \| --all \| --deps` |

### Session Persistence Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `save-session.sh` | Save session state for resumption | `./save-session.sh <session> <branch> <path> <project> "<prompt>"` |
| `list-saved-sessions.sh` | List all saved sessions with status | `./list-saved-sessions.sh [--json] [--filter status]` |
| `update-session-status.sh` | Update session status | `./update-session-status.sh <session> <status> [claude-id]` |
| `get-claude-session-id.sh` | Extract Claude session ID from tmux | `./get-claude-session-id.sh <session>` |
| `resume-session.sh` | Resume an interrupted session | `./resume-session.sh <session> [--continue-message "msg"]` |
| `resume-all.sh` | Resume all interrupted sessions | `./resume-all.sh [--dry-run] [--filter pattern]` |
| `sync-session-ids.sh` | Sync IDs from running sessions | `./sync-session-ids.sh [session]` |

### Quick Reference

```bash
SKILL_DIR=~/.claude/skills/parallel-worktree-orchestrator/scripts

# Phase 0: Check prerequisites
$SKILL_DIR/check-wt-config.sh

# Phase 0: Generate config (if needed)
$SKILL_DIR/generate-wt-config.sh nodejs post-create pre-merge
$SKILL_DIR/generate-wt-config.sh rust post-create pre-merge
$SKILL_DIR/generate-wt-config.sh research post-create pre-merge post-switch

# Phase 2: Launch agents
$SKILL_DIR/launch-agent.sh feature/auth auth "Implement JWT authentication"

# Phase 3: Monitor
$SKILL_DIR/monitor-sessions.sh

# Phase 3: Send input to waiting sessions
$SKILL_DIR/send-input.sh --waiting yes
$SKILL_DIR/send-input.sh auth yes

# Phase 3: View session details
$SKILL_DIR/session-details.sh auth 50

# Phase 4: Cleanup
$SKILL_DIR/cleanup.sh --dry-run
$SKILL_DIR/cleanup.sh

# Phase 5: Resume (if sessions were interrupted)
$SKILL_DIR/list-saved-sessions.sh
$SKILL_DIR/resume-all.sh --dry-run
$SKILL_DIR/resume-all.sh
$SKILL_DIR/resume-session.sh my-session

# Sync session IDs from running sessions (for sessions launched before persistence)
$SKILL_DIR/sync-session-ids.sh
```

### generate-wt-config.sh Options

| Project Type | Description |
|--------------|-------------|
| `nodejs` | npm/yarn/pnpm with package.json |
| `rust` | Cargo.toml based project |
| `python` | pyproject.toml or requirements.txt |
| `research` | Documentation/research repository |

| Hook | When |
|------|------|
| `post-create` | After worktree creation (install deps) |
| `pre-merge` | Before merging (run tests, lint) |
| `post-switch` | When switching worktrees |
| `post-merge` | After successful merge |

### send-input.sh Options

```bash
# Send to specific session
send-input.sh my-session yes

# Send to ALL sessions
send-input.sh --all yes

# Send only to WAITING sessions (auto-detects)
send-input.sh --waiting yes
```

### cleanup.sh Options

```bash
# Preview what would be deleted
cleanup.sh --dry-run

# Delete everything (sessions + worktrees)
cleanup.sh

# Only kill tmux sessions
cleanup.sh --sessions-only

# Only delete worktrees
cleanup.sh --worktrees-only

# Filter by name pattern
cleanup.sh auth
```

### list-saved-sessions.sh Options

```bash
# List all saved sessions
list-saved-sessions.sh

# Output as JSON
list-saved-sessions.sh --json

# Filter by status
list-saved-sessions.sh --filter interrupted
list-saved-sessions.sh --filter running
list-saved-sessions.sh --filter completed
```

### resume-session.sh Options

```bash
# Resume with default "continue" message
resume-session.sh my-session

# Resume with custom message
resume-session.sh my-session --continue-message "Continue from where you left off"

# Resume without sending any message
resume-session.sh my-session --no-continue
```

### resume-all.sh Options

```bash
# Preview what will be resumed
resume-all.sh --dry-run

# Resume all interrupted sessions
resume-all.sh

# Resume with custom continue message
resume-all.sh --continue-message "Please continue your work"

# Resume only sessions matching pattern
resume-all.sh --filter auth

# Adjust delay between launches (default 3s)
resume-all.sh --delay 5
```

### sync-session-ids.sh Usage

Use this to capture Claude session IDs from sessions that were launched before
the persistence feature was added:

```bash
# Sync all running sessions
sync-session-ids.sh

# Sync a specific session
sync-session-ids.sh my-session
```

This is useful when you've hit a rate limit and want to resume later - run
`sync-session-ids.sh` before the sessions die to capture their IDs.
