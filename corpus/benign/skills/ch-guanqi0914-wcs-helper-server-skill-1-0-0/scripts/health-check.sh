#!/bin/bash

# Minimal history logger (standalone — no dependencies)
log_history() {
    local metric="$1" value="$2" threshold="${3:-}" status="${4:-ok}"
    local hist_file="${HEALTH_HISTORY_FILE:-/var/log/server-health/history.jsonl}"
    mkdir -p "$(dirname "$hist_file")" 2>/dev/null
    local ts=$(date +%%Y-%%m-%%dT%%H:%%M:%%S%%z 2>/dev/null || echo "")
    printf '{"ts":"%%s","metric":"%%s","value":%%s,"status":"%%s"}
' \
        "$ts" "$metric" "$value" "$status" >> "$hist_file" 2>/dev/null
}
# health-check.sh — Server Doctor Auto Health Check
# Usage:
#   health-check.sh              # Full diagnosis
#   health-check.sh --summary    # Summary only
#   health-check.sh --check cpu,mem,disk,proc,network  # Check specific items
#   health-check.sh --alert      # Check + alert if issues found

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

OK="${GREEN}✅${NC}"
WARN="${YELLOW}⚠️${NC}"
FAIL="${RED}❌${NC}"
INFO="${BLUE}ℹ️${NC}"

ISSUES_FOUND=0
WARNINGS_FOUND=0

