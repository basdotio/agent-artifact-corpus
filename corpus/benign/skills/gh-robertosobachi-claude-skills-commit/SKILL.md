---
name: commit
description: Stage and commit the current work, one commit per separate piece of work, each with a gitmoji title, and rate the push risk of each. Never pushes.
disable-model-invocation: true
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git diff *) Bash(git status *) Bash(git log *)
---

## Working tree

!`git status --short`

### Staged

!`git diff --staged`

### Unstaged

!`git diff`

## Your task

Commit the current work. `$ARGUMENTS`, if given, says what to commit or how to split it.

1. If anything is staged, commit only the staged changes, as one commit, and leave everything else alone.
2. Otherwise, group the unstaged changes and untracked files above into separate pieces of work, such as a feature and an unrelated docs update. Read untracked files if you need to see what they are. Files that only make sense together stay in one group. When in doubt, use fewer groups.
3. Groups are whole files. If a file holds changes for two groups, put it with the one it mostly belongs to.
4. Order the groups so each commit builds on the ones before it. For each group, run `git add -- <paths>`, then `git commit -m '<title>'`, escaping any `'` in the title as `'\''`.

Title format: `:<gitmoji>: <type>: <Subject>`

- `<gitmoji>`: one alias from gitmoji.dev that fits the change, e.g. `:sparkles:`, `:bug:`, `:recycle:`, `:memo:`, `:tada:`.
- `<type>`: one conventional commit type: feat, fix, refactor, docs, test, chore, perf, style, build or ci.
- `<Subject>`: imperative mood, capitalised, no full stop, technically specific.
- 72 characters at most, counting the alias as typed (`:sparkles:` is 10).

If there is nothing to commit, say so and stop.

## Push risk

Rate each commit on how much breaks, and for whom, if it is wrong once pushed. The highest level in a commit wins: one 🔴 file makes the whole commit 🔴.

- 🟢 Low: docs, comments or tests only, dev-only tooling, new code nothing calls yet, or a refactor with no behaviour change that tests cover.
- 🟡 Medium: a behaviour change in code with a few callers, a shared component or util, a user-visible UI change, non-trivial logic, or a minor dependency bump.
- 🔴 High: auth, payments, permissions, data migrations or schema, a public API or exported contract, a removed or renamed symbol that still has callers, build, CI, deploy or release config, env or secrets handling, a major dependency bump, or changes spread across many modules.

If a commit removes, renames or changes the signature of an exported symbol, search the repo for its callers and count them. Otherwise judge from the diff alone and explore nothing else.

Format: `<emoji> <Level>: <what it reaches and how it fails if wrong>`, one line under about 100 characters. Name the concrete caller, screen or system, never a generic phrase. Example: `🔴 High: changes token refresh used by every API call, a bug logs everyone out`. Low can be short: `🟢 Low: README only`.

## Rules

- Stage by explicit path. Never `git add -A`, `git add .` or `git commit -a`.
- Never amend, rebase, push or pass `--no-verify`.
- If a commit fails, for example a hook rejects it, stop and show the error. Don't change files to make it pass.
- The message is the title alone. Never add `Co-Authored-By` or any other AI attribution trailer.

## Report

Show `git log --oneline -n <commits made>`. Under it, one risk line per commit in the same order: `<short hash> <emoji> <Level>: <reason>`. Then the command that undoes them all: `git reset --soft HEAD~<commits made>`. Name any file that went into one commit but also held changes for another. Nothing else.
