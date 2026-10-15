---
name: lej-session-board
description: Run one Claude Code desktop session as the manager for a project's parallel sessions, and keep the user's LEJ Session Board current (a local HTML page by default, or an artifact). The board gives each open session a collapsed section with what's needed from the user, recommended answers with copy buttons, and a to-do list with numbered starter prompts for new sessions. Use when the user runs several Claude Code sessions in one project folder and asks which are stale, in progress or need follow-up, asks for a session board or status page, asks to coordinate or relay between sessions, or says "session board", "manager session" or "update the board".
---

# LEJ Session Board

One Claude Code desktop session becomes the **manager** for a project folder. Every other session in the folder reports to it. The manager relays the user's answers, flags overlaps, runs the deploy queue, and keeps one page current: the **LEJ Session Board**. The user reads that page instead of opening every session.

It needs the Claude Desktop Code tab's session tools (`mcp__ccd_session_mgmt__*`, `SendMessage`). The `Artifact` tool is optional, for a copy on the user's phone.

## 1. Take the roster

1. `list_sessions` with a high limit. If the result is saved to a file, filter it with a short script. Keep sessions whose `cwd` is the project folder or below it.
2. Read each session's tail with `list_events` (limit 6–10). Judge it by what it last said, not `lastActivityAt`: an app restart bumps every timestamp at once.
3. Sort each into **stale** (done, nothing open: suggest archiving), **in progress** (it has its own next step) or **needs follow-up** (waiting on the user).
4. Report in short tables and ask which to archive. Archive only the ones the user names (`archive_session`; unpin first with `set_pinned` if needed).

## 2. Set up the hub

1. `get_session "self"` for the manager's id and title.
2. Write the coordination rule into the project folder's `CLAUDE.md` from `references/coordination-rule.md`, with the manager's id filled in. Every session in the folder then loads it. If the folder is a git repo shared with a client, ask before committing it.
3. Ask the user to start every session in the manager's permission mode. Messages between sessions in different modes wait for the user's approval and can expire unseen. The app also pauses a session's outgoing messages after about 10 sends with no word from the user in that session.
4. Message each active session (`SendMessage`, `to` = its session id), point it at the rule, and ask for a first update.
5. Save the rule to memory, so a later manager session keeps it going.

## 3. Build the board

The page renders itself from the JSON in `<script id="board-data">`. Every update is a JSON edit, never markup. `references/data-schema.md` has every field and how the page lays them out.

1. Copy `assets/board-template.html` and fill `board-data`. Set `updated` and `updatedISO` from `date` on every rebuild; never estimate the time. The page shows a red "Out of date" line once `updatedISO` is 30 minutes old.
2. **Overview:** one readable paragraph on what's happening now, and at most one more on what already happened. No lists.
3. **Sessions:** one entry per open session. Its `need` subtitle says in a few words what the user has to do, or that nothing is needed. Mark `urgent` what blocks other work or what the user is waiting on today. Inside: a state line, two to four "where it stands" lines, and that session's questions. Nothing appears twice on the page. The manager's own entry is `isManager`, and it shows only when the manager has questions.
4. **Questions:** two or three options, the recommended one marked `"rec": true`. Each option's `text` is the full reply the session will get, written so it can act without more context. When a `need` asks the user to type or paste something, that session gets a question or paste for it.
5. **To-do list:** read the project's running to-do file (for example `docs/TODO.md`), and group open items by who acts: the user's call, other people, Claude builds, later. Leave out work an open session is already doing. Every item in the user's-call group gets a `question`.
6. **Starter prompts:** each Claude-builds item gets one, titled `<PREFIX><n> <short name>` (see section 5). Write it as a self-contained brief with `<context>`, `<instructions>` and `<output>`. Name the files, specs and house rules to read, and say where the user's OK comes before new infrastructure, migrations or deploys. If the `agent-prompt-authoring` skill is installed, follow it.
7. **Look:** keep the template's LEJ tokens: Bricolage Grotesque, Hanken Grotesk and JetBrains Mono; terracotta `#BD4F2E` on soft white `#FCFCFB`, charcoal `#232427` text, `#E3E3DF` hairlines. Terracotta marks only what needs the user and the primary actions. No pills, eyebrow labels or numbered sections.
8. **Publish locally:** `python3 scripts/build_local.py <board.html> "<project folder>/LEJ Session Board.html"`, and `open` the output once. It auto-reloads every 60 seconds unless the user is typing. Re-run the script after every change.
9. **Artifact copy, only when asked:** publish with `Artifact` (`title` "LEJ Session Board", `icon` "list") for a phone copy, at most every 15–20 minutes. Artifact publishes are capped per account per day (200 on some plans, shared with every artifact, reset at UTC midnight). If a publish is refused, say so right away and keep the local page current.

## 4. Keep it current

