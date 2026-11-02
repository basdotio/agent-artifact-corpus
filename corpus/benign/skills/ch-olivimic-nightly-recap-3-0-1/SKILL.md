---
name: nightly-recap
version: 3.0.1
description: "Sends a single Telegram message each evening with what shipped today, social/system status, wins, and tomorrow's focus, fully configurable for your stack."
author: xeroai
tags: [telegram, briefing, automation, daily, solopreneur, evening, recap]
license: MIT
---

# Nightly Recap

Sends one Telegram message each evening. What shipped today, system status, any wins worth noting, and tomorrow's focus, all in one message before you close the laptop.

Closes the loop on your day without a dashboard.

Built by Xero AI, xeroaiagency.com

---

## What's New in v2

- **Reads your actual daily log**, sources content from `memory/YYYY-MM-DD.md` instead of hard-coded Xero-specific paths. Works on any OpenClaw setup.
- **Three-tier check system**, Tier 1 always runs (workspace reads). Tier 2 and 3 only run if you configure them. No silent failures.
- **Yesterday's log fallback**, if today's log is empty, reads yesterday's for context.
- **Fail-silent on all optional integrations**, analytics and revenue scripts disappear cleanly if they error.
- **"Tomorrow's one thing"**, always ends with a single priority pulled from your workspace.
- **Delivery receipt**, writes `last_run.log` on every successful send for self-serve diagnostics.

---

## Trigger Phrases

| Phrase | Action |
|---|---|
| `nightly recap` | Run the nightly recap now (manual trigger) |
| `reconfigure nightly-recap` | Re-run guided setup and overwrite config.json |

---

## First-Run Logic

Before running the pipeline, check for config:

1. Does `config.json` exist in this skill directory?
   - **No** → Start guided setup (see Guided Setup section below)
2. Does `config.json` exist?
   - **Yes** → Validate ALL required fields:
     - Is `telegramBotToken` empty, null, or still `"YOUR_TELEGRAM_BOT_TOKEN"`? → Guided setup from that field
     - Is `telegramChatId` empty, null, or still `"YOUR_TELEGRAM_CHAT_ID"`? → Guided setup from that field
   - All fields valid? → Proceed to pipeline

---

## Guided Setup

When config doesn't exist or is invalid, run this conversation one question at a time:

```
"Hey, Nightly Recap needs a quick setup before it can run. I'll ask a few things one at a time.

First: What's your Telegram bot token? You can get one from @BotFather on Telegram, send /newbot and follow the prompts. Paste it here when ready."
```

Collect answers in order:
1. `telegramBotToken`, bot token from @BotFather
2. `telegramChatId`, chat ID from @userinfobot (send /start to get it)
3. `projectName`, what to call this project in the recap (e.g., "My SaaS", "Side Project")
4. `timezone`, e.g., "America/New_York" (default: "America/New_York")
5. Optional: "Do you have an analytics script to run at end of day? Paste the full path, or skip." → `analyticsScript`
6. Optional: "Do you have a revenue check script? Paste the full path, or skip." → `revenueScript`
7. Optional: "Any community paths to summarize (e.g., Reddit tracking file, IH log)? Paste paths comma-separated, or skip." → `communityPaths` (array)

Write config.json from answers. Confirm:

```
"All set. Here's what I configured:
- Project: [projectName]
- Telegram: configured ✓
- Analytics: [configured / not configured]
- Revenue: [configured / not configured]
- Community: [configured / not configured]

Say 'nightly recap' to run a test."
```

---

## Reconfigure Trigger

When the user says `reconfigure nightly-recap`:
1. Announce: "Re-running Nightly Recap setup. I'll ask each question again and overwrite config.json."
2. Run the full guided setup conversation above
3. Overwrite config.json with new values

---

## Main Pipeline

### Step 1, Read config.json

Load config from the skill directory. Confirm all required fields are present.

### Step 2, Tier 1: Workspace reads (always runs)

Read the following standard OpenClaw files:
- Today's `memory/YYYY-MM-DD.md`, what the agent logged today
- If today's file is empty or doesn't exist → read yesterday's `memory/YYYY-MM-DD.md` for context
- If neither exists → "Nothing logged today. Your agent ran but didn't write to the daily log."
- `HEARTBEAT.md`, for tomorrow's priority

Summarize what actually happened today from the log. What did the agent do? What shipped? What was flagged?

### Step 3, Tier 2: Optional integrations (fail-silent)

**Analytics (if `config.analyticsScript` is set):**
- Check path exists with `fs.existsSync()` before running
- Run the script TWICE: once with `--days 1` (24h data) and once with `--days 7` (7-day data)
- Capture both outputs separately
- If it errors or returns nothing → omit the analytics line silently

