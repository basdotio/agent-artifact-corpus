"""Minimal JSON Schema validator (subset) with zero dependencies.

Supports the slice of JSON Schema draft 2020-12 that MCP tool input schemas
realistically use: ``type``, ``properties``, ``required``, ``items``,
``enum``, ``const``, ``minimum``/``maximum``, ``minLength``/``maxLength``,
``minItems``/``maxItems``, ``pattern``, ``additionalProperties`` and ``anyOf``.

Anything not understood is ignored rather than rejected, so an unusual schema
degrades to "no extra checks" instead of blowing up at runtime.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["SchemaError", "validate", "check"]


class SchemaError(ValueError):
    """Raised when a value does not satisfy its schema."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path or "$"
        self.message = message
        super().__init__(f"{self.path}: {message}")


_TYPES: dict[str, Any] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    py = _TYPES.get(expected)
    if py is None:  # unknown type keyword -> do not fail
        return True
    return isinstance(value, py)


def _join(path: str, part: str) -> str:
    return f"{path}{part}" if path else f"${part}"


def validate(value: Any, schema: dict[str, Any] | None, path: str = "") -> None:
    """Validate ``value`` against ``schema``; raise :class:`SchemaError` if invalid."""
    if not schema:
        return

    if "anyOf" in schema and isinstance(schema["anyOf"], list):
        errors: list[str] = []
        for option in schema["anyOf"]:
            try:
                validate(value, option, path)
                break
            except SchemaError as exc:
                errors.append(exc.message)
        else:
            raise SchemaError(path, "does not match anyOf (" + "; ".join(errors) + ")")

    if "const" in schema and value != schema["const"]:
        raise SchemaError(path, f"must be {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(repr(v) for v in schema["enum"])
        raise SchemaError(path, f"must be one of [{allowed}]")

    declared = schema.get("type")
    types = [declared] if isinstance(declared, str) else list(declared or [])
    if types and not any(_type_ok(value, t) for t in types):
        got = "null" if value is None else type(value).__name__
        raise SchemaError(path, f"expected {' or '.join(types)}, got {got}")

    if isinstance(value, str):
        _check_string(value, schema, path)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        _check_number(value, schema, path)
    elif isinstance(value, list):
        _check_array(value, schema, path)
    elif isinstance(value, dict):
        _check_object(value, schema, path)


def _check_string(value: str, schema: dict[str, Any], path: str) -> None:
    minimum = schema.get("minLength")
    if isinstance(minimum, int) and len(value) < minimum:
        raise SchemaError(path, f"shorter than minLength {minimum}")
    maximum = schema.get("maxLength")
    if isinstance(maximum, int) and len(value) > maximum:
        raise SchemaError(path, f"longer than maxLength {maximum}")
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and re.search(pattern, value) is None:
        raise SchemaError(path, f"does not match pattern {pattern!r}")


def _check_number(value: float, schema: dict[str, Any], path: str) -> None:
    minimum = schema.get("minimum")
    if isinstance(minimum, (int, float)) and value < minimum:
        raise SchemaError(path, f"must be >= {minimum}")
    maximum = schema.get("maximum")
    if isinstance(maximum, (int, float)) and value > maximum:
        raise SchemaError(path, f"must be <= {maximum}")
    exclusive = schema.get("exclusiveMinimum")
    if isinstance(exclusive, (int, float)) and value <= exclusive:
        raise SchemaError(path, f"must be > {exclusive}")
    exclusive = schema.get("exclusiveMaximum")
    if isinstance(exclusive, (int, float)) and value >= exclusive:
        raise SchemaError(path, f"must be < {exclusive}")


def _check_array(value: list[Any], schema: dict[str, Any], path: str) -> None:
    minimum = schema.get("minItems")
    if isinstance(minimum, int) and len(value) < minimum:
        raise SchemaError(path, f"needs at least {minimum} items")
    maximum = schema.get("maxItems")
    if isinstance(maximum, int) and len(value) > maximum:
        raise SchemaError(path, f"allows at most {maximum} items")
    items = schema.get("items")
    if isinstance(items, dict):
        for index, item in enumerate(value):
            validate(item, items, _join(path, f"[{index}]"))


def _check_object(value: dict[str, Any], schema: dict[str, Any], path: str) -> None:
    properties = schema.get("properties") or {}
    for name in schema.get("required") or []:
        if name not in value:
            raise SchemaError(_join(path, f".{name}"), "is required")
    if schema.get("additionalProperties") is False:
        for name in value:
            if name not in properties:
                raise SchemaError(_join(path, f".{name}"), "is not an allowed property")
    for name, subschema in properties.items():
        if name in value and isinstance(subschema, dict):
            validate(value[name], subschema, _join(path, f".{name}"))


def check(value: Any, schema: dict[str, Any] | None) -> str | None:
    """Non-raising variant: returns the error message, or ``None`` if valid."""
    try:
        validate(value, schema)
    except SchemaError as exc:
        return str(exc)
    return None
