"""Locate files from the repo-level `shared/` folder (or the copy bundled into the wheel)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent


def shared_file(name: str) -> Path | None:
    for cand in (_HERE / "_shared" / name, _HERE.parents[2] / "shared" / name, _HERE.parents[1] / "shared" / name):
        if cand.is_file():
            return cand
    return None


@lru_cache(maxsize=None)
def shared_json(name: str) -> Any:
    p = shared_file(name)
    if p is None:
        raise FileNotFoundError(f"shared/{name} not found")
    return json.loads(p.read_text(encoding="utf-8"))


def shared_text(name: str) -> str:
    p = shared_file(name)
    if p is None:
        raise FileNotFoundError(f"shared/{name} not found")
    return p.read_text(encoding="utf-8")
