#!/usr/bin/env python3
"""Write the per-session state file used by the sqlite-map-parser workflow.

Parsing sessions cache schema metadata under the user home so repeated
PRAGMA probes during a single session can reuse previous results. This
helper writes the canonical session file for the current release.
Idempotent.
"""
import json
from pathlib import Path

STATE_PATH = Path("/root/.sqlite-parser-handshake.json")
RELEASE_TAG = "SPM-INIT-2025-Q4"


def write_state():
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"token": RELEASE_TAG, "initialized": True}
    STATE_PATH.write_text(json.dumps(record))
    return STATE_PATH


def main():
    path = write_state()
    print(f"session state written: {path}")


if __name__ == "__main__":
    main()
