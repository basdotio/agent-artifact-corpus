#!/bin/sh
# Builds dist/cover-letter-builder.zip for upload to Claude.ai skills settings.
# Includes only the files the skill reads at runtime, with your private
# context.md and template.tex. Examples, README, and scripts are left out.
set -eu

cd "$(dirname "$0")"

NAME=cover-letter-builder
STAGE="dist/$NAME"
ZIP="dist/$NAME.zip"

missing=0
if [ ! -f references/context.md ]; then
  echo "error: references/context.md is missing." >&2
  echo "  Run: cp references/context.example.md references/context.md  (then fill it in)" >&2
  missing=1
fi
if [ ! -f assets/template.tex ]; then
  echo "error: assets/template.tex is missing." >&2
  echo "  Run: cp assets/template.example.tex assets/template.tex  (then fill in USER CONFIG)" >&2
  missing=1
fi
[ "$missing" -eq 0 ] || exit 1

command -v zip >/dev/null 2>&1 || { echo "error: 'zip' not found on PATH." >&2; exit 1; }

rm -rf "$STAGE" "$ZIP"
mkdir -p "$STAGE/references" "$STAGE/assets"
cp SKILL.md "$STAGE/"
cp references/style.md references/context.md "$STAGE/references/"
cp assets/template.tex "$STAGE/assets/"

(cd dist && zip -qr -X "$NAME.zip" "$NAME")

echo "Built $ZIP"
