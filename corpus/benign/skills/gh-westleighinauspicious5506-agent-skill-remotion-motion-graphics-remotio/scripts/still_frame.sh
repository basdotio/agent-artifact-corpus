#!/usr/bin/env bash
# Extract one frame from a rendered MP4 at a timestamp (seconds) for a
# close-up check of a single moment. Usage: still_frame.sh <mp4> <seconds> <out.png>
set -euo pipefail
ffmpeg -v error -y -ss "$2" -i "$1" -frames:v 1 -vf scale=960:-1 "$3" && echo "$3"
