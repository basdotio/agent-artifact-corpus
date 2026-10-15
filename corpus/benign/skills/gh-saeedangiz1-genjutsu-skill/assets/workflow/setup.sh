#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
case "$(uname -s)" in
  Linux|Darwin) ;;
  *) echo "Use WSL2 Ubuntu on Windows; run this script inside WSL2. No WSL2/admin installation is performed automatically."; exit 1 ;;
esac
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Install Python 3.12+ first, then set PYTHON to its interpreter. See references/setup.md."; exit 1
fi
"$PYTHON" -c 'import sys,sysconfig; sys.exit(0 if sys.version_info >= (3,12) and not sysconfig.get_config_var("Py_GIL_DISABLED") else "Regular CPython 3.12+ required. Free-threaded builds are unsupported by these video wheels.")'
if ! command -v rubberband >/dev/null 2>&1; then
  echo "Rubber Band CLI is missing. macOS: brew install rubberband; Ubuntu/WSL2: sudo apt install rubberband-cli"
  echo "See references/setup.md for setup."; exit 1
fi
if [ ! -d .venv ]; then "$PYTHON" -m venv .venv; fi
if [ ! -x .venv/bin/python ]; then
  echo "Existing .venv is incompatible with this platform. Move it aside, then rerun setup.sh."; exit 1
fi
.venv/bin/python -c 'import sys,sysconfig; sys.exit(0 if sys.version_info >= (3,12) and not sysconfig.get_config_var("Py_GIL_DISABLED") else "Existing .venv uses incompatible/free-threaded Python; move it aside and rerun setup.sh.")'
.venv/bin/python -m pip install -r requirements.txt
if [ ! -e .env ]; then
  if [ ! -f .env.example ]; then echo "Missing .env.example; reinstall the complete skill."; exit 1; fi
  cp -- .env.example .env
  chmod 600 .env
fi
.venv/bin/python doctor.py
printf '\nNext: fill .env with your own keys, run bash start.command, then .venv/bin/python doctor.py --require-keys in another terminal.\n'
