#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [ ! -x .venv/bin/python ]; then
  echo "Run bash setup.sh first. On Windows, use WSL2 Ubuntu and run setup inside WSL2."; exit 1
fi
exec .venv/bin/python launch.py
