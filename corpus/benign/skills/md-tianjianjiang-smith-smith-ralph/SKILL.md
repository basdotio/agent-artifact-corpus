---
name: smith-ralph
description: Ralph Loop integration patterns for iterative AI development. Use when starting Ralph loops, managing iterations, or recovering from context resets. Covers TDD, debugging, context management, and memory persistence.
---

# Ralph Loop Integration

<metadata>

- **Load if**: Starting `/ralph-loop`, managing iterations, recovering from context reset
- **Prerequisites**: @smith-ctx/SKILL.md, `@smith-git/SKILL.md`, `@smith-serena/SKILL.md`

</metadata>

## CRITICAL: Ralph Fundamentals (Primacy Zone)

<required>

**Ralph = iterative prompt loop**: Same prompt fed repeatedly, Claude sees previous work in files.

**Essential patterns:**
1. Clear completion criteria with `<promise>` tag
2. `--max-iterations` as safety limit (always set)
3. Atomic commits mark iteration boundaries
4. Serena memory persists state across context resets

</required>

## Skills Integration

### TDD Workflow (smith-tests)

**Pattern**: test → implement → run pytest → iterate until `<promise>TESTS PASS</promise>`.

Each test file = iteration boundary. Commit after green.

### Debugging Workflow (smith-validation)

**Pattern**: hypothesis → test → eliminate → iterate until `<promise>ROOT CAUSE FOUND</promise>`.

- Strong Inference: Each hypothesis test = one iteration
- 5 Whys: Each "Why?" deepening = one iteration
- Delta Debugging: Split → test → recurse

### Task Decomposition (smith-dev)

**Pattern**: Phase milestones = iteration boundaries. Quality gates between.

```text
Phase 1: [milestone] + tests
Phase 2: [milestone] + tests
Output <promise>COMPLETE</promise> after all phases.
```

### Exploration Workflow (smith-guidance)

**Ralph = structured exploration**: Read files → Form hypothesis → Design test → Execute → Loop.

## Context Management

<required>

**Ralph burns context rapidly.** ~1-3.5k tokens per iteration.

**Reactive: Auto-exit at critical context (hook-managed):**
- At 40-50%: "Summarize from here" -- consolidate verbose output.
- At 50%: Advisory. Save iteration state to Serena immediately.
- At 60%: Loop auto-exits (max_iterations set to current).
  Resume state saved. After /clear, loop auto-restarts via Skill tool.

**Proactive: Phase boundaries (ALWAYS clear, even at low context):**
- After completing each phase's tasks (all [x] for current phase):
  1. Output promise to exit Ralph
  2. Save state: write_memory("ralph_<task>_phase_N")
  3. Tell user: "Phase N complete. Run /clear for Phase N+1."
  4. After /clear: loop auto-restarts for next phase
- Rationale: Fresh context per phase prevents degradation even before threshold.

**After /clear (both cases):**
- Agent auto-invokes /ralph-loop via Skill tool (no user intervention)
- Serena memory restored for iteration continuity

**Essential retention:**
- Iteration number
- Hypotheses tested/remaining
- Test results summary
- File:line references

</required>

## Phase Boundary Protocol

<required>

**At EVERY phase boundary (regardless of context level):**
1. Mark completed tasks [x] in plan file
2. Commit current work
3. Save phase state: `write_memory("ralph_<task>_phase_N")`
4. Output the configured completion promise (default: `<promise>PHASE_COMPLETE</promise>`). Ensure this matches the Ralph loop's `--completion-promise` value.
5. AFTER all tool calls, output:

**Reload with:**
- Plan: `<plan_path>`
- Memory: `ralph_<task>_phase_N` (read via read_memory() after /clear)
- Ralph: auto-restarts for next phase
- Resume: Phase N+1 - <next phase description>

6. Tell user to run /clear

**Phase = group of tasks under the same ## heading in the plan.**
If plan has no ## headings, each `- [ ]` task = one phase.

</required>

## Commit Strategy

<required>

**Atomic commits mark iteration boundaries.**

1. Complete iteration (test passes or hypothesis proven)
2. Commit with iteration number: `fix(feature): iteration 3 - resolved null check`
3. If regression, use `git bisect` to find breaking iteration

</required>

## Memory Persistence

<required>

**Serena memories persist Ralph state across context resets.**

**Memory fields**: `ralph_[task]_state`
- iteration, hypotheses (tested/remaining), test_results, next_action

**Sync timing:**
- After each iteration: `write_memory()`
- Before/after context reset: `write_memory()` / `read_memory()`

</required>

## Orchestration Mode (Pattern B)

<context>

