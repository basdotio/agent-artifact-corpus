#!/usr/bin/env bash
# Runs one golden set against the same three tools written for mcp 1.30.0 and mcp 2.2.0
# and prints what differs. Needs uv. No network calls beyond installing the two SDK versions.
set -uo pipefail
cd "$(dirname "$0")/../.."

uv run mcp-eval-gate compare \
  --config validation/sdk-1x-vs-2x/golden_set.yaml \
  --against "uv run --no-project --with mcp==2.2.0 python validation/sdk-1x-vs-2x/server_v2.py" \
  2>/dev/null
echo "exit code: $?"
