#!/bin/zsh -l
PROPERTIES_DB="$HOME/.openclaw/workspace/data/properties.db"
VPS="root@187.77.140.113"
VPS_STAGING="/root/.openclaw/workspace/data/properties.db"
LOG_FILE="$HOME/.openclaw/logs/cre-scraper.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "Starting Crexi scrape"
unset ANTHROPIC_API_KEY

claude --chrome -p "/scrape-crexi" 2>&1 | tee -a "$LOG_FILE"

log "Scrape complete. Syncing to VPS staging"
rsync -avz "$PROPERTIES_DB" "$VPS:$VPS_STAGING" 2>&1 | tee -a "$LOG_FILE"

log "Running sync to Command Center"
ssh "$VPS" "python3 /root/sync-properties.py" 2>&1 | tee -a "$LOG_FILE"

log "Done"
