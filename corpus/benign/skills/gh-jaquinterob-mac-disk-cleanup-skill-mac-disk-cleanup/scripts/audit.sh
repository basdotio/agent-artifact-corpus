#!/usr/bin/env bash
# Audit common regenerable caches on macOS (Xcode, Homebrew, npm, Docker).
set -euo pipefail

hr() { printf '%s\n' "----------------------------------------"; }

echo "=== Mac disk audit ==="
hr
df -h /
hr

size_of() {
  local path="$1"
  if [[ -e "$path" ]]; then
    du -sh "$path" 2>/dev/null | awk '{print $1}'
  else
    echo "(missing)"
  fi
}

echo "Xcode DerivedData:     $(size_of "$HOME/Library/Developer/Xcode/DerivedData")"
echo "Xcode Archives:        $(size_of "$HOME/Library/Developer/Xcode/Archives")"
echo "iOS DeviceSupport:     $(size_of "$HOME/Library/Developer/Xcode/iOS DeviceSupport")"
echo "CoreSimulator devices: $(size_of "$HOME/Library/Developer/CoreSimulator/Devices")"
echo "Homebrew cache:        $(size_of "${HOMEBREW_CACHE:-$HOME/Library/Caches/Homebrew}")"
echo "npm cache (~/.npm):    $(size_of "$HOME/.npm")"

if command -v brew >/dev/null 2>&1; then
  hr
  echo "Homebrew (brew cleanup -n dry-run, last lines):"
  brew cleanup -n 2>/dev/null | tail -15 || true
fi

if command -v docker >/dev/null 2>&1; then
  hr
  echo "Docker:"
  if docker info >/dev/null 2>&1; then
    docker system df
  else
    echo "(Docker installed but daemon not running — start Docker Desktop / Colima / Rancher to audit)"
  fi
else
  hr
  echo "Docker: (not installed)"
fi

hr
echo "Safe tier candidates: DerivedData, brew cache, npm cache, docker system prune (no volumes)."
echo "Risky tier candidates: Simulator runtimes, DeviceSupport, docker prune --volumes, Archives."