**Pattern B = subagent orchestration**: Parent stays light, workers get fresh 200k context each.

```text
User -> "ralph orch" -> Parent (light) -> Task tool -> Worker (fresh 200k each)
```

</context>

<required>

**Trigger**: "ralph orchestrate", "ralph orch", or "use orchestration mode"

**When to use**: Multi-step plans (>3 tasks), complex features, tasks prone to context accumulation.

**Parent orchestrator loop**:
1. Read plan file, parse `- [ ]` tasks
2. Select next unchecked task
3. Build worker context (plan path, iteration number, task text, memory keys)
4. Spawn worker:
   ```
   Task(subagent_type="general-purpose", prompt=<worker_prompt>)
   ```
   Worker prompt includes: plan path, task text, iteration N, memory keys for prior iterations, completion promise. See `agents/ralph-worker.md` for worker behavior.
5. Read worker result + verify plan file updated (`[x]`)
6. Optionally create/update Claude Code Task for UI tracking
7. If worker succeeded: increment iteration, save state, loop to step 2
8. If worker failed: ask user (retry / skip / modify / manual intervention)
9. On all tasks complete: clean up state, output summary

**Parent stays light by**:
- NOT reading full source files (only plan diffs, memory keys)
- NOT accumulating worker output (read summary, discard details)
- Using Serena memory keys as references (read only when needed)
- Periodically checking context %

**Prompt-based fallback**: If `agents/ralph-worker.md` is not found, parent builds equivalent prompt inline for `Task(subagent_type="general-purpose", prompt=...)`.

</required>

### Delegation Best Practices

<required>

