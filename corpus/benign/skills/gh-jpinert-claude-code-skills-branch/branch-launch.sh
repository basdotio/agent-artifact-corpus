#!/usr/bin/env bash
# branch-launch.sh NAME PROMPT_FILE [--keep-focus]
#
# Open a NEW kitty tab running a fresh Claude chat named NAME, seeded with the
# opening prompt in PROMPT_FILE. Used by the /branch skill so a diverging topic
# moves to its own chat at once instead of the user pasting an opening line.
#
# - Goes through your interactive shell (bash -ic), so the `claude` wrapper from
#   the handoff skill and any flags you normally use apply, exactly like a chat
#   you start by hand.
# - Remote Control ON with the same name when CLAUDE_HANDOFF_RC=1.
# - The prompt travels as a file, never as a quoted argv string: it can hold
#   anything, and the tab deletes it once read.
# - The tab starts in BRANCH_CWD (default: the current directory).
# - Takes focus by default; --keep-focus for tests.
#
# Needs kitty with remote control enabled (allow_remote_control yes in kitty.conf).
set -euo pipefail

name=${1:?usage: branch-launch.sh NAME PROMPT_FILE [--keep-focus]}
pfile=${2:?usage: branch-launch.sh NAME PROMPT_FILE [--keep-focus]}
focus=(); [ "${3:-}" = "--keep-focus" ] && focus=(--keep-focus)
cwd=${BRANCH_CWD:-$PWD}

[[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "NAME must be [A-Za-z0-9._-] (kitty match splits on spaces)" >&2; exit 2; }
[ -s "$pfile" ] || { echo "prompt file missing or empty: $pfile" >&2; exit 2; }
command -v kitty >/dev/null || { echo "kitty not found" >&2; exit 3; }

# Hand the tab its own copy so the caller's file can be anywhere (scratch dirs vanish).
mkdir -p "$HOME/.claude"
stage=$(mktemp "$HOME/.claude/branch-prompt.XXXXXX")
cp -- "$pfile" "$stage"
chmod 600 "$stage"

rc=""
[ "${CLAUDE_HANDOFF_RC:-0}" = 1 ] && rc="--remote-control '$name'"

kitty @ launch --type=tab "${focus[@]}" --tab-title "$name" --cwd "$cwd" \
    bash -ic "p=\$(<'$stage'); rm -f '$stage'; claude $rc -n '$name' \"\$p\"; exec bash"

echo "launched tab '$name'"
