"""Parse ``adb shell content query`` output from the Mobilerun Portal content provider."""

from __future__ import annotations

import json
from typing import Any

_WRAPPER_KEYS = ("result", "data")


def parse_content_output(raw: str) -> Any | None:
    """Return the JSON payload of a ``Row: N result=<json>`` line, unwrapped.

    The Portal wraps payloads as ``{"status": ..., "result": <value>}`` and sometimes
    double-encodes ``<value>`` as a JSON string; both layers are removed. Returns None when
    nothing parseable is found.
    """
    for line in raw.splitlines():
        line = line.strip()
        if "result=" in line:
            payload = line.split("result=", 1)[1]
        elif line.startswith(("{", "[")):
            payload = line
        else:
            continue
        try:
            return unwrap(json.loads(payload))
        except json.JSONDecodeError:
            continue
    try:
        return unwrap(json.loads(raw.strip()))
    except json.JSONDecodeError:
        return None


def unwrap(value: Any) -> Any:
    """Strip Portal ``result``/``data`` envelopes, decoding string-encoded JSON inside them."""
    if isinstance(value, dict):
        for key in _WRAPPER_KEYS:
            if key in value:
                inner = value[key]
                if isinstance(inner, str):
                    try:
                        return json.loads(inner)
                    except json.JSONDecodeError:
                        return inner
                return inner
    return value


def extract_token(payload: Any) -> str | None:
    """Pull the bearer token out of whatever shape the ``auth_token`` provider returned."""
    if isinstance(payload, str):
        return payload or None
    if isinstance(payload, dict):
        for key in ("token", "auth_token", "result", "data"):
            found = extract_token(payload.get(key))
            if found:
                return found
    return None
