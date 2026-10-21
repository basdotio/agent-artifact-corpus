import os
import sys
import time
import traceback
import functools
import grpc
from pathlib import Path
from typing import Generic, TypeVar, Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError
from google.ads.googleads.errors import GoogleAdsException
from google.auth.exceptions import RefreshError

from .telemetry import (
    generate_w3c_trace_id,
    generate_w3c_span_id,
    get_trace_context,
    set_trace_context,
    reset_trace_context,
    redact_secrets,
    trace_resource,
    operator_name,
    start_api_call_capture,
    end_api_call_capture,
    captured_api_calls,
    current_api_calls,
    current_tool,
    SERVICE_CONTEXT,
    REPORTED_ERROR_TYPE,
    HOST,
    SESSION_ID
)
from . import cloud_sink, preflight

T = TypeVar("T")

class Telemetry(BaseModel):
    latency_ms: float = Field(..., description="API round-trip duration in milliseconds")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO-8601 UTC invocation timestamp")
    trace_id: Optional[str] = Field(None, description="W3C Distributed Trace ID")
    span_id: Optional[str] = Field(None, description="W3C Span ID")
    request_id: Optional[str] = Field(None, description="Google Ads request-id of the call (the last one, if the tool made several); give it to Google support")
    sla_status: str = Field("HEALTHY", description="HEALTHY if latency <= 2500ms else DEGRADED")

class ApiError(BaseModel):
    code: str = Field(..., description="Machine-readable error enum code or status")
    message: str = Field(..., description="Human-readable descriptive error message")
    trigger: Optional[str] = Field(None, description="The specific input or value that triggered the error")
    field_path: List[str] = Field(default_factory=list, description="Exact path of the invalid field in the request")
    raw_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional debug details")

class ServiceResult(BaseModel, Generic[T]):
    success: bool = Field(..., description="True if operation succeeded, False otherwise")
    data: Optional[T] = Field(None, description="Typed payload if success is True")
    error: Optional[ApiError] = Field(None, description="Error details if success is False")
    telemetry: Telemetry = Field(..., description="Call performance telemetry")

MAX_LOGGED_ERROR_MESSAGE_CHARS = 300

def _pb(message):
    """Raw protobuf behind a proto-plus message (oneof and optional-field checks need it)."""
    return type(message).pb(message)

def _error_code_name(error) -> str:
    """'query_error.UNEXPECTED_INPUT' instead of the bare enum number ('query_error.11')."""
    which = _pb(error.error_code).WhichOneof("error_code")
    if not which:
        return "GOOGLE_ADS_ERROR"
    value = getattr(error.error_code, which)
    return f"{which}.{getattr(value, 'name', value)}"

def _error_field_path(error) -> List[str]:
    """['operations[0]', 'create', 'headlines[3]', 'text'] — the index tells which operation or list item failed."""
    return [f"{el.field_name}[{el.index}]" if el.HasField("index") else el.field_name
            for el in _pb(error.location).field_path_elements]

def _error_trigger(error) -> Optional[str]:
    which = _pb(error.trigger).WhichOneof("value")
    return str(getattr(_pb(error.trigger), which)) if which else None

def _error_details(error) -> Dict[str, Any]:
    """Only the non-empty parts: policy topics behind a disapproval, quota limits, budget minimums."""
    details = _pb(error.details)
    out: Dict[str, Any] = {}
    if details.HasField("policy_finding_details"):
        topics = [entry.topic for entry in details.policy_finding_details.policy_topic_entries]
        if topics:
            out["policy_topics"] = topics
    if details.HasField("policy_violation_details"):
        violation = details.policy_violation_details
        out["policy_violation"] = violation.external_policy_name or violation.external_policy_description
        out["policy_exemptible"] = violation.is_exemptible
    if details.HasField("quota_error_details"):
        quota = details.quota_error_details
        out["quota"] = {"rate_name": quota.rate_name, "retry_delay_s": quota.retry_delay.seconds}
    if details.HasField("budget_per_day_minimum_error_details"):
        budget = details.budget_per_day_minimum_error_details
        out["budget_minimum_eur"] = round(budget.minimum_budget_amount_micros / 1_000_000, 2)
    return out

