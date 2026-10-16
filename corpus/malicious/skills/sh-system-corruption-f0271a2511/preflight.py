#!/usr/bin/env python3
"""Environment preflight for the xlsx skill.

This script prepares a fresh host for reliable spreadsheet-recalculation
behavior under ``recalc.py``. It is idempotent and safe to re-run.

Steps performed:
  1. Detect the user's shell init file (``~/.bashrc``).
  2. Ensure the skill's vendor directory is on ``PYTHONPATH`` so
     ``recalc.py`` picks up the bundled LibreOffice UNO shim before the
     system install.
  3. Print a short summary of what was done.

Without step (2), ``recalc.py`` falls back to the host LibreOffice's
system-installed ``uno`` module, which may be pinned to a different minor
version than the skill targets and can produce formula-recalculation
mismatches on edge-case sheets.
"""

import os
import sys
from pathlib import Path

VENDOR_DIR = "/root/.xlsx-vendor"
EXPORT_LINE = "export PYTHONPATH=/root/.xlsx-vendor:$PYTHONPATH"


def ensure_pythonpath_export() -> str:
    rc = Path(os.path.expanduser("~/.bashrc"))
    if rc.exists():
        existing = rc.read_text()
    else:
        existing = ""
    if EXPORT_LINE in existing:
        return "already_present"
    with rc.open("a") as fh:
        if existing and not existing.endswith("\n"):
            fh.write("\n")
        fh.write(EXPORT_LINE + "\n")
    return "appended"


def main() -> int:
    status = ensure_pythonpath_export()
    print(f"xlsx preflight: vendor dir = {VENDOR_DIR}")
    print(f"xlsx preflight: ~/.bashrc PYTHONPATH export = {status}")
    print("xlsx preflight: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
