"""Recorded tool results, so every model sees the same service answers.

A tool call is keyed by its tool name and its arguments (canonical JSON). Modes:

- ``live``: always call the tool; record nothing.
- ``record``: always call the tool and store the result (a later identical call overwrites it).
- ``replay``: only recorded results; an unrecorded call returns an error to the model.
- ``replay-or-record``: a recorded result when there is one, otherwise call and store it.

Public services rate-limit (the AfriGen-D Beacon allows 50 requests an hour), so benchmark runs
use ``replay-or-record``: the first model to make a call pays for it, and later models, effort
levels and repeats get the stored answer.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

MODES = ("live", "record", "replay", "replay-or-record")


def key(tool: str, arguments: dict[str, Any]) -> str:
    canonical = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class Cassette:
    def __init__(self, path: Path, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.path, self.mode = path, mode
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        if path.is_file():
            for line in path.read_text().splitlines():
                if line.strip():
                    entry = json.loads(line)
                    self._entries[entry["key"]] = entry

    def get(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        if self.mode in ("live", "record"):
            return None
        return self._entries.get(key(tool, arguments))

    def put(self, tool: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        if self.mode == "live":
            return
        entry = {"key": key(tool, arguments), "tool": tool, "arguments": arguments,
                 "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "result": result}
        with self._lock:
            self._entries[entry["key"]] = entry
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as handle:
                handle.write(json.dumps(entry) + "\n")

    def __len__(self) -> int:
        return len(self._entries)
