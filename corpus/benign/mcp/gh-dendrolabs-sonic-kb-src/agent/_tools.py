"""KB tool definitions and execution dispatcher for sonic-kb.

Each retrieval function becomes an LLM-callable tool with a JSON Schema definition.
execute_tool() dispatches by name, serializes results, and catches exceptions.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from ._types import ToolDefinition, ToolResult

TOOL_DEFINITIONS: list[ToolDefinition] = [
    # --- Protocol tools ---
    ToolDefinition(
        name="get_protocol",
        description=(
            "Get full protocol documentation including states, transitions, timers, "
            "failure modes, and SONiC-specific notes (config_db_tables, FRR mapping). "
            "Returns the complete protocol knowledge base entry with resolved definitions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "protocol_id": {
                    "type": "string",
                    "description": "Protocol ID (e.g., 'bgp-4', 'ospfv2', 'bfd', 'lacp', 'lldp')",
                },
            },
            "required": ["protocol_id"],
        },
    ),
    ToolDefinition(
        name="get_protocol_state",
        description=(
            "Get details for a specific protocol state: description, transitions in/out, "
            "and related failure modes. Use when a protocol is stuck in a particular state."
        ),
        parameters={
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol ID"},
                "state": {"type": "string", "description": "State name (e.g., 'IDLE', 'ESTABLISHED', 'FULL')"},
            },
            "required": ["protocol_id", "state"],
        },
    ),
    ToolDefinition(
        name="get_protocol_failures",
        description=(
            "Get known failure patterns for a protocol. Each failure includes symptoms, "
            "root causes, resolution steps, and verification commands. "
            "Filter by keyword or state to narrow results."
        ),
        parameters={
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol ID"},
                "keyword": {"type": "string", "description": "Optional keyword filter (e.g., 'flap', 'stuck', 'hardware')"},
                "state": {"type": "string", "description": "Optional state filter"},
            },
            "required": ["protocol_id"],
        },
    ),
    ToolDefinition(
        name="get_protocol_timers",
        description=(
            "Get protocol timer details including defaults, ranges, and SONiC-specific "
            "config paths. Filter by timer name."
        ),
        parameters={
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol ID"},
                "name": {"type": "string", "description": "Optional timer name filter"},
            },
            "required": ["protocol_id"],
        },
    ),
    ToolDefinition(
        name="get_protocol_messages",
        description="Get protocol message/packet types with descriptions and key fields.",
        parameters={
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol ID"},
            },
            "required": ["protocol_id"],
        },
    ),
    ToolDefinition(
        name="get_related_protocols",
        description="Get list of protocols related to a given protocol.",
        parameters={
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol ID"},
            },
            "required": ["protocol_id"],
        },
    ),
    ToolDefinition(
        name="search_protocols_by_tag",
        description="Search protocols by tag (e.g., 'routing', 'layer-2', 'overlay', 'frr').",
        parameters={
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Tag to search for"},
            },
            "required": ["tag"],
        },
    ),
    ToolDefinition(
        name="get_verify_commands",
        description=(
            "Get verification commands for a protocol, optionally filtered by state or "
            "failure scenario. Returns SONiC CLI commands with what to look for."
        ),
        parameters={
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol ID"},
                "state": {"type": "string", "description": "Optional state filter"},
                "failure": {"type": "string", "description": "Optional failure scenario keyword"},
            },
            "required": ["protocol_id"],
        },
    ),
    # --- SONiC subsystem tools ---
    ToolDefinition(
        name="get_config_db_table",
        description=(
            "Look up a CONFIG_DB (or other Redis DB) table schema. Returns the table's "
            "key pattern, fields, which daemons read/write it, related protocols, and "
            "human error risks. This is the most important tool for SONiC config questions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Table name (e.g., 'BGP_NEIGHBOR', 'PORT', 'VLAN', 'ROUTE_TABLE')",
                },
                "db_name": {
                    "type": "string",
                    "description": "Optional DB name filter (e.g., 'CONFIG_DB', 'APPL_DB', 'STATE_DB')",
                },
            },
            "required": ["table_name"],
        },
    ),
    ToolDefinition(
        name="get_daemon_info",
        description=(
            "Get details about a SONiC daemon: which container it runs in, what DBs it "
            "reads/writes, restart impact, health check commands, and source code location."
        ),
        parameters={
            "type": "object",
            "properties": {
                "daemon_name": {
                    "type": "string",
                    "description": "Daemon name (e.g., 'orchagent', 'syncd', 'bgpcfgd', 'fpmsyncd')",
                },
            },
            "required": ["daemon_name"],
        },
    ),
    ToolDefinition(
        name="trace_config_flow",
        description=(
            "Trace the full code path for a configuration or data-flow event from user "
            "action to ASIC programming. Returns ordered steps with daemon, action, source "
            "file:function, DB writes, and verification commands at each step. "
            "Also shows failure injection points where things commonly break."
        ),
        parameters={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "What is being configured (e.g., 'route', 'vlan', 'port', 'lag', 'arp', 'bgp_neighbor')",
                },
                "action": {
                    "type": "string",
                    "description": "Optional action (e.g., 'install', 'remove', 'update'). Defaults to 'install'.",
                },
            },
            "required": ["entity_type"],
        },
    ),
    ToolDefinition(
        name="list_containers",
        description=(
            "List all SONiC Docker containers with their startup order, dependencies, "
            "key daemons, and health check commands."
        ),
        parameters={"type": "object", "properties": {}},
    ),
    # --- Diagnostic tools ---
    ToolDefinition(
        name="get_log_message",
        description=(
            "Search the log message catalog for a pattern or keyword. Returns the meaning "
            "of the log message, likely causes, and recommended next diagnostic steps. "
            "Optionally filter by daemon name."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Log message text, keyword, or regex pattern to search for",
                },
                "daemon": {
                    "type": "string",
                    "description": "Optional daemon filter (e.g., 'orchagent', 'syncd', 'bgpcfgd')",
                },
            },
            "required": ["pattern"],
        },
    ),
    ToolDefinition(
        name="detect_human_error",
        description=(
            "Check if symptoms match a known human-caused breakage pattern. Describe what "
            "the user did or what you observe, and this tool returns matching error patterns "
            "with detection commands and correct procedures. "
            "CALL THIS when you suspect config was changed outside proper SONiC channels."
        ),
        parameters={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Free-text description of what the user did or symptoms observed",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context (e.g., 'bgp', 'vlan', 'port', 'config')",
                },
            },
            "required": ["description"],
        },
    ),
    ToolDefinition(
        name="get_diagnostic_tree",
        description=(
            "Get a diagnostic decision tree for a symptom. Returns a structured tree of "
            "yes/no questions with specific commands to run and what to look for. "
            "Use node_id to resume at a specific point in the tree."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symptom": {
                    "type": "string",
                    "description": "Symptom or tree ID (e.g., 'bgp-not-establishing', 'port-down', 'route-missing')",
                },
                "node_id": {
                    "type": "string",
                    "description": "Optional node ID to resume from a specific decision point",
                },
            },
            "required": ["symptom"],
        },
    ),
    # --- Procedure tools ---
    ToolDefinition(
        name="get_procedure",
        description=(
            "Get an operational procedure with step-by-step instructions, verification "
            "at each step, rollback plan, and daemon impact. "
            "Use step_id to get a single step for resumption."
        ),
        parameters={
            "type": "object",
            "properties": {
                "procedure_id": {
                    "type": "string",
                    "description": "Procedure ID (e.g., 'config-reload', 'sonic-upgrade', 'warm-reboot')",
                },
                "step_id": {
                    "type": "string",
                    "description": "Optional step ID to get a single step",
                },
            },
            "required": ["procedure_id"],
        },
    ),
    # --- Best practices ---
    ToolDefinition(
        name="get_best_practices",
        description=(
            "Get curated best practices, tips, and common pitfalls for a topic. "
            "Topics include config management, upgrades, monitoring, BGP design, etc."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic filter (e.g., 'config', 'bgp', 'upgrade', 'monitoring')",
                },
            },
        },
    ),
    # --- Semantic search ---
    ToolDefinition(
        name="search_kb",
        description=(
            "Semantic search across the entire knowledge base using natural language. "
            "Describe a problem, symptom, or topic and get ranked results from all content "
            "types (protocols, diagnostics, procedures, human errors, code paths, etc.). "
            "Use this as a starting point when you don't know which specific tool to call."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query (e.g., 'BGP session keeps flapping after config change')",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 20)",
                },
                "content_type": {
                    "type": "string",
                    "description": "Optional filter: protocol, subsystem, code-path, human-error, diagnostic, procedure, best-practice, log, definition",
                },
            },
            "required": ["query"],
        },
    ),
    # --- Anti-hallucination ---
    ToolDefinition(
        name="get_grounding_rules",
        description=(
            "Get the anti-hallucination grounding rules for this KB. These rules constrain "
            "what advice can be given and flag version scope. Load these at the start of "
            "any troubleshooting session."
        ),
        parameters={"type": "object", "properties": {}},
    ),
    # --- Search ---
    ToolDefinition(
        name="search_source_ref",
        description=(
            "Search for SONiC source code references by keyword. Returns file:function "
            "locations for key SONiC operations. Useful for tracing where behavior is "
            "implemented in the source code."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'route install', 'orchagent', 'SAI create')",
                },
            },
            "required": ["query"],
        },
    ),
    # --- Runtime verification ---
    ToolDefinition(
        name="explain_diagnosis",
        description=(
            "Build a deterministic evidence chain for a diagnostic finding. "
            "After walking a diagnostic tree to a leaf node (finding), call this "
            "to get cross-referenced proof from code paths, protocols, DB schemas, "
            "and human error patterns showing WHY this diagnosis is correct. "
            "Same inputs always produce the same output."
        ),
        parameters={
            "type": "object",
            "properties": {
                "tree_id": {
                    "type": "string",
                    "description": "Diagnostic tree ID (e.g., 'bgp-not-establishing')",
                },
                "node_id": {
                    "type": "string",
                    "description": "Leaf node ID with the finding to explain (e.g., 'n3')",
                },
                "code_path_id": {
                    "type": "string",
                    "description": "Optional: override the code path to trace (e.g., 'vlan-create'). If omitted, uses the tree's related_code_paths or infers from tree_id.",
                },
            },
            "required": ["tree_id", "node_id"],
        },
    ),
    ToolDefinition(
        name="verify_action",
        description=(
            "Verify a proposed fix command against the KB's code path and DB schema data. "
            "Traces what happens when a config command is executed: CLI -> CONFIG_DB -> "
            "daemon -> APPL_DB -> orchagent -> ASIC_DB -> hardware. Each DB write is "
            "verified against the schema index. Call this BEFORE recommending any fix."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The proposed fix command or description (e.g., 'config vlan add 100')",
                },
                "entity_type": {
                    "type": "string",
                    "description": "Optional: entity type to trace (vlan, port, route, lag, acl, tunnel, neighbor, fdb). Inferred from action if omitted.",
                },
                "expected_fix": {
                    "type": "string",
                    "description": "Optional: what the action should accomplish (for context in the trace)",
                },
            },
            "required": ["action"],
        },
    ),
    ToolDefinition(
        name="get_troubleshoot_guide",
        description=(
            "Get the structured troubleshooting methodology. Returns a 5-phase "
            "process (DEFINE, DIAGNOSE, EVIDENCE, RESOLVE, VERIFY) with specific "
            "tools to call at each phase and rules for verified troubleshooting. "
            "Call this at the start of any troubleshooting session."
        ),
        parameters={
            "type": "object",
            "properties": {
                "phase": {
                    "type": "integer",
                    "description": "Optional: return only a specific phase (1-5). Omit for all phases.",
                },
            },
        },
    ),
]


def _serialize(result) -> str:
    """Serialize a retrieval result to JSON string with uniform kb_coverage."""
    if result is None:
        return json.dumps({"found": False, "kb_coverage": "not_indexed",
                          "coverage_note": "No matching data in the SONiC KB for this query."})
    if isinstance(result, dict):
        out = {**result, "kb_coverage": result.get("kb_coverage", "indexed")}
        return json.dumps(out, indent=2, default=str)
    if isinstance(result, list):
        return json.dumps({"results": result, "count": len(result),
                          "kb_coverage": "indexed"}, indent=2, default=str)
    if hasattr(result, "__dataclass_fields__"):
        out = {**asdict(result), "kb_coverage": "indexed"}
        return json.dumps(out, indent=2, default=str)
    return json.dumps({"result": str(result), "kb_coverage": "indexed"})


def execute_tool(name: str, arguments: dict, tool_call_id: str = "") -> ToolResult:
    """Dispatch a tool call to the appropriate retrieval function."""
    try:
        from ..retrieval.best_practices import get_best_practices
        from ..retrieval.code_paths import get_code_path, list_code_paths, trace_config_flow
        from ..retrieval.semantic_search import search_kb as _search_kb
        from ..retrieval.diagnostics import get_diagnostic_tree, list_diagnostic_trees
        from ..retrieval.evidence_chain import explain_diagnosis as _explain_diagnosis, verify_action as _verify_action
        from ..retrieval.human_errors import detect_human_error, get_human_error
        from ..retrieval.logs import get_log_message
        from ..retrieval.procedures import get_procedure, list_procedures
        from ..retrieval.protocols import (
            get_protocol,
            get_protocol_failures,
            get_protocol_messages,
            get_protocol_state,
            get_protocol_timers,
            get_related_protocols,
            get_verify_commands,
            search_protocols_by_tag,
        )
        from ..retrieval.subsystems import get_daemon_info, get_subsystem_info, list_containers
        from ..retrieval._loader import load_db_table_index, load_grounding_rules, load_methodology, load_source_refs_index, load_source_functions_artifact

        dispatch: dict = {
            "get_protocol": lambda: get_protocol(arguments["protocol_id"]),
            "get_protocol_state": lambda: get_protocol_state(
                arguments["protocol_id"], arguments["state"]
            ),
            "get_protocol_failures": lambda: get_protocol_failures(
                arguments["protocol_id"],
                keyword=arguments.get("keyword"),
                state=arguments.get("state"),
            ),
            "get_protocol_timers": lambda: get_protocol_timers(
                arguments["protocol_id"],
                name=arguments.get("name"),
            ),
            "get_protocol_messages": lambda: get_protocol_messages(arguments["protocol_id"]),
            "get_related_protocols": lambda: get_related_protocols(arguments["protocol_id"]),
            "search_protocols_by_tag": lambda: search_protocols_by_tag(arguments["tag"]),
            "get_verify_commands": lambda: get_verify_commands(
                arguments["protocol_id"],
                state=arguments.get("state"),
                failure=arguments.get("failure"),
            ),
            "get_config_db_table": lambda: _dispatch_config_db_table(
                arguments, load_db_table_index
            ),
            "get_daemon_info": lambda: get_daemon_info(arguments["daemon_name"]),
            "trace_config_flow": lambda: trace_config_flow(
                arguments["entity_type"],
                action=arguments.get("action"),
            ),
            "list_containers": lambda: list_containers(),
            "get_log_message": lambda: get_log_message(
                arguments["pattern"],
                daemon=arguments.get("daemon"),
            ),
            "detect_human_error": lambda: detect_human_error(
                arguments["description"],
                context=arguments.get("context"),
            ),
            "get_diagnostic_tree": lambda: get_diagnostic_tree(
                arguments["symptom"],
                node_id=arguments.get("node_id"),
            ),
            "get_procedure": lambda: get_procedure(
                arguments["procedure_id"],
                step_id=arguments.get("step_id"),
            ),
            "get_best_practices": lambda: get_best_practices(
                topic=arguments.get("topic"),
            ),
            "get_grounding_rules": lambda: load_grounding_rules(),
            "search_source_ref": lambda: _dispatch_source_ref_search(
                arguments, load_source_refs_index, load_source_functions_artifact
            ),
            "search_kb": lambda: _search_kb(
                arguments["query"],
                top_k=arguments.get("top_k", 5),
                content_type=arguments.get("content_type"),
            ),
            "explain_diagnosis": lambda: _explain_diagnosis(
                arguments["tree_id"],
                arguments["node_id"],
                code_path_id=arguments.get("code_path_id"),
            ),
            "verify_action": lambda: _verify_action(
                arguments["action"],
                entity_type=arguments.get("entity_type"),
                expected_fix=arguments.get("expected_fix"),
            ),
            "get_troubleshoot_guide": lambda: _dispatch_methodology(
                arguments, load_methodology
            ),
        }

        fn = dispatch.get(name)
        if fn is None:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=json.dumps({"error": f"Unknown tool: {name}"}),
                is_error=True,
            )

        _required: dict[str, list[str]] = {
            "get_protocol": ["protocol_id"],
            "get_protocol_state": ["protocol_id", "state"],
            "get_protocol_failures": ["protocol_id"],
            "get_protocol_timers": ["protocol_id"],
            "get_protocol_messages": ["protocol_id"],
            "get_related_protocols": ["protocol_id"],
            "search_protocols_by_tag": ["tag"],
            "get_verify_commands": ["protocol_id"],
            "get_config_db_table": ["table_name"],
            "get_daemon_info": ["daemon_name"],
            "trace_config_flow": ["entity_type"],
            "get_log_message": ["pattern"],
            "detect_human_error": ["description"],
            "get_diagnostic_tree": ["symptom"],
            "get_procedure": ["procedure_id"],
            "search_source_ref": ["query"],
            "search_kb": ["query"],
            "explain_diagnosis": ["tree_id", "node_id"],
            "verify_action": ["action"],
        }
        if name in _required:
            missing = [k for k in _required[name] if k not in arguments]
            if missing:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=json.dumps({"error": f"Missing required arguments: {missing}"}),
                    is_error=True,
                )

        result = fn()
        return ToolResult(tool_call_id=tool_call_id, content=_serialize(result))

    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            content=json.dumps({"error": f"{type(e).__name__}: {e}"}),
            is_error=True,
        )


def _dispatch_config_db_table(arguments: dict, load_index) -> dict | None:
    """Look up a CONFIG_DB table from the index."""
    table_name = arguments["table_name"].upper()
    db_name = arguments.get("db_name", "").upper()
    index = load_index()
    key = f"{db_name}:{table_name}" if db_name else table_name
    if key in index:
        return index[key]
    for k, v in index.items():
        if table_name in k:
            if not db_name or db_name in k:
                return v
    return None


def _dispatch_methodology(arguments: dict, load_fn) -> dict | None:
    """Return the troubleshooting methodology, optionally filtered to a single phase."""
    data = load_fn()
    phase_num = arguments.get("phase")
    if phase_num is not None:
        for p in data.get("phases", []):
            if p.get("phase") == phase_num:
                return p
        return None
    return data


def _dispatch_source_ref_search(arguments: dict, load_index, load_artifact) -> list[dict]:
    """Search source references by keyword.

    Tier 1: annotated index from code-path steps (56 entries with actor/action context).
    Tier 2: full source_functions.json artifact (18965 raw entries, local only).
    """
    query = arguments["query"].lower()
    index = load_index()
    results = []
    seen_functions: set[str] = set()
    for symbol, ref in index.items():
        if query in symbol.lower():
            results.append({"symbol": symbol, "source": "annotated", **ref})
            seen_functions.add(ref.get("source_function", ""))

    artifact = load_artifact()
    if artifact is not None:
        for entry in artifact:
            func = entry.get("function", "")
            file = entry.get("file", "")
            searchable = f"{func} {file} {entry.get('repo', '')}".lower()
            if query in searchable and func not in seen_functions:
                results.append({
                    "symbol": func,
                    "source": "artifact",
                    "source_file": f"{entry['repo']}:{file}",
                    "source_function": func,
                    "line": entry.get("line", 0),
                })
                seen_functions.add(func)
    return results
