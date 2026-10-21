#!/usr/bin/env bash
set -euo pipefail

EXT_NAME=${EXT_NAME:-chime}        # archive {name}
STAGE_DIR=".pack"
OUT_DIR="release"

# 0) sanity check
[[ -f "gemini-extension.json" ]] || { echo "gemini-extension.json not found at repo root"; exit 1; }

# 1) clean + stage
rm -rf "$STAGE_DIR" "$OUT_DIR"
mkdir -p "$STAGE_DIR" "$OUT_DIR"

# 2) copy only what the extension needs; ensure gemini-extension.json is at archive root
#    add/remove lines to match your project layout
cp gemini-extension.json "$STAGE_DIR/"
cp package.json "$STAGE_DIR/" || true
cp README* "$STAGE_DIR/" 2>/dev/null || true
cp LICENSE* "$STAGE_DIR/" 2>/dev/null || true
[ -d dist ] && cp -R dist "$STAGE_DIR/dist"
[ -d commands ] && cp -R commands "$STAGE_DIR/commands"
[ -d out ]  && cp -R out  "$STAGE_DIR/out"
# If your extension needs runtime deps, include prod node_modules:
# npm ci --omit=dev
# cp -R node_modules "$STAGE_DIR/node_modules"

# 3) create archives per naming convention
tar -C "$STAGE_DIR" -czf "$OUT_DIR/darwin.arm64.${EXT_NAME}.tar.gz" .
tar -C "$STAGE_DIR" -czf "$OUT_DIR/linux.x64.${EXT_NAME}.tar.gz" .
(cd "$STAGE_DIR" && zip -qr "../$OUT_DIR/win32.x64.${EXT_NAME}.zip" .)

# 4) show results
echo "== ls release =="
ls -al "$OUT_DIR"
