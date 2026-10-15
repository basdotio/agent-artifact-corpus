"""OS selection. `current()` is chosen once from the OS identity; tests may override it with `use()`."""

from __future__ import annotations

import os
import sys

from .base import CmdResult, Platform
from .posix import PosixPlatform
from .windows import WindowsPlatform

_current: Platform | None = None


def detect() -> Platform:
    return WindowsPlatform() if sys.platform == "win32" or os.name == "nt" else PosixPlatform()


def current() -> Platform:
    global _current
    if _current is None:
        _current = detect()
    return _current


def use(p: Platform | None) -> None:
    """Override the active platform (tests); None restores auto-detection."""
    global _current
    _current = p


__all__ = ["CmdResult", "Platform", "PosixPlatform", "WindowsPlatform", "current", "detect", "use"]
