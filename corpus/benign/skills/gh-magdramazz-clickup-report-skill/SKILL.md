---
name: clickup-report
description: Turns the user's own ClickUp tickets into a colorful, meeting-ready report in Arabic, as a Markdown file or an HTML page. Every run it asks three things - where the tickets are (the latest sprint, another sprint, a list, a folder, a space, a tag, or a date period), which status columns inside it (to do, in progress, ready for QA, done ...), and whether the result should be Markdown or HTML. Then it reads every ticket's description and comments and writes a short Arabic summary of each one, plus an executive summary, blockers and risks, counts, and talking points. The first time it runs, it asks for the ClickUp user id, workspace id and API token, checks them, and saves them. Use this skill whenever someone wants a summary, recap, status update or report of their ClickUp tasks or tickets - for a meeting with a boss or manager, a 1:1, a standup, a sprint review or a weekly update. Also use it for requests like "what did I do this sprint", "summarize my tickets", "prepare my task report" or "تقرير مهامي", even when the word "report" is not used.
---

# ClickUp report

Build a colorful, meeting-ready report of the user's ClickUp tickets, **in
Arabic**, as a Markdown file or an HTML page. The user reads it before (or
shows it in) a meeting with their boss, so every ticket must have a real,
short summary.

The bundled scripts do the API work, the counts and the layout, so the numbers
are exact and every run looks the same. You do four things: ask the three
questions, read the tickets, write the summaries, and check the result.

**Ask; do not guess.** If something is unclear, ask. Never invent an id, a
place, a status, a date or a number. A wrong report in front of a boss is worse
than a question now.

All scripts are in `scripts/` inside this skill's folder. Run them with
`python` (or `python3` if `python` is missing). They use only the standard
library. Each script prints one JSON object. Read `ok`, `error`, `problems`
and `warnings` before you continue. Put every intermediate file (`tasks.json`,
`summaries.json`) in a temporary or scratch folder, never in the user's project.

## Step 1 — Is the skill set up?

```bash
python scripts/setup_config.py --status
```

Exit code 0: configured, go to Step 3. Exit code 2: first run, go to Step 2.

## Step 2 — First run: ask, check, save

Ask for all three values in **one** message, and say where to find each one:

- **ClickUp user id**: a number. ClickUp does not show it clearly, so the user
  may answer "I don't know". You will then look it up from the token (see
  below) and ask them to confirm it.
- **Workspace (team) id**: the first number in any ClickUp URL:
  `app.clickup.com/<workspace id>/...`
- **API token**: *Settings → Apps → API Token*. It starts with `pk_`.

Optional, with defaults: the report folder (default `~/clickup-reports`).
Save the language as Arabic.

Tell the user that a token pasted into chat stays in this conversation. Offer
the private option: they run `python "<skill folder>/scripts/setup_config.py"`
in their own terminal (hidden input) and come back and say "done".

Save the values, passing the token through stdin:

```bash
printf '%s' '<token>' | python scripts/setup_config.py --user-id <id> --team-id <id> --token-stdin --language Arabic [--report-dir <dir>]
```

- **`problems` is not empty**: show them and ask what is right. Re-run with
  `--force` only if the user confirms the values anyway.
- **HTTP 401**: the token is wrong or revoked. Ask for a new one.
- **The user does not know an id**:
  `printf '%s' '<token>' | python scripts/setup_config.py --discover --token-stdin`.
  Show the token owner and the workspaces, and let the user pick, even when
  there is only one option.

Never repeat the token in chat, never write it into a file, never put it in
the report.

## Step 3 — Ask the three questions (every run)

Ask these on **every** run, with the `AskUserQuestion` tool, so the user
clicks instead of typing. Skip only a question the user already answered in
this request (for example "HTML report of my ready-for-qa tickets in Sprint 7"
answers all three).

### Question 1 — Where are the tickets?

First load the real choices:

```bash
python scripts/fetch_tasks.py --discover
```

It prints `latest_sprint`, the newest `sprints` (with dates and space),
`spaces` (with their `tags`), `folders`, and the other `lists`.

