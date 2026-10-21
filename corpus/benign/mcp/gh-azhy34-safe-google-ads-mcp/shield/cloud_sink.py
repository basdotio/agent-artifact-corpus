"""
Online copy of the audit trail: every entry goes to Cloud Logging (log "google-ads-mcp") and every tool call
becomes a Cloud Trace span, in the GCP project GOOGLE_CLOUD_PROJECT. Each operator runs the MCP on their own
machine; the owner sees all of them in Logs Explorer / Trace Explorer.

Enabled only when MCP_CLOUD_LOG_CREDENTIALS points to the key of a write-only service account
(Logs Writer + Cloud Trace Agent). Otherwise every function here is a no-op and logs/audit.jsonl works as before.
Never uses ADC (it gets overwritten by other gcloud logins) and never raises into a tool call:
logs and spans are sent by background threads, a failure costs one stderr line.
"""
import os
import sys
import logging
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from .telemetry import HOST, SESSION_ID, operator_name

LOG_NAME = "google-ads-mcp"
# Verdicts of tools/eval_tools.py: a separate log, so the journal of calls stays only calls
EVALS_LOG_NAME = "google-ads-mcp-evals"
# One entries.write call per chunk; far below the API request size limit
EVALS_WRITE_CHUNK = 100
# Only Google Ads calls become child spans; Cloud Logging / Cloud Trace own gRPC calls stay out of the trace
GOOGLE_ADS_GRPC_SERVICE_PREFIX = "google.ads.googleads"
CLOUD_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
TRACE_FIELD_PREFIX = "logging.googleapis.com/"
# Python logging has no NOTICE. Cloud Logging's NOTICE is 300; google-cloud-logging passes an unknown levelno through
# as the numeric severity, so a custom level 300 arrives as NOTICE.
NOTICE_LEVEL = 300
logging.addLevelName(NOTICE_LEVEL, "NOTICE")
LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "NOTICE": NOTICE_LEVEL, "WARNING": logging.WARNING,
          "ERROR": logging.ERROR, "CRITICAL": logging.CRITICAL}

_lock = threading.Lock()
_state: Dict[str, Any] = {"started": False, "logger": None, "tracer": None, "client": None}

def _warn(message: str) -> None:
    # stderr only: stdout carries the MCP JSON-RPC stream
    sys.stderr.write(f"[CLOUD LOG] {message}\n")

