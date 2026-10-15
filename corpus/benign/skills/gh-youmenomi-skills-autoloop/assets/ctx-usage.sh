#!/bin/bash
# ctx-usage.sh — approximate context usage of the CURRENT Claude Code session.
#   source of truth: the last assistant message's usage in the session transcript
#   (input + cache_read + cache_creation = tokens sent in the latest request).
# Usage: ctx-usage.sh [threshold-percent]   → prints "ctx=<tokens> window=<tokens> pct=<n> over=<yes|no>"
# Env:   LOOP_CTX_WINDOW overrides the window size (tokens).
set -u
THRESH=${1:-30}
SID=${CLAUDE_CODE_SESSION_ID:-}
[ -z "$SID" ] && { echo "ctx=? window=? pct=? over=unknown (no CLAUDE_CODE_SESSION_ID)"; exit 0; }
PROJ=$(pwd -P | sed 's#[/.]#-#g')   # ~/.claude/projects encodes the cwd this way
F=$(ls -t "$HOME/.claude/projects/$PROJ/$SID.jsonl" 2>/dev/null | head -1)
[ -z "$F" ] && F=$(ls -t "$HOME"/.claude/projects/*/"$SID".jsonl 2>/dev/null | head -1)
[ -z "$F" ] && { echo "ctx=? window=? pct=? over=unknown (transcript not found for $SID)"; exit 0; }
LAST=$(grep '"type":"assistant"' "$F" | tail -1)
CTX=$(printf '%s' "$LAST" | jq -r '.message.usage | ((.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0))' 2>/dev/null)
MODEL=$(printf '%s' "$LAST" | jq -r '.message.model // ""' 2>/dev/null)
[ -z "$CTX" ] || [ "$CTX" = null ] && { echo "ctx=? window=? pct=? over=unknown (no usage in transcript)"; exit 0; }
# Window size: the Claude 5 family (Opus 5.5, Sonnet 5.5, Fable 5.1) runs with a 1M window in
# the desktop app (verified 2026-10-11: a Sonnet 5.5 session at 64,835 tokens showed 7%).
# Older models default to 200k. Override with LOOP_CTX_WINDOW when in doubt.
if [ -n "${LOOP_CTX_WINDOW:-}" ]; then WIN=$LOOP_CTX_WINDOW
else case "$MODEL" in *fable*|*opus-5*|*sonnet-5*|*haiku-5*|*"[1m]"*) WIN=1000000 ;; *) WIN=200000 ;; esac; fi
PCT=$(( CTX * 100 / WIN ))
OVER=no; [ "$PCT" -ge "$THRESH" ] && OVER=yes
echo "ctx=$CTX window=$WIN pct=$PCT over=$OVER model=$MODEL threshold=$THRESH"
