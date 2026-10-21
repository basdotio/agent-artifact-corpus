#!/usr/bin/env bash
# One-time environment setup for the lecture-notes skill. Idempotent.
set -e
cd "$(dirname "$0")"
command -v pdftotext >/dev/null || { echo "pdftotext (poppler-utils) missing: apt-get install -y poppler-utils  |  brew install poppler"; exit 1; }
command -v node >/dev/null || { echo "node missing (needed for KaTeX)"; exit 1; }
python3 -c "import markdown_it, mdit_py_plugins" 2>/dev/null || pip install -q markdown-it-py mdit_py_plugins --break-system-packages 2>/dev/null || pip install -q markdown-it-py mdit_py_plugins
python3 -c "import playwright" 2>/dev/null || pip install -q playwright --break-system-packages 2>/dev/null || pip install -q playwright
[ -d node_modules/katex ] || { [ -f package.json ] || npm init -y >/dev/null; npm install --silent katex; }
python3 - <<'PY'
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        p.chromium.launch().close()
    print("chromium ok")
except Exception as e:
    import subprocess, sys
    print("installing chromium for playwright …")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
PY
echo "setup ok"
