#!/usr/bin/env bash
# Configure a private OpenAI Secure MCP Tunnel to WindAnvil Commander stdio MCP.
# Runtime secret uses a local 0600 file reference, never an inline profile key.
set -euo pipefail
umask 077

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
client="${TUNNEL_CLIENT_BIN:-$HOME/.local/bin/tunnel-client}"
python="${TALKPIPE_PYTHON:-$HOME/lab/talkpipe-runtime/.venv/bin/python}"
profile_dir="${TUNNEL_CLIENT_PROFILE_DIR:-$HOME/.config/tunnel-client}"
profile="${TUNNEL_CLIENT_PROFILE:-windanvil-commander}"
runtime_key="$profile_dir/windanvil-runtime-key"

usage() {
  printf 'Usage: %s preflight|configure|doctor|run\n' "${0##*/}" >&2
  printf 'Configuration requires CONTROL_PLANE_TUNNEL_ID.\n' >&2
  printf 'Doctor/run require an operator-installed private runtime key with Tunnels Read + Use.\n' >&2
  exit 2
}
test -x "$client" || { echo "tunnel-client not executable: $client" >&2; exit 2; }
test -x "$python" || { echo "TalkPipe Python environment unavailable: $python" >&2; exit 2; }
test -f "$root/windanvil_commander_mcp.py" || { echo "TalkPipe MCP source unavailable" >&2; exit 2; }

mode="${1:-}"
case "$mode" in
  preflight)
    exec "$python" "$root/scripts/commander-preflight.py"
    ;;
  configure)
    id="${CONTROL_PLANE_TUNNEL_ID:-}"
    if [[ ! "$id" =~ ^tunnel_[A-Za-z0-9_-]{10,128}$ ]]; then
      echo "Set CONTROL_PLANE_TUNNEL_ID from OpenAI Platform tunnel settings." >&2
      exit 2
    fi
    mkdir -p "$profile_dir"
    chmod 0700 "$profile_dir"
    "$client" init --sample sample_mcp_stdio_local \
      --profile "$profile" --profile-dir "$profile_dir" \
      --tunnel-id "$id" \
      --control-plane-api-key-ref "file:$runtime_key" \
      --health-listen-addr 127.0.0.1:0 \
      --mcp-command "$python -u $root/windanvil_commander_mcp.py"
    echo "Local tunnel profile configured. No key was written."
    ;;
  doctor|run)
    if [[ ! -f "$runtime_key" || -L "$runtime_key" ||
          "$(stat -c '%a %u' "$runtime_key")" != "600 $(id -u)" ]]; then
      echo "Restricted runtime key missing or insecure; run scripts/install-tunnel-runtime-key.sh interactively on Butcher." >&2
      exit 2
    fi
    if [[ "$mode" == doctor ]]; then
      exec "$client" doctor --profile "$profile" --profile-dir "$profile_dir" --explain
    fi
    exec "$client" run --profile "$profile" --profile-dir "$profile_dir"
    ;;
  *) usage ;;
esac
