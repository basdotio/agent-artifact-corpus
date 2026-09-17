---
name: gh-pr-feedback
description: Address GitHub pull request review feedback using the gh CLI. Use when given a PR number and asked to read the PR comments/reviews, implement unaddressed reviewer updates, prioritize project owner feedback, and submit the fixes as a stacked/sub-PR targeting the original PR branch.
---

# Gh Pr Feedback

## Overview

Implement unaddressed PR feedback by reading the PR conversation and review threads, prioritizing the project owner's guidance, and delivering fixes via a stacked PR that targets the original PR branch.

## Workflow

### 1) Gather PR context

- Use `gh pr view <PR#> --json title,number,author,baseRefName,headRefName,headRepository,headRepositoryOwner,reviewDecision,url` to capture branch names and repo.
- Use `gh pr view <PR#> --comments` to read top-level PR conversation comments.
- Use the API to read inline review comments (line comments), which `gh pr view` may not expose:
  - `gh api repos/<owner>/<repo>/pulls/<PR#>/comments --paginate`
- Optionally fetch review metadata:
  - `gh api repos/<owner>/<repo>/pulls/<PR#>/reviews`

### 2) Identify the project owner

- Determine the project owner from the repository owner (user/org) via `gh repo view --json owner`.
- Treat comments authored by that owner (or their designated maintainers if explicitly stated in the thread) as highest priority.

### 3) Build the feedback list

- Extract actionable items from review comments and top-level PR conversation comments.
- Mark items as **owner**, **non-owner**, and **owner-ignore**:
  - **owner**: authored by the project owner.
  - **owner-ignore**: any item the owner explicitly says to ignore/skip/leave as-is.
  - **non-owner**: all other reviewers.
- If the owner provides guidance on implementation details, follow that guidance even if it conflicts with other reviewer suggestions.

### 4) Check what is already addressed

- Compare feedback items against the current PR changes and comment follow-ups.
- Only implement items that are clearly unaddressed.
- If unclear, leave a brief note in the sub-PR description about the ambiguity.

### 5) Synchronize with origin

- Ensure local refs are up to date before checking out the PR head:
  - `git fetch origin --prune`

### 6) Create a stacked sub-PR branch

- Create a new branch from the PR head branch (not from `main`):
  - `gh pr checkout <PR#>`
  - `git checkout -b pr-<PR#>-feedback`
- Implement the updates locally, following the owner's guidance for how to fix issues.
- Commit changes with a concise message that references the PR number.

### 7) Open a sub-PR targeting the original PR branch

- Push the branch and create a PR with the base set to the original PR head branch:
  - `git push -u origin pr-<PR#>-feedback`
  - `gh pr create --base <original-pr-head-branch> --head pr-<PR#>-feedback --title "PR <PR#> feedback fixes" --body "Addresses unaddressed review feedback from PR <PR#>. Prioritized owner comments; ignored items the owner said to skip."`
- If the repo uses stacked PR conventions (labels, prefixes, or templates), follow them.
- After the sub-PR is committed and pushed, comment on the original PR with a link to the new sub-PR and a brief description of the changes it includes.

### 8) Summarize and notify

- In the sub-PR description and/or a PR comment, summarize which feedback items were addressed and which were intentionally ignored due to owner instruction.
- If any feedback was deferred, state why and where it should be handled.

## Notes

- Never implement feedback the owner explicitly says to ignore.
- If the owner’s guidance is ambiguous, ask for clarification in the sub-PR or PR comment rather than guessing.
- Keep the sub-PR focused on feedback items only; avoid unrelated refactors.

## Suggested gh commands (examples)

```bash
gh pr view 123 --json title,number,author,baseRefName,headRefName,headRepository,headRepositoryOwner,reviewDecision,url
gh pr view 123 --comments
gh api repos/<owner>/<repo>/pulls/123/comments --paginate
gh api repos/<owner>/<repo>/pulls/123/reviews

git fetch origin --prune
gh pr checkout 123
git checkout -b pr-123-feedback

# implement updates

git status
git add -A
git commit -m "PR 123 feedback fixes"

git push -u origin pr-123-feedback
gh pr create --base <original-pr-head-branch> --head pr-123-feedback \
  --title "PR 123 feedback fixes" \
  --body "Addresses unaddressed review feedback from PR 123. Prioritized owner comments; ignored items the owner said to skip."
```
