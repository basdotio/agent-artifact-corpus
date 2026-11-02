#!/bin/bash
TEXT=$1
VOICE=${2:-JARVIS}
LANG=${3:-es}
OUTPUT_FILE="/tmp/tts_$(date +%s).wav"

curl -s -X POST http://sphinx.espuny.net:5100/v1/audio/speech \
     -F "input=$TEXT" \
     -F "voice=$VOICE" \
     -F "language=$LANG" \
     --output "$OUTPUT_FILE"

echo "$OUTPUT_FILE"
