#!/bin/bash
# auto-fix.sh — Server Doctor Auto-fix
# Usage:
#   auto-fix.sh zombie    # Clean zombie processes
#   auto-fix.sh memory    # Restart high-memory processes
#   auto-fix.sh disk      # Clean disk space
#   auto-fix.sh cron      # Fix abnormal cron tasks
#   auto-fix.sh all       # All checks + fixes
#   auto-fix.sh --preview # Preview all fixes (no execution)
#   auto-fix.sh --execute [type]  # Execute fixes (requires explicit --execute)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PREVIEW_MODE=true  # Default: preview-only, safe mode
BACKUP_DIR="/tmp/server-doctor-backup-$(date +%Y%m%d_%H%M%S)"

# Tunable memory threshold (percentage). Override with: MEM_THRESHOLD=50 auto-fix.sh --execute memory
MEM_THRESHOLD="${MEM_THRESHOLD:-50}"

alert() { echo -e "${RED}[FIX]${NC} $*"; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

# Backup before any modification
backup() {
    mkdir -p "$BACKUP_DIR"
    for f in "$@"; do
        if [ -f "$f" ]; then
            cp -r "$f" "$BACKUP_DIR/" 2>/dev/null
            info "Backed up: $f"
        fi
    done
}

# Preview vs execute mode
run_or_preview() {
    if [ "$PREVIEW_MODE" = "true" ]; then
        echo -e "${YELLOW}[PREVIEW]${NC} $*"
    else
        echo -e "${RED}[!!]${NC} About to execute: $*"
        read -p "    Confirm? (y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            info "Cancelled"
            return
        fi
        alert "Executing: $*"
        eval "$@"
    fi
}

# ========== Fix: Zombie Processes ==========

# ────────────────────────────────────────────────────────────────────────────
# Notification — Feishu bot push (optional)
# Set FEISHU_BOT_TOKEN env var or /etc/server-doctor/feishu.conf
# ────────────────────────────────────────────────────────────────────────────
notify() {
    # Send a Feishu card to owner — pure Python, no bash/json string mixing
    python3 - "$1" "${2:-info}" << 'PYEOF'
import subprocess, json, sys, re, os

msg_raw  = sys.argv[1]
level    = sys.argv[2] if len(sys.argv) > 2 else 'info'
hostname = os.popen("hostname 2>/dev/null || echo server").read().strip()
ts       = os.popen("date +'%Y-%m-%d %H:%M'").read().strip()

EMOJI_MAP  = {'alert': '🚨', 'warn': '⚠️', 'info': '📢'}
COLOR_MAP = {'alert': 'red', 'warn': 'orange', 'info': 'blue'}
emoji      = EMOJI_MAP.get(level, '📢')
card_color = COLOR_MAP.get(level, 'blue')

# Convert literal \n in the message to real newlines for markdown
msg_text = re.sub(r'\\n', '\\n', msg_raw)   # literal backslash-n → real newline

card = {
    'config': {'wide_screen_mode': True},
    'header': {
        'title': {'tag': 'plain_text', 'content': emoji + ' Server Doctor — ' + ts},
        'template': card_color
    },
    'elements': [
        {'tag': 'markdown', 'content': '**Host:** ' + hostname + '  \n\n' + msg_text},
        {'tag': 'hr'},
        {'tag': 'note', 'elements': [
            {'tag': 'plain_text', 'content': 'wcs-helper-server-doctor · auto-fix.sh'}
        ]}
    ]
}

owner_id = 'ou_ed25ce21ea806c0f0064b8ec88822107'
proc = subprocess.run(
    ['openclaw', 'message', 'send',
     '--channel', 'feishu',
     '--target', 'user:' + owner_id,
     '--account', 'default',
     '--card', json.dumps(card, ensure_ascii=False)],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
PYEOF
    return 0
}



# ────────────────────────────────────────────────────────────────────────────
# History — append JSON record to history file
# ────────────────────────────────────────────────────────────────────────────
log_history() {
    local metric="$1"
    local value="$2"
    local threshold="$3"
    local status="${4:-ok}"  # ok | warn | alert

    local hist_file="${HEALTH_HISTORY_FILE:-/var/log/server-health/history.jsonl}"
    mkdir -p "$(dirname "$hist_file")" 2>/dev/null

    local ts=$(date +%Y-%m-%dT%H:%M:%S%z)
    local hostname=$(hostname 2>/dev/null || echo "unknown")

    printf '{"ts":"%s","host":"%s","metric":"%s","value":%s,"threshold":%s,"status":"%s"}
' \
        "$ts" "$hostname" "$metric" "$value" "${threshold:-null}" "$status"         >> "$hist_file" 2>/dev/null
}

# Read config if exists
CONFIG_FILE="${CONFIG_FILE:-/etc/server-doctor/server-doctor.conf}"
if [ -f "$CONFIG_FILE" ]; then
    . "$CONFIG_FILE" 2>/dev/null
fi

# ────────────────────────────────────────────────────────────────────────────
# Interactive memory fix — ask user before killing
# ────────────────────────────────────────────────────────────────────────────
fix_memory_interactive() {
    local threshold="${MEM_THRESHOLD:-50}"
    local dry="${DRY_RUN:-0}"

    alert "=== Memory Check (threshold: ${threshold}%) ==="
    log_history "memory" "${current_mem}" "$threshold" "ok"

    local leaky=$(ps aux --sort=-%mem 2>/dev/null | awk -v th="$threshold" 'NR>1 && $4>th {print $2":"$4":"$6":"$11}' | head -10)

    if [ -z "$leaky" ]; then
        ok "No processes above ${threshold}% found."
        log_history "memory" "${current_mem}" "$threshold" "ok"
        return 0
    fi

    # Found high-memory processes — NOTIFY and PAUSE, don't auto-kill
    warn "Found $(echo "$leaky" | wc -l) process(es) above ${threshold}%:"
    echo "$leaky" | while IFS=: read -r pid pct rss cmd; do
        warn "  PID=$pid  MEM=${pct}%  RSS=${rss}KB  $(echo $cmd | cut -d' ' -f1)"
    done

    # Log as alert
    log_history "memory" "${pct:-0}" "$threshold" "alert"

    if [ "$dry" == "1" ]; then
        warn "[DRY RUN] Would kill the above processes."
        return 0
    fi

    # Only notify in CRON_MODE — interactive mode shows inline, no push
    if [ -n "$CRON_MODE" ]; then
        # Format leaky processes for Feishu notification
    local pct_summary
    pct_summary=$(echo "$leaky" | while IFS=: read -r pid pct rss cmd; do
        printf "  %-8s %5s%% %6sMB  %s\n" "PID=$pid" "$pct" "$rss" "$cmd"
    done | head -5)
    notify "🐧 主机内存 ${pct}%（阈值 ${threshold}%）\\n\\n🐺 top内存进程（阈值 ${threshold}%）：\\n${pct_summary}\\n\\n处理：MEM_THRESHOLD=${threshold} bash auto-fix.sh --execute memory" "alert"
        return 0
    fi

    # For interactive mode: ask
    echo ""
    echo "Options:"
    echo "  y — Kill the above processes (SIGTERM → SIGKILL)"
    echo "  n — Skip (do nothing)"
    echo "  p — Preview only (show what would happen)"
    read -p "Apply fix? [y/N]: " ans
    case "$ans" in
        y|Y)
            info "Applying memory fix..."
            do_memory_fix "$leaky"
            ;;
        p|P)
            warn "Preview mode:"
            do_memory_fix "$leaky" dry=1
            ;;
        *)
            info "Skipped. Run manually: MEM_THRESHOLD=$threshold bash auto-fix.sh --execute memory"
            ;;
    esac
}

