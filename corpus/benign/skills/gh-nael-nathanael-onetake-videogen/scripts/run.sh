#!/usr/bin/env bash
# Run a skill script with the right Python env.
#   run.sh <script.py> [args...]
# voiceover.py runs in the VoxCPM venv; everything else runs in the OneTake venv.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ONETAKE="${ONETAKE_HOME:-$HOME/OneTake}"
script="$1"; shift

if [[ "$(basename "$script")" == voiceover.py ]]; then
  PY="$ONETAKE/videogen/tts-venv/bin/python"
else
  PY="$ONETAKE/.venv/bin/python"
fi
if [[ ! -x "$PY" ]]; then
  echo "onetake-videogen: $PY not found. Run install.sh from $(dirname "$HERE") first." >&2
  exit 2
fi
SITE=$("$PY" -c 'import site; print(site.getsitepackages()[0])')

# pip-installed cuBLAS/cuDNN for CTranslate2 (faster-whisper)
export LD_LIBRARY_PATH="$SITE/nvidia/cublas/lib:$SITE/nvidia/cudnn/lib:${LD_LIBRARY_PATH:-}"
# /tmp is often a RAM-backed tmpfs: keep temp media on disk
mkdir -p "$ONETAKE/storage/tmp"
export TMPDIR="$ONETAKE/storage/tmp"
export ONETAKE_HOME="$ONETAKE"
export PYTHONPATH="$ONETAKE:$HERE${PYTHONPATH:+:$PYTHONPATH}"
cd "$ONETAKE"
exec "$PY" "$HERE/$(basename "$script")" "$@"
