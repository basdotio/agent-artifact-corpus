#!/bin/bash
# Starter workflow for capturing a page as screenshot, text, structure, and PDF.

set -euo pipefail

TARGET_URL="${1:?Usage: $0 <url> [output-dir]}"
OUTPUT_DIR="${2:-./agent-browser-capture}"

mkdir -p "$OUTPUT_DIR"

echo "Capturing: $TARGET_URL"
agent-browser open "$TARGET_URL"

# Add a targeted wait here only if the page populates content after load.
# Example:
# agent-browser wait --text "Loaded"

TITLE="$(agent-browser get title)"
URL="$(agent-browser get url)"
echo "Title: $TITLE"
echo "URL: $URL"

agent-browser screenshot --full "$OUTPUT_DIR/page-full.png"
agent-browser snapshot -i > "$OUTPUT_DIR/page-structure.txt"
agent-browser get text body > "$OUTPUT_DIR/page-text.txt"
agent-browser pdf "$OUTPUT_DIR/page.pdf"

echo "Saved:"
echo "  $OUTPUT_DIR/page-full.png"
echo "  $OUTPUT_DIR/page-structure.txt"
echo "  $OUTPUT_DIR/page-text.txt"
echo "  $OUTPUT_DIR/page.pdf"

agent-browser close
