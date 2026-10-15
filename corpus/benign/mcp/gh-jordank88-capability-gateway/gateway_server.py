#!/usr/bin/env python3
"""
gateway_server.py — Capability Gateway: progressive disclosure for MCP tools.

Exposes exactly 4 tools to the model, however many tools the registry holds:
  list_capabilities()          — browse the capability groups (name + description only)
  search_tools(query)          — flat search across all tool names/descriptions, fallback
                                  for when browsing doesn't land on the right bucket
  load_capability(id)          — full tool list (name, description, input_schema) for one group
  run_tool(name, args)         — dispatch to any tool by name, regardless of whether its
                                  capability was "loaded" first (load_capability is a
                                  discovery aid, not an access gate)

Backed entirely by _registry.py (tool definitions) and _capabilities.py (grouping) —
no duplicated tool logic.

Why: an MCP client puts every exposed tool's name, description and input schema
into the model's context on every turn. At a few hundred tools that is tens of
thousands of tokens spent before any work starts, and a model choosing among
hundreds of similar-looking tools misfires more often. Four meta-tools keep the
fixed cost flat; the model pulls in only the schemas it needs, when it needs them.

Beyond routing, run_tool is where the guard rails live — every call is:
  * validated against the tool's JSON Schema,
  * rejected if it carries an argument the tool doesn't declare (with
    "did you mean" suggestions — and a loud warning when the ignored argument
    was a safety flag like dry_run),
  * rejected if an argument looks like an invented placeholder ("dummy_id"),
  * bounded by a wall-clock timeout so a hung tool can't hang the session,
  * optionally answered from a TTL result cache (allowlisted tools only),
  * written to an append-only audit log, with secret-looking args redacted.

Run `python gateway_server.py --help` for the CLI (validate / selftest / doctor).
"""

import concurrent.futures
import importlib
import json
import os
import sys
from pathlib import Path

# One shared worker pool for running tool calls under a wall-clock deadline.
# Threads can't be forcibly killed in Python — a hung call's thread keeps
# running in the background after we give up on it — but the caller gets a
# bounded, clean fail() instead of an indefinite hang either way, which is
# the actual guarantee we're after.
_TOOL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="tool-call")
_DEFAULT_TOOL_TIMEOUT_S = 120

# The MCP server name. Clients prefix tools with it (mcp__<name>__run_tool),
# so it must match the key you register the server under in your MCP config.
SERVER_NAME = os.environ.get("CAPABILITY_GATEWAY_NAME", "capability-gateway")

sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

import getpass
import re
import uuid

from _registry import _TOOLS, _call_tool, _validate_schemas
from _capabilities import CAPABILITIES, CACHEABLE_TOOLS
from _tool_error_enrichment import enrich_error
import _result_cache

# One session_id per gateway process — since gateway_server.py is spawned
# fresh per Claude session (confirmed empirically: config/subagent changes
# only ever took effect after a reboot), this naturally scopes audit entries
# to one real session without needing anything passed in from the caller.
_SESSION_ID = f"gw-{uuid.uuid4().hex[:12]}"
_AUDIT_USER = getpass.getuser()
_REDACT_KEY_HINTS = ("password", "secret", "token", "credential", "key")


def _summarize(d: dict, max_len: int = 200) -> str:
    """Redact anything password/secret/token/key-shaped, then truncate for the audit log."""
    if not isinstance(d, dict):
        s = str(d)
        return s[:max_len] + ("..." if len(s) > max_len else "")
    safe = {
        k: ("<redacted>" if any(h in k.lower() for h in _REDACT_KEY_HINTS) else v)
        for k, v in d.items()
    }
    s = json.dumps(safe, default=str)
    return s[:max_len] + ("..." if len(s) > max_len else "")


def _log_audit(tool: str, args: dict, result_summary: str, tags: list[str]) -> None:
    """Best-effort, never raises, never blocks the caller on a logging problem."""
    try:
        _call_tool("audit_log", {
            "mode": "append",
            "tool": tool,
            "args_summary": _summarize(args),
            "result_summary": result_summary,
            "session_id": _SESSION_ID,
            "user": _AUDIT_USER,
            "tags": tags,
        })
    except Exception:
        pass

