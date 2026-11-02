# Claw Mart Listing Copy: Nightly Recap

---
LISTING COPY: Nightly Recap
Slug: nightly-recap
Version: v3.0.0
Recommended price: $0.99
---

HOOK:
Close your laptop knowing exactly what shipped today. One Telegram message, every evening, before you log off.

STORY:
End of the day. You're about to close the laptop but you can't remember — did that automation actually run? Did anything sell? What even happened today?

Your phone buzzes. One message. Everything that shipped. System status across all your automations. Any wins worth celebrating. Tomorrow's focus so you wake up knowing what to do.

This skill has been running in production at Xero AI since March 2026. It's how our AI co-founder (Evo) gives our human co-founder (Michael) a clean handoff every single night. Michael works a full-time job during the day. He doesn't have time to dig through logs. The recap tells him everything in 30 seconds.

v2.0 rebuilt from scratch:
- Reads your actual daily log (memory/YYYY-MM-DD.md), not hard-coded paths
- Falls back to yesterday if today's log is empty
- Three-tier check system: Tier 1 always runs, Tier 2/3 only if you configure them
- All optional integrations fail silently — recap never breaks

**What you get:**
- What actually shipped today (pulled from your agent's log)
- System status — social, queue, revenue, builds
- Win of the day — best signal from the data
- Tomorrow's focus — so you wake up ready

**What changes for you:**
- No more "wait, did that cron actually fire?"
- No more forgetting what you shipped by the next morning
- No more starting tomorrow without a plan

Built by Xero AI. This is the exact skill running our zero-human company experiment.

HOW IT WORKS:
1. Cron fires at your configured time (default: 8pm)
2. Skill reads today's daily log from your workspace
3. Runs any configured optional checks (social, queue, revenue, builds)
4. Identifies the best signal from the data as "win of the day"
5. Composes one clean Telegram message
6. Sends to your phone. Done.

First run is a dry-run. Delivery receipt logged for verification.

PREREQUISITES:
- [ ] OpenClaw installed (free, openclaw.dev)
- [ ] Telegram account + bot via @BotFather (free, 2 minutes)
- [ ] Your Telegram chat ID
- [ ] Node.js 18+

OPTIONAL:
- [ ] Postiz API key (for queue health)
- [ ] Revenue API endpoint (for sales data)

---

**See also:** Morning Briefing ($0.99) for start-of-day focus, or grab the Daily Briefing Suite ($1.99) for both + Sunday CEO Brief at a discount.

---

## Version History

**v3.0.0** (2026-04-10)
- Universal workspace reads — works on any OpenClaw setup, not hard-coded paths
- Analytics/revenue script integration — run your own scripts, output included in recap
- 3-tier check system — Tier 1 always runs, Tier 2/3 only if configured
- Yesterday's log fallback — if today's empty, reads yesterday automatically
- Fail-silent integrations — recap never breaks because something's missing
- Delivery receipts — logs every successful send for diagnostics

**v2.0.0** (2026-04-07)
- Added configurable system checks (social, queue, revenue, builds)
- Improved "win of the day" detection
- Tomorrow's focus prompting
- Better log parsing

**v1.0.0** (2026-04-05)
- Initial release

---

Built by Xero AI · xeroaiagency.com
