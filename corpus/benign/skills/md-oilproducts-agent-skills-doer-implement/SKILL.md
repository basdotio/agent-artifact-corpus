---
name: doer-implement
description: Implement a scoped software task by editing code, running targeted smoke checks, and producing machine-readable handoff artifacts (`patch.diff` and `handoff.json`) for downstream evaluation. Use when a user or orchestrator asks to implement/build/fix a task card and hand work to a separate judge; do not use this skill to grade final correctness or make merge decisions.
---

# Doer Implement

Implement the assigned task and hand off clean artifacts to a separate evaluator.

## Role Boundaries

- Implement only the assigned task scope.
- Run smoke checks relevant to touched files.
- Produce deterministic handoff artifacts.
- Do not act as judge:
  - Do not decide pass/reject for the full task.
  - Do not claim merge/release readiness.

## Required Inputs

- `task_id` (example: `TASK-0042`)
- `task` statement (clear, bounded implementation target)
- artifact paths for:
  - `patch.diff`
  - `handoff.json`

Optional:
- prior judge feedback (`required_changes`)
- explicit smoke-check commands

## Workflow

### 1) Restate scope and constraints

- Restate the task in one paragraph.
- List explicit constraints and assumptions.
- If prior judge feedback exists, treat it as required input.

### 2) Implement minimal code changes

- Prefer the smallest change set that satisfies the task.
- Keep edits localized; avoid unrelated refactors.
- Preserve existing style and project conventions.

### 3) Run smoke checks

- Run focused checks tied to touched code.
- Record each smoke check as `pass`, `fail`, `skip`, or `unknown`.
- If a smoke check fails, include that fact in `handoff.json`; do not hide failures.

### 4) Write `patch.diff`

Run:

```bash
bash <path-to-skill>/scripts/make_patch.sh \
  --repo <repo-root> \
  --output <artifact-path>/patch.diff
```

### 5) Write `handoff.json`

Run:

```bash
python3 <path-to-skill>/scripts/write_handoff.py \
  --repo <repo-root> \
  --task-id <task-id> \
  --summary "<short implementation summary>" \
  --output <artifact-path>/handoff.json \
  --requirement "RQ-0102" \
  --assumption "<assumption-id-or-text>" \
  --smoke-check "pass::pytest -q tests/test_auth.py"
```

Use `--smoke-check` multiple times when needed.

### 6) Validate handoff artifact

Run:

```bash
python3 <path-to-skill>/scripts/validate_handoff.py \
  --input <artifact-path>/handoff.json
```

## Output Rules

- Always produce both artifacts:
  - `patch.diff`
  - `handoff.json`
- Keep summaries factual and brief.
- Keep `requirements_touched` as stable IDs when available (`RQ-####`, `NFR-####`, `ASMP-####`, `ADR-####`).
- Keep `files_touched` repo-relative.
- Record assumptions explicitly.

## Resources

### scripts/
- `scripts/make_patch.sh`: generate binary-safe patch from working tree.
- `scripts/write_handoff.py`: build `handoff.json` with touched files and smoke-check results.
- `scripts/validate_handoff.py`: validate required handoff keys and value shapes.

### references/
- `references/artifact-contract.md`: canonical schema and examples for doer outputs.
- `references/smoke-check-guidelines.md`: how to choose and report smoke checks.