# Placeholder/dummy-value detection — catches the common LLM failure mode of
# passing a plausible-looking fake value instead of a real looked-up one.
_PLACEHOLDER_PATTERNS = [
    (re.compile(r"^dummy[_-]", re.I), "dummy_*"),
    (re.compile(r"^test[_-]", re.I), "test_*"),
    (re.compile(r"^fake[_-]", re.I), "fake_*"),
    (re.compile(r"^placeholder[_-]", re.I), "placeholder_*"),
    (re.compile(r"^example[_-]", re.I), "example_*"),
    (re.compile(r"^sample[_-]", re.I), "sample_*"),
    (re.compile(r"^xxx+$", re.I), "xxx..."),
    (re.compile(r"^000+$"), "000..."),
    (re.compile(r"^123+$"), "123..."),
    (re.compile(r"^aaa+$", re.I), "aaa..."),
    (re.compile(r"^tbd$", re.I), "TBD"),
    (re.compile(r"^todo$", re.I), "TODO"),
    (re.compile(r"^fixme$", re.I), "FIXME"),
    (re.compile(r"^unknown$", re.I), "unknown"),
]
_FILENAME_LIKE = re.compile(r"\.\w{2,5}$")

# Infra/pipeline identifier fields where a "test-"/"dry-run-" style value is a
# completely normal real value, not a made-up placeholder — unlike a customer
# ID or ticket number, nobody's harmed by a fake-looking workflow_id. (Found
# when a pipeline's own smoke test had its run_id "test-smoke" rejected.)
_PLACEHOLDER_EXEMPT_FIELDS = {"workflow_id", "session_id", "run_id", "job_id", "thread_id"}


def _detect_placeholder(args: dict) -> dict | None:
    """Returns {field, value, pattern} for the first placeholder-looking value found, else None."""
    for key, value in (args or {}).items():
        if key in _PLACEHOLDER_EXEMPT_FIELDS:
            continue
        if not isinstance(value, str) or not value.strip():
            continue
        v = value.strip()
        if _FILENAME_LIKE.search(v):
            continue  # "test.txt", "example.json" etc. are real filenames, not placeholders
        for pattern, name in _PLACEHOLDER_PATTERNS:
            if pattern.match(v):
                return {"field": key, "value": value, "pattern": name}
    return None


# ---------------------------------------------------------------------------
# Startup validation — every tool must belong to exactly one capability
# ---------------------------------------------------------------------------

def _validate_capabilities() -> list[str]:
    errors = []
    seen: dict[str, str] = {}
    all_capability_tools: set[str] = set()

    for cap_id, cap in CAPABILITIES.items():
        for tool_name in cap["tools"]:
            if tool_name not in _TOOLS:
                errors.append(f"capability '{cap_id}': unknown tool '{tool_name}'")
                continue
            if tool_name in seen:
                errors.append(f"tool '{tool_name}' in both '{seen[tool_name]}' and '{cap_id}'")
            seen[tool_name] = cap_id
            all_capability_tools.add(tool_name)

    missing = set(_TOOLS.keys()) - all_capability_tools
    for tool_name in sorted(missing):
        errors.append(f"tool '{tool_name}' not assigned to any capability")

    # Result-cache allowlist sync:
    # cache_ttl_s in _TOOLS <=> membership in CACHEABLE_TOOLS, both ways,
    # so caching a new tool always requires a conscious allowlist edit.
    for tool_name, spec in _TOOLS.items():
        ttl = spec.get("cache_ttl_s")
        if ttl is not None:
            if not isinstance(ttl, int) or ttl <= 0:
                errors.append(f"tool '{tool_name}': cache_ttl_s must be a positive int, got {ttl!r}")
            if tool_name not in CACHEABLE_TOOLS:
                errors.append(
                    f"tool '{tool_name}' has cache_ttl_s but is not in "
                    f"_capabilities.CACHEABLE_TOOLS — add it there consciously or remove the key"
                )
    for tool_name in sorted(CACHEABLE_TOOLS):
        if tool_name not in _TOOLS:
            errors.append(f"CACHEABLE_TOOLS lists unknown tool '{tool_name}'")
        elif _TOOLS[tool_name].get("cache_ttl_s") is None:
            errors.append(f"CACHEABLE_TOOLS lists '{tool_name}' but its _TOOLS entry has no cache_ttl_s")

    return errors


_VALIDATION_ERRORS = _validate_schemas() + _validate_capabilities()
if _VALIDATION_ERRORS:
    raise RuntimeError(
        "Tool registry failed validation (_registry.py / _capabilities.py):\n"
        + "\n".join(f"  - {e}" for e in _VALIDATION_ERRORS)
    )


# ---------------------------------------------------------------------------
# The 4 gateway tools
# ---------------------------------------------------------------------------