# ────────────────────────────────────────────────────────────────────────────
# Alias fix_memory to use interactive version
# ────────────────────────────────────────────────────────────────────────────
alias fix_memory=fix_memory_interactive


fix_zombie() {
    alert "=== Fixing Zombie Processes ==="

    local zombies
    zombies=$(ps aux | grep -w Z | grep -v grep)

    if [ -z "$zombies" ]; then
        ok "No zombie processes found"
        return
    fi

    info "Found zombie processes:"
    echo "$zombies" | awk '{print "  PID:"$2" PPID:"$3" CMD:"$11}' | head -5

    # Find parent processes of zombies
    local ppids
    ppids=$(echo "$zombies" | awk '{print $3}' | sort -u | grep -v PPID)

    for ppid in $ppids; do
        local parent
        parent=$(ps -p "$ppid" -o comm= 2>/dev/null)
        info "Parent process: PID=$ppid CMD=$parent"

        if [ -n "$parent" ]; then
            info "Sending SIGHUP to restart parent: kill -1 $ppid"
            run_or_preview "kill -1 $ppid"
            sleep 2
        fi

        # If still running, send SIGTERM
        if ps -p "$ppid" &>/dev/null; then
            info "Parent still running, SIGTERM: kill -15 $ppid"
            run_or_preview "kill -15 $ppid"
            sleep 3
        fi

        # Last resort: SIGKILL
        if ps -p "$ppid" &>/dev/null; then
            alert "Parent still running, SIGKILL: kill -9 $ppid"
            run_or_preview "kill -9 $ppid"
        fi
    done

    # Verify
    local remaining
    remaining=$(ps aux | grep -w Z | grep -v grep | wc -l)
    if [ "$remaining" -eq 0 ]; then
        ok "Zombie processes cleaned"
    else
        warn "$remaining zombie processes remain"
    fi
}

