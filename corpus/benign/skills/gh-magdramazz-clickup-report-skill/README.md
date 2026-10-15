# clickup-report — a Claude Code skill

Turn your ClickUp tickets into a **colorful, meeting-ready report in Arabic**
(an HTML page or a Markdown file). Each run asks where the tickets are (a
sprint, list, folder, space, tag or period), which status columns, and which
format. Start it with one sentence:

> make my clickup report for my meeting with my manager

Claude asks three quick click-to-answer questions:

1. **Where?** the latest sprint, another sprint, a folder, list or space, a tag,
   or a date period (the choices come live from your workspace)
2. **Which columns?** e.g. only `in progress`, or `ready for qa` + `done`
   (each shown with how many of your tickets are in it)
3. **Which format?** an HTML page, a Markdown file, or both

Then it reads every matching ticket you are assigned (the full description and
the latest comments) and writes a report organized **by sprint → by status
column**, with a short Arabic summary of each ticket, the risks, and talking
points you can say out loud.

It works for any developer, whatever language or framework you use: the skill
only talks to ClickUp.

---

## What you get

**HTML page** (right-to-left, light and dark mode, prints cleanly to PDF):
- a gradient header with the sprint / place, the chosen columns and the date
- colored KPI tiles: done, in progress, to do, at risk, total, and a progress bar
- the executive summary and the talking points side by side
- a red *Blocked / at risk* table and a count table per status column
- one card per ticket, in its ClickUp column color, with priority / due date /
  time chips and the summary

**Markdown file** (renders in VS Code, GitHub and Obsidian):

```
<div dir="rtl">
# 📊 تقرير السبرنت — Jane Doe
> السبرنت: Sprint 12 (2026-03-02 → 2026-03-15) · الأعمدة: كل الأعمدة
## 📈 نظرة سريعة          ← ✅ done · 🔵 in progress · ⚪ to do · ⚠️ at risk + 🟩⬜ progress bar
## 🧭 الملخص التنفيذي      ← > [!TIP] callout: outcomes, counts, biggest risk, what's next
## 🎤 نقاط للحديث          ← > [!IMPORTANT] callout: sentences to say in the meeting
## 🚧 العوائق والمخاطر      ← > [!WARNING] callout + table
## 🗂️ المهام حسب السبرنت
### 📁 Sprint 12 (10)
#### 🟣 Ready for qa (2)
##### [Add CSV export to the orders page](https://app.clickup.com/t/…)
`🟣 ready for qa` · 🟠 الأولوية: عالية · 📅 موعد التسليم: 2026-03-12
📝 short Arabic summary: the goal, what happened, where it stands now
</div>
```

Statuses use **your workspace's own names and order** ("ready for qa",
"in review", "blocked" and so on).

## Features

- **First-run setup:** Claude asks for your ClickUp user id, workspace id and
  API token. It checks them against the ClickUp API and saves them. If you
  don't know your user id, it looks it up from the token and asks you to
  confirm.
- **Three questions every run:** where the tickets are, which status columns,
  and HTML or Markdown. The options are loaded live from your workspace.
- **Arabic by default:** labels, layout (right-to-left) and summaries are in
  Arabic. Task names stay exactly as they are in ClickUp. Set
  `--language English` for English labels.
- **Nothing half-done:** the build refuses to write the report until every
  ticket has a summary.
- **Latest sprint by date:** it finds the sprint with the most recent start
  date that has already started. A sprint created in advance is skipped. You
  can also ask for a named sprint, or a date period ("last 14 days").
- **Real ticket summaries:** each ticket gets 2–4 sentences: what it is about,
  what happened (taken from the comments), and where it stands now. This
  works even when tickets are written in another language or use a
  user-story template.
