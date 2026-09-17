---
name: commit-changes
description: Commit AI-made changes safely: detect mixed changes, stage only agent edits, and write commits with model-prefixed messages.
---

# Commit Changes Skill

Use this skill when the user asks to commit changes made by the agent.

## Workflow

1) Summarize changes and ask for commit confirmation.
2) Detect mixed changes:
   - Run `git status -sb`
   - Run `git diff` (and `git diff --staged` if needed)
   - Identify files modified by the agent in this session.
3) Stage only agent changes:
   - Use `git add <files>` or `git add -p` for mixed files.
   - Leave user changes unstaged; notify the user.
4) Commit with model prefix:
   - Format: `[MODEL_NAME]: <type>: <short description>`
   - Use conventional types when appropriate (feat/fix/refactor/docs/test/chore).
5) Report result:
   - Provide commit hash and short summary.
   - Offer to push if appropriate (never auto-push).

## Safety & Rules

- Never commit user changes without explicit permission.
- Never amend unless explicitly requested.
- Never force push or rewrite history.
- If the pre-commit hook fails, report the failure and ask whether to fix or proceed.
- If git is not initialized, inform the user and ask to initialize.

## Mixed Changes Message Template

If user changes are present, say:

- "I detected uncommitted changes you made in: <files>. I will only commit my changes: <files>. Your changes remain unstaged."

## Model Prefix

Use the current model identifier. If unknown, use `[AI]`.
