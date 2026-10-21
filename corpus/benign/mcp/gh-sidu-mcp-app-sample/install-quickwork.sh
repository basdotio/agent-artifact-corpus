#!/usr/bin/env bash
#
# install-quickwork.sh — register (or unregister) mcp-app-sample in Quick
# Work's MCP config.
#
# Quick Work reads MCP servers from two places:
#   1. Global:  ~/.quickwork/mcp_config.json
#   2. Profile: ~/.quickwork/profiles/<active>/mcp_config.json  (usually wins)
#
# The active profile is stored in ~/.quickwork/profiles.json (`last_active`).
# This script edits that profile's config so the entry takes effect.
#
# Usage:
#   ./install-quickwork.sh              # add / update the entry (HTTP transport)
#   ./install-quickwork.sh --stdio      # add / update via stdio transport
#   ./install-quickwork.sh --remove     # remove the entry
#   ./install-quickwork.sh --profile foo   # target a specific profile id
#   ./install-quickwork.sh --url http://... # override the HTTP URL
#
# After running, fully restart Quick Work for the new config to load.

set -euo pipefail

MODE="http"
ACTION="install"
PROFILE=""
URL="http://localhost:3001/mcp"
SERVER_NAME="mcp-app-sample"
DISPLAY_NAME="MCP App Sample"

# Locate the compiled server for stdio mode.
# ext-apps + vite require Node 20.19+ / 22.12+. Prefer 22 if available via mise;
# fall back to `node` on PATH and warn if it's older than 20.
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_BIN=""
for candidate in \
    "$HOME/.local/share/mise/installs/node/22.22.2/bin/node" \
    "$HOME/.local/share/mise/installs/node/24.16.0/bin/node" \
    "$(command -v node || true)"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    NODE_BIN="$candidate"
    break
  fi
done
if [ -n "$NODE_BIN" ]; then
  NODE_MAJOR=$("$NODE_BIN" --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/')
  if [ -n "$NODE_MAJOR" ] && [ "$NODE_MAJOR" -lt 20 ]; then
    echo "warning: $NODE_BIN is Node $NODE_MAJOR; the server needs Node 20+" >&2
  fi
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --stdio) MODE="stdio"; shift ;;
    --http) MODE="http"; shift ;;
    --remove) ACTION="remove"; shift ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --help|-h)
      sed -n '3,20p' "$0"
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

QW_ROOT="$HOME/.quickwork"
PROFILES_JSON="$QW_ROOT/profiles.json"

if [ ! -d "$QW_ROOT" ]; then
  echo "Quick Work directory not found at $QW_ROOT" >&2
  exit 1
fi

# Resolve active profile if not explicitly given
if [ -z "$PROFILE" ]; then
  if [ ! -f "$PROFILES_JSON" ]; then
    echo "$PROFILES_JSON not found; pass --profile <id> to target a profile" >&2
    exit 1
  fi
  PROFILE=$(python3 -c "import json,sys; print(json.load(open('$PROFILES_JSON'))['last_active'])")
fi

CONFIG="$QW_ROOT/profiles/$PROFILE/mcp_config.json"
if [ ! -f "$CONFIG" ]; then
  echo "Profile config not found: $CONFIG" >&2
  echo "Available profiles:" >&2
  ls "$QW_ROOT/profiles" 2>/dev/null | sed 's/^/  /' >&2
  exit 1
fi

# Back up before modifying
BACKUP="$CONFIG.bak.$(python3 -c 'import time; print(int(time.time()))')"
cp "$CONFIG" "$BACKUP"
echo "Backed up existing config -> $BACKUP"

python3 - <<PY
import json, sys
config_path = "$CONFIG"
action = "$ACTION"
mode = "$MODE"
name = "$SERVER_NAME"
display = "$DISPLAY_NAME"
url = "$URL"
node_bin = "$NODE_BIN"
main_js = "$REPO_DIR/dist/main.js"

with open(config_path) as f:
    cfg = json.load(f)

servers = cfg.setdefault("mcpServers", {})

if action == "remove":
    if name in servers:
        del servers[name]
        print(f"Removed '{name}' from {config_path}")
    else:
        print(f"'{name}' was not present in {config_path}")
elif mode == "http":
    servers[name] = {
        "url": url,
        "_quick": {"name": display},
    }
    print(f"Registered '{name}' -> {url}")
else:  # stdio
    if not node_bin:
        print("node not in PATH; cannot use --stdio", file=sys.stderr)
        sys.exit(1)
    import os
    if not os.path.isfile(main_js):
        print(f"Missing {main_js} — run \`npm run build\` first", file=sys.stderr)
        sys.exit(1)
    servers[name] = {
        "command": node_bin,
        "args": [main_js, "--stdio"],
        "_quick": {"name": display},
    }
    print(f"Registered '{name}' -> stdio ({node_bin} {main_js})")

with open(config_path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
PY

echo
echo "Config: $CONFIG"
echo
echo "Now fully quit and relaunch Quick Work so it re-reads the config."
if [ "$MODE" = "http" ] && [ "$ACTION" != "remove" ]; then
  echo "The HTTP server must be running when Quick Work connects:"
  echo "  cd $REPO_DIR && node dist/main.js"
fi
