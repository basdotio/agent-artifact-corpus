#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
exec uv run \
  --with fastmcp \
  "$SCRIPT_DIR/grep-app-mcp.py" "$@"