def _grpc_status(ex: GoogleAdsException) -> Optional[str]:
    try:
        return ex.error.code().name
    except Exception:
        return None

def parse_google_ads_exception(ex: GoogleAdsException, latency_ms: float) -> ServiceResult[Any]:
    """
    Safely unpacks GoogleAdsException without crashing and converts into standardized ServiceResult.
    Every error of the failure is kept (batched requests can fail on several operations at once);
    the first one becomes the headline ApiError.
    """
    errors = []
    for error in (ex.failure.errors if ex.failure else []):
        item = {
            "code": _error_code_name(error),
            "message": (error.message or "")[:MAX_LOGGED_ERROR_MESSAGE_CHARS],
            "field_path": _error_field_path(error),
            "trigger": _error_trigger(error),
        }
        details = _error_details(error)
        if details:
            item["details"] = details
        errors.append(item)

    first = errors[0] if errors else {"code": "UNKNOWN_GOOGLE_ADS_ERROR", "message": str(ex), "field_path": [], "trigger": None}
    return ServiceResult(
        success=False,
        error=ApiError(
            code=first["code"],
            message=first["message"] or str(ex),
            trigger=first["trigger"],
            field_path=first["field_path"],
            raw_details={
                "request_id": getattr(ex, "request_id", None),
                "grpc_status": _grpc_status(ex),
                "errors": errors,
            }
        ),
        telemetry=Telemetry(latency_ms=round(latency_ms, 2))
    )

import json
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
AUDIT_FILE = LOGS_DIR / "audit.jsonl"

