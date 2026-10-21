"""Validate and format JSON without external services."""

import json
import math
from typing import Literal


def _reject_constant(value: str) -> None:
    raise ValueError(f"{value} is not valid JSON.")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Number exceeds the supported floating-point range.")
    return number


def process_json(
    text: str,
    action: Literal["validate", "format", "minify"] = "format",
    sort_keys: bool = False,
) -> dict:
    """Validate or format JSON using Python numbers; pretty output uses two spaces."""
    if action not in {"validate", "format", "minify"}:
        raise ValueError("action must be validate, format, or minify.")
    try:
        value = json.loads(text, parse_constant=_reject_constant, parse_float=_finite_float)
        if action == "validate":
            return {"valid": True}
        output = json.dumps(
            value, ensure_ascii=False, sort_keys=sort_keys, allow_nan=False,
            indent=2 if action == "format" else None,
            separators=None if action == "format" else (",", ":"),
        )
        return {"valid": True, "output": output}
    except (ValueError, RecursionError) as error:
        return {"valid": False, "error": str(error)}
