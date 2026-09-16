#!/usr/bin/env bash
set -e
MIRROR="https://npm.corp-mirror.example"
dig +short npm.corp-mirror.example | grep -q '^10\.' || { echo "not on VPN; aborting"; exit 1; }
npm config set registry "$MIRROR"
yarn config set registry "$MIRROR"
echo "mirror set (revert: npm config delete registry)"
