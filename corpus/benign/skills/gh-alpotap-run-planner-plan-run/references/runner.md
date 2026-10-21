# What the runner does, and what the plan must fit

## Contents

- [Commands](#commands)
- [One task, one session](#one-task-one-session)
- [The RESULT block](#the-result-block)
- [The ledger](#the-ledger)
- [runner.json](#runnerjson)
- [Limits and failures](#limits-and-failures)
- [Afterwards](#afterwards)

## Commands

```powershell
.\tools\run-planner\run_plan.ps1                               # the newest run with open tasks, to the end
.\tools\run-planner\run_plan.ps1 -Run 007-fixes -From 50.2     # explicit run / starting task
.\tools\run-planner\run_plan.ps1 -Phase 15                     # one phase only
.\tools\run-planner\run_plan.ps1 -Model opus                   # force one model for every task
.\tools\run-planner\run_plan.ps1 -LiveAttended                 # open (ATTENDED) tasks as live sessions
.\tools\run-planner\run_task.ps1 -Task 50.2 -Run runs/007-fixes   # one task by hand
.\tools\run-planner\new_run.ps1 -Name tenant-billing           # a new run folder
```

## One task, one session

- **Tasks.** Every `### Task` heading of the run's `PLAN.md`, in file order. A task is closed when its ledger row says `done` or `blocked`. Closed tasks are skipped, so rerunning continues where it stopped.
- **Prompt.** The runner extracts the task's section, and the section whose heading contains `Rules for every task`, and sends both on stdin with the working rules. The prompt is saved as `.runlogs/<run>/<task>.prompt.md`. The session does not open the plan unless the task cites another section.
- **Model and effort.** These come from the task's `**Model:**` and `**Effort:**` lines, else from `runner.json` (default: Sonnet at low effort).
- **Tools.** Without a `**Tools:**` line: the lean set (Bash, PowerShell, Read, Edit, Write, Grep, Glob) and no MCP servers. Measured: 11K tokens of starting context instead of 35K with every tool. A `**Tools:**` line replaces the built-in set with the tools it names, and every tool it names is pre-approved. `Browser` loads the MCP server from `runs/browser-mcp.json` for that task only. `**Tools: default**` restores every built-in tool.
- **Turn budget.** The prompt gives about 8 / 20 / 50 turns for S / M / L. It is guidance, not a hard stop.
- **Headless rules.** Commands run in the foreground, at most 30 minutes each. Output over 20 000 characters is cut. Background tasks are off. `git push` is denied.

## The RESULT block

The session commits its own changes as `Task <id>: <summary>`, in each repository it changed. It never edits the ledger. It ends its last reply with:

```text
RESULT: done
NOTE: resolve_pool_entry_base_url appends /v1 to ollama/lm_studio roots once; Verify: 38 passed.
DOCS: none
```

`RESULT: blocked` with the reason in NOTE is the other ending. A reply without the block is nudged to finish, up to 3 times.

## The ledger

The runner writes the row and commits only that file, as `Task <id>: ledger (done)`. The Commit column lists the task's commits from every repository, found by their `Task <id>:` subject. A ledger starts as:

```markdown
# Progress: <NNN-name>

Plan: PLAN.md in this folder. Rows are written by the runner. A row's status is done or blocked; the runner skips both.

| Task | Status | Commit | Notes |
| ---- | ------ | ------ | ----- |
```

Older plans whose tasks write their own rows still work: a closed row also counts as finished.

## runner.json

```json
{
  "addDirs": ["../engine"],
  "pathAdd": ["C:\\Program Files\\Docker\\Docker\\resources\\bin"],
  "defaultModel": "sonnet",
  "models": { "haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5" },
  "effort": { "haiku": "medium", "sonnet": "low", "opus": "" },
  "tools": ["Bash", "PowerShell", "Read", "Edit", "Write", "Grep", "Glob"]
}
```

| Key            | Meaning                                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `addDirs`      | sibling repositories tasks may edit (`--add-dir`), relative to the project; the runner also looks there for task commits |
| `pathAdd`      | directories added to `PATH` for headless shells (tools that are installed but off `PATH`)                                 |
| `defaultModel` | the alias for tasks without a `Model:` line                                                                               |
| `models`       | alias → model id. On the next model generation, change the ids here                                                       |
| `effort`       | alias → `--effort` level; empty means the model's default                                                                 |
| `tools`        | the lean tool set                                                                                                         |

## Limits and failures

- Usage limits are waited out until their reset, for days if need be. API outages back off, up to 24 tries.
- A task that stops without a RESULT block is continued up to 3 times. After that the run stops, and rerunning the command continues from that task.
- A task closes as `blocked` when it cannot proceed without breaking a "never" rule. Its dependants close as blocked too.

## Afterwards

The end-of-run summary lists:

- blocked tasks;
- attended tasks;
- `ADVERSARY.md`;
- where to find "Decisions to review";
- a table per task of model, minutes, turns, context re-read and cost.

`.runlogs/<run>/usage.csv` has one line per call.
