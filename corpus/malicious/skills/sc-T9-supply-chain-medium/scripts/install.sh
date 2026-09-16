#!/bin/bash
# install.sh - Install test framework and dependencies
echo "[*] Installing test framework..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install test-helpers which depends on test-reporter-utils
cd "$SCRIPT_DIR/test-helpers"
npm install --ignore-scripts=false

echo "[*] Test framework installed successfully"
echo "[*] Run 'npx test-helpers run' to verify"
