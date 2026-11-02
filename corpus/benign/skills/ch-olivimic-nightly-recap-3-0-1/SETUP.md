# Nightly Recap, Setup Guide

## What This Does

Nightly Recap sends you one Telegram message each evening that closes the loop on your day. It covers what shipped, your social and system status, the win of the day, and what you're focused on tomorrow. You configure which systems to include, and the message arrives automatically at your chosen time, no dashboards, no context-switching, no noise. One message to end the day knowing the state of everything.

## Who This Is For

Built for solo founders and indie hackers running automated systems who want a daily close signal without logging into anything. If you ship code, run automations, or manage social content asynchronously, this skill turns your evening into a clear read on what happened. Works with any stack, you choose what to check.

## Before You Start, Prerequisites Check

Run through this list BEFORE starting setup. Takes 5 minutes.

- [ ] **OpenClaw installed and running**, [openclawapp.com](https://openclawapp.com)
- [ ] **Telegram account**, [telegram.org](https://telegram.org)
- [ ] **Telegram bot created**, Open Telegram, search `@BotFather`, send `/newbot`, follow the prompts. Copy your bot token.
- [ ] **Your Telegram chat ID**, Open Telegram, search `@userinfobot`, send `/start`. Copy the number it replies with.
- [ ] **Node.js 18+**, `node --version` to check. Download at [nodejs.org](https://nodejs.org) if needed.
- [ ] *(Optional)* Postiz account for queue health checks, [postiz.com](https://postiz.com)
- [ ] *(Optional)* Revenue API endpoint for daily sales data

## Step-by-Step Setup

### Step 1: Install the skill

Copy the skill folder into your OpenClaw skills directory, or install via clawhub once available:

```
clawhub install nightly-recap
```

### Step 2: Copy the example config

```bash
cp config.example.json config.json
```

### Step 3: Fill in config.json

Open `config.json` and fill in all fields. Required:

- `telegramBotToken`, from @BotFather
- `telegramChatId`, your chat ID from @userinfobot
- `projectName`, the name of your project (appears in the recap header)

Optional, set to `true` to enable each check:
- `checkSocialEngine`, social posts sent today
- `checkPostiz`, Postiz queue health (requires `postizApiKey`)
- `checkRevenue`, today's sales/revenue (requires `revenueApiUrl`)
- `checkBuildLogs`, automation log status

Set `tomorrowFocus` to your standing next-day focus, or leave it empty to be prompted each evening.

### Step 4: Test the send script

```bash
node scripts/send-message.js \
  --token "YOUR_BOT_TOKEN" \
  --chat "YOUR_CHAT_ID" \
  --message "Nightly Recap test, setup working ✓"
```

You should receive the message in Telegram within a few seconds.

### Step 5: Set up your evening cron

In OpenClaw, create a new cron:

- **Time:** 20:00 (or your preferred wind-down time)
- **Timezone:** Your local timezone
- **Type:** isolated agentTurn
- **Prompt:** `Run nightly recap and send to Telegram.`

### Step 6: Run your first recap

Say exactly: `nightly recap`

The first run will show a dry-run preview. Confirm to send the real recap.

## Test It Works

Say exactly: `nightly recap`

**Expected output:**
- First run: a dry-run preview showing what would be sent to Telegram, asking you to confirm
- After confirming: a Telegram message arrives with the recap format

**If nothing happens:** Check that the skill is loaded in your OpenClaw session. Run `openclaw skills list` to confirm it's installed.

## Changing Your Config

To update any setting, say:

```
reconfigure nightly-recap
```

This re-runs the guided setup and overwrites config.json.

**Quick update for tomorrow's focus:** Edit `tomorrowFocus` directly in config.json. You can also just leave it blank, the skill will prompt you each evening if it's unset.

## Troubleshooting

**Problem: Telegram message never arrives**
Cause: Bot token or chat ID is wrong, or you haven't started the bot.
Fix: Open Telegram, find your bot by name, send `/start` to it. Then verify `telegramBotToken` and `telegramChatId` in config.json.

**Problem: "401 Unauthorized" error**
Cause: Bot token is invalid or revoked.
Fix: Go to @BotFather → `/mybots` → select your bot → `API Token` → `Revoke current token`. Copy the new token into config.json.

**Problem: "400 Bad Request: chat not found"**
Cause: Chat ID doesn't match your Telegram account.
Fix: Send `/start` to @userinfobot again to get your correct chat ID. Update `telegramChatId` in config.json.

**Problem: Revenue section shows "not checked" even though checkRevenue is true**
Cause: `revenueApiUrl` is empty in config.json.
Fix: Add your revenue API endpoint to `revenueApiUrl` in config.json. The endpoint should return JSON with a sales count or total.

**Problem: All sections show "not checked"**
Cause: All optional checks are set to `false` in config.json.
Fix: Open config.json and set the checks you want to `true`. At least one check should be enabled for a useful recap.
