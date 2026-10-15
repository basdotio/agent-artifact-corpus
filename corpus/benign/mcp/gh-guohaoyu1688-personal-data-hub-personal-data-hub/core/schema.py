"""YAML schemas with validated identifiers and add-only compatibility rules."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

META = {"id", "created_at", "updated_at", "source_file", "actor"}
TYPES = {
    "text": "TEXT",
    "integer": "INTEGER",
    "decimal": "TEXT",
    "boolean": "INTEGER",
    "date": "TEXT",
    "datetime": "TEXT",
}
MASK = "[REDACTED]"


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
        raise ValueError(
            "identifiers must be lowercase letters, digits and underscores, starting with a letter"
        )
    return value


def validate_schema(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("schema must be a YAML mapping")
    table = identifier(raw.get("table"))
    columns = raw.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ValueError(f"{table}: columns must be a non-empty mapping")
    result = copy.deepcopy(raw)
    result.setdefault("label", table.replace("_", " ").title())
    result.setdefault("unique", [])
    result.setdefault("due_fields", [])
    for name, options in columns.items():
        identifier(name)
        if name in META:
            raise ValueError(f"{table}: {name} is a reserved metadata field")
        if not isinstance(options, dict) or options.get("type", "text") not in TYPES:
            raise ValueError(f"{table}.{name}: unsupported field type")
        result["columns"][name].setdefault("type", "text")
        for flag in ("required", "sensitive"):
            if flag in options and type(options[flag]) is not bool:
                raise ValueError(f"{table}.{name}: {flag} must be boolean")
        if "aliases" in options and (
            not isinstance(options["aliases"], list)
            or any(not isinstance(x, str) for x in options["aliases"])
        ):
            raise ValueError(f"{table}.{name}: aliases must be a list of strings")
    for key in ("unique", "due_fields"):
        if not isinstance(result[key], list) or any(name not in columns for name in result[key]):
            raise ValueError(f"{table}: {key} must list declared columns")
        if len(set(result[key])) != len(result[key]):
            raise ValueError(f"{table}: {key} cannot contain duplicates")
    for name in result["due_fields"]:
        if result["columns"][name]["type"] != "date":
            raise ValueError(f"{table}.{name}: due fields must use date type")
    return result


def load_schemas(path: Path) -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for source in sorted([*path.glob("*.yaml"), *path.glob("*.yml")]):
        schema = validate_schema(yaml.safe_load(source.read_text(encoding="utf-8")))
        if schema["table"] in schemas:
            raise ValueError(f"duplicate table schema: {schema['table']}")
        schemas[schema["table"]] = schema
    return schemas


def merge_schema(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    if old["unique"] != new["unique"]:
        raise ValueError(f"{old['table']}: unique keys cannot change after initialization")
    merged = copy.deepcopy(new)
    for name, previous in old["columns"].items():
        current = new["columns"].get(name)
        if current is None:
            merged["columns"][name] = previous
            continue
        if previous["type"] != current["type"]:
            raise ValueError(f"{old['table']}.{name}: column types cannot change")
        if previous.get("required", False) != current.get("required", False):
            raise ValueError(f"{old['table']}.{name}: required constraint cannot change")
        # Removal of a sensitive flag never silently exposes previously private data.
        merged["columns"][name]["sensitive"] = previous.get("sensitive", False) or current.get(
            "sensitive", False
        )
    merged["due_fields"] = list(dict.fromkeys(old["due_fields"] + new["due_fields"]))
    return merged
