---
name: token-watchdog
version: 1.0.0
description: Monitors OpenClaw agent token spend per session and alerts via Telegram when cost exceeds estimated budget (2x threshold). Prevents runaway debugging loops from burning $3,000+ unnoticed.
---

# Token Watchdog

**Stop debugging loops before they bankrupt you.**

AI agents in runaway debug loops can burn $3,000+ before anyone notices. Token Watchdog monitors your actual session spend in real-time and pings you on Telegram the moment costs go off the rails.

## How it works

- Reads your live session `.jsonl` file directly (no API call needed)
- Estimates expected cost based on task complexity keywords
- Polls every 30 seconds
- Sends Telegram alert when actual spend hits **2x the estimate**
- At 3x: sends final warning and exits

> ⚠️ Cost figures are OpenClaw's internal estimates (~90% accurate vs Anthropic billing).  
> This tool is a **danger signal detector**, not a precise billing tracker.

## Install

### Option A — via SynapseAI (recommended)

```bash
curl -sL https://ddaekeu3-cyber.github.io/synapse-ai/tools/token-watchdog/token-watchdog.mjs \
  -o ~/.openclaw/workspace/token-watchdog.mjs
```

### Option B — via ClawHub

```bash
clawhub install token-watchdog
```

## Usage

```bash
# Auto-estimate based on task description
node ~/.openclaw/workspace/token-watchdog.mjs --task "Fix auth timeout bug"

# Manual cost estimate (dollars)
node ~/.openclaw/workspace/token-watchdog.mjs --estimate 1.50 --task "DB migration"

# Background mode
nohup node ~/.openclaw/workspace/token-watchdog.mjs --task "Complex refactor" &
```

## Complexity estimates (auto)

| Task type | Keywords | Estimated cost |
|---|---|---|
| High | debug, refactor, migration, 디버깅 | $1.50 |
| Medium | implement, create, build, 구현 | $0.50 |
| Low | read, check, list, 확인 | $0.10 |
| Default | (anything else) | $0.30 |

## Telegram alert format

```
🚨 Token budget exceeded!

Estimated: $0.50
Current:   $1.12 (224%)

Agent paused. Continue? Reply "계속" or "중지"
```

## Requirements

- OpenClaw with Telegram channel configured
- Node.js v18+
- Session files at `~/.openclaw/agents/main/sessions/`

## Also available on SynapseAI

SynapseAI is a shared solution DB for OpenClaw agents.  
If you find new patterns or improvements for this tool, contribute them at:  
👉 https://ddaekeu3-cyber.github.io/synapse-ai/