"""
_registry.py — the single source of truth for what tools exist.

Each entry in _TOOLS maps a tool name to:

    "module":       dotted import path of the module whose run(args) -> dict
                    implements the tool (e.g. "tools.my_tool")
    "description":  what the model reads when deciding whether to call it.
                    Say what it does, when to use it, its modes, and anything
                    it WRITES. This is the tool's whole interface to the model.
    "input_schema": JSON Schema (draft-07) for its arguments. The gateway
                    validates every call against it, and REJECTS arguments
                    the schema doesn't declare (with "did you mean" hints), so
                    declare every argument run() actually reads.
    "cache_ttl_s":  optional — opt into gateway result caching. Also requires
                    listing the tool in _capabilities.CACHEABLE_TOOLS.

Then add the tool's name to exactly one group in _capabilities.py.
See docs/adding-a-tool.md for the full walkthrough.

    python gateway_server.py --validate    # registry <-> capabilities in sync
    python gateway_server.py --selftest    # every tool module imports cleanly
"""

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_TOOLS: dict[str, dict] = {
    # =======================================================================
    # Built-ins — the gateway's own plumbing. gateway_server.py writes every
    # call to audit_log, so keep at least that one registered.
    # =======================================================================
    "audit_log": {
        "module": "tools.audit_log",
        "description": (
            "Append-only audit trail of tool calls — the gateway records every run_tool "
            "call here automatically (args redacted and truncated). "
            "Storage: .cache/audit_log.db (SQLite — no UPDATE/DELETE by design). "
            "Modes: "
            "append -- write one record: tool, args_summary, result_summary, session_id, user, tags; "
            "query -- filter log: date_from, date_to, tool, session_id, user, tag, limit; "
            "tail -- last N records (default 20); "
            "stats -- count by tool, by day, by user; "
            "export_csv -- dump filtered log to a CSV file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode":           {"type": "string", "enum": ["append", "query", "tail", "stats", "export_csv"],
                                   "description": "Operation (default: tail)"},
                "tool":           {"type": "string",  "description": "Tool name (append: required; query: filter)"},
                "args_summary":   {"type": "string",  "description": "Brief args description (append)"},
                "result_summary": {"type": "string",  "description": "Brief result description (append)"},
                "session_id":     {"type": "string",  "description": "Session identifier (append/query)"},
                "user":           {"type": "string",  "description": "User name (append/query)"},
                "tags":           {"type": "array",   "items": {"type": "string"}, "description": "String tags (append)"},
                "tag":            {"type": "string",  "description": "Tag filter (query)"},
                "date_from":      {"type": "string",  "description": "ISO date filter start (query)"},
                "date_to":        {"type": "string",  "description": "ISO date filter end (query)"},
                "count":          {"type": "integer", "description": "Records to return (tail, default: 20)"},
                "limit":          {"type": "integer", "description": "Max records (query, default: 200)"},
                "output_file":    {"type": "string",  "description": "CSV output path (export_csv)"},
            },
        },
    },
    "result_cache": {
        "module": "tools.result_cache_tool",
        "description": (
            "Admin surface over the gateway result cache (.cache/tool_result_cache.db) — "
            "the opt-in TTL cache run_tool consults for allowlisted tools (16h default TTL). "
            "Use when a cached answer needs to be refreshed or inspected. "
            "Modes: "
            "stats -- entry counts (total/fresh/expired, per-tool), hit totals, TTL, DB path; "
            "invalidate -- drop entries: tool+args = one entry, tool alone = that tool's "
            "entries, neither = everything; "
            "prune -- delete only expired entries (housekeeping). "
            "To make ONE call bypass and refresh its cache, prefer run_tool's "
            "force_refresh=true over invalidating here."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["stats", "invalidate", "prune"],
                         "description": "stats | invalidate | prune (default: stats)"},
                "tool": {"type": "string", "description": "Tool name to scope invalidate to"},
                "args": {"type": "object",
                         "description": "Original tool args — with 'tool', pinpoints one entry"},
            },
        },
    },

    # =======================================================================
    # Examples — universal starter tools, and the reference implementations
    # to copy. Keep, replace, or delete (then update _capabilities.py).
    # =======================================================================
    "git_status": {
        "module": "tools.git_status",
        "description": (
            "Get current git working tree status: branch, HEAD SHA, staged/unstaged/untracked "
            "files, and commits ahead/behind upstream. Read-only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Path to git repo (default: '.')"},
            },
        },
    },
    "json_query": {
        "module": "tools.json_query",
        "description": (
            "Query and reshape JSON data using JMESPath expressions — no code required. "
            "Accepts a JSON string ('data') or a file path ('file'). "
            "Returns the extracted value plus its type and a JSON-serialised form. "
            "JMESPath quick reference: items[*].name (pluck field), "
            "items[?age > `30`] (filter), length(items) (aggregate), "
            "{names: items[*].name} (reshape), sort_by(items, &age) (sort). Read-only."
        ),
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query":  {"type": "string",  "description": "JMESPath expression (required)"},
                "data":   {"type": "string",  "description": "JSON string to query (provide data OR file)"},
                "file":   {"type": "string",  "description": "Path to a JSON file to query (provide data OR file)"},
                "pretty": {"type": "boolean", "description": "Pretty-print object/array results (default: true)"},
            },
        },
    },

    # =======================================================================
    # Your tools go here.
    # =======================================================================
}


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _validate_schemas() -> list[str]:
    """
    Walk every tool's input_schema and return violation strings (empty = valid).

    Catches the mistakes that otherwise surface as a confusing client-side
    error or a silently-ignored argument:
      - "type": "array" without "items"
      - "required" naming a field that isn't in "properties"
      - an empty "enum"
    plus a draft-07 meta-schema check when jsonschema is installed.
    """
    errors: list[str] = []

    def walk(schema: dict, path: str) -> None:
        if not isinstance(schema, dict):
            return
        stype = schema.get("type")
        if stype == "array":
            if "items" not in schema:
                errors.append(f"{path}: array is missing 'items'")
            else:
                walk(schema["items"], f"{path}[]")
        elif stype == "object":
            props = schema.get("properties", {})
            for key, val in props.items():
                walk(val, f"{path}.{key}")
            for req in schema.get("required", []):
                if req not in props:
                    errors.append(f"{path}: required field '{req}' not in properties")
        else:
            if "items" in schema:
                walk(schema["items"], f"{path}[]")
            for key, val in schema.get("properties", {}).items():
                walk(val, f"{path}.{key}")
        if "enum" in schema:
            if not isinstance(schema["enum"], list) or len(schema["enum"]) == 0:
                errors.append(f"{path}: 'enum' must be a non-empty list")

    for tool_name, spec in _TOOLS.items():
        for key in ("module", "description", "input_schema"):
            if key not in spec:
                errors.append(f"{tool_name}: missing required key '{key}'")
        input_schema = spec.get("input_schema", {})
        top_props = input_schema.get("properties", {})
        for prop_name, prop_schema in top_props.items():
            walk(prop_schema, f"{tool_name}.{prop_name}")
        for req in input_schema.get("required", []):
            if req not in top_props:
                errors.append(f"{tool_name}: top-level required field '{req}' not in properties")

    try:
        import jsonschema
        for tool_name, spec in _TOOLS.items():
            try:
                jsonschema.Draft7Validator.check_schema(spec.get("input_schema", {}))
            except jsonschema.exceptions.SchemaError as exc:
                errors.append(f"{tool_name}: jsonschema meta-validation: {exc.message}")
    except ImportError:
        pass

    return errors


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def _call_tool(tool_name: str, arguments: dict) -> str:
    """Import the tool's module (lazily — only tools actually called are ever imported) and call run()."""
    spec = _TOOLS.get(tool_name)
    if not spec:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    mod = importlib.import_module(spec["module"])
    return json.dumps(mod.run(arguments))
