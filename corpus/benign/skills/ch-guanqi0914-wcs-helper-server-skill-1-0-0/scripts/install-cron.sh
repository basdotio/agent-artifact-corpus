#!/bin/bash
# install-cron.sh — Auto-install cron jobs for Server Doctor
# Usage: bash install-cron.sh [interval]
#   interval: hourly | every6h | daily (default: every6h)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HEALTH_BIN="bash ${SKILL_DIR}/scripts/health-check.sh"
FIX_BIN="bash ${SKILL_DIR}/scripts/auto-fix.sh"
CRON_FILE="/etc/cron.d/wcs-server-doctor"

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
ok() { echo -e "${GREEN}[OK]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*" >&2; }

# Parse interval
INTERVAL="${1:-every6h}"
case "$INTERVAL" in
    hourly|1h)   HEALTH_CRON="0 * * * *"; FIX_CRON="5 * * * *"; INTERVAL_DESC="every hour" ;;
    every6h|6h)  HEALTH_CRON="0 */6 * * *"; FIX_CRON="5 */6 * * *"; INTERVAL_DESC="every 6 hours" ;;
    daily|1d)    HEALTH_CRON="0 2 * * *"; FIX_CRON="5 2 * * *"; INTERVAL_DESC="daily at 2am" ;;
    *) fail "Unknown interval: $INTERVAL"; echo "Usage: $0 [hourly|every6h|daily]"; exit 1 ;;
esac

info "Installing Server Doctor cron jobs (${INTERVAL_DESC})..."

# Check if we can write to /etc/cron.d (needs root)
if [ -w /etc/cron.d ] || [ "$(id -u)" = "0" ]; then
    info "Using /etc/cron.d/ for system-wide cron..."
    
    # Remove old entry if exists
    [ -f "$CRON_FILE" ] && warn "Overwriting existing $CRON_FILE"
    
    cat > "$CRON_FILE" << CRONEOF
# Server Doctor — auto-installed by wcs-helper-server-doctor skill
# Interval: ${INTERVAL_DESC}
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Health check every ${INTERVAL_DESC} — log only, no alerts
${HEALTH_CRON} root ${HEALTH_BIN} --summary >> /var/log/server-health.log 2>&1

# Auto-fix preview every ${INTERVAL_DESC} — logs what would be done
${FIX_CRON} root ${FIX_BIN} --preview all >> /var/log/server-auto-fix.log 2>&1

CRONEOF
    
    chmod 644 "$CRON_FILE"
    ok "Cron installed: $CRON_FILE"
    echo ""
    echo "Health checks: ${HEALTH_CRON} root ${HEALTH_BIN} --summary"
    echo "Auto-fix log:   ${FIX_CRON} root ${FIX_BIN} --preview all"
    echo ""
    echo "Logs:"
    echo "  tail -f /var/log/server-health.log    # watch health"
    echo "  tail -f /var/log/server-auto-fix.log  # watch auto-fix"
    echo ""
    echo "To uninstall:"
    echo "  sudo rm $CRON_FILE"
    
else
    # Fallback: user crontab
    warn "Cannot write to /etc/cron.d/ (not root). Installing to user crontab..."
    
    (crontab -l 2>/dev/null | grep -v "wcs-server-doctor\|server-health\|server-auto-fix"; \
     echo "# Server Doctor — auto-installed by wcs-helper-server-doctor skill"; \
     echo "# Interval: ${INTERVAL_DESC}"; \
     echo "${HEALTH_CRON} ${HEALTH_BIN} --summary >> /var/log/server-health.log 2>&1"; \
     echo "${FIX_CRON} ${FIX_BIN} --preview all >> /var/log/server-auto-fix.log 2>&1") | \
     crontab -
    
    ok "Cron installed to user crontab."
    echo ""
    crontab -l | grep -E "server-health|server-auto-fix|wcs-server" | sed 's/^/  /'
    echo ""
    echo "To uninstall:"
    echo "  crontab -e  # then delete the Server Doctor lines"
fi

# Create log files
for log in /var/log/server-health.log /var/log/server-auto-fix.log; do
    touch "$log" 2>/dev/null || sudo touch "$log"
done
ok "Log files ready: /var/log/server-health.log /var/log/server-auto-fix.log"
ok "Installation complete!"
