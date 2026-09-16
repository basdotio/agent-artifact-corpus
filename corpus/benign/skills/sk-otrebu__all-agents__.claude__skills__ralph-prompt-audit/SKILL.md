---
name: ralph-prompt-audit
description: "Audit and repair aaa ralph command examples in this repo's prompts using LLM-as-judge backed by the live CLI command table. Use when user asks to find prompt drift, stale Ralph commands, or sync prompt examples with current CLI syntax."
---

# Ralph Prompt Audit

Repo-specific prompt drift checker for Ralph workflows.

This skill uses a hybrid approach:

1. Deterministic context collection (`aaa completion table --format json` + file/example extraction)
2. LLM-as-judge to detect stale, invalid, or misleading command examples

## Scope

Audit only these files unless user asks otherwise:

- `context/workflows/ralph/**/*.md`
- `.claude/skills/ralph-*/SKILL.md`

Do **not** normalize slash-command examples (`/ralph-plan ...`, `/ralph-review ...`) unless explicitly requested.

## Arguments

- `check` (default): audit and report findings only
- `fix`: audit and apply high-confidence fixes
- `--scope <glob>`: optional narrower scope for targeted audits

## Workflow

### 1) Collect deterministic context

Run:

```bash
bash .claude/skills/ralph-prompt-audit/scripts/collect-context.sh
```

This creates `tmp/ralph-prompt-audit/` with:

- `command-table.json` - live CLI matrix from `aaa completion table --format json`
- `ralph-command-matrix.md` - condensed command/option view for `aaa ralph`
- `review-files.txt` - prompt/skill files to audit
- `cli-invocations.txt` - extracted `aaa ralph` examples with file:line
- `README.md` - generation metadata

### 2) Run LLM judge pass

Launch a fresh subagent (`general`) and give it:

- `tmp/ralph-prompt-audit/ralph-command-matrix.md`
- `tmp/ralph-prompt-audit/cli-invocations.txt`
- target files from `tmp/ralph-prompt-audit/review-files.txt`

Ask for strict output in JSON with this schema:

```json
{
  "findings": [
    {
      "file": "path/to/file.md",
      "line": 123,
      "example": "aaa ralph ...",
      "issue": "why this is stale/invalid",
      "suggested": "aaa ralph ...",
      "confidence": "high|medium|low",
      "autoFixSafe": true
    }
  ]
}
```

Judge criteria:

- command exists in current `aaa ralph` table
- flags shown are valid for that command
- required flags are present in examples when relevant
- examples do not combine mutually exclusive source flags
- preserve intent and surrounding docs context

### 3) Apply fixes (only in `fix` mode)

Apply only `autoFixSafe: true` findings with `high` confidence.

If ambiguity remains, keep file unchanged and report it under "needs decision".

### 4) Verify after changes

Run collector again, then run targeted drift checks (`rg`) for known stale patterns.

Report:

- files checked
- files changed
- unresolved findings

## Repo-specific invariants to enforce

- `aaa ralph plan tasks` uses `--supervised` / `--headless` (not `--auto`)
- `aaa ralph review stories` and `aaa ralph review gap stories` use `--milestone <path>`
- `aaa ralph subtasks complete` examples should include `--commit <hash>` and `--session <id>`
- `aaa ralph plan subtasks` source flags are exclusive (`--milestone|--story|--task|--file|--text|--review-diary`)
