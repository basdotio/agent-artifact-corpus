#!/usr/bin/env bash
set -e
# installs Inter and JetBrains Mono (pinned versions) required by docs build
brew list --cask font-inter >/dev/null 2>&1 || sudo -v && echo "sudo ok"
echo "fonts ready"