def cloud_config() -> Optional[Tuple[str, str]]:
    """(project, key path) when the online journal is configured, else None."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    key_path = os.getenv("MCP_CLOUD_LOG_CREDENTIALS")
    return (project, key_path) if project and key_path else None

def _start_logging(project: str, credentials):
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    from google.cloud.logging_v2.resource import Resource

    client = google.cloud.logging.Client(project=project, credentials=credentials)
    # Created before gRPC instrumentation, so log writes never show up as spans
    client.logging_api
    _state["client"] = client
    # Explicit resource: auto-detection probes the GCE metadata server, which only delays a local machine
    handler = CloudLoggingHandler(client, name=LOG_NAME, resource=Resource(type="global", labels={}))
    logger = logging.getLogger(f"{LOG_NAME}.cloud")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers = [handler]
    return logger

def _is_google_ads_call(details) -> bool:
    """gRPC filter: '/google.ads.googleads.v21.services.GoogleAdsService/Search' -> traced.
    Replaces filters.service_prefix, which splits the method with os.path and never matches on Windows ('\\google...')."""
    method = getattr(details, "full_method", None) or getattr(details, "method", None) or ""
    if isinstance(method, bytes):
        method = method.decode()
    return method.lstrip("/").startswith(GOOGLE_ADS_GRPC_SERVICE_PREFIX)

def _start_tracing(project: str, credentials):
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from google.cloud.trace_v2 import TraceServiceClient

    provider = TracerProvider(resource=Resource.create({"service.name": LOG_NAME}))
    exporter = CloudTraceSpanExporter(project_id=project, client=TraceServiceClient(credentials=credentials))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    try:
        from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient
        GrpcInstrumentorClient(filter_=_is_google_ads_call).instrument()
    except Exception as e:
        _warn(f"Google Ads API child spans disabled: {e}")
    return trace.get_tracer(LOG_NAME)

def start() -> None:
    """
    Creates the log client, tracer and gRPC instrumentation once. server.py calls it at startup, so the first tool call
    does not pay for it in its latency_ms (it measured ~190 ms); send/tool_span call it again as a fallback.
    Not at import time: .env is loaded by core.config after this module is imported.
    """
    if _state["started"]:
        return
    with _lock:
        if _state["started"]:
            return
        _state["started"] = True
        config = cloud_config()
        if not config:
            return
        project, key_path = config
        try:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(key_path, scopes=CLOUD_SCOPES)
        except Exception as e:
            _warn(f"online journal disabled, cannot read MCP_CLOUD_LOG_CREDENTIALS: {e}")
            return
        try:
            _state["logger"] = _start_logging(project, credentials)
        except Exception as e:
            _warn(f"Cloud Logging disabled: {e}")
        try:
            _state["tracer"] = _start_tracing(project, credentials)
        except Exception as e:
            _warn(f"Cloud Trace disabled: {e}")

def send(entry: Dict[str, Any]) -> None:
    """
    Sends one already redacted audit entry. Trace and span go into the LogEntry fields
    (Cloud Logging promotes the logging.googleapis.com/* JSON keys only for stdout agents, not for the API);
    operator/host/function/action_type/session_id become labels, cheap to filter in Logs Explorer.
    """
    start()
    logger = _state["logger"]
    if logger is None:
        return
    try:
        # severity is the LogEntry's own field below; a copy inside jsonPayload only clutters the fields panel
        payload = {k: v for k, v in entry.items() if not k.startswith(TRACE_FIELD_PREFIX) and k != "severity"}
        status = "OK" if entry.get("success") else (entry.get("error_code") or "FAILED")
        logger.log(
            LEVELS.get(entry.get("severity", "INFO"), logging.INFO),
            f"{entry.get('function')} {status}",
            extra={
                "json_fields": payload,
                "trace": entry.get(TRACE_FIELD_PREFIX + "trace"),
                "span_id": entry.get(TRACE_FIELD_PREFIX + "spanId"),
                "trace_sampled": bool(entry.get(TRACE_FIELD_PREFIX + "trace_sampled")),
                "labels": {
                    "operator": str(entry.get("operator") or operator_name()),
                    "host": str(entry.get("host") or HOST),
                    "function": str(entry.get("function")),
                    # MCP tool the agent called; empty for entries written outside a tool call
                    "tool": str(entry.get("tool") or ""),
                    "action_type": str(entry.get("action_type")),
                    "session_id": str(entry.get("session_id") or SESSION_ID),
                },
            },
        )
    except Exception as e:
        _warn(f"entry not sent: {e}")

def writer_ready() -> bool:
    """True when the writer key is configured and the cloud client started."""
    start()
    return _state["client"] is not None

def write_evals(records: List[Dict[str, Any]]) -> Tuple[int, Optional[str]]:
    """
    Writes eval verdicts to the log google-ads-mcp-evals, one API call per chunk. Each record: payload (dict),
    insert_id, timestamp (aware datetime), severity, labels, trace (optional full trace resource name).
    Returns (written, error): the first failed chunk stops the writing and its message is returned, nothing is raised.
    """
    start()
    client = _state["client"]
    if client is None:
        return 0, "cloud writer is not configured (GOOGLE_CLOUD_PROJECT + MCP_CLOUD_LOG_CREDENTIALS)"
    written = 0
    try:
        from google.cloud.logging_v2.resource import Resource
        logger = client.logger(EVALS_LOG_NAME)
        resource = Resource(type="global", labels={})
        for i in range(0, len(records), EVALS_WRITE_CHUNK):
            chunk = records[i:i + EVALS_WRITE_CHUNK]
            batch = logger.batch()
            for r in chunk:
                batch.log_struct(r["payload"], insert_id=r["insert_id"], timestamp=r["timestamp"], severity=r["severity"],
                                 labels=r["labels"], trace=r.get("trace"), resource=resource)
            batch.commit()
            written += len(chunk)
    except Exception as e:
        _warn(f"eval verdicts not written: {e}")
        return written, str(e)[:300]
    return written, None

@contextmanager
def tool_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Cloud Trace span around one tool call; yields None while tracing is off."""
    start()
    tracer = _state["tracer"]
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(name, attributes=attributes or None) as span:
        yield span

# Spans of the journal itself (Cloud Logging and Cloud Trace reads, the local file): their gRPC calls are kept out of the
# automatic instrumentation, so without these a slow journal read looked like slow code of ours in get_cloud_trace
JOURNAL_SPAN_PREFIXES = ("cloud_logging.", "cloud_trace.", "journal.")

@contextmanager
def child_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """A span inside the running tool call (name starts with one of JOURNAL_SPAN_PREFIXES); a no-op while tracing is off."""
    start()
    tracer = _state["tracer"]
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(name, attributes=attributes or None) as span:
        yield span

def span_ids(span) -> Optional[Tuple[str, str]]:
    """(trace_id, span_id) in W3C hex, so the journal entry and the span carry the same IDs."""
    if span is None:
        return None
    context = span.get_span_context()
    if not context.is_valid:
        return None
    return f"{context.trace_id:032x}", f"{context.span_id:016x}"

def record_exception(exc: BaseException) -> None:
    """
    Adds the exception (type, message, stack trace) as an event on the running tool-call span, so Trace Explorer shows
    why the call failed. Only for exceptions that escaped our own code; a no-op while tracing is off.
    """
    if _state["tracer"] is None:
        return
    try:
        from opentelemetry import trace
        trace.get_current_span().record_exception(exc)
    except Exception as e:
        _warn(f"exception not recorded on the span: {e}")

SPAN_ATTRIBUTES = ("function", "tool", "action_type", "success", "latency_ms", "sla_status", "error_code", "request_id", "operator", "session_id")

def finish_span(span, entry: Dict[str, Any]) -> None:
    """Copies the call outcome from the journal entry onto the span; a failed call gets the ERROR status."""
    if span is None:
        return
    try:
        from opentelemetry.trace import Status, StatusCode
        span.set_attributes({key: entry[key] for key in SPAN_ATTRIBUTES if entry.get(key) is not None})
        if entry.get("success") is False:
            # error.type: OpenTelemetry's low-cardinality error attribute, also on Google's MCP spans
            span.set_attribute("error.type", str(entry.get("error_code") or "FAILED"))
            # Only a real failure marks the span as an error: a refusal (shield, mandatory log check) is a WARNING in the
            # journal and would otherwise inflate the error rate in Trace Explorer
            if entry.get("severity") in ("ERROR", "CRITICAL"):
                span.set_status(Status(StatusCode.ERROR, str(entry.get("error_code") or "FAILED")))
    except Exception as e:
        _warn(f"span not annotated: {e}")
