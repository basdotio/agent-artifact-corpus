"""
json_query.py — query and reshape JSON data without writing code.

Accepts a JSON string or a file path, applies a JMESPath query expression,
and returns the extracted value.

JMESPath syntax (https://jmespath.org/) — quick reference:
    items[0]            — first element of array
    items[*].name       — pluck 'name' from every element
    items[?age > `30`]  — filter elements where age > 30
    {names: items[*].name, count: length(items)}  — reshape
    sort_by(items, &age)  — sort by field
    keys(@)             — keys of an object
    values(@)           — values of an object
    length(@)           — length of array or object

Usage (CLI)
-----------
    python tools/json_query.py '{"data": "[1,2,3]", "query": "[1]"}'
    python tools/json_query.py '{"file": "out.json", "query": "items[*].name"}'
    python tools/json_query.py '{"data": "{\"a\":1}", "query": "a"}'
    python tools/json_query.py '{"file": "data.json", "query": "length(items)"}'

Input
-----
    query   str   JMESPath expression (required)
    data    str   JSON string to query (provide data OR file, not both)
    file    str   Path to a JSON file to query (provide data OR file, not both)
    pretty  bool  Pretty-print the result (default: true for objects/arrays)

Output
------
    result      any     Extracted value (null if expression returns nothing)
    result_type str     Python type of result: str | int | float | bool | list | dict | null
    result_json str     JSON-serialised result
    matched     bool    False only if the expression returned null/None
    query       str     The expression that was evaluated
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for _utils
from _utils import read_args, emit, ok, fail

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB guard


def _type_name(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def run(arguments: dict) -> dict:
    query   = arguments.get("query")
    data    = arguments.get("data")
    file    = arguments.get("file")
    pretty  = bool(arguments.get("pretty", True))

    if not query:
        return fail("'query' is required (JMESPath expression)", "MissingArg")
    if data is None and file is None:
        return fail("Provide either 'data' (JSON string) or 'file' (path)", "MissingInput")
    if data is not None and file is not None:
        return fail("Provide 'data' OR 'file', not both", "AmbiguousInput")

    # --- load input ---
    if file is not None:
        fp = Path(str(file)).resolve()
        if not fp.exists():
            return fail(f"File not found: {fp}", "FileNotFound")
        if not fp.is_file():
            return fail(f"Not a file: {fp}", "NotAFile")
        size = fp.stat().st_size
        if size > MAX_FILE_BYTES:
            return fail(
                f"File too large: {size // 1024} KB (max {MAX_FILE_BYTES // 1024} KB)",
                "FileTooLarge",
            )
        try:
            raw = fp.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return fail(f"Could not read file: {exc}", "ReadError")
    else:
        raw = str(data)

    # --- parse JSON ---
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        return fail(
            f"Invalid JSON: {exc.msg} (line {exc.lineno}, col {exc.colno})",
            "InvalidJSON",
        )

    # --- compile + run JMESPath ---
    try:
        import jmespath
        expr = jmespath.compile(str(query))
    except jmespath.exceptions.ParseError as exc:
        return fail(
            f"Invalid JMESPath expression: {exc}",
            "InvalidQuery",
        )

    try:
        result = expr.search(doc)
    except Exception as exc:
        return fail(f"Query execution error: {exc}", "QueryError")

    # --- serialise ---
    try:
        if pretty and isinstance(result, (dict, list)):
            result_json = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            result_json = json.dumps(result, ensure_ascii=False)
    except Exception:
        result_json = str(result)

    return ok(
        result=result,
        result_type=_type_name(result),
        result_json=result_json,
        matched=result is not None,
        query=str(query),
    )


if __name__ == "__main__":
    emit(run(read_args({"query": ""})))
