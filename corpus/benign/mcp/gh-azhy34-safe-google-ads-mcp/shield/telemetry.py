import os
import sys
import re
import json
import uuid
import socket
import secrets
import logging
import subprocess
import contextvars
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone

# W3C Context variables for distributed tracing
current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_trace_id", default=None)
current_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_span_id", default=None)
current_parent_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_parent_span_id", default=None)

def generate_w3c_trace_id() -> str:
    """Generates a 32-character hex W3C compliant Trace ID."""
    return secrets.token_hex(16)

def generate_w3c_span_id() -> str:
    """Generates a 16-character hex W3C compliant Span ID."""
    return secrets.token_hex(8)

def set_trace_context(trace_id: Optional[str] = None, span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> list:
    """Sets W3C Trace context for the current async execution. Returns tokens for reset_trace_context."""
    tokens = []
    if trace_id:
        tokens.append((current_trace_id, current_trace_id.set(trace_id)))
    if span_id:
        tokens.append((current_span_id, current_span_id.set(span_id)))
    if parent_span_id:
        tokens.append((current_parent_span_id, current_parent_span_id.set(parent_span_id)))
    return tokens

def reset_trace_context(tokens: list) -> None:
    """Restores the trace context saved by set_trace_context, so separate tool calls don't share a trace."""
    for var, token in reversed(tokens):
        var.reset(token)

def get_trace_context() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Returns current (trace_id, span_id, parent_span_id)."""
    return current_trace_id.get(), current_span_id.get(), current_parent_span_id.get()

HOST = socket.gethostname()
# One MCP server process = one agent session: Claude Code starts its own server per session, parallel sessions get
# separate processes, and /mcp Reconnect starts a new one. trace_id is one tool call; session_id ties a run together.
SESSION_ID = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(2)}"

def gcp_project() -> str:
    """GCP project of the online log and traces (azhyshchev); 'local' while cloud logging is not configured.
    Read on every call: core.config loads .env after this module may already be imported."""
    return os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "local"

def trace_resource(trace_id: str) -> str:
    """Cloud Logging trace field format; Logs Explorer turns it into a link to the trace."""
    return f"projects/{gcp_project()}/traces/{trace_id}"

def operator_name() -> str:
    """Who runs this MCP server (MCP_OPERATOR in .env): every clone logs into the same online journal."""
    return os.getenv("MCP_OPERATOR") or "unknown"

def _service_version() -> str:
    """Short git revision of this clone ('986a27c', '986a27c-dirty' with uncommitted edits); MCP_VERSION overrides it."""
    if os.getenv("MCP_VERSION"):
        return os.environ["MCP_VERSION"]
    try:
        # GIT_OPTIONAL_LOCKS=0: --dirty must not refresh and rewrite .git/index while other sessions run git
        out = subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=7"], cwd=Path(__file__).resolve().parent,
                             capture_output=True, text=True, timeout=3, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"

# Error Reporting (docs: error-reporting/docs/formatting-error-messages) groups an ERROR entry of the journal when it
# carries serviceContext plus a stack trace (or the ReportedErrorEvent @type and a reportLocation)
SERVICE_CONTEXT = {"service": "google-ads-mcp", "version": _service_version()}
REPORTED_ERROR_TYPE = "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent"

# Every Google Ads API call made inside the current tool call: method, time, status, request-id, attempt and, for a failed
# call, the request itself. core/client.py's gRPC interceptor fills it. Google's logging guide asks for the request-id of
# every call (for a successful one it is reachable only from an interceptor) and the full request of a failed one.
# The list is mutable, so a call made on another thread of the same tool call still lands in it.
current_api_calls: contextvars.ContextVar[Optional[list]] = contextvars.ContextVar("current_api_calls", default=None)
# MCP tool the agent called (server.py sets it); the journal's `function` is the Python function behind it
current_tool: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_tool", default=None)

def start_api_call_capture() -> contextvars.Token:
    """Opens an empty list of API calls for one tool call; hand the token to end_api_call_capture."""
    return current_api_calls.set([])

def end_api_call_capture(token: contextvars.Token) -> None:
    current_api_calls.reset(token)

def record_api_call(method: str, ms: float, status: str, request_id: Optional[str] = None, attempt: int = 1,
                    request: Optional[str] = None) -> None:
    """Called by the gRPC interceptor once per attempt; outside a tool call (no open list) it does nothing."""
    calls = current_api_calls.get()
    if calls is None:
        return
    call: Dict[str, Any] = {"method": method, "ms": round(ms, 1), "status": status, "attempt": attempt}
    if request_id:
        call["request_id"] = request_id
    if request:
        call["request"] = request
    calls.append(call)

def captured_api_calls() -> list:
    return list(current_api_calls.get() or [])

# Optional OpenTelemetry integration (if installed)
try:
    from opentelemetry import trace
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

# Zero-Trust DLP Regex Patterns for Google Ads, APIs, and credentials
GADS_BEARER_REGEX = r'(?i)\b(ya29\.[A-Za-z0-9_-]{50,150})\b'
GOOGLE_API_KEY_REGEX = r'\bAIzaSy[A-Za-z0-9_-]{33}\b'
GADS_REFRESH_TOKEN_REGEX = r'(?i)(refresh_token[\'"\s:=]+)([A-Za-z0-9_\-\./]{30,80})'
GADS_CLIENT_SECRET_REGEX = r'(?i)(client_secret[\'"\s:=]+)([A-Za-z0-9_\-]{20,50})'
GADS_DEV_TOKEN_REGEX = r'(?i)(developer_token[\'"\s:=]+)([A-Za-z0-9_\-]{15,40})'
CONNECTION_PWD_REGEX = r'(://[^:]+:)([^@]+)(@)'

def redact_secrets(data: Any) -> Any:
    """
    Zero-Trust DLP Guard:
    Recursively scans strings, dicts, or lists and redacts sensitive credentials.
    """
    if isinstance(data, str):
        text = re.sub(GADS_BEARER_REGEX, '[REDACTED_GADS_BEARER]', data)
        text = re.sub(GOOGLE_API_KEY_REGEX, '[REDACTED_GOOGLE_KEY]', text)
        text = re.sub(GADS_REFRESH_TOKEN_REGEX, r'\1[REDACTED_REFRESH_TOKEN]', text)
        text = re.sub(GADS_CLIENT_SECRET_REGEX, r'\1[REDACTED_CLIENT_SECRET]', text)
        text = re.sub(GADS_DEV_TOKEN_REGEX, r'\1[REDACTED_DEV_TOKEN]', text)
        text = re.sub(CONNECTION_PWD_REGEX, r'\1[REDACTED_PASSWORD]\3', text)
        return text
    elif isinstance(data, dict):
        return {k: redact_secrets(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_secrets(elem) for elem in data]
    return data

class GCPJsonFormatter(logging.Formatter):
    """
    Structured JSON Formatter strictly adhering to Google Cloud Trace & Logging standard.
    Produces official special keys:
      - logging.googleapis.com/trace
      - logging.googleapis.com/spanId
      - logging.googleapis.com/trace_sampled
    """
    RESERVED_ATTRS = {
        'args', 'asctime', 'created', 'filename', 'funcName', 'levelname',
        'levelno', 'lineno', 'module', 'msecs', 'message', 'msg', 'name',
        'pathname', 'process', 'processName', 'relativeCreated', 'stack_info',
        'thread', 'threadName', 'exc_info', 'exc_text'
    }

    def __init__(self, project_id: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id = project_id or gcp_project()

    def format(self, record: logging.LogRecord) -> str:
        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)
        parent_span_id = getattr(record, "parent_span_id", None)
        sampled = getattr(record, "trace_sampled", True)

        # 1. Check OpenTelemetry if available
        if OTEL_AVAILABLE and (not trace_id or not span_id):
            current_span = trace.get_current_span()
            span_context = current_span.get_span_context() if current_span else None
            if span_context and span_context.is_valid:
                trace_id = trace_id or f"{span_context.trace_id:032x}"
                span_id = span_id or f"{span_context.span_id:016x}"
                sampled = span_context.trace_flags.sampled

        # 2. Contextvars fallback
        if not trace_id:
            trace_id = current_trace_id.get()
        if not span_id:
            span_id = current_span_id.get()
        if not parent_span_id:
            parent_span_id = current_parent_span_id.get()

        log_entry: Dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "logger_name": record.name,
            "component": "google-ads-mcp"
        }

        # Format GCP Trace official attributes
        if trace_id:
            if self.project_id:
                log_entry["logging.googleapis.com/trace"] = f"projects/{self.project_id}/traces/{trace_id}"
            else:
                log_entry["logging.googleapis.com/trace"] = str(trace_id)
            if span_id:
                log_entry["logging.googleapis.com/spanId"] = str(span_id)
            if parent_span_id:
                log_entry["parent_span_id"] = str(parent_span_id)
            log_entry["logging.googleapis.com/trace_sampled"] = bool(sampled)

        # Capture custom extra fields with DLP redaction
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and key not in ("trace_id", "span_id", "parent_span_id", "trace_sampled"):
                log_entry[key] = redact_secrets(value)

        if record.exc_info:
            log_entry["exception"] = redact_secrets(self.formatException(record.exc_info))

        return json.dumps(log_entry, ensure_ascii=False)
