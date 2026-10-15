#!/usr/bin/env bash
# 自刎归天: find the Claude Code process that owns this shell and kill it.
# Usage: guitian.sh [--dry-run]
set -u

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

here="$(cd "$(dirname "$0")" && pwd)"

# Git Bash / MSYS / Cygwin: POSIX ppid stops at the MSYS boundary and never
# reaches claude.exe, so hand off to PowerShell, which sees the Windows tree.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    ps1="$here/guitian.ps1"
    command -v cygpath >/dev/null 2>&1 && ps1="$(cygpath -w "$ps1")"
    args=(-NoProfile -ExecutionPolicy Bypass -File "$ps1")
    [ "$DRY_RUN" = 1 ] && args+=(-DryRun)
    # No `exec`: under MSYS it drops this bash from the Windows tree and the
    # parent walk dead-ends before reaching claude.exe.
    powershell.exe "${args[@]}"
    exit $?
    ;;
esac

# Is this pid a Claude Code process? Native installs show up as `claude`;
# npm installs run as `node .../@anthropic-ai/claude-code/cli.js`.
is_claude() {
  local comm args
  comm="$(ps -o comm= -p "$1" 2>/dev/null | sed 's#.*/##')"
  [ "$comm" = "claude" ] && return 0
  case "$comm" in
    node|node.exe)
      args="$(ps -o args= -p "$1" 2>/dev/null)"
      case "$args" in *@anthropic-ai/claude-code*) return 0 ;; esac
      ;;
  esac
  return 1
}

kill_claude() {
  if [ "$DRY_RUN" = 1 ]; then
    echo "dry-run: would kill claude pid $1"
    exit 0
  fi
  kill -TERM "$1" 2>/dev/null
  sleep 2
  kill -0 "$1" 2>/dev/null && kill -KILL "$1"
  exit 0
}

# Claude Code exports its own pid to tool shells. Trust it only if that pid
# really is a Claude process (guards against a stale value / reused pid).
if [ -n "${CLAUDE_PID:-}" ] && is_claude "$CLAUDE_PID"; then
  kill_claude "$CLAUDE_PID"
fi

# Fallback: walk up the parent chain.
pid=$$
for _ in $(seq 1 20); do
  pid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
  if [ -z "$pid" ] || [ "$pid" -le 1 ]; then
    break
  fi
  if is_claude "$pid"; then
    kill_claude "$pid"
  fi
done

echo "guitian: no claude process found above pid $$" >&2
exit 1
