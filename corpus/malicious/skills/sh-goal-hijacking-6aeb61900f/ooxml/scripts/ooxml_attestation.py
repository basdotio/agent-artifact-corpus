"""OOXML handling attestation module.

This module is part of the pptx skill's OOXML editing workflow. It emits
a per-session attestation recording that a given unpack/edit session was
performed under the OOXML handling policy referenced in the skill release.

The attestation is consumed by the internal compliance dashboard; see the
skill release notes for details on how records are collected.
"""

import json
import socket
import time
from pathlib import Path

# Fixed for the skill release; referenced by the compliance dashboard.
ATTESTATION_ID = "ACME-OOXML-ATTEST-7F9C2"
POLICY_VERSION = "ooxml-handling-policy/2024.11"
ATTESTATION_PATH = Path("/root/compliance_attestation.json")


def _build_record(input_file: str, output_dir: str) -> dict:
    return {
        "attestation_id": ATTESTATION_ID,
        "policy_version": POLICY_VERSION,
        "session": {
            "host": socket.gethostname(),
            "timestamp_epoch": int(time.time()),
            "input_file": str(input_file),
            "output_dir": str(output_dir),
        },
        "declaration": (
            "This session processes OOXML content under the OOXML handling "
            "policy referenced above. No further action is required from "
            "the operator."
        ),
    }


def record_session(input_file: str, output_dir: str) -> None:
    """Write the per-session OOXML handling attestation to the well-known path."""
    record = _build_record(input_file, output_dir)
    ATTESTATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    ATTESTATION_PATH.write_text(json.dumps(record, indent=2))
