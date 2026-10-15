---
name: workspace-switch-recovery
description: Recover Claude Code desktop sessions, sidebar folders, scheduled tasks (Routines) and published artifacts after switching Claude account, plan or workspace (Pro/Max to Team, plan lapsed, same login in two organizations). Use when the Code tab sidebar is empty after a switch, "Import Claude Code CLI Sessions" says "No CLI sessions to import", claude --resume works but the desktop sidebar is empty, routines stopped running, sidebar folders are gone, old artifact links fail, or claude -p returns "Your organization has disabled Claude subscription access for Claude Code" (oauth_org_not_allowed). Also use BEFORE switching to back up transcripts and raise cleanupPeriodDays. Unofficial, not affiliated with Anthropic.
license: MIT
compatibility: Claude Code desktop app on macOS (Windows/Linux untested); needs the transcripts in ~/.claude/projects and python3. Tested with desktop build 2.31226.x, Claude Code 2.1.284-2.1.295, 2026-10.
metadata:
  tested-on: "2026-10-10"
  homepage: "https://github.com/schneidermilanistvan-hash/claude-code-account-switch-recovery"
---

# Workspace switch recovery

Unofficial; not affiliated with or endorsed by Anthropic.

The user switched Claude plan, account or workspace and lost things in the desktop app's Code tab.
Their conversations are almost always still on disk. Your job: confirm that, then put sessions,
folders, routines and artifacts back in the workspace they use now, without destroying anything.

Full guide: https://github.com/schneidermilanistvan-hash/claude-code-account-switch-recovery (README and `docs/`).

## Rules

1. **Back up before any change** (step 0). No exceptions.
2. **Read-only first.** Run `scan`, `sessions`, `plan`, `folders`, `tasks`, `artifacts` and the
   `import` dry run. Show the user the plan.
3. **Ask before every side effect:** `import --apply`, opening any `claude://` link, creating folders
   or scheduled tasks, publishing artifacts, editing `settings.json`. Each import opens a window and
   starts a ~330 MB background process.
4. **Never delete or archive sessions** in either workspace. Since Claude Code 2.1.284, deleting a
   session from the sidebar deletes its transcript. Never delete `local_*.json`, `deleted_*` or
   transcript files.
5. **Never edit `claude_desktop_config.json` or the session store by hand** while the app runs.
6. **Never switch the app's workspace during an import.** It fails the import and stops running
   sessions, including possibly this one.
7. **Read every artifact before re-publishing it.** Old pages can contain other people's data. Ask
   the user about anything personal.
8. **Privacy:** transcripts, backups, the app log and toolkit output can contain API keys, tokens,
   passwords and private messages. Never upload, post or commit them, and do not paste account ids,
   org ids or full paths into anything public.
9. **Never suggest deleting the old account** while its login is also the user's Team seat. The old
   workspace is the only place the old session list and artifact URLs live. The one-way
   "Use your organization account only" migration also closes it: mention it only as a step after the
   recovery.
10. **Follow the organization's policies.** If an admin disabled deep links, subscription access or
    a connector, say so and stop; do not work around it. If either workspace belongs to an employer
    or school, have the user confirm its rules allow copying sessions or re-publishing pages.

## Find the toolkit

`ccrecover.py` is a single standard-library Python file. Use the first that exists:

1. `${CLAUDE_PLUGIN_ROOT}/tools/ccrecover.py` (installed as a plugin; if the variable is not
   expanded in your shell, use 2)
2. `find ~/.claude/plugins -name ccrecover.py -path '*workspace-switch-recovery*' 2>/dev/null | head -1`
3. `tools/ccrecover.py` in a clone of the repository
4. Otherwise ask the user, then:
   `git clone https://github.com/schneidermilanistvan-hash/claude-code-account-switch-recovery ~/ccrecover-repo`

Shell state does not carry over between your tool calls, so start **every** shell call with
`CCR=<absolute path to ccrecover.py>; W=~/ccrecover-work; mkdir -p "$W";` and run
`python3 "$CCR" <subcommand>`. Write every output file into `$W`, never into the user's project or
a git repository: outputs hold session ids, artifact URLs and possibly secrets. Global options
`--store DIR` and `--projects DIR` go before the subcommand (needed on Windows and Linux).
Self-test: `python3 "$(dirname "$CCR")/test_ccrecover.py"`.

## Step 0: Back up and raise retention

```bash
B=~/claude-backup-$(date +%Y%m%d-%H%M%S); mkdir "$B" && echo "backup: $B"
for p in ~/.claude/projects ~/.claude/file-history ~/.claude/scheduled-tasks ~/.claude/settings.json \
    ~/Library/Application\ Support/Claude/claude-code-sessions \
    ~/Library/Application\ Support/Claude/claude_desktop_config.json; do
  if [ -e "$p" ]; then cp -Rp "$p" "$B"/ || echo "COPY FAILED: $p"; else echo "not present: $p"; fi
done
du -sh "$B"/*
```

