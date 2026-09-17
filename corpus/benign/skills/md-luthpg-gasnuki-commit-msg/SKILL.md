---
name: commit-msg
description: Analyzes staged files, generates an appropriate commit message, and executes the commit.
---

# Commit Message Skill

Generate a commit message for staged files and execute the commit.

## Commit Procedure

1. Read staged file differences using `git diff --staged`.
2. Check the current branch using `git branch -a`.
   - If on `main` branch or if the branch name does not reflect the staged changes, create and switch to a new branch:

     ```powershell
     git branch <new-branch-name>
     git checkout <new-branch-name>
     ```

3. Review the last 3 commit messages using `git log -n 3` to understand the project's commit style.
4. Generate a commit message based on:
   - The staged changes
   - The observed commit message style
5. Execute the commit using `git commit` in a Windows 11 PowerShell environment.

## Rules

- Only commit staged files. Do not include unstaged changes.
- Execute each git command separately. Do not chain commands.
