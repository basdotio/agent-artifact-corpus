#!/bin/sh
# Portable entrypoint for any coding agent.
#
#   sh <skill-dir>/scripts/laya.sh selftest
#   printf '%s' '<json>' | sh <skill-dir>/scripts/laya.sh select
#
# Resolves its own directory, so the agent only needs the skill path. POSIX sh, python3 only.
# Override the interpreter with LAYA_PYTHON when python3 is not the right one on PATH.
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY=${LAYA_PYTHON:-python3}

command -v "$PY" >/dev/null 2>&1 || {
    echo '{"status":"unknown","auto_action":false,"error":{"code":"missing_python","message":"python3 not found; set LAYA_PYTHON"}}'
    exit 2
}

exec "$PY" "$DIR/laya.py" "$@"