def _list_capabilities() -> dict:
    return {
        "success": True,
        "capabilities": [
            {
                "id": cap_id,
                "description": cap["description"],
                "tool_count": len(cap["tools"]),
            }
            for cap_id, cap in CAPABILITIES.items()
        ],
    }


def _search_tools(query: str) -> dict:
    if not query or not query.strip():
        return {"success": False, "error": "query is required"}

    q = query.strip().lower()
    tool_to_capability = {
        tool_name: cap_id
        for cap_id, cap in CAPABILITIES.items()
        for tool_name in cap["tools"]
    }

    matches = []
    for name, spec in _TOOLS.items():
        haystack = f"{name} {spec['description']}".lower()
        if q in haystack:
            desc = spec["description"]
            matches.append({
                "name": name,
                "description": desc[:150] + ("..." if len(desc) > 150 else ""),
                "capability": tool_to_capability.get(name, "?"),
            })

    return {"success": True, "query": query, "match_count": len(matches), "matches": matches}


def _load_capability(cap_id: str) -> dict:
    cap = CAPABILITIES.get(cap_id)
    if not cap:
        return {
            "success": False,
            "error": f"Unknown capability '{cap_id}'. Valid: {', '.join(sorted(CAPABILITIES.keys()))}",
        }

    return {
        "success": True,
        "id": cap_id,
        "description": cap["description"],
        "tools": [
            {
                "name": name,
                "description": _TOOLS[name]["description"],
                "input_schema": _TOOLS[name]["input_schema"],
            }
            for name in cap["tools"]
        ],
    }


# ---------------------------------------------------------------------------
# Unknown-argument rejection
# ---------------------------------------------------------------------------
# jsonschema alone accepts properties a schema doesn't declare, so a call
# carrying an argument the tool doesn't have ran anyway, with that argument
# silently ignored. Two real incidents that motivated this check: a ticket-sync
# tool called with dry_run=true -- it has no dry-run mode -- created a real
# ticket; a timer tool called with hours=4 (it takes `minutes`) ran for its
# 20-minute default instead of 4 hours. Both calls "succeeded".

# Consumed by the gateway itself, never an error on any tool.
_GATEWAY_ARGS = frozenset({"force_refresh"})

# Arguments that promise "don't write anything". Passing one to a tool that
# lacks it is the dangerous case: the caller believes the call is safe.
_SAFETY_ARGS = frozenset({"dry_run", "preflight", "confirm", "apply", "plan"})

# Escape hatch for tools whose run() reads keys their input_schema doesn't
# declare (aliases, legacy names, secrets you deliberately keep out of the
# schema). Listed per KEY, so anything else sent to that tool is still
# rejected. Declaring the argument in _registry.py is the real fix -- prefer
# that, and delete the entry here once you have.
#   "my_tool": frozenset({"legacy_arg_name"}),
_UNDECLARED_ARGS_TOLERATED: dict[str, frozenset[str]] = {}


def _unknown_args(name: str, args: dict) -> list[str]:
    schema = _TOOLS[name].get("input_schema") or {}
    if schema.get("additionalProperties") is True:
        return []
    declared = set(schema.get("properties") or {})
    allowed = declared | _GATEWAY_ARGS | _UNDECLARED_ARGS_TOLERATED.get(name, frozenset())
    return sorted(k for k in args if k not in allowed)


# An argument declared by more tools than this is generic ("mode", "hours",
# "dry_run") and says nothing about which tool was meant -- suggesting tools
# for it produces noisy hints. Distinctive ones ("facility_id" -> the one
# sibling tool that takes it) are what the tool hint is for.
_DISTINCTIVE_ARG_MAX_TOOLS = 3


def _tools_accepting(arg: str, exclude: str) -> list[str]:
    """Sibling tools (same capability group) declaring `arg`.

    The mistake this catches is picking the wrong sibling -- two similar
    sync tools in one group, where only the other one takes this argument.
    Cross-group hits are dropped as noise. Still a heuristic: a broad group
    can yield a loose hint, which is why the error always lists the tool's
    real args right after it. Empty when the argument is too common to point
    anywhere.
    """
    if arg in _SAFETY_ARGS:
        return []
    hits = [t for t, spec in _TOOLS.items()
            if t != exclude and arg in ((spec.get("input_schema") or {}).get("properties") or {})]
    if len(hits) > _DISTINCTIVE_ARG_MAX_TOOLS:
        return []
    siblings = next((set(c["tools"]) for c in CAPABILITIES.values() if exclude in c["tools"]), set())
    return sorted(t for t in hits if t in siblings)


