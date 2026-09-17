---
name: current-branch-diff
description: |
  Read the code changes in the current Git branch compared to its parent branch, ignoring generated artifacts (`.wat`, `.hir`, `.masm`) and lockfiles (`.lock`). Run `git parent-branch` to print the parent branch name.
---

# Current Branch Diff (ignore artifacts)

## Quick start

1. Print the parent branch:
   - `git parent-branch`
2. Review the diff (merge-base comparison) while ignoring `.wat`, `.hir`, `.masm`, and `.lock` files:
   - `parent="$(git parent-branch)"`
   - `git diff --stat "$parent"...HEAD -- . ':(exclude)*.wat' ':(exclude)*.hir' ':(exclude)*.masm' ':(exclude)*.lock'`
   - `git diff "$parent"...HEAD -- . ':(exclude)*.wat' ':(exclude)*.hir' ':(exclude)*.masm' ':(exclude)*.lock'`

## Notes

- Prefer `"$parent"...HEAD` (three dots) to compare against the merge-base with the parent branch.
- If you want a quick file list first:
  - `git diff --name-only "$parent"...HEAD -- . ':(exclude)*.wat' ':(exclude)*.hir' ':(exclude)*.masm' ':(exclude)*.lock'`