alert() { echo -e "${RED}[ALERT]${NC} $*" ; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" ; }
info() { echo -e "${BLUE}[INFO]${NC} $*" ; }
ok() { echo -e "${GREEN}[OK]${NC} $*" ; }

# Log a health metric to history file (JSON Lines format)
log_history() {
    local metric="$1" value="$2" threshold="${3:-}" status="${4:-ok}"
    local hist_file="${HEALTH_HISTORY_FILE:-/var/log/server-health/history.jsonl}"
    mkdir -p "$(dirname "$hist_file")" 2>/dev/null
    local ts
    ts=$(date +%Y-%m-%dT%H:%M:%S%z 2>/dev/null)
    printf '{"ts":"%s","metric":"%s","value":"%s","threshold":"%s","status":"%s"}
' \
        "$ts" "$metric" "$value" "${threshold:-null}" "$status" >> "$hist_file" 2>/dev/null
}


check_load() {
    local load
    load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local cores
    cores=$(nproc)
    local load_val
    load_val=$(echo "$load" | bc -l 2>/dev/null || echo "0")
    local threshold
    threshold=$(echo "$cores * 0.7" | bc -l 2>/dev/null || echo "999")
    
    echo "=== System Load ==="
    uptime | sed 's/^/  /'
    
    if (( $(echo "$load_val > $threshold" | bc -l 2>/dev/null) )); then
        alert "Load too high: ${load}(${cores} cores, should stay below $(printf '%.1f' $threshold)）"
        ISSUES_FOUND=$((ISSUES_FOUND+1))
    else
        ok "Load normal: ${load}"
    fi
    echo ""
    [[ "$HEALTH_HISTORY" == "1" ]] && { local load_status=$(echo "$load_val > $threshold" | bc -l 2>/dev/null); [[ "$load_status" == "1" ]] && log_history "load" "${load_val:-0}" "$threshold" "alert" || log_history "load" "${load_val:-0}" "$threshold" "ok"; }
}

check_memory() {
    echo "=== Memory ==="
    free -h | sed 's/^/  /'
    
    local available
    available=$(free | grep Mem | awk '{print $7}')
    local total
    total=$(free | grep Mem | awk '{print $2}')
    local pct
    pct=$(echo "100 - ($available*100/$total)" | bc -l 2>/dev/null | awk '{printf "%.0f", $1}')
    
    if [ "$pct" -gt 90 ]; then
        alert "Memory usage: ${pct}%（CRITICAL — over 90%）"
        ISSUES_FOUND=$((ISSUES_FOUND+1))
    elif [ "$pct" -gt 75 ]; then
        warn "Memory usage: ${pct}%（HIGH — recommend attention）"
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    else
        ok "Memory usage: ${pct}%"
    fi
    echo ""
    [[ "$HEALTH_HISTORY" == "1" ]] && log_history "memory" "${pct:-0}" "90" "$([[ ${pct:-0} -gt 90 ]] && echo alert || [[ ${pct:-0} -gt 75 ]] && echo warn || echo ok)"
}

check_disk() {
    echo "=== Disk Space ==="
    df -h / | sed '1d' | awk '{print "  " $1 ": "$3"/"$2" ("$5" used)"}'
    
    local usage
    usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    
    if [ "$usage" -gt 90 ]; then
        alert "Disk usage: ${usage}%（CRITICAL — over 90%）"
        ISSUES_FOUND=$((ISSUES_FOUND+1))
    elif [ "$usage" -gt 80 ]; then
        warn "Disk usage: ${usage}%(high)"
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    else
        ok "Disk usage: ${usage}%"
    fi
    
    # Inode check
    local inode_usage
    inode_usage=$(df -i / | tail -1 | awk '{print $5}' | tr -d '%')
    if [ "$inode_usage" -gt 80 ]; then
        warn "inode usage: ${inode_usage}% (may have issues)"
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    fi
    echo ""
    [[ "$HEALTH_HISTORY" == "1" ]] && log_history "disk" "${usage:-0}" "90" "$([[ ${usage:-0} -gt 90 ]] && echo alert || [[ ${usage:-0} -gt 80 ]] && echo warn || echo ok)"
}

check_top_processes() {
    echo "=== Top 5 CPU Processes ==="
    ps aux --sort=-%cpu | head -6 | tail -5 | awk '{printf "  %s %s%% CPU %s%% MEM %s\n", $11, $3, $4, $2}' | sed 's|/.*/||' | sed 's/  /\n/'

    echo ""
    echo "=== Top 5 Memory Processes ==="
    ps aux --sort=-%mem | head -6 | tail -5 | awk '{printf "  %s %s%% MEM %s%% CPU\n", $11, $4, $3}' | sed 's|/.*/||' | sed 's/  /\n/'
    echo ""
}

check_zombie() {
    echo "=== Zombie Processes ==="
    local zombies
    zombies=$(ps aux | grep -w Z | grep -v grep | wc -l)
    if [ "$zombies" -gt 0 ]; then
        warn "Found ${zombies} zombie processes"
        ps aux | grep -w Z | grep -v grep | awk '{print "  PID:"$2" PPID:"$3" CMD:"$11}' | head -5
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    else
        ok "No zombie processes"
    fi
    echo ""
}



check_network() {
    echo "=== Network Connectivity ==="
    
    # GitHub
    local gh_status
    gh_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://api.github.com/ 2>/dev/null || echo "000")
    if [ "$gh_status" = "200" ]; then
        ok "GitHub API: OK"
    else
        warn "GitHub API: HTTP $gh_status（may be blocked or network issue）"
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    fi
    
    # DNS
    local dns_status
    dns_status=$(nslookup google.com 2>&1 | grep -c "NXDOMAIN\|server can't find" || echo "0")
    if [ "$dns_status" -gt 0 ]; then
        warn "DNS resolution error"
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    else
        ok "DNS OK"
    fi
    echo ""
}

check_docker() {
    echo "=== Docker Containers ==="
    if command -v docker &>/dev/null; then
        local running
        running=$(docker ps --format "{{.Names}}" 2>/dev/null | wc -l)
        if [ "$running" -gt 0 ]; then
            ok "Docker running: ${running} containers"
            docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | sed 's/^/  /'
        else
            warn "No Docker containers running"
        fi
    else
        info "Docker not installed (skipped)"
    fi
    echo ""
}

check_openclaw() {
    echo "=== OpenClaw Status ==="
    if pgrep -f "openclaw" &>/dev/null; then
        ok "OpenClaw process running"
    else
        warn "OpenClaw process not found (may need to start)"
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    fi
    
    # gateway status
    if openclaw gateway status &>/dev/null; then
        local status
        status=$(openclaw gateway status 2>&1 | head -1)
        ok "Gateway: $status"
    fi
    echo ""
}

check_large_files() {
    echo "=== Large Files (>100MB) ==="
    local big_files
    big_files=$(find / -xdev -type f -size +100M 2>/dev/null | head -10)
    if [ -n "$big_files" ]; then
        warn "Found large files:"
        echo "$big_files" | xargs -I{} ls -lh {} 2>/dev/null | awk '{print "  "$5" "$9}' | head -5
        WARNINGS_FOUND=$((WARNINGS_FOUND+1))
    else
        ok "No very large files (>100MB)"
    fi
    echo ""
}

print_summary() {
    echo ""
    echo "═══════════════════════════════"
    echo "         Health Summary"
    echo "═══════════════════════════════"
    if [ "$ISSUES_FOUND" -eq 0 ] && [ "$WARNINGS_FOUND" -eq 0 ]; then
        echo -e "${GREEN}All checks OK${NC}"
    elif [ "$ISSUES_FOUND" -eq 0 ]; then
        echo -e "${YELLOW}⚠️ $WARNINGS_FOUND warnings${NC}"
    else
        echo -e "${RED}❌ $ISSUES_FOUND  issues，$WARNINGS_FOUND warnings${NC}"
    fi
    echo "═══════════════════════════════"
}

# ========== Main ===========
main() {
    local mode="full"
    local checks=""
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --summary)
                mode="summary"
                shift
                ;;
            --check)
                mode="selective"
                checks="$2"
                shift 2
                ;;
            --alert)
                mode="alert"
                shift
                ;;
            --history|--export)
                mode="history"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo ""
    echo "🩺 Server Doctor — $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    case "$mode" in
        summary)
            check_load
            check_memory
            check_disk
            print_summary
            ;;
        history)
            HEALTH_HISTORY=1 check_load
            HEALTH_HISTORY=1 check_memory
            HEALTH_HISTORY=1 check_disk
            print_summary
            echo "History: /var/log/server-health/history.jsonl"
            ;;
        selective)
            IFS=',' read -ra CHKS <<< "$checks"
            for c in "${CHKS[@]}"; do
                case "$c" in
                    cpu|load)  check_load ;;
                    mem|memory) check_memory ;;
                    disk)     check_disk ;;
                    proc|process) check_top_processes; check_zombie ;;
                    network) check_network ;;
                    docker)   check_docker ;;
                    openclaw) check_openclaw ;;
                    files)    check_large_files ;;
                esac
            done
            print_summary
            ;;
        alert)
            check_load; check_memory; check_disk; check_network
            print_summary
            if [ "$ISSUES_FOUND" -gt 0 ] || [ "$WARNINGS_FOUND" -gt 0 ]; then
                echo ""
                echo "Check for issues, run full diagnosis:"
                echo "  bash health-check.sh"
            fi
            ;;
        full|*)
            check_load
            check_memory
            check_disk
            check_top_processes
            check_zombie
            check_network
            check_docker
            check_openclaw
            check_large_files
            print_summary
            ;;
    esac
}

main "$@"
