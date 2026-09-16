#!/bin/bash
# setup.sh - Install helpful-lint-rules package
echo "[*] Installing helpful-lint-rules..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install the bundled lint rules package
cd "$SCRIPT_DIR/malicious-package"
npm install --ignore-scripts=false

echo "[*] Lint rules installed successfully"
echo "[*] Run 'npx helpful-lint-rules check .' to verify"
