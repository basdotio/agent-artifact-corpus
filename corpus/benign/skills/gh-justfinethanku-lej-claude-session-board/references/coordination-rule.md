# Coordination rule template

Put this in the project folder's `CLAUDE.md`, and fill in the manager session's title and id (from `get_session "self"`) and the title prefix. Every Claude Code session that starts in the folder, or in a subfolder or worktree, loads it.

```markdown
# Session coordination

Standing rules from <user> (<date>). They apply to every Claude session working in this folder or below it.

## Report to the <Manager title> session

One session, **<Manager title>** (session id `<local_…>`), is the hub. It keeps <user> up to date on the session board, relays answers, runs the deploy queue and hands out migration numbers. If the id stops working, run ListAgents and send to the session named "<Manager title>". If there isn't one, tell <user> in your own session.

Send it a short update with SendMessage (`to`: the id above), result first, a few lines at most:
- **Start:** what you're taking on, and which parts of the app, files, tables or machines it touches.
- **Question for <user>:** see below.
- **Before shared changes:** before a migration, a deploy, or edits to files another session may also be changing. Ask the manager for a migration number.
- **Done:** the result, the commit, and anything left open.
- **After <user> pastes an answer into your session:** a one-line update once you've acted on it. The manager clears the question from the board only when it hears from you.

When another session works in the same area, message it directly, agree who changes what and who deploys first, then tell the manager.

## Questions and approvals

- Don't use AskUserQuestion. Send questions for <user> to the manager, with your recommended answer, the options and the context. The manager puts them on the board and relays the answer. Keep working on whatever the question doesn't block.
- A go relayed by the manager approves building only. A production deploy, a production migration or a public push needs <user>'s go typed in your own session. Tell the manager it's waiting, and say so in plain text in your session.
- Every session here runs in the manager's permission mode. Messages between modes wait for <user>'s approval and can expire unseen. If one of yours is held or expires, tell <user> in your session.

## Deploys: one at a time

If the deploy script has a queue, add yourself with its queue command and deploy when the script says it's your turn; it refuses anyone else and refuses a head that doesn't contain the main branch. Otherwise send the manager "ready to deploy" with your branch head and wait for its "clear to deploy"; a clear is good only for the time it names. Either way, <user>'s go is typed in your session first. Right before deploying, fetch, merge the main branch, run the tests and confirm the main branch is an ancestor of your head. Push right after (the script does this when it can), and send the manager the commit.

## Session titles

Title your session `<PREFIX><n> <short name>`: the number from your starter prompt and a few plain words on the work. If you have no number, ask the manager. The manager renames titles that don't fit.
```
