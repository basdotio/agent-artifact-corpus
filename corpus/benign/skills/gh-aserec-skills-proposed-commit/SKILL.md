---
name: proposed-commit
description: Commit with a chat-proposed message. Use when asked to commit, reuse that message, or draft one, confirm it, and commit. Not for a message-only ask.
version: 1.0.0
metadata:
  author: Danel Ceresa <dceresa1988@gmail.com>
  version: 1.0.0
  tags:
    - git
    - commits
---

# Proposed commit

## Purpose

Use this when the user asked to create a commit. Commit with the message already proposed for the current diff. When no such message exists, draft one from that diff and the repo commit rules, show it to the user, and commit only after the user approves it.

The work is done when `git status` shows the new commit, or the turn stopped on a check below or on a pending approval and no commit was created.

## Instructions

Run this only after the user asked to commit. A request to draft a message and stop is not this skill.

### 1. Take the proposed message

Search the current request, then earlier turns from newest to oldest. Copy a message only when it was offered as the commit message for the changes still in the worktree:

- The user wrote the message in this request.
- The user pointed at an earlier proposal ("commit that", "use that message").
- The latest proposal was offered for this diff and the user did not reject it.

Skip a proposal that describes a change already committed, or a diff the worktree no longer has. A summary that was never offered as the commit message does not count.

Done when the message is copied verbatim, or the search records that none exists.

### 2. Draft a message when none exists

Skip this step when step 1 copied a message. Do not rewrite a copied message.

Run these commands in parallel:

- `git status`
- `git diff` and `git diff --staged`
- `git log -15 --oneline`

Read the commit conventions in the repo's contributing or engineering guide before writing the subject. Find them from `AGENTS.md`, `CLAUDE.md`, or `CONTRIBUTING.md`. Apply them:

- Subject is `type(scope): imperative summary`, at most 72 characters, with no trailing period.
- Types are `feat`, `fix`, `chore`, `docs`, `test`, `refactor`. Scope is the package or area the guide names, or the one the last 15 subjects use.
- Add a bullet body only for a reason the diff does not show. Five bullets or fewer. Add a ticket id only when the guide asks for one. No `Co-Authored-By` trailer and no agent attribution.
- When the repo has no such guide, use the same Conventional Commits shape and match the last 15 subjects.

Write the draft in a fenced block and ask the user to approve it or change it. End the turn there. Do not commit a draft the user has not approved.

When the user approves, go to step 3 with that draft. When the user edits it, the edited text is the message. When the user rejects it, write a new draft and ask again.

Done when the user approved the fenced message, and it follows the rules above.

### 3. Decide whether the commit is allowed

Use the status from step 2, or run `git status` when step 2 was skipped.

Stop with no commit when any of these hold:

- The worktree and the index have no changes.
- A path is a secret: a dotenv file other than an example template, a credential file, or anything inside a secrets directory.
- The message and the diff name different changes, and no path subset is clear.

Do not update git config. Do not push. Do not amend in this step. Do not pass `--no-verify` or `--no-gpg-sign`.

Done when the commit is allowed, or the reply names the check that stopped it.

### 4. Stage and commit

Stage the paths the message describes. Leave unrelated paths and every secret path unstaged. When the diff is one change, stage all of its non-secret paths.

Commit with the message from step 1 or step 2. Pass it through a quoted heredoc so the body stays intact. Add no trailer.

```bash
git commit -m "$(cat <<'EOF'
type(scope): imperative summary

- reason the diff does not show
EOF
)"
```

Run `git status` after the command returns.

Done when `git status` shows the new commit and a clean result for the paths it included, or the command failed and step 5 runs.

### 5. Recover a failed commit

Read the hook or command output.

- A proposed message that fails validation stays as written. Report the error and stop. Do not replace it.
- An approved draft that fails validation gets one corrected draft. Show it and ask for approval again before a new `git commit`. Do not amend a commit that failed.
- When a hook edits files after a successful commit, amend only if the user asked to commit, HEAD was created in this turn, and the commit is not pushed. Otherwise leave the hook edits unstaged and say so.

Done when `git status` shows one successful commit, or the reply quotes the error and states that nothing new was committed.

## Examples

### Message already proposed

```text
Input. An earlier turn fenced this message, and the user says "commit that":

feat(ui): add notification centre

- header bell opens the centre for the mock feed

Result. git commit uses that subject and bullet unchanged. No second message is drafted.
```

### No message yet

```text
Input. The user says "commit". The chat has no commit message. git diff adds a logout button on the account page.

Result. The agent fences a draft and asks for approval. No git commit runs yet:

feat(web): add account logout

- click clears the local session and returns to login

The user replies "ok". git commit uses that draft unchanged.
```

### Nothing to commit

```text
Input. The user says "commit". git status prints "nothing to commit, working tree clean".

Result. No git commit runs. The reply says the worktree is clean.
```

## Prerequisites

The directory is a git repo, and the user asked to commit. Read the repo's commit conventions when drafting. No extra tools or keys.

## Limitations

This skill creates one new commit for the current diff. It does not push, open a merge request, or amend an older commit. A request to draft a message and stop stays with the message skill. When the harness blocks `git commit`, report the message and stop.

## Troubleshooting

**The commit command returns an error.** Follow step 5. A failed commit is never amended. Quote the hook output in the reply.

**A secret path is staged.** Unstage it, leave it out of the commit, and say which path was excluded. Do not commit that path.

**The proposed message fails validation.** Keep the user's message. Report the error. Do not silently rewrite a message the user already accepted.

**The draft no longer matches the diff.** Discard it and run step 2 again against the current `git diff` before committing.
