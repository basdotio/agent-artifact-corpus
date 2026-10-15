"""Evidence chain retrieval for runtime diagnosis verification.

Assembles deterministic, cross-referenced evidence chains from the KB graph.
No LLM reasoning -- pure data traversal: same input always produces same output.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ._loader import (
    load_code_path,
    load_code_path_index,
    load_db_table_index,
    load_diagnostic_tree,
    load_human_error,
    load_protocol,
)

# tree_id keyword -> code path entity_type (for trees missing related_code_paths)
_TREE_TO_CODE_PATH: dict[str, str] = {
    "vlan": "vlan-create",
    "lag": "lag-create",
    "port": "port-config",
    "route": "route-install-bgp",
}


def explain_diagnosis(
    tree_id: str,
    node_id: str,
    code_path_id: str | None = None,
) -> dict | None:
    """Build a deterministic evidence chain for a diagnostic finding.

    Returns structured proof showing WHY this diagnosis is correct,
    cross-referenced against code paths, protocols, DB schemas,
    and human error patterns.
    """
    tree = load_diagnostic_tree(tree_id)
    if tree is None:
        return None

    node = None
    for n in tree.get("nodes", []):
        if n.get("node_id") == node_id:
            node = n
            break
    if node is None:
        return None
    if node.get("node_type") != "leaf":
        return {"error": "explain_diagnosis requires a leaf node (finding), not a branch node"}

    diagnostic_path = _trace_path_to_node(tree, node_id)

    path_id = code_path_id or _resolve_code_path(tree)
    code_path_evidence = _build_code_path_evidence(path_id, node) if path_id else None

    proto_id = tree.get("related_protocol", "")
    protocol_grounding = _build_protocol_grounding(proto_id, node) if proto_id else None

    human_errors = []
    for err_id in tree.get("related_errors", []):
        err = load_human_error(err_id)
        if err:
            human_errors.append({
                "error_id": err.get("error_id"),
                "display_name": err.get("display_name"),
                "what_goes_wrong": err.get("what_goes_wrong", ""),
                "detection_commands": err.get("detection_commands", []),
                "correct_procedure": err.get("correct_procedure", ""),
            })

    db_tables = _extract_db_tables(code_path_evidence, node)
    verify_plan = _collect_verify_commands(node, code_path_evidence, protocol_grounding)

    gaps = []
    if not diagnostic_path:
        gaps.append("path_reconstruction_failed")
    if not code_path_evidence:
        gaps.append("no_code_path_coverage")
    if not protocol_grounding:
        gaps.append("no_protocol_grounding")
    if not human_errors:
        gaps.append("no_human_error_checks")
    if not db_tables:
        gaps.append("no_db_table_verification")

    return {
        "diagnosis": {
            "tree_id": tree_id,
            "node_id": node_id,
            "finding": node.get("finding", ""),
            "action": node.get("action", ""),
        },
        "evidence_chain": {
            "diagnostic_path": diagnostic_path,
            "code_path_evidence": code_path_evidence,
            "protocol_grounding": protocol_grounding,
            "human_error_check": human_errors,
            "db_tables_involved": db_tables,
            "verification_plan": verify_plan,
        },
        "completeness": {
            "has_diagnostic_path": bool(diagnostic_path),
            "has_code_path": code_path_evidence is not None,
            "has_protocol_grounding": protocol_grounding is not None,
            "has_human_error_check": len(human_errors) > 0,
            "has_db_tables": len(db_tables) > 0,
            "gaps": gaps,
        },
    }


def verify_action(
    action: str,
    entity_type: str | None = None,
    expected_fix: str | None = None,
) -> dict | None:
    """Verify a proposed fix against the KB's code path and DB schema data.

    Traces what happens when a config command is executed: CLI -> CONFIG_DB ->
    daemon -> APPL_DB -> orchagent -> ASIC_DB, with each DB write verified
    against the db_table_index.
    """
    etype = entity_type or _infer_entity_type(action)
    if not etype:
        return {"found": False, "error": "Could not determine entity_type from action text. Provide entity_type parameter."}

    path_id = _find_code_path_by_entity(etype)
    if not path_id:
        return {"found": False, "error": f"No code path found for entity_type '{etype}'."}

    cp = load_code_path(path_id)
    if cp is None:
        return {"found": False, "error": f"Code path '{path_id}' not found."}

    db_index = load_db_table_index()
    action_trace = []
    db_writes = []
    daemon_chain = []

    for step in cp.get("steps", []):
        trace_entry = {
            "step": step.get("step"),
            "actor": step.get("actor", ""),
            "action": step.get("action", ""),
            "verify": step.get("verify", ""),
        }
        if step.get("source_file"):
            trace_entry["source_file"] = step["source_file"]
        if step.get("source_function"):
            trace_entry["source_function"] = step["source_function"]
        action_trace.append(trace_entry)

        actor = step.get("actor", "")
        if actor and actor not in daemon_chain:
            daemon_chain.append(actor)

        dw = step.get("db_write")
        if dw:
            table = dw.get("table", "")
            db = dw.get("db", "")
            db_key = f"CONFIG_DB:{table}" if "config" in db.lower() else table
            schema_entry = db_index.get(db_key)
            if schema_entry is None:
                for k in db_index:
                    if table.upper() in k.upper():
                        schema_entry = db_index[k]
                        break
            db_writes.append({
                "table": table,
                "db": db,
                "key_pattern": dw.get("key_pattern", ""),
                "fields": dw.get("fields", []),
                "verified_in_schema": schema_entry is not None,
                "verify": step.get("verify", ""),
            })

    verify_commands = [s.get("verify") for s in cp.get("steps", []) if s.get("verify")]

    coverage_gaps = []
    if not db_writes:
        coverage_gaps.append("no_db_writes_documented")
    unverified = [w["table"] for w in db_writes if not w["verified_in_schema"]]
    if unverified:
        coverage_gaps.append(f"tables_not_in_schema_index: {unverified}")

    return {
        "path_id": path_id,
        "display_name": cp.get("display_name", ""),
        "trigger": cp.get("trigger", ""),
        "action_trace": action_trace,
        "db_writes": db_writes,
        "daemon_chain": daemon_chain,
        "verify_commands": verify_commands,
        "coverage_gaps": coverage_gaps,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trace_path_to_node(tree: dict, target_id: str) -> list[dict]:
    """BFS from root to target node, recording the branch taken at each step."""
    nodes_by_id = {n["node_id"]: n for n in tree.get("nodes", [])}
    if not nodes_by_id:
        return []

    start = tree["nodes"][0]["node_id"]
    queue: list[tuple[str, list[dict]]] = [(start, [])]
    visited: set[str] = set()

    while queue:
        nid, path = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        node = nodes_by_id.get(nid)
        if node is None:
            continue

        if nid == target_id:
            return path

        for answer, next_id in node.get("branches", {}).items():
            queue.append((next_id, path + [{
                "node_id": nid,
                "question": node.get("question", ""),
                "answer_branch": answer,
                "commands": node.get("commands", []),
            }]))

    return []


def _resolve_code_path(tree: dict) -> str | None:
    """Get the code path ID from the tree's cross-refs or infer from tree_id."""
    related = tree.get("related_code_paths", [])
    if related:
        return related[0]
    tid = tree.get("tree_id", "")
    for keyword, path_id in _TREE_TO_CODE_PATH.items():
        if keyword in tid:
            return path_id
    return None


