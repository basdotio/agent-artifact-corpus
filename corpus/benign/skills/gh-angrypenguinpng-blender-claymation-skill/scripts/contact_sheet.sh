#!/usr/bin/env bash
# Tile every Nth frame into one image to review story beats at a glance.
# usage: scripts/contact_sheet.sh <frames_dir> <out.jpg> [every=20] [cols=4]
set -euo pipefail
dir="$1"; out="$2"; every="${3:-20}"; cols="${4:-4}"
n=$(ls "$dir"/[0-9][0-9][0-9][0-9].png | wc -l | tr -d ' ')
rows=$(( (n / every + cols) / cols ))
ffmpeg -y -loglevel error -framerate 12 -i "$dir/%04d.png" \
  -vf "select='not(mod(n\,$every))',scale=480:-1,tile=${cols}x${rows}" -frames:v 1 "$out"
echo "$out ($n frames, every $every)"