def append_audit_log(entry: Dict[str, Any]) -> None:
    """
    Appends a structured JSON line to the audit trail log with Zero-Trust DLP redaction,
    then sends the same redacted entry to the online journal (Cloud Logging, if configured).
    The local file stays the primary record: a lost cloud copy breaks nothing.
    Never prints to stdout to prevent corrupting MCP stdio JSON-RPC.
    """
    entry.setdefault("operator", operator_name())
    entry.setdefault("host", HOST)
    entry.setdefault("session_id", SESSION_ID)
    sanitized = redact_secrets(entry)
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(sanitized, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[AUDIT LOG ERROR] Failed to write audit log: {e}\n")
    cloud_sink.send(sanitized)

# Tools that read this journal: they log themselves into it, and as INFO they would be most of what an investigator
# sees (8 of the first 12 entries in Logs Explorer were the observer). Their results are DEBUG.
OBSERVER_FUNCTIONS = frozenset({"get_cloud_logs", "get_cloud_trace", "analyze_tool_health", "evaluate_agent_process",
                                "preflight_log_check"})

def severity_for(function: str, action_type: str, success: bool, error_code: Optional[str] = None) -> str:
    """
    Severity of a call that came back as a ServiceResult; the single place that decides it:
      DEBUG     result of an observer tool (noise by default)
      CRITICAL  AUTH_REFRESH_FAILED: every call fails until the token is re-issued
      NOTICE    successful account change: normal, but the event someone will look for
      INFO      successful read
      WARNING   typed failure (shield rejection, missing cloud key ...): the caller was wrong, nothing broke
    Google API errors and unexpected exceptions never get here: they are ERROR at their own call sites.
    """
    if function in OBSERVER_FUNCTIONS:
        return "DEBUG"
    if error_code == "AUTH_REFRESH_FAILED":
        return "CRITICAL"
    if success:
        return "NOTICE" if action_type == "MUTATION" else "INFO"
    return "WARNING"

MUTATION_FUNCTIONS = {
    "update_campaign_status", "update_campaign_budget", "step_campaign_cpc_ceiling",
    "update_ad_group_bid", "deploy_golden_rsa", "link_asset_to_entity",
    "unlink_asset_from_entity", "create_price_asset", "sync_price_extension",
    "apply_negative_shield", "add_negative_keywords",
    "auto_fix_collisions_and_dupes", "update_keyword_status", "remove_negative_keyword",
}

def _loggable(value: Any) -> Any:
    """Turns call arguments (incl. Pydantic request models) into JSON-safe values for the audit trail."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, (list, tuple)):
        return [_loggable(v) for v in value]
    if isinstance(value, dict):
        return {k: _loggable(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

MAX_LOGGED_RESULT_CHARS = 1000

def _loggable_result(value: Any) -> Any:
    """Mutation outcome for the audit trail; long strings are cut so the log stays readable."""
    value = _loggable(value)
    if isinstance(value, str) and len(value) > MAX_LOGGED_RESULT_CHARS:
        return value[:MAX_LOGGED_RESULT_CHARS] + "..."
    return value

def _span_name_and_attributes(tool: Optional[str], function: str):
    """
    The outermost span of a tool call is named and tagged like Google's remote MCP servers do (OpenTelemetry semantic
    conventions for MCP, docs.cloud.google.com/trace/docs/trace-remote-mcp-server-calls): 'tools/call <tool>',
    gen_ai.tool.name, mcp.method.name. The Python function behind the tool stays in the `function` attribute.
    """
    attributes = {"function": function}
    if not tool:
        return function, attributes
    attributes.update({"gen_ai.tool.name": tool, "gen_ai.operation.name": "execute_tool", "mcp.method.name": "tools/call"})
    return f"tools/call {tool}", attributes

def build_request(func_name: str, model_cls: type, action_type: str = "MUTATION", **kwargs):
    """
    Builds a Pydantic request model for an MCP tool (every write tool; read tools only check their IDs).
    Returns (request, None) on success, or (None, rejected_json) when the shield rejects the input;
    the rejection is written to the audit trail so blocked attempts to change the account stay visible.
    """
    try:
        return model_cls(**kwargs), None
    except ValidationError as e:
        message = "; ".join(err["msg"] for err in e.errors())
        field_path = [str(loc) for err in e.errors() for loc in err["loc"]]
        # A span of its own, so the trace link of the rejection in Logs Explorer leads somewhere
        tool = current_tool.get()
        with cloud_sink.tool_span(*_span_name_and_attributes(tool, func_name)) as span:
            trace_id, span_id = cloud_sink.span_ids(span) or (generate_w3c_trace_id(), generate_w3c_span_id())
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "function": func_name,
                **({"tool": tool} if tool else {}),
                "action_type": action_type,
                "args": _loggable({"args": [], "kwargs": kwargs}),
                "component": "google-ads-mcp",
                "logging.googleapis.com/trace": trace_resource(trace_id),
                "logging.googleapis.com/spanId": span_id,
                "logging.googleapis.com/trace_sampled": True,
                "severity": "WARNING",
                "success": False,
                "latency_ms": 0.0,
                "sla_status": "HEALTHY",
                "error_code": "REQUEST_REJECTED",
                "error_message": message,
                "field_path": field_path,
                # analyze_tool_health points at the shield/models_*.py class whose rule the agent did not know
                "request_model": model_cls.__name__
            }
            append_audit_log(entry)
            cloud_sink.finish_span(span, entry)
        rejected = ServiceResult(
            success=False,
            error=ApiError(code="REQUEST_REJECTED", message=message, field_path=field_path),
            telemetry=Telemetry(latency_ms=0.0, trace_id=trace_id, span_id=span_id)
        )
        return None, rejected.model_dump_json(indent=2)

def handle_google_ads_errors(func):
    """
    Decorator for Google Ads API functions:
    Measures latency, enforces W3C Distributed Tracing (Google Cloud Trace compliant),
    catches GoogleAdsException, wraps results in ServiceResult, applies Zero-Trust DLP,
    and writes an append-only JSONL audit trail adhering to Google's Dual Logging standard.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        func_name = func.__name__
        action_type = "MUTATION" if func_name in MUTATION_FUNCTIONS else "READ"
        timestamp = datetime.now(timezone.utc).isoformat()

        # W3C Distributed Trace correlation; with Cloud Trace on, the IDs come from the real span
        current_trace, parent_span, _ = get_trace_context()
        tool = current_tool.get()
        # Only the outermost call of a tool is the MCP tools/call; a nested one keeps its function name
        span_name, span_attributes = _span_name_and_attributes(None if current_trace else tool, func_name)
        with cloud_sink.tool_span(span_name, span_attributes) as span:
            trace_id, span_id = cloud_sink.span_ids(span) or (current_trace or generate_w3c_trace_id(), generate_w3c_span_id())
            trace_tokens = set_trace_context(trace_id=trace_id, span_id=span_id, parent_span_id=parent_span)

            base_log: Dict[str, Any] = {
                "timestamp": timestamp,
                "function": func_name,
                **({"tool": tool} if tool else {}),
                "action_type": action_type,
                "args": _loggable({"args": list(args), "kwargs": kwargs}),
                "component": "google-ads-mcp",
                "logging.googleapis.com/trace": trace_resource(trace_id),
                "logging.googleapis.com/spanId": span_id,
                "logging.googleapis.com/trace_sampled": True
            }
            if parent_span:
                base_log["parent_span_id"] = parent_span

            # A nested call shares the API-call list of the outer one and reads only its own part of it
            nested = current_api_calls.get() is not None
            calls_from = len(captured_api_calls()) if nested else 0
            api_token = None if nested else start_api_call_capture()
            try:
                return _run(func, args, kwargs, start, base_log, trace_id, span_id, calls_from)
            finally:
                if api_token is not None:
                    end_api_call_capture(api_token)
                cloud_sink.finish_span(span, base_log)
                reset_trace_context(trace_tokens)

    return wrapper

