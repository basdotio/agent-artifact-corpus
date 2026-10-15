#!/usr/bin/env bash
# Break a reference video into contact sheets so its motion can be mapped beat
# by beat (backgrounds, cuts, text timing, transitions) before writing scenes.
#
# Usage: analyze_reference.sh <video> <out_dir>
# Produces: <out_dir>/overview.png (1 fps, whole video) and
#           <out_dir>/seg_<start>s.png (4 fps, 8-second windows, 32 frames each)
set -euo pipefail
VIDEO="$1"; OUT="$2"; mkdir -p "$OUT"
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of default=noprint_wrappers=1 "$VIDEO" | tee "$OUT/probe.txt"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO" | cut -d. -f1)
COLS=6; ROWS=$(( (DUR + COLS) / COLS ))
ffmpeg -v error -y -i "$VIDEO" -vf "fps=1,scale=180:-1,tile=${COLS}x${ROWS}" "$OUT/overview.png"
START=0
while [ "$START" -lt "$DUR" ]; do
  ffmpeg -v error -y -ss "$START" -t 8 -i "$VIDEO" -vf "fps=4,scale=160:-1,tile=8x4" "$OUT/seg_${START}s.png"
  START=$((START + 8))
done
echo "wrote $(ls "$OUT"/*.png | wc -l | tr -d ' ') sheets to $OUT — read them with the image viewer and write the beat map"
