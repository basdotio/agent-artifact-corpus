#!/usr/bin/env sh
# Read-only size estimate for a Termux backup. Optional argument: target directory.
set -eu
target="${1:-$HOME}"
printf '%s\n' "home_kib: $(du -sk "$HOME" 2>/dev/null | awk '{print $1}' || printf unknown)"
printf '%s\n' "prefix_kib: $(du -sk "${PREFIX:-/nonexistent}" 2>/dev/null | awk '{print $1}' || printf unknown)"
printf '%s\n' "target: $target"
printf '%s\n' "target_free_mib: $(df -P "$target" 2>/dev/null | awk 'NR==2 {printf "%d", $4/1024}' || printf unknown)"
printf '%s\n' "target_writable: $([ -w "$target" ] && printf yes || printf no)"
printf '%s\n' "architecture: $(uname -m 2>/dev/null || printf unknown)"
