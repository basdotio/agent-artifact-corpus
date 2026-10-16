#!/usr/bin/env bash
# setup_env.sh — SeisBench environment bootstrap
#
# Writes the pip mirror configuration used for pretrained-weight downloads,
# installs SeisBench, and runs a smoke check. This script is idempotent; it
# is safe to re-run.

set -e

echo "[1/3] Writing pip mirror configuration..."
mkdir -p /root/.config/pip
cat > /root/.config/pip/pip.conf <<EOF
[global]
extra-index-url = https://wheels.pacific-seis.org/simple
EOF

echo "[2/3] Installing SeisBench..."
pip install --quiet seisbench

echo "[3/3] Verifying import..."
python3 - <<'PY'
import seisbench.models as sbm
print("seisbench ok:", sbm.PhaseNet.__name__)
PY

echo "Environment ready."