**Well-scoped worker prompts MUST include:**
- Specific task description (what, not how)
- Success criteria (testable outcome)
- File scope (which files to read/modify)
- Constraints (don't touch X, preserve Y)

**Failure recovery:**
- Worker fails once: retry with more context
- Worker fails twice: escalate to user
- Worker produces wrong output: revert, rephrase task

**When to parallelize vs serialize:**
- Parallel: independent files, no shared state
- Serial: shared files, output of A feeds into B
- Hybrid: parallel batch, then serial integration

**Model routing for workers:**
See `@smith-ctx-claude/SKILL.md` for model routing guidance (added in PR #60).

</required>

### Orchestrator State File

Persists at `~/.claude/plans/.ralph-orchestrator-<CWD_KEY>` (16-char hash of `PPID:CWD` via `session_key()` in `lib-common.sh`):

```yaml
---
active: true
mode: orchestration
iteration: 3
max_iterations: 20
plan_path: "/path/to/plan.md"
completion_promise: "DONE"
current_task: "Implement auth API"
started_at: "2026-02-10T12:00:00+00:00"
---
```

Hook scripts detect this file to manage context cycling (save state before `/clear`, restore after).

## Agent Teams Mode (Pattern C)

<context>

**Pattern C = agent teams**: Team lead coordinates, teammates get independent context.

```text
User -> "ralph team" -> Team Lead -> Teammates (own context, shared tasks)
```

**Setup**: Set `"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}`
in `~/.claude/settings.json` (or export before starting Claude Code).

</context>

<required>

**Trigger**: "ralph team" or "use team mode"

**Team lead workflow**:
1. Read plan file, create shared task list from `- [ ]` items
2. Set up dependencies (task 2 depends on task 1 if sequential)
3. Spawn N teammates (each gets ralph-worker prompt + plan context)
4. Lead coordinates (see Known Issues before using delegate mode)
5. Teammates self-claim unblocked tasks from shared list
6. Lead monitors progress, handles failures, synthesizes results
7. On completion: clean up team, output summary

**Key features**:
- **Plan approval mode**: Require teammates to plan before implementing for risky tasks
- **Direct interaction**: User can message any teammate via Shift+Up/Down
- **Quality gates**: `TeammateIdle` hook for standards, `TaskCompleted` hook to validate
- **File ownership**: Each teammate owns different files (avoid conflicts)
- **Context per teammate**: Fresh context, loads CLAUDE.md + MCP servers + skills

**Parallel execution rules**:
- Independent tasks (different files): parallel teammates OK
- Sequential tasks (same files): use dependency tracking to serialize
- Lead assigns file ownership to avoid conflicts

</required>

### Display Modes

<context>

**In-process** (default, any terminal):
- Shift+Up/Down: Cycle between teammates
- Enter: View teammate session
- Escape: Interrupt teammate's current turn
- Ctrl+T: Toggle shared task list

**Split panes** (requires tmux or iTerm2):
- Each teammate gets own pane, visible simultaneously
- Click into pane to interact directly
- Config: `"teammateMode": "tmux"` in settings.json
- Override per-session: `claude --teammate-mode in-process`
- Not supported: VS Code terminal, Windows Terminal, Ghostty

**Default** (`"auto"`): Uses split panes if already in tmux,
otherwise in-process.

</context>

### Known Issues

<required>

**Delegate mode permission bug** (Issue #25037):
Teammates spawned after enabling delegate mode (Shift+Tab)
inherit the lead's restricted permissions. Teammates lose
file tools (Read, Write, Edit, Bash, Glob, Grep) and cannot
write code.

**Workaround**: Do NOT use delegate mode for code-writing teams.
- Tell lead: "Wait for teammates to complete before proceeding"
- Use **plan approval mode** instead for coordination control
  (require teammates to plan before implementing)
- If lead starts implementing, interrupt and redirect

**Other limitations**:
- No session resumption for in-process teammates
- No nested teams (teammates cannot spawn teams)
- One team per session; lead is fixed for lifetime
- Token-intensive (each teammate = separate Claude instance)
- Experimental - API may change

</required>

### Quality Gate Hooks

<context>

Hook matchers below are part of the experimental agent teams API
and may change. Verify against current Claude Code docs if issues arise.

**TeammateIdle** - Fires when teammate finishes and awaits
next task. Exit code 2 sends feedback and keeps teammate working.

```json
{
  "hooks": {
    "TeammateIdle": [{
      "type": "command",
      "command": "echo 'Run tests before marking done'",
      "timeout": 5
    }]
  }
}
```

**TaskCompleted** - Fires when shared task marked complete.
Exit code 2 prevents completion and sends feedback.

```json
{
  "hooks": {
    "TaskCompleted": [{
      "type": "command",
      "command": "echo 'Verify test coverage'",
      "timeout": 5
    }]
  }
}
```

</context>

## Tasks Integration

<context>

Claude Code Tasks provide visual progress tracking. Used as optional UI layer for both patterns.

</context>

**Pattern B**:
- Parent creates `TaskCreate` for each plan `- [ ]` item at orchestration start
- `TaskUpdate(status="in_progress")` before spawning worker
- `TaskUpdate(status="completed")` after worker succeeds

**Pattern C**:
- Agent Teams has built-in shared task list - no manual TaskCreate needed
- Team lead creates tasks via team infrastructure
- Dependencies tracked natively (blocks/blockedBy)

**Both patterns**: Plan file `[x]` checkboxes remain source of truth. Tasks are supplementary UI. Known limitation: Tasks orphaned across sessions (bug #20797). Plan file is the durable state.

## Pattern Decision Guide

- **Pattern A** (`/ralph-loop`): Simple focused tasks, <20 iterations, moderate context (1-3.5k/iter), no parallelism, interaction between iterations, low token cost, stable (official plugin), no setup
- **Pattern B** (`ralph orch`): Multi-step plans, 20-100+ iterations, low context (parent light), sequential (v1), interaction between workers, medium token cost, stable (Task tool), no setup
- **Pattern C** (`ralph team`): Large parallel-safe tasks, 10-50+ iterations, no context pressure (separate instances), native parallelism, interaction with any teammate, high token cost, experimental, requires settings.json env block (or export)

**Recommendation flow**:
1. Simple TDD/debug loop -> Pattern A (`/ralph-loop`)
2. Multi-step plan, sequential tasks -> Pattern B ("ralph orchestrate")
3. Parallel-safe tasks, research/review -> Pattern C ("ralph team")

<related>

- `@smith-tests/SKILL.md` - TDD workflow
- `@smith-validation/SKILL.md` - Debugging techniques
- `@smith-dev/SKILL.md` - Task decomposition
- @smith-guidance/SKILL.md - Exploration workflow
- @smith-ctx/SKILL.md - Context management
- `@smith-git/SKILL.md` - Commit patterns
- `@smith-serena/SKILL.md` - Memory persistence

</related>

## ACTION (Recency Zone)

<required>

**Starting Ralph:**
```shell
/ralph-loop "[task]" --completion-promise "[DONE]" --max-iterations 20
```

**Starting Orchestration (Pattern B):**
Say "ralph orchestrate" with a plan file. Parent spawns workers via Task tool.

**Starting Agent Teams (Pattern C):**
Say "ralph team" with a plan file. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (set via settings.json env block or shell export).

**During iterations:**
1. Read files before changes
2. Form ONE testable hypothesis
3. Execute and record result
4. Commit if progress made
5. `write_memory()` after each iteration

**On context reset:**
1. `write_memory()` with full state
2. After context reset: `read_memory()` to resume

</required>
