# The 15-minute sweep

Create it with `CronCreate` in the manager session, `recurring: true`, cron `7,22,37,52 * * * *` (off the :00 and :30 marks). It runs only while the manager is idle, lives only in this session, and expires after 7 days. Run `CronList` on every resume, and re-create it if it's missing. Fill in the folder and the title prefix.

```text
Board sweep (standing, every 15 min). Keep the LEJ Session Board true without the user asking:
1. ReadNotifications, and handle any session messages first.
2. list_sessions. For every session in <project folder> (skip any the user keeps out of the loop) whose lastActivityAt is newer than the board's updatedISO, read its last ~15 events with list_events. Look for: answers the user typed or pasted straight into the session (clear that question from the board), deploys started or finished, new questions, new blockers, done or idle states. Add any session that isn't on the board yet (and give it a <PREFIX> number if it has none). Check titles fit `<PREFIX><n> <short name>`.
3. For each session that changed, rewrite its entry (never prepend): state, need, two or three current `where` lines, open questions only. Then check the overview against the open questions and needs, and remove shipped to-do items. Update only what changed: state, need, where, questions, urgent and tone. Recompute the overview if a priority changed. Always set updated (from `date '+%A, %b %-d, %Y, %-I:%M %p ET'`) and updatedISO (from `date -u +%Y-%m-%dT%H:%M:%SZ`), even when nothing else changed, then rebuild the local page.
4. Reply to the user only if something needs them (a new question, a finished deploy, a failure). Otherwise stay silent: one line at most, like "Board checked, no changes."
```

`lastActivityAt` jumps for every session when the app restarts. If every session looks active at once, judge each by what its tail says, not by the timestamp.
