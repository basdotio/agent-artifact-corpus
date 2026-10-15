#!/usr/bin/env bash
# Run a scene script headless.   scripts/blender.sh examples/igloo.py --still 120 --res 960 540
set -euo pipefail
B="${BLENDER:-}"
if [ -z "$B" ]; then
  if command -v blender >/dev/null 2>&1; then B=blender
  elif [ -x /Applications/Blender.app/Contents/MacOS/Blender ]; then B=/Applications/Blender.app/Contents/MacOS/Blender
  else
    echo "Blender not found. macOS: brew install --cask blender | Linux: sudo snap install blender --classic | or https://www.blender.org/download/" >&2
    exit 1
  fi
fi
script="$1"; shift
exec "$B" -b -P "$script" -- "$@"
