---
name: ralph-calibrate
description: Run Ralph calibration checks to analyze intention drift, technical quality, and self-improvement opportunities. Use when user asks to "ralph calibrate", "check drift", "analyze sessions", or needs to verify work alignment.
---

# Ralph Calibrate

Thin wrapper over the CLI runtime. Do not re-implement calibration logic here.

## Execution

1. Parse arguments from `/ralph-calibrate`.
2. If no `<check>` argument is provided, show the Usage section and stop.
3. Accept checks: `intention`, `technical`, `improve`, `all`.
4. Resolve `subtasks.json` absolute path by searching up from the current directory to project root.
5. Build command: `aaa ralph calibrate <check> --subtasks <resolved-absolute-path> [--review] [--force]`.
6. Run the command via Bash tool.
7. Display CLI stdout/stderr to the user as the calibration result.

Do not add prerequisite checks, sequential orchestration, or config logic in this skill; the CLI handles those.

## Usage

```text
/ralph-calibrate <check> [--review] [--force]
```

## Checks

- `intention` - Analyze intention drift from completed subtasks
- `technical` - Analyze technical quality drift
- `improve` - Analyze session logs for self-improvement
- `all` - Run all calibration checks

## Options

- `--review` - Stage proposals for approval
- `--force` - Auto-apply without approval prompts

## Examples

```bash
/ralph-calibrate intention
/ralph-calibrate technical --review
/ralph-calibrate improve --force
/ralph-calibrate all --force
```

## CLI Equivalent

```bash
aaa ralph calibrate <check> --subtasks <path-to-subtasks.json> [--review] [--force]
```
