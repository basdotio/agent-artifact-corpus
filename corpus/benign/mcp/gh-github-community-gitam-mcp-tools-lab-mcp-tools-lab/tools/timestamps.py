"""Deterministic timestamp conversion, independent of your computer's timezone."""

import math
from datetime import datetime, timedelta, timezone
from typing import Literal


def convert_timestamp(value: str, direction: Literal["to_iso", "to_unix"] = "to_iso") -> dict:
    """Convert Unix seconds to UTC ISO 8601, or an offset-aware ISO date to seconds.

    ISO input must include a time and timezone, such as 2026-01-01T12:00:00+05:30.
    """
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        if direction == "to_iso":
            seconds = float(value)
            if not math.isfinite(seconds):
                raise ValueError("Timestamp must be finite.")
            date = epoch + timedelta(seconds=seconds)
        elif direction == "to_unix":
            date = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if date.tzinfo is None or date.utcoffset() is None:
                raise ValueError("ISO date must include a timezone, such as Z or +05:30.")
            date = date.astimezone(timezone.utc)
            seconds = (date - epoch).total_seconds()
        else:
            raise ValueError("direction must be to_iso or to_unix.")
    except (ValueError, OverflowError) as error:
        raise ValueError(f"Cannot convert timestamp: {error}") from error
    return {"unix_seconds": seconds, "iso_utc": date.isoformat().replace("+00:00", "Z")}