- **Risk detection:** overdue, blocked or on-hold statuses, no update for 14+
  days, tracked time over the estimate, and blockers in comments ("can't
  test", "waiting on…"). Claude also reads the comments for QA send-backs.
- **Asks instead of guessing:** if an id, a sprint or a period is unclear,
  Claude asks.
- **Read-only:** the skill only sends GET requests, so it never changes
  anything in ClickUp.

## Install

Requirements:
- [Claude Code](https://claude.com/claude-code)
- Python 3.8+ (standard library only; nothing to `pip install`)

```bash
# all your projects (recommended)
git clone https://github.com/magdramazz/clickup-report-skill ~/.claude/skills/clickup-report

# or one project only
git clone https://github.com/magdramazz/clickup-report-skill <project>/.claude/skills/clickup-report
```

On Windows, `~` is `C:\Users\<you>`. Restart Claude Code after you install it.

## Use

Just ask:

| You say | You get |
|---|---|
| `make my clickup report` | the latest sprint, if that is your saved default |
| `report for the last sprint for my 1:1` | the latest sprint, chosen by date |
| `clickup report for Sprint 6` | that sprint (Claude asks if the name matches several lists) |
| `what did I do in the last 14 days in clickup` | a date period instead of a sprint |
| `HTML report of my ready-for-qa tickets in Sprint 7` | answers all three questions at once |
| `report on my "laravel dashboard" tag` | every ticket with that tag |
| `/clickup-report` | runs the skill directly |

Reports are saved to `~/clickup-reports/clickup-report-<date>.html` or `.md`.

### First run

Claude asks for:

1. **User id**: you can answer "I don't know"; Claude finds it from the token.
2. **Workspace id**: the first number in any ClickUp URL:
   `app.clickup.com/<workspace id>/...`
3. **API token**: in ClickUp, *Settings → Apps → API Token* (starts with
   `pk_`).

Optional: the report folder, the report language (default Arabic), and the
default scope ("latest sprint" or "ask me each time").

**To keep the token out of the chat,** run the setup yourself in a terminal.
It hides the token while you type:

```bash
python ~/.claude/skills/clickup-report/scripts/setup_config.py
```

### Change settings later

```bash
python scripts/setup_config.py --status                        # show settings (token masked)
python scripts/setup_config.py --default-scope latest-sprint   # or: ask
python scripts/setup_config.py --group-by tag                  # list | folder | space | tag | status
python scripts/setup_config.py --language Arabic
python scripts/setup_config.py --report-dir ~/Documents/reports
python scripts/setup_config.py --reset                         # forget everything
```

Or ask Claude, for example: *"change my clickup token"*.

## Privacy and security

- **Read-only:** the scripts only send GET requests to `api.clickup.com`.
- **Where the token is stored:** in your user config folder, never in a
  project or a report:
  - Windows: `%APPDATA%\clickup-report\config.json`
  - macOS/Linux: `~/.config/clickup-report/config.json` (file mode `600`)
- The token is only ever printed masked (`pk_1…AB12`).
- If `CLICKUP_API_TOKEN` is set in your environment, it is used only when no
  token is saved.
- Temporary task data is written to a temp folder and deleted after the report
  is built.

## How it works

| File | Role |
|---|---|
| `SKILL.md` | The instructions Claude follows (ask 3 questions → fetch → write summaries → build → check) |
| `scripts/setup_config.py` | First-run setup, validation, id discovery, preferences, reset |
| `scripts/fetch_tasks.py` | Lists the choices (`--discover`), shows the status columns (`--peek`), fetches your tasks and comments, flags risks |
| `scripts/build_report.py` | Renders the HTML or Markdown report from the task data and Claude's `summaries.json` |
| `scripts/clickup_client.py` | Config storage and a small read-only ClickUp API v2 client (retries, rate limits) |
| `references/clickup-api.md` | API notes and troubleshooting |

The scripts do everything that must be exact: the API calls, the counts, the
dates and the tables. Claude does what needs judgment: reading the tickets,
writing the summaries, and spotting risks that keywords miss.

## Troubleshooting

| Problem | Fix |
|---|---|
| `HTTP 401` | The token is wrong or was regenerated. Run the setup again. |
| "Workspace … is not visible to this token" | You gave a space or list id. The workspace id is the **first** number in the URL. |
| "no started sprint found" | No list has a start and due date. Ask for a date period instead, or set dates on your sprint lists. |
| Tracked time shows `—` | Your workspace does not use ClickUp time tracking. |
| A ticket is missing | It is not **assigned** to you (only watching it does not count), or it is in another sprint. |

More: [`references/clickup-api.md`](references/clickup-api.md).

## License

[MIT](LICENSE)