**Revenue (if `config.revenueScript` is set):**
- Check path exists with `fs.existsSync()` before running
- Run script, capture output
- If it errors or returns nothing → omit the revenue line silently

### Step 4, Tier 3: Community (fail-silent)

**If `config.communityPaths[]` is set:**
- For each path: check it exists with `fs.existsSync()`, then read and summarize
- Skip any path that doesn't exist, no error

**If not configured:** community section omitted entirely.

### Step 5, Tomorrow's priority

Read `HEARTBEAT.md` for the top checklist item or active task.
If nothing found → read `AGENTS.md` for any active priorities.
Always produces at least one "tomorrow" line, never blank.

### Step 6, Compose the recap

Assemble a single Telegram message. Be specific — use real numbers and real events. This is Michael's end-of-day operational read, not a vague summary.

```
🌙 Nightly Recap, [Day, Date]

📋 Today:
   • [item 1 — most significant thing that shipped or happened]
   • [item 2]
   • [item 3, omit if nothing else notable]
   (pull from daily log, be specific — crons run, posts made, builds shipped, errors fixed)

💰 Revenue: [from revenueScript — all-time total + today's sales. e.g. "All-time: $2.00 · Today: $0 · 0 new sales"]
📊 Site (24h):
   • Views: [pageviews from --days 1 run]
   • Visitors: [unique visitors from --days 1 run]
   • Top page: [top page + hits from --days 1 run]
   • Conversions: [Book 1 purchase events from --days 1 run, or 0]
📊 Site (7d):
   • Views: [pageviews from --days 7 run]
   • Visitors: [unique visitors from --days 7 run]
   • Top page: [top page + hits from --days 7 run]
   • Conversions: [Book 1 purchase events from --days 7 run, or 0]
🤖 Reddit: [from communityPaths — current karma + best comment this week, omit if no data]
🗊 Twitter: [from communityPaths — recent reply activity, omit if no data]

⚠️ Flags: [anything broken, erroring, or needs attention tomorrow — omit if clean]
🎯 Tomorrow: [single top priority from HEARTBEAT.md or ACTIVE_TASKS.md]
```

Real numbers only. Run every configured script and read every community file before composing. Never say "not configured" — just omit the section if there's genuinely no data.

### Step 7, Send to Telegram

Use `scripts/send-message.js` to deliver the recap:

```bash
node scripts/send-message.js --token "TOKEN" --chat "CHAT_ID" --message "MESSAGE"
```

### Step 8, Write delivery receipt

On successful send, append one line to `last_run.log` in the skill directory:

```
2026-04-08T20:00:01Z OK nightly-recap sent
```

If delivery fails:
1. Show the exact error
2. Check token validity (401 = bad token, 400 = bad chat ID)
3. Prompt: "Delivery failed, run 'reconfigure nightly-recap' to update your Telegram credentials."
4. Write failure to log: `2026-04-08T20:00:01Z FAILED [error message]`

---

## Dry Run (First Trigger)

On the very first trigger after setup (check `tracking.json` → `firstRunCompleted: false`), run in dry-run mode:

```
[DRY RUN, nothing was sent]

Here's what I would have sent to Telegram:

---
🌙 Nightly Recap, [Day, Date]

📋 Today: Day 1, nothing logged yet. Your agent is running.
🎯 Tomorrow: [top item from HEARTBEAT or AGENTS]

→ Ready to go deeper? Co-Founder in a Box: xeroaiagency.com/skills
---

Ready to go live? Say 'nightly recap' again to send the real recap.
```

After the user confirms and the message sends successfully, set `firstRunCompleted` to `true` in `tracking.json`.

---

## Cron Setup

To run automatically each evening, add a cron in OpenClaw:

```
Time: 20:00 (or your preferred wind-down time)
Timezone: Your local timezone
Type: isolated agentTurn
Prompt: Run nightly recap and send to Telegram.
```

Requires OpenClaw with agentTurn cron support. Check your version: `openclaw --version`

---

## Troubleshooting

If the recap stops arriving, check `last_run.log` in the skill folder to see the last successful send time and any errors. Most issues are Telegram credential problems, run `reconfigure nightly-recap` to fix.

---

## Config Reference

| Field | Required | Default | Description |
|---|---|---|---|
| `telegramBotToken` | ✅ |, | Telegram bot token from @BotFather |
| `telegramChatId` | ✅ |, | Your Telegram chat ID from @userinfobot |
| `projectName` | ✅ |, | Your project name for the recap header |
| `timezone` | ✅ | `America/New_York` | Your local timezone (IANA format) |
| `analyticsScript` | ❌ |, | Full path to an analytics script (must output plain text) |
| `revenueScript` | ❌ |, | Full path to a revenue check script (must output plain text) |
| `communityPaths` | ❌ | `[]` | Array of file paths to read for community status |