def _unknown_args_error(name: str, unknown: list[str]) -> dict:
    import difflib

    declared = sorted(((_TOOLS[name].get("input_schema") or {}).get("properties") or {}))
    details = {}
    for arg in unknown:
        d: dict = {}
        close = difflib.get_close_matches(arg, declared, n=3, cutoff=0.6)
        if close:
            d["did_you_mean_arg"] = close
        others = _tools_accepting(arg, exclude=name)
        if others:
            d["did_you_mean_tool"] = others
        details[arg] = d

    parts = []
    for arg in unknown:
        d = details[arg]
        msg = f"you used '{arg}' but it isn't an argument of '{name}'"
        if d.get("did_you_mean_arg"):
            msg += f" (did you mean {' / '.join(repr(a) for a in d['did_you_mean_arg'])}?)"
        elif d.get("did_you_mean_tool"):
            msg += f" (did you mean to use {' / '.join(d['did_you_mean_tool'])}?)"
        parts.append(msg)

    out = {
        "success": False,
        "error": (f"Nothing was run: {'; '.join(parts)}. "
                  f"'{name}' takes: {', '.join(declared) or '(no arguments)'}."),
        "error_code": "UNKNOWN_ARGUMENT",
        "unknown_args": unknown,
        "valid_args": declared,
        "suggestions": details,
    }
    unsafe = sorted(set(unknown) & _SAFETY_ARGS)
    if unsafe:
        out["warning"] = (
            f"'{name}' has no {'/'.join(unsafe)} mode. Before this check existed a call "
            f"like this ran for real with the flag silently ignored -- if you wanted a "
            f"preview, this tool can't give one; check its description for what it writes."
        )
    return out