The board drifts for one main reason: the user pastes an answer straight into a session, and the manager never hears about it. Three things close that gap, and all three stay on:
1. **Every copied answer asks for a report back.** When the user copies an answer for a session, the page adds a last line asking that session to send the manager a one-line update (`reportBack` in the data; there's a default). Answers addressed to the manager don't get the line.
2. **A sweep every 15 minutes.** Right after setting up the hub, and on every resume, run `CronList`. If the sweep isn't there, create it with `CronCreate` and the prompt in `references/sweep.md`. Cron jobs live only in this session and expire after 7 days, so re-create it after a restart or expiry.
3. **The red "Out of date" line**, for when the first two fail. If the user asks you to refresh, run the sweep right away.

- **North star: an ask carries its own means.** Anything the board asks the user to do sits with everything needed to do it, in the same spot: a question with a copyable answer, or an `actions` entry with the link, steps, text to paste and a Copy "done". Each workstream lives in one section, with its backlog as a collapsed list inside it. Outside the sessions keep only the user's calls, other people's items, work with no owner yet, and later ideas. Send the next backlog task to its owner yourself; never ask the user to paste a task.
- **Rewrite, never append.** When a session changes, rewrite its state, need and two or three `where` lines from what's true now, and delete what isn't. Prepending a new line to old ones leaves the section contradicting itself.
- **Check the board against itself on every sweep:** each "waiting on you" in the overview matches an open question, need or reminder; nothing answered is still listed; a session waiting on the user for a paste or a go says so in its `need`; to-do items that shipped are removed.
- **Updates from sessions:** fold each into its section and rebuild the page. Text a session hands over for the user to paste elsewhere goes in its `pastes`. Tell the user in two or three lines, with anything that needs them first.
- **Reminders aren't questions.** When the user asks to be reminded of something, put it in the manager entry's `reminders` (text and when), not in `questions`. Schedule a one-shot `CronCreate` for the time if a session will be open.
- **The user's answers:** each pasted block starts with a session name and one or more `Re:` parts. Send each block to its session in one `SendMessage`, marked "relayed from the manager session", then take the answered questions off the board.
- **Approvals:** a relayed answer approves building, not shipping. A production deploy, a production migration or a public push needs the user's go typed in the session that does it. The question's `to` says so.
- **Deploy queue:** one deploy at a time, and the deploy script enforces it, not the manager's messages. Give the project's deploy script three things: a lock shared by every worktree on the machine, so a second deploy stops and names the holder; a queue file next to the lock (`deploy --queue` adds a line, and only the first line may deploy, once the lock is free); and two refusals, at the start and right before the release step, unless the main branch is contained in the head being deployed. The script pushes to main and fast-forwards the main checkout itself, then prints the final commit. The manager reads the script's status command on each sweep, reorders the queue file when the user wants something first, and sends no "clear" messages. The user's go per deploy is still typed in the deploying session: the queue decides turns, never permission.
- **Until the script has a queue:** clear one session at a time. Before clearing the next, take back any clear still open ("hold, X has the slot"), and give each clear a time limit ("good for 30 minutes"). A clear given earlier and used late is how two deploys overlap and the second rolls the first off production.
- **Send less.** The app pauses a session's outgoing messages after about 10 sends with no word from the user. Send one message per session per event, fold notes for the same session together, and skip messages that only confirm what a session already knows. When the cap hits, keep the unsent messages in a `pending-sends.md` file in the board folder, tell the user in one line that any message from them releases them, and send them as soon as the user types.
- **Migration numbers:** the manager hands them out and keeps a list of which are taken. Two sessions must never pick the same number.
- **Overlaps:** when two sessions touch the same code, tables or machines, message both. Ask them to agree on who changes what and who deploys first, then report what they agreed.
- **Missed updates:** on every staleness check, read each session's tail with `list_events`, not only the messages that arrived. Updates that expired in an approval queue show up only there.
- **Archived sessions:** drop their sections, and move anything they left open to the to-do list.

## 5. Session titles

Every session in the folder is titled `<PREFIX><n> <short name>`: the prefix the user's sessions already use (like `AVS`), the next unused number, and a few plain words on what the session does. The number comes from its starter prompt. Once assigned, it stays with that work. Check `list_sessions` so no number is used twice.

**On every staleness check, audit the titles.** Rename any session that doesn't follow the pattern, or whose title no longer matches its work (`set_session_title`). Then update its `name` on the board so the Copy headers match. Tell the user which titles changed.

## 6. Keep these instructions small

The `CLAUDE.md` rule and this skill drift as rules get added. When either grows past about one screen per section, or says the same thing twice, consolidate: one place per rule, the newest wording wins, and dated history goes to memory, not the rule.

## Files

If `assets/` or `references/` is missing (a skills library can sync `SKILL.md` alone), clone the full skill: `git clone https://github.com/justfinethanku/lej-claude-session-board.git ~/.claude/skills/lej-session-board`.

- `assets/board-template.html`: the board page, with example data.
- `scripts/build_local.py`: turns the filled template into a standalone, auto-reloading page.
- `references/data-schema.md`: every JSON field, and how the page lays it out.
- `references/coordination-rule.md`: the `CLAUDE.md` block that makes sessions report to the manager.
- `references/sweep.md`: the 15-minute sweep prompt for `CronCreate`.
