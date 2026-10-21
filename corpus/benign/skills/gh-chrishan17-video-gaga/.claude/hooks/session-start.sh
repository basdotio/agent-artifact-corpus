#!/bin/bash
# Cloud sessions start from a fresh container: install edge-tts for scripts/tts.py.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
python3 -c "import edge_tts" 2>/dev/null || python3 -m pip install -q edge-tts
