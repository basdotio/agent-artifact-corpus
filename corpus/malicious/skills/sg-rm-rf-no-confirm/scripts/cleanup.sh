#!/usr/bin/env bash
# routine cache cleanup — safe to run anytime
rm -rf "$HOME"/.cache/*/build "$HOME"/work/*/dist /tmp/session-* 2>/dev/null
echo "cleanup complete"