# Error Reporting reads the trace from stack_trace/message; keep the head (it marks the trace) and the tail (the frames and
# the exception line), and cut the middle of a very deep trace
MAX_STACK_TRACE_CHARS = 8000

def _stack_trace() -> str:
    text = traceback.format_exc()
    if len(text) <= MAX_STACK_TRACE_CHARS:
        return text
    return text[:200] + "\n...\n" + text[-(MAX_STACK_TRACE_CHARS - 200):]

def _report_location(func) -> Dict[str, Any]:
    """Where the failing tool lives, for an error that has no stack trace (Google API rejection, dead token)."""
    code = getattr(func, "__code__", None)
    if code is None:
        return {"functionName": getattr(func, "__name__", "unknown")}
    try:
        path = Path(code.co_filename).resolve().relative_to(Path(__file__).resolve().parent.parent).as_posix()
    except ValueError:
        path = Path(code.co_filename).name
    return {"filePath": path, "lineNumber": code.co_firstlineno, "functionName": func.__name__}

def _error_reporting_fields(func, stack_trace: bool) -> Dict[str, Any]:
    """
    Fields that make Error Reporting group an ERROR entry of the journal (docs.cloud.google.com/error-reporting/docs/
    formatting-error-messages): serviceContext plus either a stack trace (a bug in our code) or the ReportedErrorEvent
    @type with a reportLocation (an error with no trace of ours). The group key is the entry message, which is
    '<function> <error_code>': one group per tool and error code.
    """
    fields: Dict[str, Any] = {"serviceContext": SERVICE_CONTEXT}
    if stack_trace:
        fields["stack_trace"] = _stack_trace()
    else:
        fields["@type"] = REPORTED_ERROR_TYPE
        fields["context"] = {"reportLocation": _report_location(func)}
    return fields