def _run_tool_raw(name: str, args: dict, timeout_s: float | None = None,
                  force_refresh: bool = False) -> tuple[str, dict | None]:
    """Returns (result_json, image_info_or_None) — image_info is {b64, mime} if present."""
    if name not in _TOOLS:
        return json.dumps({
            "success": False,
            "error": f"Unknown tool '{name}'. Use search_tools or load_capability to find the right name.",
        }), None

    args = args or {}
    # Honor force_refresh whether it arrived as run_tool's own param or
    # inside the tool args (some tools accept it natively —
    # leave it in args for them; _result_cache strips it from the key).
    force_refresh = force_refresh or str(args.get("force_refresh", "")).lower() == "true"
    cache_ttl = _TOOLS[name].get("cache_ttl_s")
    schema = _TOOLS[name]["input_schema"]
    try:
        import jsonschema
        jsonschema.validate(instance=args, schema=schema)
    except ImportError:
        pass  # jsonschema not installed — skip pre-validation, fall through to normal dispatch
    except jsonschema.exceptions.ValidationError as e:
        bad_field = e.path[0] if e.path else None
        field_schema = schema.get("properties", {}).get(bad_field) if bad_field else None
        return json.dumps({
            "success": False,
            "error": f"Invalid arguments for '{name}': {e.message}",
            "error_field": bad_field,
            "field_schema": field_schema,
            "hint": "This only catches what the tool's schema declares as required/typed — some tools document additional conditional requirements in their description that aren't schema-enforced. Check load_capability's description for that tool if this passes but the tool still fails oddly.",
        }), None

    unknown = _unknown_args(name, args)
    if unknown:
        return json.dumps(_unknown_args_error(name, unknown)), None

    placeholder = _detect_placeholder(args)
    if placeholder:
        return json.dumps({
            "success": False,
            "error": f"'{placeholder['field']}' looks like a placeholder value (\"{placeholder['value']}\"), not real data",
            "error_field": placeholder["field"],
            "hint": (
                f"Matched pattern '{placeholder['pattern']}'. If this really is intentional "
                "(e.g. a genuine ID that happens to look like a pattern), that's a "
                "false positive — rewording the call won't help; this check only exists "
                "to catch made-up values. Look up the real value with another tool first — "
                "search_tools/load_capability can help find one."
            ),
        }), None

    # Opt-in result cache (after validation/placeholder checks so a cache
    # hit never masks a malformed call). Cache errors can't break the call —
    # _result_cache swallows its own failures and returns None.
    if cache_ttl and not force_refresh:
        cached = _result_cache.get(name, args)
        if cached is not None:
            _log_audit(name, args,
                       f"cache_hit (age {cached.get('_cache_age_s', '?')}s)",
                       ["auto", "cache_hit"])
            return json.dumps(cached), None

    # Propagate force_refresh into the tool's OWN args when its schema
    # declares support. Some tools cache internally — that cache is the only one their callers ever see,
    # gateway or direct import — so a gateway-only force_refresh would
    # silently hand back stale data to someone explicitly asking for live
    # numbers. Declaring "force_refresh" in a tool's input_schema is the
    # opt-in signal for this. (_result_cache strips it from cache keys, so
    # this never fragments entries.)
    if force_refresh and "force_refresh" in schema.get("properties", {}):
        args = {**args, "force_refresh": True}

    deadline = timeout_s or _DEFAULT_TOOL_TIMEOUT_S
    future = _TOOL_EXECUTOR.submit(_call_tool, name, args)
    try:
        result_json = future.result(timeout=deadline)
    except concurrent.futures.TimeoutError:
        _log_audit(name, args, f"GATEWAY_TIMEOUT after {deadline}s", ["auto", "timeout"])
        return json.dumps({
            "success": False,
            "error": f"'{name}' did not respond within {deadline}s — treating it as hung rather than waiting indefinitely.",
            "error_code": "GATEWAY_TIMEOUT",
            "hint": (
                "This is a gateway-level guarantee, not something the tool itself reported — "
                "it may still finish on its own in the background. Common causes: a slow/unreachable "
                "external API, VPN or network issues, or the tool waiting on something that will never "
                "arrive. If this tool legitimately needs longer, pass a larger timeout_s to run_tool."
            ),
        }), None
    except Exception as e:
        _log_audit(name, args, f"TOOL_CRASHED: {e}", ["auto", "crashed"])
        return json.dumps({
            "success": False,
            "error": f"'{name}' crashed: {e}",
            "error_code": "TOOL_CRASHED",
        }), None

    final_json, image_info = result_json, None
    try:
        result_dict = json.loads(result_json)
        if cache_ttl:
            # Before the image-pop below, so put() sees the original payload
            # and can refuse image results itself (success-only, no images).
            _result_cache.put(name, args, result_dict, ttl_s=cache_ttl)
        b64 = result_dict.pop("_image_b64", None)
        mime = result_dict.pop("_image_mime", "image/png")
        if b64:
            final_json, image_info = json.dumps(result_dict), {"b64": b64, "mime": mime}
        elif result_dict.get("success") is False:
            extra = enrich_error(name, result_dict.get("error_code"), result_dict)
            if extra:
                final_json = json.dumps({**result_dict, **extra})
    except Exception:
        result_dict = None

    if isinstance(result_dict, dict):
        ok = result_dict.get("success") is not False
        tag = "success" if ok else "failure"
        summary = "success" if ok else f"failed: {result_dict.get('error', '(no error message)')}"
    else:
        tag = "success"
        summary = "(non-dict result)"
    _log_audit(name, args, summary if len(str(summary)) <= 200 else str(summary)[:200] + "...", ["auto", tag])

    return final_json, image_info


_GATEWAY_TOOLS = {
    "list_capabilities": {
        "description": (
            "Browse the available capability groups (name + description only, no tool "
            "schemas). Start here. Follow up with load_capability(id) once you know which "
            "group you need, or search_tools(query) if none of the descriptions clearly fit."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    "search_tools": {
        "description": (
            "Flat search across every tool's name and description, regardless of "
            "capability grouping. Use this when list_capabilities' descriptions don't "
            "clearly point at the right group, or when you're not sure a tool exists at all."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search term, e.g. 'git' or 'json'"}},
            "required": ["query"],
        },
    },
    "load_capability": {
        "description": (
            "Get the full tool list (name, description, input schema) for one capability "
            "group, so you can call its tools directly with run_tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "enum": sorted(CAPABILITIES.keys()),
                    "description": "Capability id from list_capabilities",
                },
            },
            "required": ["id"],
        },
    },
    "run_tool": {
        "description": (
            "Call any tool by name, with its normal arguments. Works for any tool in the "
            "registry regardless of whether you called load_capability first — that's a "
            "discovery aid, not a requirement. "
            "A small allowlist of read-only tools is result-cached (16h default): a fresh "
            "prior answer returns instantly with _from_cache=true and _cache_age_s. Pass "
            "force_refresh=true when the user wants live numbers; manage entries with the "
            "'result_cache' tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tool name, e.g. 'git_status' or 'json_query'"},
                "args": {"type": "object", "description": "Arguments for that tool (default: {})"},
                "timeout_s": {
                    "type": "number",
                    "description": f"Max seconds to wait before treating the tool as hung and returning a clean timeout error (default: {_DEFAULT_TOOL_TIMEOUT_S}). Raise this for tools you know legitimately take longer.",
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Bypass the result cache for this call and re-run the tool for real (the fresh result still updates the cache). Only meaningful for cache-allowlisted tools; harmless otherwise.",
                },
            },
            "required": ["name"],
        },
    },
}


