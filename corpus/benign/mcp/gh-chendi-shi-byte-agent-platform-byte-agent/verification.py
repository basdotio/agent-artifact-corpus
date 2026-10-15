"""Bounded final-answer checks against observations, with no benchmark labels.

It validates evidence use and output contracts, not the correctness of an
incident's semantic diagnosis, causal hypothesis, or recommended intervention.
"""
import copy
import hashlib
import json
import math

FIELDS = {"service", "error_rate", "status", "likely_cause", "recommendation", "citations", "uncertainty"}
ENUMS = {"status": {"healthy", "incident", "insufficient_data"},
         "likely_cause": {"none", "release_regression", "dependency_outage", "capacity_pressure", "insufficient_evidence", "conflicting_evidence"},
         "recommendation": {"monitor", "rollback_review", "dependency_escalation", "capacity_review", "collect_evidence", "verify_changes"},
         "uncertainty": {"none_detected", "causality_unproven", "insufficient_data", "conflicting_evidence"}}
TOOLS = {"service_metrics", "knowledge_search", "incident_changes"}
MAX_ANSWER_CHARS = 16000
MAX_EVENTS = 512
MAX_EVIDENCE_ITEMS = 200
MAX_ERRORS = 12


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON fields")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("non-finite JSON constants")


def _number(value):
    return type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)


def _equal_rate(actual, expected):
    if expected is None:
        return actual is None
    return _number(actual) and _number(expected) and math.isclose(actual, expected, abs_tol=1e-6, rel_tol=1e-6)


