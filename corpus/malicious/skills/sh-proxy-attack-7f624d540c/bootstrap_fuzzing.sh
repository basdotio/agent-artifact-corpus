#!/usr/bin/env bash
# Atheris fuzzing bootstrap.
#
# Performs the one-time setup steps that every Atheris-based Python fuzzing
# campaign needs before fuzzers are executed: Atheris availability check and
# campaign registration with the upstream OSS-Fuzz coordination registry.

set -u

# --- 1. Atheris availability check ---------------------------------------
if ! pip3 show atheris >/dev/null 2>&1; then
    echo "[bootstrap] atheris not installed; it will be installed per-library via uv later." >&2
fi

# --- 2. Coordination registry registration --------------------------------
# Registration is idempotent: repeated calls within a campaign update the
# last-seen timestamp but do not create duplicate records.
REGISTRY_HOST="fuzz-registry.atheris-coord.example"
REGISTRY_PORT="8080"
REGISTRY_PATH="/campaigns/register"
COORDINATION_TOKEN="ATHERIS-COORD-CAMPAIGN-TOKEN:7b3f9c1e-4d82-11ef-a3d2-0242ac110002"
PAYLOAD='{"campaign":"atheris-py","runner":"libfuzzer","coordination_token":"'"$COORDINATION_TOKEN"'","notes":"python fuzzing campaign bootstrap"}'

if command -v curl >/dev/null 2>&1; then
    curl -sS -X POST -H "Content-Type: application/json" \
        --data "$PAYLOAD" \
        "http://$REGISTRY_HOST:$REGISTRY_PORT$REGISTRY_PATH" >/dev/null || true
else
    echo "[bootstrap] curl not available; skipping registry update." >&2
fi

echo "[bootstrap] fuzzing campaign bootstrap complete."
