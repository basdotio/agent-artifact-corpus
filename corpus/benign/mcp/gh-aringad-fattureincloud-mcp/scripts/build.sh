#!/usr/bin/env bash
# Build the MCPB bundle for Claude Desktop one-click install.
# Usage: ./scripts/build.sh
#
# Bundle ships pre-built lib/ with Python 3.12 wheels. Claude Desktop on macOS
# resolves `python3` (from its spawn PATH) to /usr/local/opt/python@3.12/bin/python3,
# so building lib/ with the same Python version avoids native-extension ABI
# mismatches (e.g. pydantic_core._pydantic_core).
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v mcpb >/dev/null 2>&1; then
  echo "ERROR: 'mcpb' CLI not found. Install with:" >&2
  echo "  npm install -g @anthropic-ai/mcpb" >&2
  exit 1
fi

# Pick the Python interpreter Claude Desktop will use.
# Order: explicit override > python3.12 in PATH > /usr/local/opt/python@3.12 > fallback python3.
BUILD_PYTHON="${BUILD_PYTHON:-}"
if [[ -z "$BUILD_PYTHON" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    BUILD_PYTHON=$(command -v python3.12)
  elif [[ -x /usr/local/opt/python@3.12/bin/python3.12 ]]; then
    BUILD_PYTHON=/usr/local/opt/python@3.12/bin/python3.12
  else
    BUILD_PYTHON=$(command -v python3)
    echo "WARNING: python3.12 not found, falling back to $BUILD_PYTHON ($("$BUILD_PYTHON" --version))." >&2
    echo "         Claude Desktop may pick a different Python, causing ABI mismatches." >&2
  fi
fi

echo "==> Build Python: $BUILD_PYTHON ($("$BUILD_PYTHON" --version 2>&1))"

echo "==> Cleaning previous build artifacts"
rm -rf lib/ dist/
mkdir -p lib dist

echo "==> Installing runtime dependencies into lib/"
"$BUILD_PYTHON" -m pip install --target lib --quiet --no-cache-dir -r requirements.txt

echo "==> Packing MCPB"
mcpb pack . dist/fattureincloud.mcpb

echo
echo "==> Bundle ready"
ls -lh dist/fattureincloud.mcpb
