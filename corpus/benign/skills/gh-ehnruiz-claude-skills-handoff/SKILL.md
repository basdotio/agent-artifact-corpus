---
name: handoff
description: Write a handoff note so a fresh session can continue this one's work. Use when the user says to hand off, wrap up, or save progress for later, or when a long session is about to end with work still open.
argument-hint: 'What the next session will focus on'
disable-model-invocation: true
---

# Handoff

Write a note that lets a session with no memory of this one carry on without asking what happened.

**Project copy first.** If the repository has its own `.claude/skills/handoff/SKILL.md`, read it and follow it instead of this file. A skill installed for all your projects outranks a project skill with the same name, so without this step a repository's own version of this skill would never run.

## Where

Save it to `~/.claude/projects/<project slug>/handoffs/<YYYY-MM-DD>-<topic>.md`, the topic in two to four kebab-case words. The slug is Claude Code's own folder name for the main checkout's path (every character that is not a letter or digit becomes `-`), so a session in a git worktree saves beside the others; `python3 hooks/handoff_notice.py --print-dir` from this repository's install prints it. Keep it outside the repository so it never lands in a commit, and outside any session scratch directory, which the next session cannot see. Tell the user the path.

## What goes in it, in this order

1. **Goal**: one or two sentences on what the work is for.
2. **State**: what is done, and how each "done" was verified (the command and its result, the PR, the commit).
3. **Decisions**: what was decided and why, so the next session does not reopen it.
4. **Open questions**: what is still undecided, and who decides it.
5. **Next steps**: in order, each one concrete enough to start on.
6. **Useful skills and agents**: which ones fit the next steps.

Put Goal and State first; tools that preview a handoff often show only its opening.

## Rules

- Point to issues, PRs, commits and files by number, hash or path. Do not copy their content in.
- Leave out secrets: API keys, tokens, webhook URLs, passwords, personal data.
- If the user passed an argument, shape the note around that focus.
