#!/usr/bin/env bash
# Starts the FastMCP test server locally as a remote (HTTP) MCP server.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d .venv ]; then
  echo "Creating virtual environment in .venv..."
  python3 -m venv .venv
fi

.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "Starting MCP server at http://0.0.0.0:8000/mcp"
echo "In this codespace, forward port 8000 to reach it from outside, or test locally with:"
echo "  fastmcp inspect main.py:mcp"
echo ""

exec .venv/bin/python main.py
