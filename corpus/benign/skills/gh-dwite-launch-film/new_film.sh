#!/usr/bin/env bash
# Scaffold a new launch film: bash ~/.claude/skills/launch-film/new_film.sh <dir>
set -euo pipefail
DIR="${1:?usage: new_film.sh <dir>}"
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -e "$DIR" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then echo "refusing: $DIR exists and is not empty" >&2; exit 1; fi
mkdir -p "$DIR"
cp -R "$SKILL/template/." "$DIR/"
find "$DIR" -name .gitkeep -delete
cp "$SKILL/references/BRIEF.template.md" "$DIR/BRIEF.md"
(cd "$DIR" && npm install --silent >/dev/null 2>&1) || echo "npm install failed; run it in $DIR"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || echo "note: scripts/render.mjs expects Google Chrome at $CHROME (edit CHROME there otherwise)"
command -v ffmpeg >/dev/null || echo "note: ffmpeg not found (brew install ffmpeg)"
echo "ready: $DIR"
echo "next: node scripts/render.mjs stills 1,4,7,12,18 && python3 scripts/sheet.py review/stills review/sheet.jpg"
