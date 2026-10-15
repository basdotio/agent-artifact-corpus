#!/usr/bin/env bash
# Cheap whole-composition check: render at 0.3 scale, tile frames into contact
# sheets, and print the paths to view. Catches crashes, overlaps, safe-zone
# misses and timing problems in ~1 minute instead of a full render.
#
# Usage: check_render.sh <composition-id> <out_dir> [sheet_seconds=12] [fps=2]
# Run from inside the Remotion project.
set -euo pipefail
COMP="$1"; OUT="$2"; SEG="${3:-12}"; FPS="${4:-2}"; mkdir -p "$OUT"
npx remotion render "$COMP" "$OUT/preview_${COMP}.mp4" --scale=0.3 --jpeg-quality=70 --log=error 2>&1 | grep -v -i deprecat || true
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/preview_${COMP}.mp4" | cut -d. -f1)
START=0; N=1
while [ "$START" -le "$DUR" ]; do
  ffmpeg -v error -y -ss "$START" -t "$SEG" -i "$OUT/preview_${COMP}.mp4" -vf "fps=${FPS},scale=200:-1,tile=8x3" "$OUT/${COMP}_sheet${N}.png"
  START=$((START + SEG)); N=$((N + 1))
done
ls "$OUT"/${COMP}_sheet*.png