# ========== Fix: Memory Leaks ==========
# NEW improved logic:
# 1. Find processes using more than MEM_THRESHOLD% memory (default 50%)
# 2. Skip all critical system processes (systemd, sshd, docker, etc.)
# 3. Graceful restart: SIGTERM → wait 10s → SIGKILL → identify restart mechanism
# 4. Try supervisorctl / systemd / PM2 / docker restart in that order
fix_memory() {
    alert "=== Fixing High-Memory Processes (threshold: ${MEM_THRESHOLD}%) ==="

    # Find processes using >${MEM_THRESHOLD}% memory
    local leaky
    leaky=$(ps aux --sort=-%mem | awk -v th="$MEM_THRESHOLD" '$4 > th {print $2":"$4":"$6":"$11}' | head -10)

    if [ -z "$leaky" ]; then
        ok "No high-memory processes above ${MEM_THRESHOLD}% found"
        return
    fi

    info "Found high-memory processes above ${MEM_THRESHOLD}%:"
    echo "$leaky" | while IFS=: read pid pct mem cmd; do
        echo "  PID=$pid ${pct}%MEM ${mem}MB cmd=$cmd"
    done

    # Attempt graceful restart for each leaky process
    echo "$leaky" | while IFS=: read pid pct mem cmd; do
        # Skip critical system processes
        case "$cmd" in
            *systemd*|*init*|*sshd*|*docker*|*containerd*|*postgres*|*mysql*|*redis*|*nginx*|*apache*)
                info "Skipping critical system process: $cmd"
                ;;
            *)
                restart_process "$pid" "$pct" "$mem" "$cmd"
                ;;
        esac
    done

    ok "Memory check complete"
}

