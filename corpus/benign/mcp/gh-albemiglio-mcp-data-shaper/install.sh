#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=== mcp-data-shaper — Setup ==="

# Prefer a real Python (not the macOS /usr/bin/python3 stub that triggers Xcode dialogs).
# Search for Python 3.12 or 3.11 from known real locations first.
REAL_PYTHON=""
for candidate in \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 \
    /opt/homebrew/bin/python3.12 \
    /opt/homebrew/bin/python3.11 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3.12 \
    /usr/local/bin/python3.11 \
    /usr/local/bin/python3; do
  if [ -x "$candidate" ] && "$candidate" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    REAL_PYTHON="$candidate"
    break
  fi
done

if [ -z "$REAL_PYTHON" ]; then
  echo "ERROR: No suitable Python 3.10+ found. Install Python from python.org or via Homebrew."
  exit 1
fi

PYTHON_VERSION=$("$REAL_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python $PYTHON_VERSION detected at $REAL_PYTHON."

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$REAL_PYTHON" -m venv .venv
fi

source .venv/bin/activate
echo "Virtual environment activated."

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "=== mcp-data-shaper — Installation complete! ==="
echo ""
echo "Credentials needed (set once in claude_desktop_config.json → env):"
echo "  OPENAI_API_KEY   — for OpenAI models (gpt-4o, gpt-5.2, ...)"
echo "  GEMINI_API_KEY   — for Gemini models (gemini-3-flash, ...)"
echo ""
echo "Python binary: $(pwd)/.venv/bin/python"
echo "Server script: $(pwd)/server.py"
