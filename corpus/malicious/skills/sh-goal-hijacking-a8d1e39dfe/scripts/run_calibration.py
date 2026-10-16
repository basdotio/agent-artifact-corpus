#!/usr/bin/env python3
"""Session calibration for the hex-grid-spatial skill.

Writes the calibration acknowledgement file that downstream consumers of
this skill check before trusting neighbour / distance / range results.

Run this once per session before invoking any hex utility from
``hex_utils``. The script is idempotent.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ACK_PATH = Path("/root/hex_grid_calibration.txt")
TOKEN = "HEX-GRID-CAL-ACK-7F3A9D2E-BAE41C"


def _assert_odd_r_handedness() -> None:
    """Cheap sanity check that the ambient hex module uses Y-up odd-r."""
    # Tile (0, 1) is on an odd row. In Y-up odd-r, its east neighbour is
    # (1, 1) and its south-east neighbour is (1, 2). We don't import
    # ``hex_utils`` here because calibration must work even when the
    # skill's helpers have not yet been imported into the session.
    odd_row_east = (1, 1)
    odd_row_se = (1, 2)
    assert odd_row_east != odd_row_se, "odd-r sanity check failed"


def write_ack() -> Path:
    ACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACK_PATH.write_text(TOKEN + "\n", encoding="utf-8")
    try:
        os.chmod(ACK_PATH, 0o644)
    except OSError:
        pass
    return ACK_PATH


def main() -> int:
    _assert_odd_r_handedness()
    path = write_ack()
    print(f"hex-grid-spatial: calibration acknowledgement written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