def _find_code_path_by_entity(entity_type: str) -> str | None:
    """Find a code path by entity_type from the code path index."""
    index = load_code_path_index()
    et_lower = entity_type.lower()
    for pid, meta in index.items():
        if meta.get("entity_type", "").lower() == et_lower:
            return pid
    for pid, meta in index.items():
        if et_lower in pid.lower():
            return pid
    return None


def _infer_entity_type(action: str) -> str | None:
    """Infer entity_type from a config command string."""
    a = action.lower()
    patterns = [
        (r"\bvlan\b", "vlan"),
        (r"\bportchannel\b|\blag\b|\bbond\b", "lag"),
        (r"\binterface\b|\bport\b|\bmtu\b|\bspeed\b", "port"),
        (r"\broute\b|\bbgp\b|\bstatic\b", "route"),
        (r"\bacl\b", "acl"),
        (r"\bvxlan\b|\bvtep\b", "tunnel"),
        (r"\barp\b|\bneighbor\b", "neighbor"),
        (r"\bfdb\b|\bmac\b", "fdb"),
    ]
    for pattern, etype in patterns:
        if re.search(pattern, a):
            return etype
    return None


def _build_code_path_evidence(path_id: str, node: dict) -> dict | None:
    """Load a code path and find the failure point matching the diagnostic node."""
    cp = load_code_path(path_id)
    if cp is None:
        return None

    finding_text = f"{node.get('finding', '')} {node.get('action', '')}".lower()
    failure_point = _match_failure_point(cp, finding_text)

    relevant_steps = cp.get("steps", [])
    if failure_point and failure_point.get("between_steps"):
        lo, hi = failure_point["between_steps"]
        relevant_steps = [s for s in relevant_steps if lo - 1 <= s.get("step", 0) <= hi + 1]

    steps_out = []
    for s in relevant_steps:
        entry = {
            "step": s.get("step"),
            "actor": s.get("actor", ""),
            "action": s.get("action", ""),
            "verify": s.get("verify", ""),
        }
        if s.get("source_file"):
            entry["source_file"] = s["source_file"]
        if s.get("source_function"):
            entry["source_function"] = s["source_function"]
        if s.get("db_write"):
            entry["db_write"] = s["db_write"]
        steps_out.append(entry)

    return {
        "path_id": path_id,
        "display_name": cp.get("display_name", ""),
        "failure_point": failure_point,
        "relevant_steps": steps_out,
    }


