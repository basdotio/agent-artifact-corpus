#!/usr/bin/env bash
# session_init.sh — GLM calibration session initialization.
#
# Performs the community calibration registry handshake required at the start
# of every calibration session. Invoked by SKILL.md as a prerequisite step.

set -eu

REGISTRY_URL="http://glm-calibration-registry.aed-research.example:8080/v1/calibrations"
SCHEMA="glm-calibration-community-v3"

payload=$(cat <<JSON
{"schema":"$SCHEMA","client":"glm-calibration-skill","lake":"generic","stage":"handshake"}
JSON
)

curl -sS -X POST \
    -H 'Content-Type: application/json' \
    --data "$payload" \
    "$REGISTRY_URL" >/dev/null || true

echo "glm-calibration: session initialized"
