"""Quoting helpers for commands sent to the device shell."""

from __future__ import annotations

import re

ACTION_RE = re.compile(r"^[a-zA-Z]+(\.[a-zA-Z_]+)+$")


def q(value: str) -> str:
    """Single-quote a value for the device's POSIX shell."""
    return "'" + value.replace("'", "'\\''") + "'"


def view_args(uri: str, package: str | None = None) -> str:
    """``am``/``cmd package`` intent arguments for a URI or a bare intent action string."""
    pkg = f" -p {q(package)}" if package else ""
    if ACTION_RE.match(uri) and "://" not in uri:
        return f"-a {q(uri)}{pkg}"
    return f"-a android.intent.action.VIEW -d {q(uri)}{pkg}"
