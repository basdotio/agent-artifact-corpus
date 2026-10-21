#!/usr/bin/env bash
# Interactive secret input on Butcher; does not print or log the key.
set -euo pipefail
umask 077

dir="${TUNNEL_CLIENT_PROFILE_DIR:-$HOME/.config/tunnel-client}"
key_file="$dir/windanvil-runtime-key"
if [[ ! -t 0 ]]; then
  echo "Run directly in an interactive terminal on Butcher." >&2
  exit 2
fi
mkdir -p "$dir"
chmod 0700 "$dir"
if [[ -L "$key_file" ]]; then
  echo "BLOCKED: runtime key path is a symlink." >&2
  exit 2
fi
read -r -s -p "Paste Restricted Tunnels Read + Use API key (not in chat): " secret
printf '\n'
if [[ ! "$secret" == sk-* || ${#secret} -lt 24 || ${#secret} -gt 2048 ]]; then
  unset secret
  echo "BLOCKED: invalid API key shape." >&2
  exit 2
fi
temp="$(mktemp "$dir/.windanvil-runtime-key.XXXXXXXX")"
trap 'rm -f -- "$temp"' EXIT
printf '%s' "$secret" > "$temp"
unset secret
chmod 0600 "$temp"
mv -f -- "$temp" "$key_file"
trap - EXIT
echo "Restricted runtime key provisioned locally (mode 0600). No value displayed."