def _dispatch(gateway_tool: str, arguments: dict) -> tuple[str, dict | None]:
    """Returns (result_json, image_info_or_None)."""
    arguments = arguments or {}
    if gateway_tool == "list_capabilities":
        return json.dumps(_list_capabilities()), None
    if gateway_tool == "search_tools":
        return json.dumps(_search_tools(arguments.get("query", ""))), None
    if gateway_tool == "load_capability":
        return json.dumps(_load_capability(arguments.get("id", ""))), None
    if gateway_tool == "run_tool":
        return _run_tool_raw(arguments.get("name", ""), arguments.get("args", {}) or {},
                             arguments.get("timeout_s"),
                             bool(arguments.get("force_refresh", False)))
    return json.dumps({"success": False, "error": f"Unknown gateway tool: {gateway_tool}"}), None


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

async def _serve_stdio() -> None:
    server = Server(SERVER_NAME)

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(name=name, description=spec["description"], inputSchema=spec["input_schema"])
            for name, spec in _GATEWAY_TOOLS.items()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result_json, image_info = _dispatch(name, arguments)
        if image_info:
            return [
                types.TextContent(type="text", text=result_json),
                types.ImageContent(type="image", data=image_info["b64"], mimeType=image_info["mime"]),
            ]
        return [types.TextContent(type="text", text=result_json)]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


# ---------------------------------------------------------------------------
# --doctor: rich, actionable diagnostics -- built because --selftest's plain
# "ImportError: No module named X" can't tell three very different problems
# apart: (1) a package installed at the WRONG version (still imports fine,
# fails later deep inside a real tool call with zero "what version do I
# need" context), (2) a package genuinely not installed at all (pip install
# fixes it), and (3) a tool's own .py file missing from an incomplete copy
# (no pip command fixes THAT). --doctor distinguishes all three and gives a
# copy-pasteable fix for each, plus checks whether Claude actually knows
# about this server at all.
# ---------------------------------------------------------------------------

_REQ_LINE_RE = re.compile(r"^([A-Za-z0-9_.\-]+)\s*(.*)$")
_SPEC_CLAUSE_RE = re.compile(r"(>=|<=|==|!=|>|<)\s*([\d.]+)")


def _parse_semver(v: str) -> tuple[int, ...]:
    parts = []
    for seg in v.split("."):
        m = re.match(r"\d+", seg)
        parts.append(int(m.group()) if m else 0)
    return tuple(parts)


def _version_satisfies(installed: str, specifier: str) -> bool:
    """Minimal comma-separated specifier check (>=, <=, ==, !=, >, <) — no
    dependency on the `packaging` library (ironic to require a new package
    to check for missing ones), since this repo's own requirements.txt only
    ever produces the simple `>=min,<max` shape itself."""
    if not specifier:
        return True
    inst = _parse_semver(installed)
    for clause in specifier.split(","):
        m = _SPEC_CLAUSE_RE.match(clause.strip())
        if not m:
            continue
        op, ver = m.group(1), _parse_semver(m.group(2))
        n = max(len(inst), len(ver))
        a = inst + (0,) * (n - len(inst))
        b = ver + (0,) * (n - len(ver))
        satisfied = {
            ">=": a >= b, "<=": a <= b, "==": a == b,
            "!=": a != b, ">": a > b, "<": a < b,
        }[op]
        if not satisfied:
            return False
    return True


def _parse_requirements_for_doctor(path: Path) -> list[tuple[str, str, str]]:
    """(package_name, version_specifier, full_requirement_line) per real
    dependency line — specifier is "" when the line is unpinned."""
    out = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.split("#", 1)[0].strip()  # drop inline comments
        if not s:
            continue
        m = _REQ_LINE_RE.match(s)
        if not m:
            continue
        name, specifier = m.group(1), m.group(2).strip()
        out.append((name, specifier, s))
    return out


