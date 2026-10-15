#!/bin/bash
# autoloop run-round.sh — start ONE loop round as an independent `claude -p` process.
# Lives in the installed skill (~/.claude/skills/autoloop/assets); repos call it through the
# two-line stub scripts/harness/run-round.sh. Version: ../VERSION next to this file.
#
#   scripts/harness/run-round.sh <fable|opus> [--model ID] [--effort L] [--timeout SEC]
#                                             [--budget USD] [--prompt FILE]
#
# Exit codes: 0 round process finished (read the summary for its outcome)
#             75 another round is already running in this repo
#             124 round timed out and was killed
#             2 bad usage / missing files
#
# What it guarantees, whoever the worker is:
#   - the worker runs in its own process group; on timeout the whole group is killed
#   - after the worker exits, leftover processes whose cwd is inside this repo are killed
#     (the app's own processes and this script's ancestors are never touched)
#   - a .loop.lock left behind by a dead worker is removed
#   - the worker's JSON goes to logs/loop/<ts>-<role>.json, a one-line summary next to it
set -u
LOOP_HOME=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)   # prompts and VERSION live here
ROOT=${LOOP_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}
cd "$ROOT" || exit 2

ROLE=${1:-}; shift || true
case "$ROLE" in
  # Models/efforts: override per repo with LOOP_MODEL_DECIDE / LOOP_MODEL_IMPLEMENT /
  # LOOP_EFFORT_DECIDE / LOOP_EFFORT_IMPLEMENT in .claude/settings.json "env".
  fable) MODEL=${LOOP_MODEL_DECIDE:-claude-fable-5-1}; EFFORT=${LOOP_EFFORT_DECIDE:-high}; PROMPT="$LOOP_HOME/decide.md" ;;
  opus)  MODEL=${LOOP_MODEL_IMPLEMENT:-claude-opus-5-5}; EFFORT=${LOOP_EFFORT_IMPLEMENT:-high}; PROMPT="$LOOP_HOME/implement.md" ;;
  sweep) ;;  # cleanup only: kill leftovers under this repo, remove dead locks, start nothing
  *) echo "usage: run-round.sh <fable|opus|sweep> [--model ID] [--effort L] [--timeout SEC] [--budget USD] [--prompt FILE]" >&2; exit 2 ;;
esac
# Defaults from real rounds in threejs-character (Opus high, Blender gens, full CI): 30–52 min.
# Override per repo with LOOP_TIMEOUT / LOOP_BUDGET in .claude/settings.json "env".
TIMEOUT=${LOOP_TIMEOUT:-5400}
BUDGET=${LOOP_BUDGET:-20}
while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL=$2; shift 2 ;;
    --effort) EFFORT=$2; shift 2 ;;
    --timeout) TIMEOUT=$2; shift 2 ;;
    --budget) BUDGET=$2; shift 2 ;;
    --prompt) PROMPT=$2; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
CLAUDE=${CLAUDE_BIN:-$HOME/.local/bin/claude}
[ -x "$CLAUDE" ] || { echo "claude CLI not found at $CLAUDE" >&2; exit 2; }
[ "$ROLE" = sweep ] || [ -f "$PROMPT" ] || { echo "prompt file not found: $PROMPT" >&2; exit 2; }

LOGDIR=$ROOT/logs/loop; mkdir -p "$LOGDIR"
TS=$(date +%Y%m%d-%H%M%S)
OUT=$LOGDIR/$TS-$ROLE.json; ERR=$LOGDIR/$TS-$ROLE.err; SUM=$LOGDIR/$TS-$ROLE.summary
RUNLOCK=$ROOT/.loop-round.pid

# --- one round per repo -------------------------------------------------------
if [ -f "$RUNLOCK" ]; then
  OLD=$(cat "$RUNLOCK" 2>/dev/null)
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    echo "BUSY: round pid $OLD is still running (lock $RUNLOCK)" >&2; exit 75
  fi
  # The previous round's runner is dead, so no round is running: its .loop.lock is stale
  # whatever its mtime says (the 30-minute heartbeat rule is for rounds we don't own).
  echo "stale $RUNLOCK (pid $OLD dead) removed" >&2; rm -f "$RUNLOCK" "$ROOT/.loop.lock"
fi
echo $$ > "$RUNLOCK"

# --- processes this script must never kill: itself and its ancestors ---------
SAFE=" $$ "
p=$PPID
while [ "$p" -gt 1 ] 2>/dev/null; do SAFE="$SAFE$p "; p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' '); [ -z "$p" ] && break; done

