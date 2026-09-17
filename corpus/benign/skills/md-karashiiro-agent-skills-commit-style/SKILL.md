---
name: commit-style
description: Use this before making any commit as the user has special formatting requirements that need to be followed for consistency across projects. If you ask to commit code you just wrote, or if the user asks you to commit something, you should check this skill first to understand how the user wants you to do it.
---

# Commit Changes

Create a git commit using conventional commits format.

## Commit Style

- **Format**: `type(scope): description` or `type: description`
- **Types**: `feat`, `fix`, `docs`, `chore` (minimal set)
- **Scope**: Optional, use when it adds clarity (e.g., `feat(auth):`, `fix(ipc):`)
- **No AI attribution by default**: Do not add "Generated with Claude Code" or Co-Authored-By lines unless required by the project standards (always check, first)
- **No emojis**: Keep messages plain text

## Verbosity Rules

- **Small changes** (~1-4 files, simple modification): Title only, ~50-72 chars
- **Medium changes** (5-7 files, related modifications): Title + 1-3 sentence body
- **Large changes** (8+ files or significant feature): Title + bullet point list

## Workflow

Note: For steps where it says to ask for directions, use your question tools, if available.

1. **Show current status**: Run `git status` to see all changes
2. **Show diff summary**: Run `git diff --stat` for overview, `git diff` for details if needed
3. **Interactive staging**: Ask which files/changes to include in this commit
4. **Draft message**: Based on staged changes, draft a conventional commit message
5. **Review**: Show the proposed message and ask for approval or edits
6. **Commit**: Execute the commit (without --no-verify unless requested)

## Instructions

Follow this workflow step by step. Be concise in your communication. When showing diffs, summarize large changes rather than dumping everything.

For the commit message:
- Use imperative mood ("Add feature" not "Added feature")
- First line should be under 72 characters
- If body is needed, separate from title with blank line
- Body lines should wrap at 72 characters

Example small commit:
```
docs: add design documentation index
```

Example medium commit:
```
feat(auth): implement OAuth token refresh

Add automatic token refresh when access token expires within 5 minutes.
Tokens are persisted to OS keychain via frontend IPC.
```

Example large commit:
```
docs: overhaul documentation

- Add cross-platform backend path resolution to frontend-architecture.md
- Clarify multi-turn conversation status in backend-adapter.md
- Create ROADMAP.md with phase breakdown
- Add asset authoring timeline to animation-system.md
- Create design docs index page
```
