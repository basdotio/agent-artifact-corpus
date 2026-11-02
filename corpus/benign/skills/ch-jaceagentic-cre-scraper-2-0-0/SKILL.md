---
name: cre-scraper
version: 2.0.0
description: Scrapes commercial real estate listings from Crexi and LoopNet using Claude in Chrome on a Mac Mini with residential IP. Bypasses Cloudflare bot protection. Extracts structured financials, broker contacts, and AI investment analysis. Saves to SQLite and syncs to OpenClaw Command Center dashboard.
requirements:
  binaries:
    - claude
    - rsync
    - sqlite3
  platform: macOS
  notes: Requires Claude Code with Claude in Chrome extension. Residential IP required — does not work from VPS/datacenter IPs.
---

# CRE Scraper v2.0

Scrape commercial real estate listings from Crexi and LoopNet using Claude in Chrome.

## Architecture
```
Mac Mini (residential IP + Chrome)
  → /scrape-crexi or /scrape-loopnet slash commands
  → ~/.openclaw/workspace/data/properties.db
  → rsync to VPS staging
  → sync-properties.py → Command Center dashboard
```

## Requirements

- macOS with Claude Code installed
- Claude in Chrome browser extension active
- Logged into Crexi (crexi.com) and LoopNet (loopnet.com) in Chrome
- SSH key authorized on VPS
- `chromeEnabled: true` in ~/.claude/settings.json

## Usage

Run Crexi scrape (all 21 combinations):
```bash
~/.openclaw/skills/cre-scraper/run-scrape.sh
```

Run enrichment on unenriched properties:
```bash
~/.openclaw/skills/cre-scraper/enrich-batch.sh [batch_size]
```

Or inside Claude Code:
```
/scrape-crexi
/scrape-loopnet
```

## Configuration

- **States:** FL, GA, NC, TN, AL, LA, ID
- **Asset types:** rv_park, self_storage, marina
- **Price range:** $800K–$3M
- **Min units:** 50+ (when known)
- **Value-add threshold:** VAS ≥ 40

## What gets scraped

Per listing:
- Address, city, state, zip
- Asking price, cap rate, NOI, occupancy
- Units/pads/slips, SF, year built, acreage
- Pro-forma cap rate and NOI
- Broker name, firm, full phone (click-reveal)
- Description and investment highlights
- AI analysis: IRR, DSCR, Cash-on-Cash, Value-Add Score, AI Confidence

## Cron schedule (launchd)

- **7:00am** — Crexi scrape (ai.crexi.scraper)
- **8:00am** — LoopNet scrape (ai.loopnet.scraper)
- **Midnight** — Enrichment batch (ai.crexi.enricher)

## Trigger phrases
- "scrape new deals"
- "run the Crexi scraper"
- "find new RV parks in Florida"
- "check LoopNet for self storage in Tennessee"
- "enrich unenriched properties"
- "sync deals to dashboard"

## Output

Properties saved to `~/.openclaw/workspace/data/properties.db` and synced to OpenClaw Command Center dashboard via `sync-properties.py`.