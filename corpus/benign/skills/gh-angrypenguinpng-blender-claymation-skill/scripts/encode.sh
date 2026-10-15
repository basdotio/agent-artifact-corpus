#!/usr/bin/env bash
# 12 fps PNG frames -> 24 fps H.264 with light film grain + vignette.
# usage: scripts/encode.sh <frames_dir> <out.mp4> [fps=12]
set -euo pipefail
dir="$1"; out="$2"; fps="${3:-12}"
ffmpeg -y -loglevel error -framerate "$fps" -i "$dir/%04d.png" \
  -vf "noise=alls=3:allf=t,vignette=angle=PI/6,fps=24,format=yuv420p" \
  -c:v libx264 -preset slow -crf 19 -movflags +faststart "$out"
ffprobe -v error -show_entries stream=width,height:format=duration,size -of compact "$out"