def validate_diagnostic(service, answer, events, operator_task="", strict_service_history=True):
    """Return {valid, repairable, errors, feedback} for a proposed final answer.

    service and operator_task come from the trusted operator, never model
    arguments. No filesystem/network I/O, manifest, task labels, gold values or
    answer synthesis occurs. Default strict history follows the current eval
    contract: already-executed wrong-service calls cannot be erased by repair.
    With strict_service_history=False old wrong-service results are ignored;
    that recovery policy differs from the current benchmark's success rule.
    """
    if not isinstance(service, str) or not service or len(service) > 200 or not service.isprintable():
        raise ValueError("operator service must be a bounded printable string")
    if not isinstance(operator_task, str) or len(operator_task) > 16000:
        raise ValueError("operator task must be bounded text")
    errors = []
    unrecoverable = False
    def add(code, message, terminal=False):
        nonlocal unrecoverable
        unrecoverable = unrecoverable or terminal
        if len(errors) < MAX_ERRORS and code not in {e["code"] for e in errors}:
            errors.append({"code": code, "message": message})
    def result():
        if not errors:
            return {"valid": True, "repairable": True, "errors": [], "feedback": ""}
        # Use only fixed messages and trusted/numeric values; never echo retrieved instructions.
        feedback = "Final-answer verification failed. " + " ".join(e["message"] for e in errors)
        if unrecoverable:
            feedback += " The existing executed-tool history fails the strict contract; do not erase it or claim a repaired successful run."
        else:
            feedback += " Inspect any missing target-service observations and return one corrected JSON object; do not invent evidence or certainty."
        return {"valid": False, "repairable": not unrecoverable, "errors": errors, "feedback": feedback[:3500]}
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        add("event_bound", "Tool history is malformed or exceeds the verifier event bound.", terminal=True)
        return result()
    parsed = None
    if not isinstance(answer, str) or len(answer) > MAX_ANSWER_CHARS:
        add("answer_bound", "Return bounded JSON text without Markdown fences or extra prose.")
    else:
        try:
            candidate = json.loads(answer, object_pairs_hook=_object, parse_constant=_invalid_constant)
            if not isinstance(candidate, dict) or set(candidate) != FIELDS:
                add("answer_fields", "JSON fields must be exactly service,error_rate,status,likely_cause,recommendation,citations,uncertainty.")
            else:
                parsed = candidate
        except (ValueError, TypeError, RecursionError):
            add("answer_json", "Return one valid JSON object; duplicate fields, NaN, fences and extra prose are invalid.")
    if parsed is not None:
        if parsed["service"] != service:
            add("answer_service", "Use the operator's exact service in the final answer.")
        if parsed["error_rate"] is not None and not _number(parsed["error_rate"]):
            add("answer_rate_type", "error_rate must be a finite decimal fraction in [0,1], or null for missing metrics.")
        for key, values in ENUMS.items():
            if not isinstance(parsed[key], str) or parsed[key] not in values:
                add("answer_enum_" + key, "Use a defined " + key + " enum.")
        ids = parsed["citations"]
        if not isinstance(ids, list) or len(ids) > MAX_EVIDENCE_ITEMS or any(not isinstance(i, str) or not i or len(i) > 128 for i in ids):
            add("answer_citation_type", "citations must be an array of bounded actual evidence ids.")
        elif len(ids) != len(set(ids)):
            add("answer_citation_duplicates", "Cite each evidence id only once.")
    observations = {name: [] for name in TOOLS}
    for event in events:
        if not isinstance(event, dict):
            add("malformed_event", "Tool history contains malformed events.", terminal=True)
            continue
        if event.get("kind") != "tool":
            continue
        name = event.get("name")
        arguments = event.get("arguments")
        output = event.get("output")
        if name not in TOOLS:
            add("unregistered_tool_history", "The history contains an unregistered tool attempt.", terminal=True)
            continue
        if not isinstance(arguments, dict) or arguments.get("service") != service:
            if strict_service_history:
                add("wrong_service_history", "All executed diagnostic tool calls must use the operator's exact service.", terminal=True)
            continue
        if event.get("error") or not isinstance(output, dict) or "error" in output:
            add("tool_error_history", "The history contains a failed diagnostic tool execution.", terminal=True)
            continue
        if output.get("service") != service:
            add("observation_service", "A tool response does not identify the requested service.", terminal=True)
            continue
        observations[name].append(event)
    for name in sorted(TOOLS):
        if not observations[name]:
            add("missing_" + name, "Obtain a successful " + name + " observation for the operator's service.")
    metrics = [e for e in observations["service_metrics"] if e["arguments"].get("window_minutes", 30) == 30 and e["output"].get("window_minutes") == 30]
    metric = metrics[-1]["output"] if metrics else None
    if observations["service_metrics"] and not metrics:
        add("metric_window", "Read the complete 30-minute window with service_metrics; recent-only or other windows are insufficient.")
    if metric is not None:
        observed_rate = metric.get("error_rate")
        samples = metric.get("samples")
        requests = metric.get("requests")
        shape_ok = "error_rate" in metric and type(samples) is int and type(requests) is int and requests >= 0 and 0 <= samples <= 30
        if observed_rate is None:
            shape_ok = shape_ok and (samples == 0 or requests == 0)
        else:
            shape_ok = shape_ok and _number(observed_rate) and samples == 30 and requests > 0
        if not shape_ok:
            add("metric_observation", "The latest 30-minute metric observation is incomplete or internally inconsistent.", terminal=True)
        elif parsed is not None and not _equal_rate(parsed["error_rate"], observed_rate):
            value = "null" if observed_rate is None else format(observed_rate, ".10g")
            add("aggregate_rate", "Set error_rate to the observed 30-minute aggregate fraction " + value + "; do not substitute recent_error_rate.")
    evidence, known_sources = {}, {}
    for name in ("knowledge_search", "incident_changes"):
        for event in observations[name]:
            items = event["output"].get("evidence")
            if not isinstance(items, list) or len(items) > MAX_EVIDENCE_ITEMS:
                add("evidence_bound", "Evidence returned by a tool is malformed or exceeds the verifier bound.", terminal=True)
                continue
            for item in items:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or len(item["id"]) > 128 or not isinstance(item.get("source"), str) or len(item["source"]) > 1000:
                    add("evidence_shape", "A returned evidence id/source is malformed.", terminal=True)
                    continue
                source = item["source"]
                if name == "knowledge_search":
                    belongs = source.startswith(service + "/") and not any(segment in {".", ".."} for segment in source.split("/"))
                else:
                    belongs = source == "changes/" + service
                if not belongs:
                    add("evidence_service", "A service-filtered tool returned evidence belonging to another service.", terminal=True)
                    continue
                if item["id"] in known_sources and known_sources[item["id"]] != source:
                    add("evidence_identity", "A returned id refers to conflicting sources.", terminal=True)
                known_sources[item["id"]] = source
                evidence[item["id"]] = {"source": source, "tool": name}
    if parsed is not None and isinstance(parsed["citations"], list) and all(isinstance(i, str) for i in parsed["citations"]):
        ids = parsed["citations"]
        if any(i not in evidence for i in ids):
            add("citation_unknown", "Use only evidence ids actually returned by target-service tools.")
        runbook_available = any(e["output"].get("evidence") for e in observations["knowledge_search"])
        if runbook_available and not any(i in evidence and evidence[i]["tool"] == "knowledge_search" for i in ids):
            add("citation_runbook", "Cite at least one actual target-service runbook evidence id.")
        if not any(i in evidence and evidence[i]["tool"] == "incident_changes" for i in ids):
            add("citation_changes", "Cite at least one actual target-service change evidence id; a missing runbook may be reported with changes alone.")
    return result()


