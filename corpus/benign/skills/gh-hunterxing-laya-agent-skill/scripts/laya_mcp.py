#!/usr/bin/env python3
"""Minimal stdio MCP server exposing the Laya development decisions as native tools.

Standard library only, no SDK: one JSON-RPC object per line on stdin/stdout, diagnostics on
stderr. Any MCP client can register it as a local server
and call Laya without a shell wrapper. See references/integration.md for capability-based client
configuration.

The tool result is always the same advisory JSON the CLI prints; ``isError`` is set when the
helper could not decide, so a client never reads a failure as a negative answer.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from laya import SKILL_VERSION, load_config, main_like_decide, selftest as run_selftest  # noqa: E402
from laya_protocol import PROTOCOL, DecisionError  # noqa: E402

DEFAULT_PROTOCOL = "2024-11-05"
CANDIDATE = {
    "type": "array",
    "minItems": 1,
    "maxItems": 6,
    "items": {
        "type": "object",
        "required": ["id"],
        "properties": {"id": {"type": "string"}, "description": {"type": "string"}, "text": {"type": "string"}},
    },
}

TOOLS = [
    {
        "name": "laya_models",
        "description": "List the Laya decision models this gateway serves. Use it to confirm the backend is reachable and to read the real model ids.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "laya_select",
        "description": "Pick one candidate from a short code-built list (2-6 items) for a request, with a fit probability per candidate. Advisory only: it does not load or run the chosen skill.",
        "inputSchema": {
            "type": "object",
            "required": ["request", "candidates"],
            "properties": {"request": {"type": "string"}, "candidates": CANDIDATE},
            "additionalProperties": False,
        },
    },
    {
        "name": "laya_rerank",
        "description": "Rank short excerpts (2-6, under 240 characters each) by how useful they are as evidence for a query.",
        "inputSchema": {
            "type": "object",
            "required": ["query", "candidates"],
            "properties": {"query": {"type": "string"}, "candidates": CANDIDATE},
            "additionalProperties": False,
        },
    },
    {
        "name": "laya_triage",
        "description": "Classify a first error into dependency, source, test, environment or unknown. A keyword heuristic is authoritative; the model only breaks ties.",
        "inputSchema": {
            "type": "object",
            "required": ["first_error"],
            "properties": {
                "first_error": {"type": "string"},
                "request": {"type": "string"},
                "command": {"type": "string"},
                "exit_code": {"type": "integer"},
                "environment": {"type": "string"},
                "recent_change": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "laya_verify",
        "description": "Say whether the supplied evidence supports, contradicts or is insufficient for a claim. It cannot establish facts that are not in the evidence.",
        "inputSchema": {
            "type": "object",
            "required": ["claim", "evidence"],
            "properties": {"claim": {"type": "string"}, "evidence": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "laya_change_review",
        "description": "Derive a review-risk floor, minimum test scope and review tags from changed-file metadata plus optional test evidence. The floor is deterministic and cannot be lowered by the model.",
        "inputSchema": {
            "type": "object",
            "required": ["summary", "changed_files"],
            "properties": {
                "summary": {"type": "string"},
                "changed_files": {"type": "array", "minItems": 1, "maxItems": 60, "items": {"type": "string"}},
                "diff_stats": {"type": "object", "properties": {"files": {"type": "integer"}, "additions": {"type": "integer"}, "deletions": {"type": "integer"}}},
                "tests": {"type": ["object", "string", "array"]},
                "notes": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "laya_decide",
        "description": "Ask caller-defined typed questions (choice, score, noul) about one state when no built-in workflow fits. Up to 32 questions, 20 choice options each.",
        "inputSchema": {
            "type": "object",
            "required": ["state", "questions"],
            "properties": {"state": {"type": ["string", "object", "array"]}, "questions": {"type": "object"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "laya_selftest",
        "description": "Prove the deployment still works: models, routing, deterministic policy, local input guard, plus the pinned model-quality baseline.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

MODES = {
    "laya_select": ("select", ("request", "candidates")),
    "laya_rerank": ("rerank", ("query", "candidates")),
    "laya_triage": ("triage", ("first_error",)),
    "laya_verify": ("verify", ("claim", "evidence")),
    "laya_change_review": ("change-review", ("summary", "changed_files")),
    "laya_decide": ("decide", ("state", "questions")),
}


def log(message):
    if os.environ.get("LAYA_MCP_DEBUG"):
        print(message, file=sys.stderr, flush=True)


def reply(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def call_tool(name, arguments):
    if not isinstance(arguments, dict):
        arguments = {}
    if name == "laya_models":
        from laya import fetch
        config = load_config()
        listing, elapsed = fetch(config, "/models")
        return {"status": "ok", "models": [m["id"] for m in listing.get("data", [])], "latency_ms": elapsed}, False
    if name == "laya_selftest":
        return run_selftest(load_config()), False
    if name in MODES:
        mode, required = MODES[name]
        missing = [key for key in required if key not in arguments]
        if missing:
            raise DecisionError("invalid_input", "Missing required argument(s): %s" % ", ".join(missing))
        payload = {key: value for key, value in arguments.items() if key in ("state", "questions", "request", "candidates", "query", "first_error", "command", "exit_code", "environment", "recent_change", "claim", "evidence", "summary", "changed_files", "diff_stats", "tests", "notes")}
        return main_like_decide(load_config(), mode, payload), False
    raise DecisionError("invalid_input", "Unknown tool %r." % name)


def handle(request):
    method = request.get("method")
    params = request.get("params") or {}
    ident = request.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": params.get("protocolVersion") or DEFAULT_PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "laya-agent-skill", "version": SKILL_VERSION},
            "instructions": "Typed Laya decisions (%s). Results are advisory: auto_action is always false and no tool call authorizes a risky action." % PROTOCOL,
        }}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": ident, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        try:
            result, is_error = call_tool(name, params.get("arguments") or {})
        except DecisionError as error:
            result = {"status": "unknown", "auto_action": False, "error": {"code": error.code, "message": str(error)},
                      "fallback": "Continue with the main model and existing tools; no action was authorized."}
            is_error = True
        except (OSError, ValueError, TypeError, KeyError, IndexError) as error:  # noqa: BLE001
            result = {"status": "unknown", "auto_action": False, "error": {"code": "input_or_response_error", "message": str(error)[:200]}}
            is_error = True
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, allow_nan=False)}],
            "isError": bool(is_error) or result.get("status") == "unknown",
        }}
    if ident is None:
        return None
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "Method not found: %s" % method}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            log("skipped unparseable line")
            continue
        if not isinstance(request, dict):
            continue
        try:
            response = handle(request)
        except Exception as error:  # noqa: BLE001 - the server must stay alive for the client
            log("handler error: %r" % (error,))
            response = None if request.get("id") is None else {
                "jsonrpc": "2.0", "id": request.get("id"),
                "error": {"code": -32603, "message": "Internal error; no decision was made."}}
        if response is not None:
            reply(response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
