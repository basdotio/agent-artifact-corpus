---
name: commit
description: Create semantic commits following conventional commits format with proper granularity
---

# Commit Skill

This skill enforces meaningful commit messages and proper commit workflow.

## Commit Granularity

- **MUST**: Commit changes at logical checkpoints
- **MUST**: Each commit includes only ONE logical change (feature, bug fix, refactor, etc.)
- **NEVER**: Combine multiple unrelated changes into one commit
- **NEVER**: Commit partial/broken implementations

## Branch Policy

**CRITICAL: Protect main/master branches**

- **NEVER**: Commit directly to `main` or `master` branches
- **MUST**: Work on feature branches (e.g., `feature/add-auth`, `fix/login-bug`)
- **MUST**: Merge changes via pull requests only
- **EXCEPTION**: Only commit to `main`/`master` if the user explicitly requests it

### Before Committing

Always check the current branch:

```bash
git branch --show-current
```

**If on main/master**:
1. **STOP** - Do not commit
2. Create a feature branch: `git checkout -b feature/descriptive-name`
3. Then commit your changes
4. Push and create a pull request

**Exception**: If the user explicitly says "commit to main" or "commit to master", then proceed.

## Message Format

Follow the **Conventional Commits** format:

```
<type>[optional scope]: <subject>

[optional body]

[optional footer]
```

### Type

Must be one of:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build config, etc.)
- `ci`: CI/CD configuration changes

### Scope (Optional)

Indicates the affected area when applicable:
- Examples: `auth`, `api`, `ui`, `db`, `core`, `cli`
- Use lowercase
- Keep it concise (1-2 words)
- Omit if the change doesn't belong to a specific area

### Subject

**Describes WHAT changed**

- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize first letter
- No period at the end
- Maximum 72 characters
- Be specific and descriptive

### Body (Optional)

**Explains WHY the change was made**

- Describe the reason and motivation for the change
- Explain the problem that this change solves
- Wrap at 72 characters
- Separate from subject with blank line

### Footer (Optional)

- Breaking changes: `BREAKING CHANGE: description`
- Issue references: `Closes #123`, `Fixes #456`

## Examples

### Good Commits

```bash
feat(auth): add JWT token refresh mechanism

Implements automatic token refresh before expiration.
Reduces authentication errors and improves UX.

Closes #234
```

```bash
fix(api): handle null response in user endpoint

Previously threw uncaught exception when user not found.
Now returns 404 with proper error message.
```

```bash
perf(db): optimize query performance with indexes

Adds composite index on (user_id, created_at).
Reduces query time from 2s to 50ms for user dashboard.
```

```bash
docs: update installation steps

Installation steps were outdated after recent dependency changes.
```

### Bad Commits ❌

```bash
# Too vague
fix: bug fix

# Multiple changes
feat: add login and update user profile

# Wrong tense
fixed: bug in login

# Not specific
update code

# Capitalized, has period
Feat(auth): Add login.
```

## Workflow

1. **Check branch**: Verify not on `main`/`master` with `git branch --show-current`
2. **Review changes**: `git status` and `git diff`
3. **Stage files**: Only files related to this logical change
4. **Write message**: Follow format above
5. **Commit**: Create commit with meaningful message
6. **Verify**: `git log -1` to review the commit

## Co-authored Tag

- Claude Code adds co-authored tag automatically
- Keep the tag for commits (helps track AI assistance)
- Remove tool mentions from PR descriptions per CLAUDE.md

## Notes

- Prefer smaller, focused commits over large commits
- Each commit should be potentially revertible independently
- Commit messages become part of project history - make them count
