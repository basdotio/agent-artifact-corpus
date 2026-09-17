---
name: pr-squash-commit-message
description: Draft a high-quality squash merge commit message for a GitHub PR using Conventional Commits format. Analyzes PR title/body, diff, and changed files to generate a structured commit message.
metadata:
  version: "1.0"
  intent: "commit-message"
---

## Goal

Produce a clean, informative squash merge commit message for a GitHub Pull Request following this project's commit message conventions.

## References

- [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [Chris Beams: How to Write a Git Commit Message](https://cbea.ms/git-commit/) (especially "what" and "why")

## Inputs to use (in priority order)

1. Diff (`gh pr diff` or `git diff origin/main`)
2. Linked issues (e.g., #123)
3. Key changed files / modules (high-level)
4. PR title
5. PR description/body

If some inputs are missing, ask the user to provide them OR infer conservatively from what is available.

### CHANGELOG.md handling

When a PR includes changes to `CHANGELOG.md`:

- **Omit from commit message**: Routine entry additions under `[Unreleased]` that simply document the PR's other changes. This is expected for every PR and adds no information.

- **Include in commit message**: Structural changes, format updates, past entry corrections, or any changes unrelated to the PR's primary purpose.

## Output format

The commit message MUST follow [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) format:

### Structure

```
<type>: <description> (#<PR-number>)

<body>

<footers>
```

### First line (subject)

- Format: `<type>: <description> (#<PR-number>)`
- Length: <= 72 characters preferred
- Type: One of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Description: Imperative mood ("Add", "Fix", "Update", not "Added", "Fixes", "Updated")
- MUST end with PR number in parentheses: `(#123)`

### Body

2–8 short lines or bullet points covering:

- **Why**: Problem or motivation (see [Chris Beams: How to Write a Git Commit Message](https://cbea.ms/git-commit/))
- **What**: Changes made (see [Chris Beams: How to Write a Git Commit Message](https://cbea.ms/git-commit/))
- **Impact**: Effects on users, system, or development (SHOULD include)

Use bullets for multiple changes. Keep it scannable.

### Footers

- `Fixes: #123` / `Closes: #123` / `Resolves: #123` — use when this PR resolves an issue (issues should generally be created before PRs)
- `Related: #123` / `Reference: #123` — use to reference related issues not fully resolved by this PR
- `BREAKING CHANGE: <what/why/migration>` — only if applicable

## Language policy

Always write commit messages in English.

## Title policy (how to craft the subject line)

Use imperative mood:
- "Add …", "Fix …", "Refactor …", "Improve …"

Title must be specific:
- Avoid vague words: "update", "tweak", "misc", "fix bug"
- Include the _user-visible or system-visible_ effect
- If relevant, include subsystem/module as scope or in wording

## Type selection guide

- `feat`: New feature for users or significant new capability
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, missing semicolons, etc.) that don't affect code execution
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

## Body policy

Keep it scannable:
- Prefer bullets when listing changes
- Mention notable tradeoffs, migrations, or risk
- Include impact on users, system, or development workflow

## Examples

### Example A: Feature addition

Input:
- PR #20
- Diff: Adds homebrew-tap directory to workspace configs
- Linked issue: (none)
- Key changed files: .devcontainer/devcontainer.json, devcontainer.json
- PR title: Add homebrew-tap directory to workspace access configs
- PR body: Enables access to acevif/homebrew-tap for formula updates

Output:

```
feat: Add homebrew-tap directory to workspace access configs (#20)

- Enable access to acevif/homebrew-tap repository in dev container
- Add workspaceFolder to both root and nested devcontainer configs

Impact: Developers can now update Homebrew formula from within the dev container
```

### Example B: Bug fix with issue

Input:
- PR #456
- Diff: (omitted)
- Linked issue: #400
- Key changed files: src/validation.rs, tests/validation_tests.rs
- PR title: Fix passphrase validation for WPA3
- PR body: Enforce 8-63 ASCII or 64 hex; align with spec; update error messages

Output:

```
fix: Correct WPA3 SAE passphrase validation rules (#456)

- Enforce 8-63 ASCII or 64-hex passphrase requirements per spec
- Add comprehensive validation tests for edge cases
- Surface clearer validation errors to users

Impact: WPA3 password validation now correctly rejects invalid inputs

Fixes: #400
```

### Example C: Breaking change

Input:
- PR #789
- Diff: Changes API response format
- Linked issue: #700
- Key changed files: src/api/response.rs, docs/API.md
- PR title: Migrate API responses to JSON:API format
- PR body: Standardize on JSON:API v1.1 for consistency

Output:

```
refactor: Migrate API responses to JSON:API format (#789)

- Adopt JSON:API v1.1 specification for all endpoints
- Update response serializers and documentation
- Add migration guide for API consumers

Impact: All API consumers must update their response parsing logic

BREAKING CHANGE: API response format changed from custom structure to JSON:API v1.1.
See docs/MIGRATION.md for upgrade instructions.

Fixes: #700
```

## Workflow

1. Fetch PR information (diff, title, body, linked issues)
2. Analyze the changes:
   - Identify the type (feat, fix, docs, etc.)
   - Determine the core problem and solution
   - Note the impact on users/system
3. Draft the commit message following the format above
