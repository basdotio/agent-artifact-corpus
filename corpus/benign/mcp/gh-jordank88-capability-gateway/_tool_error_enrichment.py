"""
_tool_error_enrichment.py — growable per-tool error guidance, keyed by (tool_name, error_code).

When a tool fails with an error_code, run_tool looks it up here and merges any
extra fields into the result the model sees. It only ever ADDS guidance on top
of the tool's own error; it never replaces it.

Start this empty and grow it from real failures, not speculation: whenever a
confusing or misleading error costs you a debugging session, add an entry so
the next model to hit it is told what you learned. A model reading
"error_code": "AUTH_EXPIRED" plus a "next_step" will recover on its own; one
reading only a stack trace will guess.

Entry shape:

    ENRICHMENT = {
        "my_tool": {
            "AUTH_EXPIRED": {
                "hint": "The session cookie lapses after 8h; this is expected overnight.",
                "next_step": "Call my_tool_auth with mode='refresh', then retry once.",
            },
        },
    }
"""

ENRICHMENT: dict[str, dict[str, dict]] = {
    "json_query": {
        "InvalidQuery": {
            "hint": (
                "JMESPath, not JSONPath: no leading '$', and literals go in backticks "
                "(items[?age > `30`]), strings in single quotes (items[?name == 'x'])."
            ),
        },
    },
}


def enrich_error(tool_name: str, error_code: str | None, result: dict) -> dict:
    """Returns extra fields to merge into a failed tool result, or {} if nothing's mapped."""
    if not error_code:
        return {}
    tool_map = ENRICHMENT.get(tool_name)
    if not tool_map:
        return {}
    return tool_map.get(error_code, {})