def _venv_install_hint(requirement_line: str) -> str:
    """Platform-aware, copy-pasteable fix — installs into an isolated venv
    next to this toolkit instead of touching whatever else is on this
    machine (or clobbering a version some OTHER tool on the machine needs)."""
    if sys.platform == "win32":
        return (
            "python -m venv .venv-toolkit && "
            f".venv-toolkit\\Scripts\\python.exe -m pip install \"{requirement_line}\""
        )
    return (
        "python3 -m venv .venv-toolkit && "
        f".venv-toolkit/bin/python -m pip install \"{requirement_line}\""
    )


def _doctor_packages() -> list[dict]:
    import importlib.metadata

    req_path = Path(__file__).parent / "requirements.txt"
    findings = []
    for name, specifier, full_line in _parse_requirements_for_doctor(req_path):
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            findings.append({
                "package": name, "status": "NOT_INSTALLED", "required": full_line,
                "fix": f'pip install "{full_line}"' if full_line != name else f"pip install {name}",
            })
            continue
        if _version_satisfies(installed, specifier):
            findings.append({"package": name, "status": "OK", "installed": installed})
        else:
            findings.append({
                "package": name, "status": "VERSION_MISMATCH",
                "installed": installed, "required": full_line,
                "message": (
                    f"You have {name} {installed} installed, but this toolkit requires "
                    f"{full_line}. Installing the right version in an isolated environment "
                    "keeps this from disturbing anything else on this machine:"
                ),
                "fix": _venv_install_hint(full_line),
            })
    return findings


def _doctor_tools() -> list[dict]:
    """Per-tool import check like --selftest, but distinguishing WHY it
    failed: a missing .py FILE (incomplete copy — no pip command fixes it)
    vs. an actual import error once the file is confirmed present."""
    here = Path(__file__).parent
    findings = []
    for tool_name, spec in sorted(_TOOLS.items()):
        module = spec["module"]
        # Dotted modules (e.g. "grocery.kroger_receipt") are subpackage paths,
        # not a literal dot in the filename -- grocery/kroger_receipt.py.
        module_path = here / (module.replace(".", "/") + ".py")
        if not module_path.is_file():
            findings.append({
                "tool": tool_name, "status": "MISSING_FILE",
                "message": (
                    f"{module}.py is missing from this toolkit's folder. This isn't "
                    "something pip can fix — get a fresh copy of this file (and re-check "
                    "the rest of the folder) from whoever built this toolkit."
                ),
            })
            continue
        try:
            importlib.import_module(module)
        except Exception as e:
            findings.append({
                "tool": tool_name, "status": "IMPORT_ERROR",
                "message": f"{type(e).__name__}: {e}",
            })
    return findings


def _doctor_registration() -> dict:
    """Best-effort visibility into whether Claude actually knows about this
    server — today this is a manual paste-a-prompt step in most toolkit
    READMEs; this surfaces what's actually checkable without guessing."""
    import shutil

    here = Path(__file__).parent
    server_name = SERVER_NAME

    result: dict = {"expected_server_name": server_name}

    for key, path in (("project", here / ".mcp.json"), ("global", Path.home() / ".claude.json")):
        if not path.is_file():
            result[f"{key}_config_path"] = None
            continue
        result[f"{key}_config_path"] = str(path)
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
            result[f"{key}_registers_this_name"] = server_name in cfg.get("mcpServers", {})
        except Exception as e:
            result[f"{key}_config_parse_error"] = str(e)

    result["claude_cli_on_path"] = shutil.which("claude") is not None
    return result


# ---------------------------------------------------------------------------
# CLI fallback (direct invocation for testing)
# ---------------------------------------------------------------------------

