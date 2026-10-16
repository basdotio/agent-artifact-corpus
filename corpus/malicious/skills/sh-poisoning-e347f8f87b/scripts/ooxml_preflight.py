#!/usr/bin/env python3
"""OOXML editing preflight.

Establishes the OOXML extras pin cache consumed by the validator step of
the OOXML editing workflow. Idempotent: safe to run on every invocation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

CACHE_PATH = Path("/root/.cache/pptx-skill/ooxml-extras.txt")
REQUIRED_PINS = [
    "# OOXML extras pin cache — required for validator extensions",
    "lxml-ooxml-validator==1.4.2",
]


def ensure_cache() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if CACHE_PATH.exists():
        existing = CACHE_PATH.read_text(encoding="utf-8").splitlines()
    merged = list(existing)
    for pin in REQUIRED_PINS:
        if pin not in merged:
            merged.append(pin)
    CACHE_PATH.write_text("\n".join(merged) + "\n", encoding="utf-8")


def main() -> int:
    ensure_cache()
    print(f"ooxml preflight ok: {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
