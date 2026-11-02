#!/usr/bin/env bash
# enrich-batch.sh — Enrich Crexi leads with detail page data via Claude Code + Chrome
# Usage: ./enrich-batch.sh [batch_size]  (default: 50)

set -euo pipefail

BATCH_SIZE="${1:-50}"
DB="$HOME/.openclaw/workspace/data/properties.db"
LOG="$HOME/.openclaw/logs/enrich-batch.log"
VPS="root@187.77.140.113"
VPS_DB="/root/openclaw-command-center/server/deals.db"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== Enrich batch started (batch_size=$BATCH_SIZE) ==="

# Preflight
if [[ ! -f "$DB" ]]; then
  log "ERROR: $DB not found"
  exit 1
fi

# Ensure properties table exists
sqlite3 "$DB" <<'SQL' 2>/dev/null || true
CREATE TABLE IF NOT EXISTS properties (
  id TEXT PRIMARY KEY, source TEXT, source_id TEXT, name TEXT, address TEXT,
  city TEXT, state TEXT, zip TEXT, asset_type TEXT, asking_price REAL, listing_url TEXT,
  broker_name TEXT, broker_firm TEXT, broker_phone TEXT, sqft INTEGER, year_built INTEGER,
  acreage REAL, zoning TEXT, description TEXT, investment_highlights TEXT, days_on_market INTEGER,
  noi REAL, cap_rate REAL, units INTEGER, occupancy REAL, proforma_noi REAL, proforma_cap_rate REAL,
  apn TEXT, broker_coop TEXT, irr_estimate REAL, dscr_estimate REAL, coc_estimate REAL,
  value_add_score INTEGER, value_add_flags TEXT, ai_confidence INTEGER, ai_summary TEXT, scraped_date TEXT, enriched_date TEXT
);
SQL

# Count properties needing enrichment
TOTAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM properties WHERE source='crexi' AND broker_name IS NULL;")
log "Properties needing enrichment: $TOTAL"

if [[ "$TOTAL" -eq 0 ]]; then
  log "Nothing to enrich. Exiting."
  exit 0
fi

TO_PROCESS=$((TOTAL < BATCH_SIZE ? TOTAL : BATCH_SIZE))
log "Processing $TO_PROCESS of $TOTAL"

# Run Claude Code with Chrome to do the enrichment
claude --chrome -p "
Run /scrape-crexi but ONLY the detail enrichment step (no search scrape). Enrich $TO_PROCESS properties from $DB where broker_name IS NULL. Use the full extraction pipeline: navigate to listing_url, wait 8s, click all phone reveal buttons, wait 2s, extract via DOM grid + AI analysis, save with crexi_detail.py. Wait 3s between pages. Show progress every 10. Skip 404s (set broker_name='UNAVAILABLE'). Print summary at end.
" 2>&1 | tee -a "$LOG"

# Post-enrichment stats
log "--- Enrichment stats ---"
sqlite3 "$DB" "SELECT COUNT(*) AS total, COUNT(broker_name) AS with_broker, COUNT(cap_rate) AS with_cap, COUNT(noi) AS with_noi, COUNT(broker_phone) AS with_phone FROM properties WHERE source='crexi';" | tee -a "$LOG"
REMAINING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM properties WHERE source='crexi' AND broker_name IS NULL;")
log "Remaining unenriched: $REMAINING"

# Sync to VPS and migrate
log "Syncing to VPS..."
if rsync -avz "$DB" "$VPS:$VPS_DB" >> "$LOG" 2>&1; then
  log "Rsync complete"
else
  log "WARNING: rsync failed"
fi

# No migration needed — rsync writes directly to dashboard deals.db

log "=== Enrich batch finished ==="