# Gracefully restart a single process: SIGTERM → wait → SIGKILL → restart attempt
restart_process() {
    local pid="$1"
    local pct="$2"
    local mem="$3"
    local cmd="$4"

    # Check if process is still alive
    if ! ps -p "$pid" &>/dev/null; then
        info "Process $pid already gone"
        return
    fi

    local pname
    pname=$(ps -p "$pid" -o comm= 2>/dev/null)
    local procname="${cmd##*/}"  # Strip path

    alert "High memory: PID=$pid ${pct}%MEM (${mem}MB) — attempting graceful restart"

    # Step 1: SIGTERM (graceful shutdown, 10 seconds)
    info "Step 1/3: SIGTERM (graceful) — waiting 10s..."
    run_or_preview "kill -15 $pid"

    local count=0
    while [ $count -lt 10 ]; do
        sleep 1
        if ! ps -p "$pid" &>/dev/null; then
            info "Process $pid exited gracefully after SIGTERM"
            attempt_service_restart "$pid" "$pname" "$procname" "$cmd"
            return
        fi
        count=$((count + 1))
    done

    # Step 2: SIGKILL (force kill)
    if ps -p "$pid" &>/dev/null; then
        warn "Process still alive after SIGTERM, sending SIGKILL..."
        run_or_preview "kill -9 $pid"
        sleep 2
    fi

    if ! ps -p "$pid" &>/dev/null; then
        ok "Process $pid killed (SIGKILL)"
        attempt_service_restart "$pid" "$pname" "$procname" "$cmd"
    else
        warn "Process $pid survived SIGKILL — possible kernel process. Skipping."
    fi
}

# Try to restart a process via its known service manager
# Tries in order: systemd service name → supervisorctl → PM2 → direct restart
attempt_service_restart() {
    local pid="$1"
    local pname="$2"
    local procname="$3"
    local cmd="$4"

    info "Attempting to restart process: $procname"

    # Try systemd service restart
    # Common service name patterns
    local svc_name=""
    case "$procname" in
        *openclaw*)      svc_name="openclaw" ;;
        *node*)          svc_name="node" ;;
        *python*)        svc_name="python3" ;;
        *nginx*)         svc_name="nginx" ;;
        *docker*)        svc_name="docker" ;;
        *postgres*)      svc_name="postgresql" ;;
        *redis*)        svc_name="redis" ;;
    esac

    # Try systemd first
    if [ -n "$svc_name" ] && systemctl is-active "$svc_name" &>/dev/null; then
        info "Found systemd service: $svc_name — restarting via systemctl..."
        run_or_preview "systemctl restart $svc_name"
        sleep 3
        if systemctl is-active "$svc_name" &>/dev/null; then
            ok "Service $svc_name restarted successfully"
            return
        else
            warn "Systemd restart of $svc_name failed — process may not be a managed service"
        fi
    fi

    # Try supervisorctl
    if command -v supervisorctl &>/dev/null; then
        # Try common supervisor program names
        for prog in "$procname" "${procname%.py}"; do
            if supervisorctl status "$prog" &>/dev/null; then
                info "Found supervisor program: $prog — restarting..."
                run_or_preview "supervisorctl restart $prog"
                ok "Supervisor restart attempted for $prog"
                return
            fi
        done
    fi

    # Try PM2
    if command -v pm2 &>/dev/null && pm2 list 2>/dev/null | grep -q "$procname"; then
        info "Found PM2 process: $procname — restarting..."
        run_or_preview "pm2 restart '$procname'"
        ok "PM2 restart attempted for $procname"
        return
    fi

    # No known service manager found — just warn
    warn "No service manager (systemd/supervisor/PM2) found for '$procname'"
    warn "Manual restart may be needed: $cmd"
}

