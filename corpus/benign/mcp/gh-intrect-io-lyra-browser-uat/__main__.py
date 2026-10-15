"""``python -m lyra_browser.uat`` is ``lyra-uat``: the batch runner starts its children this
way, with the interpreter that is already running it, so it needs no console script on PATH."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
