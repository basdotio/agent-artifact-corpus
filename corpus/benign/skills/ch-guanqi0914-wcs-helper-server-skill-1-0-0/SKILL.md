---
name: wcs-helper-server-skill
description: "Your server's automatic caretaker — checks CPU, memory, and disk health, alerts you only when real action is needed. Use when: server feels slow, a cron job failed, disk is running out of space, or you want a daily health report."
version: 1.0.0
metadata:
  openclaw:
    tags: ["server", "health", "memory", "disk", "cpu", "auto-fix", "monitoring"]
    user-invocable: true
---

# WCS Helper: Server Skill

> Your server's caretaker — quietly monitors health, tells you only when something needs your attention.

---

## What It Does

| Problem | How It Helps |
|---------|-------------|
| Memory running high | Shows which processes are eating RAM, tells you how to fix |
| Disk full | Finds what's taking up space, cleans it up |
| Too many background processes | Finds and removes stuck/zombie processes |
| Server slow | Diagnoses the root cause |

**Default behavior:** no alerts unless something needs action. No noise.

---

## One-Command Health Check

```bash
# Full diagnostic report
sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/health-check.sh
```

Output looks like:

```
=== System Load ===
Load: 1.2 (4 cores) — OK

=== Memory ===
Memory: 67% used — OK
Available: 2.1 GB

=== Disk ===
Disk: 43% used — OK
Largest: /var/log (4.2 GB)
```

**Status colors:** ✅ OK / ⚠️ Warning / 🚨 Alert

---

## Quick Fix Commands

Run these when something is wrong:

```bash
# Preview what a fix would do (safe — shows what will change)
sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh --preview all

# Actually run memory fix (restart memory-hungry processes)
sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh --execute memory

# Clean disk space
sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh --execute disk

# Remove stuck processes
sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh --execute zombie
```

**Rule:** Preview mode (no `--execute`) never changes anything. Safe to run.

---

## When to Use

| Situation | Command |
|-----------|---------|
| Server feels slow | `health-check.sh` — see what's wrong |
| "Disk full" warning | `auto-fix.sh --preview disk` → `auto-fix.sh --execute disk` |
| Too many processes | `auto-fix.sh --preview zombie` → `auto-fix.sh --execute zombie` |
| Just checking in | `health-check.sh --summary` — 1-line status |

---

## Alerts (Optional)

Enable automatic alerts to Feishu when issues are found:

```bash
# Add to crontab — checks every 30 minutes, alerts if needed
# Run: crontab -e  (then paste these lines)

# Every 30 min: health check + Feishu alert if issues found
*/30 * * * * sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh all 2>&1 | tee -a /var/log/server-alerts.log

# Daily at 2am: full preview (safe — no actual changes)
0 2 * * * sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh --preview all >> /var/log/server-auto-fix.log 2>&1
```

Without a cron, the skill runs on demand only. Add it to get automatic alerts.

---

## What Gets Alerted

Only these trigger a push:

- Memory above 50% with leaky processes
- Disk above 90% full
- Zombie/stuck processes detected
- Cron job failures

Everything else is logged only, no push.

---

## Architecture

```
health-check.sh  — Read-only diagnosis (always safe)
auto-fix.sh       — Changes system state (needs --execute to apply)
```

- `health-check.sh`: No changes, just reports. Run anytime.
- `auto-fix.sh`: With `--preview` = safe, shows what would happen. With `--execute` = applies changes.

---

## Troubleshooting

### "Permission denied"
Use `sudo`: `sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/health-check.sh`

### "Command not found"
The skill is installed at `~/.openclaw/skills/wcs-helper-server-skill/`. Use the full path or `cd` there first.

### "Nothing happens when I run --execute"
Preview mode (`--preview`) is default. You need `--execute` to apply changes.

### "Alerts not coming through"
1. Check Feishu is connected: `openclaw status`
2. Verify the cron is running: `crontab -l | grep server-skill`
3. Test manually: `CRON_MODE=1 bash auto-fix.sh --execute memory`

---

## Self-Test

Verify the skill is working:

```bash
# 1. Health check (should always work without sudo on this server)
bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/health-check.sh --summary

# 2. Preview mode (should show current state)
sudo bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh --preview all

# 3. Notify test (sends a Feishu card)
DISABLE_NOTIFY=0 CRON_MODE=1 bash ~/.openclaw/skills/wcs-helper-server-skill/scripts/auto-fix.sh --preview memory
```

Expected: Step 1 shows a status table. Step 2 shows what would be cleaned. Step 3 sends a Feishu card.

---

## Uninstall

```bash
# Remove from crontab
crontab -e  # delete the line with wcs-helper-server-skill

# Remove skill files
rm -rf ~/.openclaw/skills/wcs-helper-server-skill
```

No system changes remain after uninstall.