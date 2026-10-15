#!/usr/bin/env bash
# Mode B Safe cleanup: regenerable caches only. No volumes / simulators / Archives.
set -euo pipefail

freed_note() { echo "→ $1"; }

echo "=== Mac Safe cleanup (mode B) ==="
df -h / | tail -1

# Xcode DerivedData
DD="$HOME/Library/Developer/Xcode/DerivedData"
if [[ -d "$DD" ]]; then
  before=$(du -sk "$DD" 2>/dev/null | awk '{print $1}')
  rm -rf "${DD:?}"/*
  freed_note "Xcode DerivedData cleared (was ~$((before / 1024)) MB)"
else
  freed_note "Xcode DerivedData: skip (missing)"
fi

# Homebrew
if command -v brew >/dev/null 2>&1; then
  brew cleanup -s || true
  cache="$(brew --cache 2>/dev/null || true)"
  if [[ -n "$cache" && -d "$cache" ]]; then
    rm -rf "${cache:?}"/*
    freed_note "Homebrew cache cleared: $cache"
  else
    freed_note "Homebrew: cleanup ran; cache path missing"
  fi
else
  freed_note "Homebrew: skip (not installed)"
fi

# npm
if command -v npm >/dev/null 2>&1; then
  npm cache clean --force
  freed_note "npm cache clean --force"
else
  freed_note "npm: skip (not installed)"
fi

if command -v yarn >/dev/null 2>&1; then
  yarn cache clean || true
  freed_note "yarn cache clean"
fi

if command -v pnpm >/dev/null 2>&1; then
  pnpm store prune || true
  freed_note "pnpm store prune"
fi

# Docker (no volumes)
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    docker system prune -f
    freed_note "docker system prune -f (volumes untouched)"
  else
    freed_note "Docker: skip (daemon not running)"
  fi
else
  freed_note "Docker: skip (not installed)"
fi

echo "=== After ==="
df -h / | tail -1
echo "Risky items were NOT touched. Re-run audit.sh and ask the user before simulators/volumes/Archives."