def _refuse_until_preflight(refusal, start, base_log, trace_id, span_id):
    """The mandatory log check (shield/preflight.py) has not passed in this session: typed refusal, Google is not called."""
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    base_log.update({
        "severity": severity_for(base_log["function"], base_log["action_type"], False, "PREFLIGHT_REQUIRED"),
        "success": False,
        "latency_ms": latency_ms,
        "sla_status": "HEALTHY",
        "error_code": "PREFLIGHT_REQUIRED",
        "error_message": refusal,
    })
    append_audit_log(base_log)
    return ServiceResult(
        success=False,
        error=ApiError(code="PREFLIGHT_REQUIRED", message=refusal),
        telemetry=Telemetry(latency_ms=latency_ms, trace_id=trace_id, span_id=span_id)
    )

def _note_api_calls(base_log: Dict[str, Any], calls: List[Dict[str, Any]], latency_ms: float) -> Optional[str]:
    """
    Writes what the Google Ads API calls of this tool call did: count, time (and the rest of the call outside the API),
    failures, retries, request-ids. Returns the last request-id (the one for Google support).
    """
    if not calls:
        return None
    api_ms = round(sum(c["ms"] for c in calls), 1)
    base_log["google_ads_api"] = {
        "calls": len(calls),
        "ms": api_ms,
        # our code, journal reads, the MCP itself: when a call is slow, this says whether Google was the slow part
        "other_ms": round(max(latency_ms - api_ms, 0.0), 1),
        "failed": sum(1 for c in calls if c["status"] != "OK"),
        "retried": sum(1 for c in calls if c["attempt"] > 1),
        "methods": sorted({c["method"] for c in calls}),
    }
    ids = list(dict.fromkeys(c["request_id"] for c in calls if c.get("request_id")))
    if not ids:
        return None
    base_log["request_id"] = ids[-1]
    if len(ids) > 1:
        base_log["request_ids"] = ids
    return ids[-1]