# Leftover policy: a process is swept only if its cwd is inside this repo AND its command
# looks like a build/test/server tool. Shells, editors, the Claude app and this script's
# own process tree are never touched, so a terminal the user left open in the repo survives.
SWEEP_PATTERN=${LOOP_SWEEP_PATTERN:-'(^|/)(vite|node|npm|npx|pnpm|yarn|tsc|esbuild|blender|cargo|rustc|playwright|chrom[a-z]*|python3?|tail|watchman)( |$)'}
KILLED=""
sweep() {  # sets KILLED="<pid>(<cmd>) ..." — no subshell, so the list survives
  KILLED=""
  while read -r pid cwd; do
    [ -z "$pid" ] && continue
    case "$SAFE" in *" $pid "*) continue ;; esac
    local cmd; cmd=$(ps -o command= -p "$pid" 2>/dev/null)
    [ -z "$cmd" ] && continue
    case "$cmd" in *Claude.app*|*"Claude Helper"*|*claude-code/*|*"$CLAUDE"*) continue ;; esac
    echo "$cmd" | grep -qE "$SWEEP_PATTERN" || continue
    kill -TERM "$pid" 2>/dev/null && KILLED="$KILLED $pid($(echo "$cmd" | cut -c1-30 | tr ' ' '_'))"
  done < <(lsof -a -d cwd -u "$(id -un)" -Fpn 2>/dev/null | awk -v root="$ROOT" '
      /^p/ {pid=substr($0,2)} /^n/ {d=substr($0,2); if (index(d, root)==1) print pid, d}')
  if [ -n "$KILLED" ]; then sleep 2; for k in $KILLED; do kill -KILL "${k%%(*}" 2>/dev/null; done; fi
}

if [ "$ROLE" = sweep ]; then
  sweep; NOTE=""
  if [ -f "$ROOT/.loop.lock" ]; then NOTE=" lock=removed($(head -c 120 "$ROOT/.loop.lock" | tr '\n' ' '))"; rm -f "$ROOT/.loop.lock"; fi
  rm -f "$RUNLOCK"
  echo "sweep: killed=[${KILLED# }]$NOTE"; exit 0
fi

# --- launch the worker in its own process group --------------------------------
START=$(date +%s)
perl -e 'setpgrp(0,0); exec @ARGV or die "exec: $!"' -- \
  "$CLAUDE" -p "$(cat "$PROMPT")" \
  --permission-mode auto --permission-prompts none \
  --model "$MODEL" --effort "$EFFORT" --max-budget-usd "$BUDGET" \
  --output-format json > "$OUT" 2> "$ERR" < /dev/null &
PID=$!
echo "round started: role=$ROLE model=$MODEL effort=$EFFORT pid=$PID timeout=${TIMEOUT}s log=$OUT"
# If this script is stopped (TaskStop, Ctrl-C, kill), take the worker group down with it.
# The stopper (TaskStop) may SIGKILL this script moments after the TERM, so do the
# cheap, important things first: free the locks and write the summary; sweep last.
on_signal() {
  trap - TERM INT HUP
  kill -TERM -- "-$PID" 2>/dev/null
  rm -f "$ROOT/.loop.lock" "$RUNLOCK"
  echo "$TS $ROLE $MODEL exit=130 $(( $(date +%s) - START ))s interrupted | LOOP-STATUS: INTERRUPTED — run-round was stopped by a signal; worker group $PID killed" | tee "$SUM"
  kill -KILL -- "-$PID" 2>/dev/null
  sweep
  exit 130
}
trap on_signal TERM INT HUP

TIMED_OUT=0
while kill -0 "$PID" 2>/dev/null; do
  if [ $(( $(date +%s) - START )) -ge "$TIMEOUT" ]; then
    echo "TIMEOUT after ${TIMEOUT}s: killing process group $PID" >&2
    kill -TERM -- "-$PID" 2>/dev/null; sleep 5; kill -KILL -- "-$PID" 2>/dev/null
    TIMED_OUT=1; break
  fi
  sleep 2
done
wait "$PID" 2>/dev/null; EXIT=$?
kill -KILL -- "-$PID" 2>/dev/null   # anything left in the group
ELAPSED=$(( $(date +%s) - START ))

# --- cleanup --------------------------------------------------------------------
sweep
LOCK_NOTE=""
if [ -f "$ROOT/.loop.lock" ]; then LOCK_NOTE=" lock=removed($(head -c 120 "$ROOT/.loop.lock" | tr '\n' ' '))"; rm -f "$ROOT/.loop.lock"; fi
rm -f "$RUNLOCK"

# --- summary --------------------------------------------------------------------
if [ "$TIMED_OUT" = 1 ]; then
  STATUS="LOOP-STATUS: TIMEOUT (killed after ${TIMEOUT}s)"
  IS_ERR=true; DENIALS=0; COST=0; TURNS=0
elif jq -e . "$OUT" >/dev/null 2>&1; then
  IS_ERR=$(jq -r '.is_error' "$OUT"); DENIALS=$(jq -r '.permission_denials | length' "$OUT")
  COST=$(jq -r '.total_cost_usd // 0 | . * 100 | round / 100' "$OUT"); TURNS=$(jq -r '.num_turns // 0' "$OUT")
  STATUS=$(jq -r '.result // ""' "$OUT" | grep -E '^LOOP-STATUS:' | tail -1)
  [ -z "$STATUS" ] && STATUS="LOOP-STATUS: UNKNOWN (no status line; result: $(jq -r '.result // ""' "$OUT" | head -c 200 | tr '\n' ' '))"
else
  STATUS="LOOP-STATUS: ERROR (no JSON; exit=$EXIT; stderr: $(head -c 200 "$ERR" | tr '\n' ' '))"
  IS_ERR=true; DENIALS=0; COST=0; TURNS=0
fi
SUMMARY="$TS $ROLE $MODEL exit=$EXIT ${ELAPSED}s turns=$TURNS cost=\$$COST is_error=$IS_ERR denials=$DENIALS killed=[${KILLED# }]$LOCK_NOTE | $STATUS"
echo "$SUMMARY" | tee "$SUM"
[ "$TIMED_OUT" = 1 ] && exit 124
exit 0