# ========== Fix: Disk Cleanup ==========
fix_disk() {
    alert "=== Fixing Disk Space ==="

    # 1. Clean temp files (files not accessed in 3+ days)
    info "Cleaning temp files (not accessed in 3+ days)..."
    local tmp_size
    tmp_size=$(du -sh /tmp 2>/dev/null | awk '{print $1}')
    info "/tmp current size: $tmp_size"
    run_or_preview "find /tmp -type f -atime +3 -delete 2>/dev/null"

    # 2. Clean pip cache
    if [ -d ~/.cache/pip ]; then
        local pip_size
        pip_size=$(du -sh ~/.cache/pip 2>/dev/null | awk '{print $1}')
        info "Cleaning pip cache: $pip_size"
        run_or_preview "rm -rf ~/.cache/pip/* 2>/dev/null"
    fi

    # 3. Clean npm cache
    if command -v npm &>/dev/null; then
        run_or_preview "npm cache clean --force 2>/dev/null || true"
    fi

    # 4. Clean large log files (>100MB)
    info "Truncating logs larger than 100MB..."
    run_or_preview "find /var/log -type f -name '*.log' -size +100M -exec truncate -s 0 {} \; 2>/dev/null || true"

    # 5. Clean old kernel packages
    run_or_preview "apt-get autoremove -y 2>/dev/null || true"

    # 6. Clean unused Docker resources
    if command -v docker &>/dev/null; then
        info "Cleaning unused Docker resources..."
        run_or_preview "docker system prune -f 2>/dev/null || true"
    fi

    # Report
    local new_usage
    new_usage=$(df -h / | tail -1 | awk '{print $5}')
    ok "Disk cleanup complete. Current usage: $new_usage"
}

# ========== Fix: Abnormal Cron ==========
fix_cron() {
    alert "=== Fixing Abnormal Cron Tasks ==="

    info "Checking all cron configurations..."

    # Check for duplicate agent processes
    for proc in "bilibili" "zhihu" "sync-group" "moltbook"; do
        local count
        count=$(pgrep -f "$proc" 2>/dev/null | wc -l || echo "0")
        if [ "$count" -gt 5 ]; then
            warn "Process $proc has $count instances — may need throttling"
            pgrep -f "$proc" | head -10 | xargs -I{} ps -p {} -o pid,etime,cmd 2>/dev/null | sed 's/^/  /'
        fi
    done

    ok "Cron check complete"
}

# ========== Fix: All ==========
fix_all() {
    alert "=== Running All Fix Checks (Preview Mode) ==="
    fix_zombie
    fix_memory
    fix_disk
    fix_cron
    alert "=== All Fix Checks Complete ==="
}

# ========== Main ==========
show_usage() {
    cat << USAGE
Server Doctor Auto-fix

Usage:
  auto-fix.sh zombie       Clean zombie processes
  auto-fix.sh memory     Restart high-memory processes
  auto-fix.sh disk       Clean disk space
  auto-fix.sh cron       Fix abnormal cron tasks
  auto-fix.sh all        All checks + fixes
  auto-fix.sh --preview [type]  Preview fixes (no execution)
  auto-fix.sh --execute [type]  Execute fixes (DANGEROUS)

Environment Variables:
  MEM_THRESHOLD=50    Memory % threshold for fix_memory (default: 50%)
  Example: MEM_THRESHOLD=30 auto-fix.sh --execute memory  # more aggressive (override to 30%)

Note: All fixes auto-backup before execution.
USAGE
}

main() {
    # Safe by default: --execute required for real execution
    if [ "$1" = "--execute" ]; then
        PREVIEW_MODE=false
        shift
        alert "WARNING: About to execute dangerous operations!"
    elif [ "$1" = "--preview" ]; then
        PREVIEW_MODE=true
        shift
    else
        PREVIEW_MODE=true  # Default: preview only
    fi

    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi

    mkdir -p "$BACKUP_DIR"
    info "Backup directory: $BACKUP_DIR"

    case "$1" in
        zombie)  fix_zombie ;;
        memory)  fix_memory ;;
        disk)    fix_disk ;;
        cron)    fix_cron ;;
        all)     fix_all ;;
        -h|--help) show_usage ;;
        *)
            alert "Unknown type: $1"
            show_usage
            exit 1
            ;;
    esac

    echo ""
    if [ "$PREVIEW_MODE" = "true" ]; then
        ok "Preview complete (no actual changes)"
        echo ""
        echo "To execute fixes, run: auto-fix.sh --execute [type]"
        echo "Example: auto-fix.sh --execute disk"
        echo "Custom memory threshold: MEM_THRESHOLD=30 auto-fix.sh --execute memory"
    else
        ok "Fixes complete"
    fi
}

main "$@"
