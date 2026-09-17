---
name: telegram-outage-debug
description: Debug and explain Telegram “bot not responding” outages in OpenClaw (DM vs group, requireMention vs dmPolicy/pairing vs token 409 vs network fetch failures vs LLM timeouts). Use when diagnosing why a Telegram bot suddenly stops replying, when building a timeline from gateway.log/gateway.err.log, or when enabling temporary diagnostics flags (telegram.http) to capture root cause.
---

# Telegram Outage Debug (OpenClaw)

Goal: turn “bot 不回了” into a **precise classification + timeline + next action**.

This skill assumes default OpenClaw paths:

- Config: `~/.openclaw/openclaw.json`
- Logs:
  - `~/.openclaw/logs/gateway.log`
  - `~/.openclaw/logs/gateway.err.log`

## Mental model (3 hops)

For any Telegram message that should produce a reply:

1) **Inbound** Telegram → OpenClaw (polling/webhook)
2) **LLM** OpenClaw → model provider
3) **Outbound** OpenClaw → Telegram (sendMessage / sendChatAction)

“Bot 不回” can be caused by failure in ANY hop.

## First decision: DM vs Group

### DM (private chat)
Common blockers:
- `dmPolicy: pairing` (needs pairing approve)
- `dmPolicy: allowlist` + sender not in `allowFrom`
- outbound sendMessage failure (network)
- LLM timeout

### Group / Topic
Common blockers:
- `requireMention: true` (expected: only replies when mentioned)
- BotFather privacy mode blocks non-mention group messages even if config says `requireMention:false`
- group allowlist / groupPolicy / allowFrom not-allowed
- outbound sendMessage failure

## Quick classification checklist (fast)

Run these (CLI is node-based here):

```bash
openclaw gateway status
openclaw channels status --probe --timeout 20000
openclaw pairing list telegram
```

Interpretation:
- If Telegram account shows **not running** / **409** → token conflict.
- If DM is `pairing` and sender not approved → you’ll often see a pairing request (sometimes bot can’t deliver pairing message if outbound is broken).
- If `channels status --probe` says `works`, provider/token are likely OK; focus on outbound/network or LLM.

## Log triage: the handful of lines that matter

### A) Token conflict (two pollers) → 409
Look for: `409`, `Conflict`, `terminated by other getUpdates request`.

### B) Outbound to Telegram failing (network)
Look for:
- `sendMessage failed: Network request for 'sendMessage' failed!`
- `sendChatAction failed: Network request for 'sendChatAction' failed!`
- `TypeError: fetch failed`

This means: **reply may be generated but cannot be delivered**.

### C) LLM slow/timeout
Look for:
- `FailoverError: LLM request timed out`
- lane wait exceeded / embedded run timeout

This means: **inbound received, but model step did not finish**.

### D) Config gating / allowlist
Look for:
- `not-allowed`
- `skipping group message`
- `requireMention` gating notes

## Build a timeline from logs (recommended)

Use the bundled script to extract a window around a local timestamp.

### Script
- `scripts/extract-window.sh`

Example (PST):
```bash
cd ~/.openclaw/workspace-claw-config/skills/telegram-outage-debug
./scripts/extract-window.sh \
  --local "2026-02-03 00:36" --tz "America/Los_Angeles" --minutes 10 --tail 800000 \
  --grep "telegram|sendMessage failed|sendChatAction failed|fetch failed|409|Conflict|pairing|not-allowed|LLM request timed out"
```

Tip: logs can be multi-GB; increase/decrease `--tail` depending on how far back you’re debugging.

Outputs:
- a UTC window
- matching lines from `gateway.err.log` and `gateway.log`

## Explanation template (use in chat)

When reporting to the user, keep it short and structured:

- **Impact**: DM/group, which bot/account, since when.
- **Evidence**: 2–6 log lines (timestamps included).
- **Classification**: 409 token conflict vs pairing gating vs outbound network vs LLM timeout vs config gating.
- **Next action**: 1–3 commands or one config patch.

## Temporary deep debug (only when needed)

If the outage is intermittent and `fetch failed` doesn’t show the underlying errno/status, temporarily enable HTTP diagnostics.

**Process (ask before changing config):**
1) backup `~/.openclaw/openclaw.json`
2) set `diagnostics.flags=["telegram.http","gateway.*"]`
3) restart gateway
4) reproduce once
5) extract only the relevant block
6) revert diagnostics flags and restart

The goal is to capture:
- HTTP status / Telegram error description
- whether request had the expected `chat_id` / `message_thread_id`
- underlying errno (timeout/reset/DNS)
