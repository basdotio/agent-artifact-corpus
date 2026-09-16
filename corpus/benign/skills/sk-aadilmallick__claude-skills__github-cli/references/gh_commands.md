# GitHub CLI (gh) Commands Reference

## Authentication

```bash
# Login to GitHub
gh auth login

# Check authentication status
gh auth status

# Logout
gh auth logout
```

## User Profile

```bash
# Get current user profile
gh api user

# Get specific user profile
gh api users/USERNAME

# Get user's followers
gh api user/followers

# Get user's following
gh api user/following
```

## Repositories

```bash
# List your repositories
gh repo list

# List repositories with specific fields
gh repo list --json name,description,stargazerCount,forkCount

# List repositories sorted by stars
gh repo list --sort stargazers

# View repository details
gh repo view OWNER/REPO

# Clone a repository
gh repo clone OWNER/REPO

# Create a new repository
gh repo create NAME --public/--private
```

## Pull Requests

```bash
# List pull requests
gh pr list

# View a specific PR
gh pr view NUMBER

# Create a PR
gh pr create

# Checkout a PR
gh pr checkout NUMBER

# List PRs you're assigned to
gh pr list --assignee @me
```

## Issues

```bash
# List issues
gh issue list

# View an issue
gh issue view NUMBER

# Create an issue
gh issue create

# Close an issue
gh issue close NUMBER
```

## Gists

```bash
# List gists
gh gist list

# Create a gist
gh gist create FILE

# View a gist
gh gist view ID
```

## GitHub Actions

```bash
# List workflow runs
gh run list

# View a specific run
gh run view RUN_ID

# Watch a run
gh run watch

# Re-run a workflow
gh run rerun RUN_ID
```

## Advanced API Queries

```bash
# Get repositories with custom jq filter
gh api user/repos --jq '.[] | {name, stars: .stargazers_count}'

# Get contribution stats
gh api users/USERNAME/events

# Search repositories
gh api search/repositories -q "q=USER:username"

# Get repository languages
gh api repos/OWNER/REPO/languages
```

## Useful Combinations

```bash
# Get top 5 most starred repos
gh repo list --limit 5 --sort stargazers

# List all private repositories
gh repo list --json name,isPrivate --jq '.[] | select(.isPrivate == true) | .name'

# Get total star count across all repos
gh api user/repos --paginate --jq '[.[] | .stargazers_count] | add'
```