def _match_failure_point(code_path: dict, finding_text: str) -> dict | None:
    """Find the failure_injection_point best matching the finding text by word overlap."""
    fps = code_path.get("failure_injection_points", [])
    if not fps:
        return None

    finding_words = set(re.findall(r"[a-z0-9_]+", finding_text))
    best_score = 0
    best_fp = None
    for i, fp in enumerate(fps):
        fp_text = f"{fp.get('failure', '')} {fp.get('symptom', '')} {fp.get('diagnosis', '')}".lower()
        fp_words = set(re.findall(r"[a-z0-9_]+", fp_text))
        score = len(finding_words & fp_words)
        if score > best_score:
            best_score = score
            best_fp = fp
    return best_fp


def _build_protocol_grounding(proto_id: str, node: dict) -> dict | None:
    """Load a protocol and find the failure_mode matching the diagnostic node."""
    proto = load_protocol(proto_id)
    if proto is None:
        return None

    finding_text = f"{node.get('finding', '')} {node.get('action', '')}".lower()
    finding_words = set(re.findall(r"[a-z0-9_]+", finding_text))

    best_fm = None
    best_score = 0
    for fm in proto.get("failure_modes", []):
        fm_text = f"{fm.get('scenario', '')} {fm.get('description', '')}".lower()
        fm_words = set(re.findall(r"[a-z0-9_]+", fm_text))
        score = len(finding_words & fm_words)
        if score > best_score:
            best_score = score
            best_fm = fm

    result = {
        "protocol_id": proto.get("protocol_id"),
        "protocol_name": proto.get("protocol_name"),
        "standard": proto.get("standard", ""),
    }
    if best_fm:
        result["matching_failure_mode"] = {
            "scenario": best_fm.get("scenario", ""),
            "description": best_fm.get("description", ""),
            "symptoms": best_fm.get("symptoms", []),
            "root_causes": best_fm.get("root_causes", best_fm.get("diagnosis", [])),
            "resolution": best_fm.get("resolution", []),
        }
    return result


def _extract_db_tables(code_path_evidence: dict | None, node: dict) -> list[dict]:
    """Extract DB tables from code path steps and diagnostic node commands."""
    db_index = load_db_table_index()
    tables_seen: set[str] = set()
    results: list[dict] = []

    if code_path_evidence:
        for step in code_path_evidence.get("relevant_steps", []):
            dw = step.get("db_write")
            if dw:
                table = dw.get("table", "")
                if table and table not in tables_seen:
                    tables_seen.add(table)
                    results.append(_lookup_table(table, dw.get("db", ""), db_index))

    commands_text = " ".join(node.get("commands", [])) + " " + node.get("action", "")
    for match in re.finditer(r"HGETALL\s+'([A-Z_]+)\|", commands_text):
        table = match.group(1)
        if table not in tables_seen:
            tables_seen.add(table)
            results.append(_lookup_table(table, "", db_index))
    for match in re.finditer(r"KEYS\s+'([A-Z_]+)\|", commands_text):
        table = match.group(1)
        if table not in tables_seen:
            tables_seen.add(table)
            results.append(_lookup_table(table, "", db_index))

    return results


def _lookup_table(table: str, db_ref: str, db_index: dict) -> dict:
    """Look up a table in the db_table_index."""
    key = f"CONFIG_DB:{table}"
    entry = db_index.get(key)
    if entry is None:
        for k, v in db_index.items():
            if table.upper() in k.upper():
                entry = v
                break

    result: dict = {"table": table}
    if entry:
        result["db"] = entry.get("db", db_ref)
        result["key_pattern"] = entry.get("key_pattern", "")
        result["verify_command"] = entry.get("verify_command", "")
        result["verified_in_index"] = True
    else:
        result["db"] = db_ref
        result["verified_in_index"] = False
    return result


def _collect_verify_commands(
    node: dict,
    code_path_evidence: dict | None,
    protocol_grounding: dict | None,
) -> list[dict]:
    """Collect and deduplicate verification commands from all evidence sources."""
    seen: set[str] = set()
    plan: list[dict] = []

    for cmd in node.get("commands", []):
        if cmd not in seen:
            seen.add(cmd)
            plan.append({"command": cmd, "source": "diagnostic_node"})

    if code_path_evidence:
        for step in code_path_evidence.get("relevant_steps", []):
            cmd = step.get("verify", "")
            if cmd and cmd not in seen:
                seen.add(cmd)
                plan.append({
                    "command": cmd,
                    "source": f"code_path:{code_path_evidence['path_id']}:step{step.get('step', '?')}",
                })

    if protocol_grounding:
        fm = protocol_grounding.get("matching_failure_mode", {})
        for cmd in fm.get("resolution", []):
            if cmd not in seen:
                seen.add(cmd)
                plan.append({"command": cmd, "source": f"protocol:{protocol_grounding['protocol_id']}"})

    return plan