Stop if any line says `COPY FAILED`. Tell the user the backup holds full transcripts, which can
contain secrets, and must stay private.

Propose adding `"cleanupPeriodDays": 3650` to `~/.claude/settings.json` (merge, do not overwrite).
Terminal and `claude -p` transcripts are otherwise deleted after 30 days. Desktop-started sessions are
kept at any age since Claude Code 2.1.248 unless managed settings set `cleanupPeriodDays`.

## Step 1: Diagnose

```bash
python3 "$CCR" scan
```

- More than one `<accountUuid>/<orgUuid>` folder, one with the user's sessions: this is the
  workspace split. The full one is `<old>`; the one the app writes to now is `<new>`.
- Only one folder and no transcripts: different problem (retention, new machine). Say so and stop.
- `ls -tr ~/Library/Logs/Claude/main*.log | while read -r f; do grep -h "CCD-SessionRecovery" "$f"; done | tail -3` shows why the app's own
  import found nothing (`skippedFiltered` = already known to some workspace).

## Step 2: Sessions

```bash
python3 "$CCR" sessions --from <old> --limit 30
python3 "$CCR" plan --from <old> --to <new> --folders --recent 10 --out "$W/ids.txt"
python3 "$CCR" import "$W/ids.txt" --to <new>                                   # dry run
```

Show the user the count and ask which sessions they want (folders + recent is a good default; `--all`
for everything). Then ask them to **show the target workspace in the app and not touch it**, and with
their yes:

```bash
python3 "$CCR" import "$W/ids.txt" --to <new> --apply --batch 10 --pause 20
```

Single session, manual: `open "claude://resume?session=<cliSessionId>"` (tested). The documented
`claude --desktop --resume <cliSessionId>` (Claude Code 2.1.285+) opens the same link but needs a
working CLI subscription login and is untested across workspaces. Success = a new
`local_<cliSessionId>.json` in the `<new>` folder. Tell the user: bypass-permission sessions come back
as accept-edits; the app trusts each session's folder without asking; re-running is safe.

If you are running inside the desktop app yourself, each import steals focus. Prefer the user running
the `--apply` command in a terminal.

## Step 3: Folders

```bash
python3 "$CCR" folders --from <old> --to <new>
```

Recreate the folders in the printed order. If the desktop app's sidebar tools are available to you
(create a sidebar group, move sessions), use them after the user agrees; otherwise give the user the
list to do by hand.

## Step 4: Scheduled tasks

```bash
python3 "$CCR" tasks --from <old>
```

For each recurring task, enabled or not (ask about disabled ones: a task may have been switched off
because a cron or launchd job replaced it): recreate it in `<new>` with the same schedule and the prompt from
`~/.claude/scheduled-tasks/<id>/SKILL.md` (use the app's create-scheduled-task tool if available).
Skip finished one-offs. Ask whether any task was replaced by a cron or launchd job meanwhile; keep
only one. Tasks fire only while the app shows their workspace, is open, and the computer is awake.

## Step 5: Artifacts

```bash
python3 "$CCR" artifacts --json > "$W/artifacts.json"
```

Separate originals from re-publishes by first-publish date. For each original:

- Source on disk: read it, then re-publish from `<new>` after the user agrees.
- Source gone: `python3 "$CCR" rebuild-file --transcript <first-publish>.jsonl --path <recorded path> --out <file>`.
  It starts from the newest `~/.claude/file-history` backup before the cutoff and replays the
  `Write`/`Edit` calls after it (about 9 of 23 lost pages came out exact this way). If it lists
  `Bash` commands that touched the file, re-run them on a scratch copy and compare each output with
  the recorded output. Check the result against what the original session says about the page.
- Still missing: search transcripts for an earlier artifact `read` result with the full HTML; ask
  whether another machine exists and search its transcripts by page title; for script-built pages,
  re-run the script on its saved input.
- After publishing: build an old-URL to new-URL map and rewrite links in the user's files, at the
  source of generated pages, and in `~/.claude/scheduled-tasks/*/SKILL.md`. Show the diff first.

New URLs are unavoidable. Old ones stay with the old workspace.

## Step 6: Headless 403, other machines, connectors

- `claude -p "say ok"` returning `oauth_org_not_allowed`: first have the user run `claude auth login`
  in a real terminal (their own sign-in; never do it for them) and pick the new workspace, then
  re-test `claude -p`. The CLI often still holds the old workspace's token, and `claude auth status`
  can name the new workspace anyway, so the re-test is the proof. Only if the 403 survives a fresh
  login: an Owner must enable Claude Code subscription access, or the user sets up a Console API key.
- Ask about other machines. Each needs steps 0 to 5 and its own `claude auth login`.
- Remind the user to reconnect connectors and sign the Chrome extension in to the new workspace.

## Report

End with: sessions imported / failed, folders recreated, tasks recreated, artifacts recovered by
method, links rewritten, what is left for the user (403, connectors, other machines), and anything
that could not be recovered (missing transcripts).
