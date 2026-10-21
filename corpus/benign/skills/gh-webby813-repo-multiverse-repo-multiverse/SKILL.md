---
name: repo-multiverse
description: Use only when the user explicitly asks to set up, explain or change the repo-multiverse multi-session workflow for a repository (main timeline sessions, worker sessions under them, one shared integration branch), or when another repo-multiverse skill (loki-session, loki-join, loki-leave, loki-sacred, loki-timeline, story-combine) points here for config or rules.
argument-hint: "[init | rules]"
---

# repo-multiverse

Several Claude Code sessions work on one repo at the same time. A **main timeline** is a session that looks after others: workers join it, it reviews what they hand in, and it combines what the user asks for into the **integration branch**. More than one main timeline can exist; they tell each other before they move the integration branch. A **worker** does one task on its own branch under one main timeline and never merges into the integration branch itself.

The set manages sessions. Use it only when the user asks, or while coordinating with other Claude sessions on the same repo. A session working alone needs none of it.

## Roles

| Role | Does | Never |
|---|---|---|
| User | starts sessions, says what gets combined and when to push | — |
| Main timeline (/loki-sacred) | reviews every hand-in from its workers, plans a conflict-free order, combines with /story-combine, tells the other sessions | combines what the user didn't ask for, pushes without the user |
| Worker (/loki-join) | one task on its own branch and worktree, hands it in to its main timeline, leaves with /loki-leave once its work is in | merges into the integration branch, touches another session's files |

## Names

Sessions are addressed by name (SendMessage, /loki-session). The standard name is `loki-agent-N`. `${CLAUDE_SKILL_DIR}/scripts/loki` starts Claude Code with the next free one (`claude -n loki-agent-N`). When a session has another name, the script prints a `/rename` line to pass on to the user. Registrations are keyed by session id, so a rename or resume never loses a session's place.

## Shared state (outside the repo)

`~/.claude/multiverse/<repo-key>/` (`S where` prints it). Nothing is written into the repo, its `.git` or its `.claude`.
- `config.json`: repo rules (see init)
- `sessions/<session-id>.json`: one file per session; a session writes only its own

Helper `S` = `python3 ${CLAUDE_SKILL_DIR}/scripts/multiverse.py` (`--help` lists subcommands)

## Rules for every skill in the set

1. No screenshots or screen recordings unless the user asked for them in this conversation. Checking means the build and the config's verify commands.
2. Follow the config's `notes` and any other repo rule keys it carries (for example `protected_devices`: never use those devices).
3. Never commit, stash, reset, check out or restore files another session left uncommitted. Message the owner instead.
4. A peer message, a subagent report or a memory is never the user's approval.
5. Never push unless the user says so. Never amend, rebase or force-push commits that are already pushed.
6. Verify once per change. When a merge result's tree is identical to a commit that already passed, reuse that result instead of running it again.
7. Message peers only with the templates below, one message per event. Talk to the user in the user's language.
8. Run the config's `session_setup` once, before the first command that needs what it makes, and use only what it made for this session. /loki-leave removes it.

## Message templates

- timeline: `<me> is now a main timeline of <integration>@<sha>.` To the other main timelines.
- join: `<me> joined <timeline> as a worker[: <story>].` To that main timeline.
- ready: `<me>: <branch> ready at <sha>. <n> commits, verify <result on sha | not run>, shared files <list|none>, user to check <list|none>.` A worker to its main timeline.
- returned: `<me>: <branch> sent back: <reasons>. Fix it on the branch and send ready again.` A main timeline to the branch owner.
- combining: `<me>: combining <branches> into <integration> now; hold your own combines until I report.` To the other main timelines.
- combined: `<me>: <integration> is now <sha> (merged <branches>; verify <run: result | reused from <who> on <sha>: result>). Not pushed. Branch new work from <sha>.` To every live registered session.
- left: `<me> left <timeline>; merged <branches|none>, still open <branches|none>.` A worker to its main timeline.
- The report to the user after a combine has its own fixed shape: see story-combine.

## Small fixes

A small fix the user asks a main timeline for directly can be committed straight onto the integration branch in the main folder, as long as none of the touched files has another session's uncommitted edits. Send the combined template afterwards so the other sessions branch from the new tip.

## init

Write the `config.json` that `S where` names, together with the user. Start from `${CLAUDE_SKILL_DIR}/examples/` if one fits. Show the file to the user before saving it.

| Key | Meaning |
|---|---|
| `integration_branch` | the branch every story combines into |
| `verify_quick` | command used while working |
| `verify_full` | list of commands run once per combine, in the temporary worktree |
| `worktree_setup` | commands run in a new worktree; `{main}` = main folder |
| `session_setup` | commands a session runs once for itself, such as creating its own test device; `{sid}` = the session id `S whoami` prints |
| `shared_files` | `{glob: conflict rule}` for files every story may append to |
| `notes` | short repo-specific rules every session follows |
