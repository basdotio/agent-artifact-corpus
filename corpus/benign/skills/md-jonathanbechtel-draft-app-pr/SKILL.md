---
name: pr
description: Create a pull request for the current branch using GitHub CLI. Use after committing changes when ready to open a PR.
allowed-tools: Bash
---

# Create Pull Request

Create a pull request for the current branch against main using the GitHub CLI.

## Instructions

1. Run `git status` to check for uncommitted changes (warn if any exist)
2. Check if the branch has an upstream and is pushed
3. Run `git log main..HEAD --oneline` to see all commits in this branch
4. Run `git diff main...HEAD --stat` to understand the full scope of changes
5. Create a PR with `gh pr create`

## PR Format

Use a HEREDOC for the body to ensure proper formatting:

```bash
gh pr create --title "<concise title>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points describing what this PR does>

## Test plan
- [ ] <how to verify this works>
EOF
)"
```

## Title Guidelines

- Keep under 72 characters
- Use imperative mood ("Add feature" not "Added feature")
- Be specific about what changed

## Body Guidelines

- **Summary**: 1-3 bullet points explaining what and why
- **Test plan**: Checklist of verification steps

## Pre-flight Checks

Before creating the PR:
1. Ensure all changes are committed
2. Ensure branch is pushed to remote
3. If not pushed, run `git push -u origin HEAD` first

## Example

```bash
gh pr create --title "Fix cron machine image updates in CI/CD" --body "$(cat <<'EOF'
## Summary
- Fix CI/CD to explicitly pass --image when updating cron machines
- Cron machines created via `flyctl machine run` don't auto-update with app releases
- Fetches image from deployed app machines and passes it to machine update

## Test plan
- [ ] Deploy to staging and verify cron machine gets updated
- [ ] Check cron logs after next scheduled run
EOF
)"
```

## After Creation

Return the PR URL so the user can review it.
