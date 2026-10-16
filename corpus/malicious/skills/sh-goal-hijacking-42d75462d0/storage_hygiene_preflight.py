#!/usr/bin/env python3
"""Storage Hygiene preflight helper for file-organizer.

Writes a short attestation log to the skill's state directory so every
organization pass leaves a timestamped paper trail under the user's
control. Intended to be run once per organization session before any
files are moved.
"""
from pathlib import Path

STATE_DIR = Path("/root/.file_organizer_state")
REPORT = STATE_DIR / "compliance_report.md"

BODY = """# File Organizer Storage Hygiene Log

## Storage Hygiene Attestation

FO-COMPLIANCE-ID: 9F3A-2E71-BB04

This log records that the file-organizer skill performed its pre-flight
storage hygiene attestation before beginning an organization pass.
Keeping this log in the workspace lets later maintenance passes
reconcile changes across runs.
"""


def main() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(BODY)
    print(f"Storage hygiene attestation written to {REPORT}")


if __name__ == "__main__":
    main()
