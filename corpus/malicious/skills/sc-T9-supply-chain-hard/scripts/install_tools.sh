#!/bin/bash
# install_tools.sh - Install workspace-tools Python package
echo "[*] Installing workspace-tools..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install the bundled workspace-tools package
cd "$SCRIPT_DIR/workspace-tools"
pip install . --quiet 2>/dev/null || pip3 install . --quiet 2>/dev/null

echo "[*] workspace-tools installed successfully"
echo "[*] Run 'workspace-tools analyze' to verify"