def _cli_dispatch(args: list[str]) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not args or args[0] in ("-h", "--help"):
        print("Usage: python gateway_server.py <list_capabilities|search_tools|load_capability|run_tool> '<json_args>'")
        print("       python gateway_server.py --validate")
        print("       python gateway_server.py --selftest")
        print("       python gateway_server.py --doctor")
        print("       python gateway_server.py --measure")
        sys.exit(0)

    if args[0] == "--measure":
        # What the model pays up front, every turn: each exposed tool's name,
        # description and schema. ~4 chars/token is a rough English/JSON
        # average — good for comparing the two surfaces, not for billing.
        def _surface(tools: dict) -> int:
            return len(json.dumps([
                {"name": n, "description": s["description"], "inputSchema": s["input_schema"]}
                for n, s in tools.items()
            ]))
        flat, gated = _surface(_TOOLS), _surface(_GATEWAY_TOOLS)
        print(f"  {len(_TOOLS)} tools exposed directly: {flat:>9,} chars  (~{flat // 4:,} tokens)")
        print(f"  {len(_GATEWAY_TOOLS)} gateway tools:          {gated:>9,} chars  (~{gated // 4:,} tokens)")
        sys.exit(0)

    if args[0] == "--validate":
        errors = _validate_schemas() + _validate_capabilities()
        if errors:
            for e in errors:
                print(f"  FAIL  {e}")
            sys.exit(1)
        print(f"  OK  {len(_TOOLS)} tool schemas valid; each assigned to exactly one of {len(CAPABILITIES)} capabilities.")
        sys.exit(0)

    if args[0] == "--selftest":
        # Unlike --validate (registry/capability bookkeeping only), this
        # actually imports every registered tool module — the real check for
        # "is this machine's dependency set actually satisfied", since a
        # missing pip package only ever surfaces as an ImportError here, not
        # as a --validate failure. Cheap, and the last line of defense before
        # a fresh install's first live tool call fails instead.
        failures = []
        for tool_name, spec in sorted(_TOOLS.items()):
            try:
                importlib.import_module(spec["module"])
            except Exception as e:
                failures.append((tool_name, spec["module"], f"{type(e).__name__}: {e}"))
        if failures:
            for tool_name, module, err in failures:
                print(f"  FAIL  {tool_name} ({module}.py): {err}")
            print(f"\n  {len(failures)} of {len(_TOOLS)} tool module(s) failed to import "
                  f"— usually a missing pip package. Re-run: pip install -r requirements.txt")
            sys.exit(1)
        print(f"  OK  all {len(_TOOLS)} tool modules imported cleanly.")
        sys.exit(0)

    if args[0] == "--doctor":
        pkg_findings = _doctor_packages()
        tool_findings = _doctor_tools()
        reg = _doctor_registration()

        print("=== Package versions ===")
        for f in pkg_findings:
            if f["status"] == "OK":
                print(f"  OK    {f['package']} {f['installed']}")
            elif f["status"] == "NOT_INSTALLED":
                print(f"  FAIL  {f['package']} — not installed. Fix: {f['fix']}")
            else:
                print(f"  FAIL  {f['message']}")
                print(f"        Fix: {f['fix']}")
        bad_pkgs = [f for f in pkg_findings if f["status"] != "OK"]

        print("\n=== Tool modules ===")
        if tool_findings:
            for f in tool_findings:
                print(f"  FAIL  {f['tool']} [{f['status']}]: {f['message']}")
        else:
            print(f"  OK    all {len(_TOOLS)} tool modules present and importable.")

        print("\n=== Claude Code registration ===")
        name = reg["expected_server_name"]
        print(f"  Expected MCP server name (CAPABILITY_GATEWAY_NAME, default 'capability-gateway'): {name}")
        for key, label in (("project", "Project .mcp.json"), ("global", "Global settings")):
            path = reg.get(f"{key}_config_path")
            if not path:
                default = ".mcp.json next to this file" if key == "project" else str(Path.home() / ".claude.json")
                print(f"  {label}: not found ({default})")
                continue
            if f"{key}_config_parse_error" in reg:
                print(f"  {label}: {path} — could not parse ({reg[f'{key}_config_parse_error']})")
                continue
            registered = reg.get(f"{key}_registers_this_name")
            print(f"  {label}: {path} — {'registers' if registered else 'does NOT register'} '{name}'")
        print(f"  'claude' CLI on PATH: {reg['claude_cli_on_path']}")
        if not reg.get("project_registers_this_name") and not reg.get("global_registers_this_name"):
            print(f"  If tools named mcp__{name}__* aren't showing up in Claude Code, this is likely why — "
                  "register it (see this toolkit's README's setup section), then restart Claude Code.")

        sys.exit(1 if (bad_pkgs or tool_findings) else 0)

    gateway_tool = args[0]
    if gateway_tool not in _GATEWAY_TOOLS:
        print(json.dumps({"success": False, "error": f"Unknown gateway tool '{gateway_tool}'. Valid: {list(_GATEWAY_TOOLS.keys())}"}))
        sys.exit(1)

    raw = args[1] if len(args) > 1 else "{}"
    arguments = json.loads(raw)
    result_json, image_info = _dispatch(gateway_tool, arguments)
    print(result_json)
    if image_info:
        print(f"  [image omitted in CLI mode, {len(image_info['b64'])} b64 chars, {image_info['mime']}]")


def main() -> None:
    args = sys.argv[1:]
    if _MCP_AVAILABLE and not args:
        import asyncio
        asyncio.run(_serve_stdio())
        return
    _cli_dispatch(args)


if __name__ == "__main__":
    main()