Then ask one question, header `Scope`. The options:
1. **Latest sprint** — put its real name and dates in the label or
   description (e.g. "Sprint 7 (2026-09-21 → 2026-10-04)").
2. **Another sprint** — name the previous one or two sprints in the description.
3. **A folder / list / space** — e.g. Backlog, Bugs.
4. **A tag or a date period** — e.g. a tag of the user's, or "last 14 days".

"Other" lets the user type anything. When the answer is a *kind* ("another
sprint", "a folder"), ask a second click question with the concrete names from
`--discover` (up to 4 options, newest or most relevant first). Two names can be
the same in different spaces (for example two "Backlog" folders): then show the
space in the description, and pass the **id** to the script.

Map the answer to one scope flag:

| Answer | Flag |
|---|---|
| Latest sprint | `--sprint latest` |
| A sprint | `--sprint "<name or id>"` |
| A list | `--list "<name or id>"` |
| A folder (all its lists) | `--folder "<name or id>"` |
| A space | `--space "<name or id>"` |
| A tag | `--tag "<tag name>"` |
| A date period | `--days N` or `--since YYYY-MM-DD [--until YYYY-MM-DD]` |

A period can be added to a list, folder, space or tag to keep only the done
tickets closed in that period (open tickets are always kept). A relative
period ("this week") becomes exact dates; repeat the dates in your answer.

### Question 2 — Which columns? and Question 3 — Which format?

Load the status columns of that scope, with the user's ticket count in each:

```bash
python scripts/fetch_tasks.py <scope flag> --peek
```

- `total` is 0: tell the user there are no tickets of theirs there, and go
  back to Question 1. Do not build an empty report.
- `bad sprint` / `bad list` / `several ... match`: show the message and ask
  which one they mean. Do not pick one yourself.

Then ask **both** questions in **one** `AskUserQuestion` call:

- **Columns** (header `Columns`, `multiSelect: true`): the first option is
  "All columns (N tickets)". The other options are the columns from
  `status_columns`, in that order, each with its count
  (e.g. "ready for qa — 2 tickets"). Only 4 options fit: when there are more
  columns, list all of them in the question text and say the user can type
  several names in "Other".
- **Format** (header `Format`): "HTML page" (colorful cards, opens in any
  browser, easy to print to PDF) and "Markdown file" (colorful emoji, tables
  and callouts, good in VS Code, GitHub or Obsidian). A third option, "Both",
  builds the two files from the same summaries.

If the user picks "All columns", do not pass `--statuses`.

## Step 4 — Fetch the tickets

```bash
python scripts/fetch_tasks.py <scope flag> [--statuses "ready for qa,in progress"] --out <tmp>/tasks.json
```

Status names are the ClickUp names from `--peek` (any case), joined by commas.
The script reads every ticket of the user in the scope, its full description,
and the latest comments (GET requests only; nothing in ClickUp changes).

- `NOT_CONFIGURED`: go back to Step 2.
- HTTP 401/403: tell the user and stop. Do not retry with other values.
- A warning "no task of the user in status column ...": tell the user.
- When `scope.other_latest_sprints` is not empty, say in one line which sprint
  you reported on, and that the other one is not included.

## Step 5 — Read every ticket and write the summaries (in Arabic)

Open `<tmp>/tasks.json`. For **every** ticket, read the whole `description` and
all of its `recent_comments`. Then write `<tmp>/summaries.json`, all text in
**Arabic** (simple, clear Modern Standard Arabic):

```json
{
  "executive_summary": ["...", "..."],
  "talking_points": ["...", "..."],
  "tickets": { "<task id>": "...", "<task id>": "..." },
  "extra_risks": [ { "id": "<task id>", "reason": "...", "date": "YYYY-MM-DD" } ]
}
```

- **`tickets`** — one entry for **every** task id in the JSON. 2–4 sentences:
  1. **ما المشكلة أو الهدف** — what the ticket is about, in business terms.
  2. **ما الذي حدث** — what was done, found or decided (comments often hold
     this: a fix, "no bug", a decision in a meeting).
  3. **أين تقف الآن وما التالي** — e.g. waiting for QA, QA asked for changes,
     blocked by something, done and deployed.

  Say who did something only when a comment shows it. When the description and
  the comments are both empty, write
  "لا يوجد وصف أو تعليقات على هذه المهمة في ClickUp." Do not build a story from
  the title. Keep technical terms, product names, ids and code names in their
  original form (e.g. `QA`, `API`, `seller`, `bulk import`).
- **`executive_summary`** — 3–5 bullets: the most important delivery, the
  counts, the biggest risk, and what comes next. Lead with outcomes
  ("تم إصلاح فرق السعر بين لوحة التحكم والمتجر") not activity ("عملت على مهام").
- **`talking_points`** — 3–5 short sentences the user can say out loud in the
  meeting. When there is a blocker, one of them asks for help or a decision.
- **`extra_risks`** — the script flags risks by keywords (overdue, blocked
  status, no update for 14 days, over estimate), so it misses risks written in
  other words: QA sent the ticket back with failing cases, a comment says the
  work cannot be tested, a dependency on another team. For each open ticket
  where the comments show such a risk, add one entry with a short Arabic reason
  and the comment's date. Leave the list empty if there is none.

Base every sentence on the JSON. If a number is not there, leave it out. Task
names are never translated — the report shows them exactly as in ClickUp.

## Step 6 — Build the report

```bash
python scripts/build_report.py <tmp>/tasks.json --summaries <tmp>/summaries.json --format html
python scripts/build_report.py <tmp>/tasks.json --summaries <tmp>/summaries.json --format md
```

Run the line for the chosen format (both lines for "Both"). Without `--out`,
the file goes to the saved report folder as `clickup-report-<date>.html|.md`.
Add `--group-by folder|space|tag|status` only if the user asks for another
grouping (the default groups by sprint/list, then by status column).

- **Exit 5, `SUMMARIES_INCOMPLETE`**: `missing_ids` lists the tickets without
  a summary, or the executive summary / talking points are empty. Write them
  and build again. Never pass `--allow-missing` for the final report.
- `unknown_summary_ids` is not empty: you used a wrong id. Fix it.
- The labels are Arabic and right-to-left when the config language is Arabic
  (`setup_config.py --status` shows it). If it says English, run
  `python scripts/setup_config.py --language Arabic` once, then fetch again.

What the report looks like:
- **HTML**: a gradient header with the scope, colored KPI tiles (done, in
  progress, to do, at risk, total), a progress bar, the executive summary and
  talking points side by side, a red risk table, a count table per column,
  then one card per ticket, colored with the ClickUp column color, with
  priority / due date / time chips and the summary. Right-to-left, light and
  dark mode, prints cleanly to PDF.
- **Markdown**: emoji status markers (✅ done, 🔵 in progress, 🟣 review/QA,
  🔴 blocked, ⚪ to do), priority emoji, a 🟩⬜ progress bar, GitHub callouts
  (`[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`) and centered tables, wrapped in
  `<div dir="rtl">`.

## Step 7 — Hand it over

Reply (in the user's language) with:
- the report path(s); for HTML, offer to open it in the browser
  (`start "" "<path>"` on Windows, `open` on macOS, `xdg-open` on Linux)
- the counts (done, in progress, to do, at risk)
- the executive summary bullets
- any `warnings` from the fetch

Do not paste the whole report into chat; the file is the deliverable. Do not
publish it anywhere: it holds internal work data. Delete the temporary JSON
files.

## Later changes

- New token, a different workspace, or a different person's ids: run Step 2
  again. Values you leave out are kept.
- Preferences only: `setup_config.py --language Arabic`, `--report-dir <dir>`
  or `--group-by tag` (this does not re-check the token).
- Forget everything: `setup_config.py --reset`. Confirm with the user first.

For API behavior (endpoints, status types, rate limits) and troubleshooting,
read `references/clickup-api.md`.
