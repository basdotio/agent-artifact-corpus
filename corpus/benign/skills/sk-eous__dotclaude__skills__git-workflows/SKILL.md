---
name: git-workflows
description: Git version control workflows, branching strategies, and best practices. Use when discussing git commands, branching, merging, rebasing, or version control workflows. Triggers on mentions of git, branch, merge, rebase, commit, pull request, GitHub, GitLab, version control.
---

# Git Workflows and Best Practices

## Commit Best Practices

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Examples
```bash
# Good commits
git commit -m "feat(auth): add OAuth2 login support"
git commit -m "fix(api): handle null response from payment gateway"
git commit -m "refactor(db): extract query builder into separate module"

# Bad commits
git commit -m "fix stuff"
git commit -m "WIP"
git commit -m "changes"
```

### Atomic Commits
```bash
# Stage specific changes
git add -p  # Interactive staging

# One logical change per commit
git commit -m "feat(user): add email validation"
git commit -m "test(user): add email validation tests"
```

## Branching Strategies

### GitHub Flow (Simple)
```
main
  └── feature/add-login
  └── fix/null-pointer
  └── feature/dashboard
```

```bash
# Create feature branch
git checkout -b feature/add-login main

# Work and commit
git add .
git commit -m "feat(auth): implement login form"

# Push and create PR
git push -u origin feature/add-login
gh pr create
```

### Git Flow (Release-based)
```
main (production)
  └── develop
        └── feature/add-login
        └── release/v1.2.0
        └── hotfix/critical-fix
```

### Trunk-Based (CI/CD)
```
main
  └── short-lived feature branches (< 1 day)
```

## Common Operations

### Rebasing
```bash
# Rebase feature on updated main
git checkout feature/add-login
git fetch origin
git rebase origin/main

# Interactive rebase to clean up commits
git rebase -i HEAD~3
# pick, squash, fixup, reword, drop
```

### Merging
```bash
# Merge with commit
git checkout main
git merge --no-ff feature/add-login

# Fast-forward merge
git merge --ff-only feature/add-login
```

### Cherry-picking
```bash
# Apply specific commit to current branch
git cherry-pick abc123

# Cherry-pick without committing
git cherry-pick --no-commit abc123
```

### Stashing
```bash
# Stash changes
git stash
git stash push -m "WIP: login feature"

# List stashes
git stash list

# Apply and remove
git stash pop

# Apply and keep
git stash apply stash@{0}
```

## Undoing Changes

### Unstaged Changes
```bash
# Discard changes in file
git checkout -- file.txt
git restore file.txt  # Git 2.23+

# Discard all changes
git checkout -- .
git restore .
```

### Staged Changes
```bash
# Unstage file
git reset HEAD file.txt
git restore --staged file.txt  # Git 2.23+

# Unstage all
git reset HEAD
```

### Committed Changes
```bash
# Undo last commit, keep changes staged
git reset --soft HEAD~1

# Undo last commit, keep changes unstaged
git reset HEAD~1

# Undo last commit, discard changes
git reset --hard HEAD~1

# Create new commit that undoes previous
git revert abc123
```

### Remote Changes
```bash
# CAUTION: Only if not pushed
git reset --hard HEAD~1

# If already pushed (creates new commit)
git revert abc123
git push
```

## Collaboration

### Pull Requests
```bash
# Update PR with new changes
git add .
git commit -m "fix: address review feedback"
git push

# Squash commits before merge
git rebase -i main
# Change 'pick' to 'squash' for commits to combine
```

### Resolving Conflicts
```bash
# During merge
git merge feature/other
# Fix conflicts in files
git add resolved-file.txt
git commit

# During rebase
git rebase main
# Fix conflicts
git add resolved-file.txt
git rebase --continue
```

### Code Review
```bash
# Fetch PR for review
gh pr checkout 123

# View changes
git diff main...HEAD
git log main..HEAD --oneline
```

## Useful Commands

### History and Search
```bash
# View history
git log --oneline --graph --all
git log --since="2 weeks ago" --author="name"

# Search commits
git log --grep="bug fix"
git log -S "function_name"  # Search content changes

# Blame
git blame file.txt
git blame -L 10,20 file.txt  # Lines 10-20
```

### Cleaning
```bash
# Remove untracked files (dry run)
git clean -n

# Remove untracked files
git clean -f

# Remove untracked files and directories
git clean -fd

# Remove ignored files too
git clean -fdx
```

### Bisect (Find Bug Introduction)
```bash
git bisect start
git bisect bad  # Current version is bad
git bisect good abc123  # Known good commit
# Git checks out middle commit
# Test and mark as good/bad
git bisect good  # or git bisect bad
# Repeat until found
git bisect reset
```

## Configuration

### Useful Aliases
```bash
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.lg "log --oneline --graph --all"
```

### Global Settings
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global pull.rebase true
git config --global init.defaultBranch main
```

## Anti-Patterns to Avoid

- Force pushing to shared branches
- Committing secrets or credentials
- Large binary files in repo
- Meaningless commit messages
- Mixing unrelated changes in one commit
- Long-lived feature branches
- Ignoring merge conflicts
- Committing generated/build files