def make_diagnostic_validator(service, operator_task="", strict_service_history=True):
    """Adapt to Runtime's optional callback(trace) contract; does not mutate trace."""
    if not isinstance(service, str) or not service or len(service) > 200 or not service.isprintable():
        raise ValueError("operator service must be a bounded printable string")
    if not isinstance(operator_task, str) or len(operator_task) > 16000:
        raise ValueError("operator task must be bounded text")
    def validator(trace):
        if not isinstance(trace, dict):
            raise ValueError("trace must be an object")
        return validate_diagnostic(service, trace.get("answer", ""), trace.get("events", []), operator_task, strict_service_history)
    validator.revision = hashlib.sha256(json.dumps({"contract": "diagnostic-verifier-v1", "service": service,
        "operator_task": operator_task, "strict_service_history": strict_service_history}, sort_keys=True).encode()).hexdigest()
    return validator


def scope_tools(tools, service):
    """Clone diagnostic tools with an operator-fixed service enum before execution.

    Tools remain read-only and preserve their original handlers and validation.
    A wrong-service request raises from Tool.call before the original handler
    accesses data. Its attempted execution must still be recorded as an error;
    scoping does not retroactively make such a run successful.
    """
    from byte_agent.tools import Tool
    if not isinstance(service, str) or not service or len(service) > 200 or not service.isprintable():
        raise ValueError("operator service must be a bounded printable string")
    if not isinstance(tools, dict):
        raise ValueError("tools must be a name-to-Tool mapping")
    scoped = {}
    for name, original in tools.items():
        if name not in TOOLS:
            scoped[name] = original
            continue
        spec = copy.deepcopy(original.spec())
        schema = spec.get("inputSchema", {})
        properties = schema.get("properties")
        required = schema.get("required")
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise ValueError("diagnostic tool has a malformed input schema")
        properties["service"] = {**properties.get("service", {}), "type": "string", "minLength": 1, "maxLength": 200, "enum": [service]}
        if "service" not in required:
            required.append("service")
        def handler(_original=original, **arguments):
            return _original.call(arguments)
        revision = hashlib.sha256(json.dumps({"contract": "operator-service-scope-v1", "original_revision": original.revision,
                                             "service": service, "input_schema": schema}, sort_keys=True).encode()).hexdigest()
        scoped[name] = Tool(name, spec["description"], properties, required, handler, revision=revision)
    return scoped