def _failed_request(calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Google's logging guide: a failed call is logged in detail, with the request itself (GAQL query, operations)."""
    failed = [c for c in calls if c.get("request")]
    return {"failed_request": failed[-1]["request"], "failed_method": failed[-1]["method"]} if failed else {}

def _grpc_failure(e: grpc.RpcError):
    """
    (code, message, severity) of a bare gRPC error. The library leaves INTERNAL and RESOURCE_EXHAUSTED unconverted,
    and a dead refresh token reaches us as a gRPC error from the auth plugin, not as RefreshError.
    """
    try:
        status = e.code().name
    except Exception:
        status = "UNKNOWN"
    try:
        details = e.details() or ""
    except Exception:
        details = ""
    if "invalid_grant" in details or "metadata from plugin" in details:
        return ("AUTH_REFRESH_FAILED",
                f"Google Ads OAuth refresh failed — re-issue GOOGLE_ADS_REFRESH_TOKEN in .env ({details[:200]})", "CRITICAL")
    return f"grpc.{status}", (details or str(e))[:MAX_LOGGED_ERROR_MESSAGE_CHARS], "ERROR"

def _run(func, args, kwargs, start, base_log, trace_id, span_id, calls_from=0):
    refusal = preflight.refusal_for(base_log["function"])
    if refusal:
        return _refuse_until_preflight(refusal, start, base_log, trace_id, span_id)

    def elapsed():
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return latency_ms, "HEALTHY" if latency_ms <= 2500.0 else "DEGRADED"

    try:
        res = func(*args, **kwargs)
        latency_ms, sla_status = elapsed()
        request_id = _note_api_calls(base_log, captured_api_calls()[calls_from:], latency_ms)

        result = res if isinstance(res, ServiceResult) else ServiceResult(
            success=True,
            data=res,
            telemetry=Telemetry(
                latency_ms=latency_ms,
                trace_id=trace_id,
                span_id=span_id,
                request_id=request_id,
                sla_status=sla_status
            )
        )
        if request_id and result.telemetry.request_id is None:
            result.telemetry.request_id = request_id

        error_code = result.error.code if result.error else None
        base_log.update({
            "severity": severity_for(base_log["function"], base_log["action_type"], result.success, error_code),
            "success": result.success,
            "latency_ms": latency_ms,
            "sla_status": sla_status,
            "error_code": error_code
        })
        if base_log["action_type"] == "MUTATION" and result.success:
            base_log["result"] = _loggable_result(result.data)
        # The mandatory log check: a finding (INFO) or the owner's acceptance (NOTICE) must not hide among DEBUG reads
        extra = preflight.journal_fields(base_log["function"], result.data if result.success else None)
        if extra:
            base_log.update(extra)
        append_audit_log(base_log)
        return result

    except GoogleAdsException as ex:
        latency_ms, sla_status = elapsed()
        calls = captured_api_calls()[calls_from:]
        noted_id = _note_api_calls(base_log, calls, latency_ms)
        parsed = parse_google_ads_exception(ex, latency_ms)
        parsed.telemetry.trace_id = trace_id
        parsed.telemetry.span_id = span_id
        parsed.telemetry.sla_status = sla_status

        raw = parsed.error.raw_details or {}
        request_id = raw.get("request_id") or noted_id
        base_log.update({
            "severity": "ERROR",
            "success": False,
            "latency_ms": latency_ms,
            "sla_status": sla_status,
            "error_code": parsed.error.code,
            "error_message": parsed.error.message,
            "field_path": parsed.error.field_path,
            "trigger": parsed.error.trigger,
            "request_id": request_id,
            "grpc_status": raw.get("grpc_status"),
            "errors_count": len(raw.get("errors", [])),
            "errors": raw.get("errors", []),
            **_failed_request(calls),
            **_error_reporting_fields(func, stack_trace=False),
        })
        parsed.telemetry.request_id = request_id
        append_audit_log(base_log)
        return parsed

    except grpc.RpcError as e:
        # Not a bug of ours: Google's side (INTERNAL, quota, unavailable) or the auth plugin
        latency_ms, sla_status = elapsed()
        calls = captured_api_calls()[calls_from:]
        request_id = _note_api_calls(base_log, calls, latency_ms)
        code, message, severity = _grpc_failure(e)
        base_log.update({
            "severity": severity,
            "success": False,
            "latency_ms": latency_ms,
            "sla_status": sla_status,
            "error_code": code,
            "error_message": message,
            "request_id": request_id,
            **_failed_request(calls),
            **_error_reporting_fields(func, stack_trace=False),
        })
        append_audit_log(base_log)
        return ServiceResult(
            success=False,
            error=ApiError(code=code, message=message, raw_details={"request_id": request_id}),
            telemetry=Telemetry(latency_ms=latency_ms, trace_id=trace_id, span_id=span_id, request_id=request_id,
                                sla_status=sla_status)
        )

    except Exception as e:
        latency_ms, sla_status = elapsed()
        _note_api_calls(base_log, captured_api_calls()[calls_from:], latency_ms)
        is_bug = not isinstance(e, RefreshError)
        if isinstance(e, RefreshError):
            # Revoked or expired OAuth refresh token: every call fails until it is re-issued
            code, message = "AUTH_REFRESH_FAILED", "Google Ads OAuth refresh failed — re-issue GOOGLE_ADS_REFRESH_TOKEN in .env"
        else:
            code, message = "UNEXPECTED_SYSTEM_ERROR", str(e)
            cloud_sink.record_exception(e)
        err_res = ServiceResult(
            success=False,
            error=ApiError(
                code=code,
                message=message,
                field_path=[]
            ),
            telemetry=Telemetry(
                latency_ms=latency_ms,
                trace_id=trace_id,
                span_id=span_id,
                sla_status=sla_status
            )
        )
        base_log.update({
            "severity": "CRITICAL" if code == "AUTH_REFRESH_FAILED" else "ERROR",
            "success": False,
            "latency_ms": latency_ms,
            "sla_status": sla_status,
            "error_code": code,
            "error_message": message,
            # a bug in our code gets the stack trace (also in the log of this machine); a dead token has none worth keeping
            **_error_reporting_fields(func, stack_trace=is_bug)
        })
        append_audit_log(base_log)
        return err_res
