"""
Reading the online journal of google-ads-mcp: Cloud Logging entries and Cloud Trace spans of every operator,
and turning them into concrete improvements of the tool (analyze_tool_health).
Read-only key of the service account mcp-log-reader (Logs Viewer + Cloud Trace User), owner only:
MCP_CLOUD_LOG_READER_CREDENTIALS. The writer key every operator has cannot read anything.
"""
import os
import re
import sys
import json
import math
import importlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import error_shield
from shield.error_shield import handle_google_ads_errors, ServiceResult, ApiError, Telemetry, OBSERVER_FUNCTIONS
from shield import cloud_sink
from shield.cloud_sink import LOG_NAME, GOOGLE_ADS_GRPC_SERVICE_PREFIX, JOURNAL_SPAN_PREFIXES
from shield.models_observability import (
    CloudLogEntryRecord, CloudLogsSummary, TraceSpanRecord, TraceRecord,
    HealthFinding, FunctionHealth, ToolHealthReport
)

READER_SCOPES = ["https://www.googleapis.com/auth/logging.read", "https://www.googleapis.com/auth/trace.readonly"]
SEVERITIES = ("DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL")
# get_cloud_logs without a severity starts here: DEBUG is the observer's own noise (see error_shield.severity_for)
DEFAULT_MIN_SEVERITY = "INFO"
# _Default bucket keeps logs 30 days
MAX_HOURS = 30 * 24
MAX_LIMIT = 200
# Counts are taken over at most this many entries; the journal is hundreds of calls a day
MAX_SCAN = 5000
MAX_MESSAGE_CHARS = 200
MAX_ARGS_CHARS = 300
TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
# Reading the journal is logged too; these calls are DEBUG in the journal and excluded from tool-health analysis
OBSERVABILITY_FUNCTIONS = OBSERVER_FUNCTIONS

class CloudReaderError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

def cloud_error_result(e: CloudReaderError) -> ServiceResult:
    return ServiceResult(success=False, error=ApiError(code=e.code, message=str(e)), telemetry=Telemetry(latency_ms=0.0))

def reader_configured() -> bool:
    return bool(os.getenv("GOOGLE_CLOUD_PROJECT") and os.getenv("MCP_CLOUD_LOG_READER_CREDENTIALS"))

def _reader():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    key_path = os.getenv("MCP_CLOUD_LOG_READER_CREDENTIALS")
    if not project or not key_path:
        raise CloudReaderError("CLOUD_READER_NOT_CONFIGURED",
            "Online journal reader is not configured: set GOOGLE_CLOUD_PROJECT and MCP_CLOUD_LOG_READER_CREDENTIALS "
            "(key of mcp-log-reader, Logs Viewer + Cloud Trace User) in .env. Local fallback: logs/audit.jsonl.")
    try:
        from google.oauth2 import service_account
        return project, service_account.Credentials.from_service_account_file(key_path, scopes=READER_SCOPES)
    except Exception as e:
        raise CloudReaderError("CLOUD_READER_NOT_CONFIGURED", f"Cannot read MCP_CLOUD_LOG_READER_CREDENTIALS: {e}")

def _permission_error(project: str, role: str, e: Exception) -> CloudReaderError:
    return CloudReaderError("CLOUD_PERMISSION_DENIED", f"mcp-log-reader needs the {role} role in project {project}: {e}")

def _quoted(value: str) -> str:
    """Logging query string literal; quotes and backslashes are dropped, IDs and names never contain them."""
    return '"' + str(value).replace("\\", "").replace('"', "") + '"'

def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def explorer_url(project: str, query: str, duration_hours: int = MAX_HOURS) -> str:
    return (f"https://console.cloud.google.com/logs/query;query={quote(query, safe='')};"
            f"duration=PT{duration_hours}H?project={project}")

def build_filter(project: str, since: datetime, until: Optional[datetime] = None, severity: Optional[str] = None,
                 operator: Optional[str] = None, function: Optional[str] = None, request_id: Optional[str] = None,
                 action_type: Optional[str] = None, session_id: Optional[str] = None, tool: Optional[str] = None) -> str:
    parts = [f'logName="projects/{project}/logs/{LOG_NAME}"', f'timestamp>="{_iso(since)}"']
    if until:
        parts.append(f'timestamp<"{_iso(until)}"')
    if severity:
        parts.append(f"severity>={severity}")
    if operator:
        parts.append(f"labels.operator={_quoted(operator)}")
    if function:
        parts.append(f"labels.function={_quoted(function)}")
    if tool:
        parts.append(f"labels.tool={_quoted(tool)}")
    if action_type:
        parts.append(f"labels.action_type={_quoted(action_type)}")
    if session_id:
        parts.append(f"labels.session_id={_quoted(session_id)}")
    if request_id:
        parts.append(f"jsonPayload.request_id={_quoted(request_id)}")
    return " AND ".join(parts)

def _as_audit_entry(entry) -> Dict[str, Any]:
    """Cloud LogEntry -> the same dict shape as a line of logs/audit.jsonl (trace fields restored)."""
    payload = dict(entry.payload) if isinstance(entry.payload, dict) else {"message": str(entry.payload)}
    labels = entry.labels or {}
    for key in ("operator", "host", "function", "tool", "action_type", "session_id"):
        if payload.get(key) is None and labels.get(key):
            payload[key] = labels[key]
    if entry.trace:
        payload["logging.googleapis.com/trace"] = entry.trace
    if entry.span_id:
        payload["logging.googleapis.com/spanId"] = entry.span_id
    payload["severity"] = payload.get("severity") or (entry.severity or "DEFAULT")
    payload["_insert_id"] = entry.insert_id
    if not payload.get("timestamp") and entry.timestamp:
        payload["timestamp"] = entry.timestamp.isoformat()
    return payload

def read_cloud_entries(log_filter: str, max_entries: int = MAX_SCAN, newest_first: bool = True):
    """Returns (entries as audit dicts, capped). Raises CloudReaderError."""
    project, credentials = _reader()
    import google.cloud.logging
    from google.api_core import exceptions as gexc
    client = google.cloud.logging.Client(project=project, credentials=credentials)
    order = google.cloud.logging.DESCENDING if newest_first else google.cloud.logging.ASCENDING
    entries: List[Dict[str, Any]] = []
    with cloud_sink.child_span("cloud_logging.list_entries", {"journal.filter": log_filter[:500]}) as span:
        try:
            for entry in client.list_entries(resource_names=[f"projects/{project}"], filter_=log_filter,
                                             order_by=order, max_results=max_entries + 1, page_size=1000):
                entries.append(_as_audit_entry(entry))
        except gexc.PermissionDenied as e:
            raise _permission_error(project, "Logs Viewer", e)
        if span is not None:
            span.set_attribute("journal.entries", len(entries))
    capped = len(entries) > max_entries
    return entries[:max_entries], capped

def read_cloud_audit_log(since: datetime, operator: Optional[str] = None, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    All operators' journal entries since `since`, oldest first, as audit dicts (verify_changes_logged source=cloud).
    Read newest first and turned around: if the scan cap is hit, the oldest entries are the ones left out.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    entries, capped = read_cloud_entries(build_filter(project, since, operator=operator, session_id=session_id), newest_first=True)
    if capped:
        sys.stderr.write(f"[CLOUD LOG] more than {MAX_SCAN} journal entries since {since.isoformat()}: the oldest were left out\n")
    return list(reversed(entries))

# The start of the online journal moves only when retention trims it (daily): one read per process every 30 minutes
JOURNAL_START_CACHE_TTL = timedelta(minutes=30)
_journal_start_cache: Dict[str, Any] = {"at": None, "value": None}

def cloud_journal_start() -> Optional[datetime]:
    """Oldest entry still kept in the online journal (retention 30 days)."""
    now = datetime.now(timezone.utc)
    if _journal_start_cache["at"] and now - _journal_start_cache["at"] < JOURNAL_START_CACHE_TTL:
        return _journal_start_cache["value"]
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    since = now - timedelta(hours=MAX_HOURS)
    entries, _ = read_cloud_entries(build_filter(project, since), max_entries=1, newest_first=False)
    value = datetime.fromisoformat(entries[0]["timestamp"]) if entries else None
    _journal_start_cache.update({"at": now, "value": value})
    return value

def local_journal_start() -> Optional[datetime]:
    """First entry of this machine's audit.jsonl."""
    path = error_shield.AUDIT_FILE
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    t = datetime.fromisoformat(json.loads(line)["timestamp"])
                    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
    except OSError:
        return None
    return None

JOURNAL_SOURCES = ("auto", "cloud", "local")

def journal_source(start: datetime, requested: str = "auto") -> str:
    """
    Which journal answers for a window that starts at `start`; the one rule of every reader (analyze_tool_health,
    evaluate_agent_process, verify_changes_logged, preflight_log_check), so they never judge one window from two journals.
    auto: the online journal (every operator) only when it reaches back to `start`, else this machine's audit.jsonl,
    which starts earlier. cloud / local: as asked. Raises CloudReaderError when cloud is asked and not readable.
    """
    if requested not in JOURNAL_SOURCES:
        raise ValueError(f"source must be one of {', '.join(JOURNAL_SOURCES)}.")
    if requested == "local":
        return "local"
    if requested == "cloud":
        _reader()
        return "cloud"
    if not reader_configured():
        return "local"
    started = cloud_journal_start()
    return "cloud" if started is not None and started <= start else "local"

def _cut(value: Any, limit: int) -> Optional[str]:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "..."

def trace_id_of(entry: Dict[str, Any]) -> Optional[str]:
    trace = entry.get("logging.googleapis.com/trace")
    return trace.rsplit("/", 1)[-1] if trace else None

def _record(entry: Dict[str, Any], project: str) -> CloudLogEntryRecord:
    latency = entry.get("latency_ms")
    return CloudLogEntryRecord(
        timestamp=str(entry.get("timestamp")),
        severity=str(entry.get("severity")),
        operator=entry.get("operator"),
        host=entry.get("host"),
        session_id=entry.get("session_id"),
        function=entry.get("function"),
        tool=entry.get("tool"),
        action_type=entry.get("action_type"),
        success=entry.get("success"),
        error_code=entry.get("error_code"),
        error_message=_cut(entry.get("error_message"), MAX_MESSAGE_CHARS),
        field_path=[str(p) for p in (entry.get("field_path") or [])],
        request_id=entry.get("request_id"),
        latency_ms=float(latency) if latency is not None else None,
        args=_cut(entry.get("args"), MAX_ARGS_CHARS),
        result=_cut(entry.get("result"), MAX_ARGS_CHARS),
        trace_id=trace_id_of(entry),
        explorer_url=explorer_url(project, f"insertId={_quoted(entry['_insert_id'])}") if entry.get("_insert_id") else None,
    )

@handle_google_ads_errors
def get_cloud_logs(hours: int = 24, severity: Optional[str] = None, operator: Optional[str] = None,
                   function: Optional[str] = None, request_id: Optional[str] = None, limit: int = 50,
                   session_id: Optional[str] = None, tool: Optional[str] = None):
    """
    Online journal of every operator: counts by severity / operator / function / error code + newest entries.
    severity is a minimum (severity>=X); without it DEBUG, the observer tools' own entries, is left out.
    """
    if not 1 <= hours <= MAX_HOURS:
        raise ValueError(f"hours must be between 1 and {MAX_HOURS}; the journal keeps 30 days.")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}.")
    if severity and severity.upper() not in SEVERITIES:
        raise ValueError(f"severity must be one of {', '.join(SEVERITIES)}.")
    try:
        project, _ = _reader()
        log_filter = build_filter(project, datetime.now(timezone.utc) - timedelta(hours=hours),
                                  severity=severity.upper() if severity else DEFAULT_MIN_SEVERITY,
                                  operator=operator, function=function, request_id=request_id, session_id=session_id,
                                  tool=tool)
        entries, capped = read_cloud_entries(log_filter)
    except CloudReaderError as e:
        return cloud_error_result(e)

    def count(key: str) -> Dict[str, int]:
        return dict(Counter(str(e.get(key) or "-") for e in entries).most_common())

    return CloudLogsSummary(
        project=project,
        log_filter=log_filter,
        explorer_url=explorer_url(project, log_filter, hours),
        period_hours=hours,
        matched=len(entries),
        scan_capped=capped,
        by_severity=count("severity"),
        by_operator=count("operator"),
        by_function=count("function"),
        by_error_code={k: v for k, v in count("error_code").items() if k != "-"},
        entries=[_record(e, project) for e in entries[:limit]],
    )

def _hex_span(value: int) -> str:
    return f"{value:016x}"

@handle_google_ads_errors
def get_cloud_trace(trace_id: str):
    """Spans of one tool call: the call itself and every Google Ads API call inside it, with timings."""
    trace_id = trace_id.strip().rsplit("/", 1)[-1].lower()
    if not TRACE_ID_RE.match(trace_id):
        raise ValueError("trace_id must be 32 hex characters (trace_id from get_cloud_logs or a ServiceResult telemetry).")
    try:
        project, credentials = _reader()
        from google.cloud import trace_v1
        from google.api_core import exceptions as gexc
        client = trace_v1.TraceServiceClient(credentials=credentials)
        try:
            with cloud_sink.child_span("cloud_trace.get_trace"):
                trace = client.get_trace(project_id=project, trace_id=trace_id)
        except gexc.PermissionDenied as e:
            raise _permission_error(project, "Cloud Trace User", e)
        except gexc.NotFound:
            raise CloudReaderError("TRACE_NOT_FOUND",
                f"Trace {trace_id} is not in Cloud Trace yet (spans arrive within ~1 minute) or was never exported "
                "(cloud journal off on that machine).")
    except CloudReaderError as e:
        return cloud_error_result(e)

    raw = sorted(trace.spans, key=lambda s: s.start_time)
    t0 = raw[0].start_time if raw else None
    span_ids = {s.span_id for s in raw}
    spans, api_calls, api_ms, journal_reads, journal_ms = [], 0, 0.0, 0, 0.0
    for s in raw:
        duration = (s.end_time - s.start_time).total_seconds() * 1000
        if s.name.lstrip("/").startswith(GOOGLE_ADS_GRPC_SERVICE_PREFIX):
            api_calls += 1
            api_ms += duration
        elif s.name.startswith(JOURNAL_SPAN_PREFIXES):
            journal_reads += 1
            journal_ms += duration
        spans.append(TraceSpanRecord(
            span_id=_hex_span(s.span_id),
            parent_span_id=_hex_span(s.parent_span_id) if s.parent_span_id in span_ids else None,
            name=s.name,
            start_offset_ms=round((s.start_time - t0).total_seconds() * 1000, 1),
            duration_ms=round(duration, 1),
            labels={k: v for k, v in dict(s.labels).items() if not k.startswith(("g.co/", "/component", "otel.", "telemetry."))},
        ))
    roots = [s for s in spans if s.parent_span_id is None]
    total = max((s.duration_ms for s in roots), default=0.0)
    return TraceRecord(
        trace_id=trace_id,
        total_ms=total,
        google_ads_api_calls=api_calls,
        google_ads_api_ms=round(api_ms, 1),
        journal_reads=journal_reads,
        journal_read_ms=round(journal_ms, 1),
        own_code_ms=round(max(total - api_ms - journal_ms, 0.0), 1),
        spans=spans,
        logs_url=explorer_url(project, f'trace="projects/{project}/traces/{trace_id}"'),
    )

# --- Tool health: what to improve in the MCP, from the journal ---

SLA_MS = 2500.0
# A second call of the same tool by the same operator this soon after a rejection = the agent guessed the contract
RETRY_WINDOW = timedelta(minutes=2)
MIN_LATENCY_SAMPLES = 3
MAX_EXAMPLES = 3
MAX_HEALTH_DAYS = 30
TOOLS_DIR = Path(__file__).resolve().parent
SHIELD_DIR = TOOLS_DIR.parent / "shield"
# Our own codes; everything with a dot is a Google Ads error code by name (query_error.UNEXPECTED_INPUT)
PREFLIGHT_REFUSAL_CODE = "PREFLIGHT_REQUIRED"
OWN_CODES = {"REQUEST_REJECTED", "UNEXPECTED_SYSTEM_ERROR", "AUTH_REFRESH_FAILED", "UNKNOWN_GOOGLE_ADS_ERROR",
             "GOOGLE_ADS_ERROR", "CLOUD_READER_NOT_CONFIGURED", "CLOUD_PERMISSION_DENIED", "TRACE_NOT_FOUND",
             PREFLIGHT_REFUSAL_CODE, "NOTHING_TO_ACKNOWLEDGE"}
# Failures on Google's side: no code change helps, only retry / access
GOOGLE_SIDE_PREFIXES = ("quota_error", "internal_error", "database_error", "authentication_error", "authorization_error",
                        # bare gRPC errors (the library leaves INTERNAL and RESOURCE_EXHAUSTED unconverted)
                        "grpc.INTERNAL", "grpc.RESOURCE_EXHAUSTED", "grpc.UNAVAILABLE", "grpc.DEADLINE_EXCEEDED",
                        "grpc.UNKNOWN", "grpc.ABORTED", "grpc.UNAUTHENTICATED", "grpc.PERMISSION_DENIED")
CATEGORY_ORDER = ["CODE_BUG", "AUTH", "NEW_ERROR_CODE", "ERROR_SPIKE", "MUTATION_CHAIN", "REJECTION_BURST",
                  "UNCLEAR_CONTRACT", "MISSING_PREVALIDATION", "UNKNOWN_OPERATOR", "GOOGLE_SIDE", "SLOW"]

# Anomalies: the analysed window against the window of equal length right before it. Google has no ready detector for
# custom logs (docs: log-based metrics + thresholds); these are the same rules, evaluated on the journal itself.
# Not enough history in the baseline = no "new" / "spike" findings, a note instead (a young journal would flag everything).
MIN_BASELINE_CALLS = 20
SPIKE_MIN_ERRORS = 3
SPIKE_FACTOR = 2.0
SPIKE_MIN_RATE_PCT = 10.0
SPIKE_MIN_BASELINE_FUNCTION_CALLS = 5
REJECTION_BURST_COUNT = 3
REJECTION_BURST_WINDOW = timedelta(minutes=10)
# Calls of this journal that are tests, not tool calls: left out of every statistic
TEST_FUNCTIONS = frozenset({"sample_test", "setup_check", "severity_probe"})
UNKNOWN_OPERATORS = (None, "", "unknown")

def _defining_file(name: str, directory: Path, pattern: str) -> Optional[str]:
    """tools/*.py or shield/models_*.py that defines `name` (function or request model)."""
    for path in sorted(directory.glob(pattern)):
        try:
            module = importlib.import_module(f"{directory.name}.{path.stem}")
        except Exception:
            continue
        if hasattr(module, name):
            return f"{directory.name}/{path.name}"
    return None

def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)], 1)

def _example(entry: Dict[str, Any]) -> Dict[str, Any]:
    example = {
        "timestamp": entry.get("timestamp"),
        "operator": entry.get("operator"),
        "error_code": entry.get("error_code"),
        "message": _cut(entry.get("error_message"), MAX_MESSAGE_CHARS),
        "field_path": entry.get("field_path") or [],
        "request_id": entry.get("request_id"),
        "trace_id": trace_id_of(entry),
        "latency_ms": entry.get("latency_ms"),
        "args": _cut(entry.get("args"), MAX_MESSAGE_CHARS),
    }
    return {k: v for k, v in example.items() if v not in (None, [], "")}

def _parse_since(since: str) -> datetime:
    try:
        value = datetime.fromisoformat(since)
    except ValueError:
        raise ValueError("since must be an ISO date or datetime, e.g. 2026-10-05 or 2026-10-05T14:00:00+00:00.")
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

def _local_entries(start: datetime, operator: Optional[str]) -> List[Dict[str, Any]]:
    path = error_shield.AUDIT_FILE
    if not path.exists():
        return []
    entries = []
    with cloud_sink.child_span("journal.read_local"):
        text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        try:
            entry = json.loads(line)
            t = datetime.fromisoformat(entry["timestamp"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        if t >= start and (operator is None or entry.get("operator") == operator):
            entries.append(entry)
    return entries

def _retried_after_rejection(rejections: List[Dict[str, Any]], calls: List[Dict[str, Any]]) -> int:
    times = sorted((datetime.fromisoformat(c["timestamp"]), c.get("operator")) for c in calls)
    retried = 0
    for r in rejections:
        t = datetime.fromisoformat(r["timestamp"])
        if any(t < ct <= t + RETRY_WINDOW and op == r.get("operator") for ct, op in times):
            retried += 1
    return retried

def _function_findings(function: str, source_file: Optional[str], calls: List[Dict[str, Any]]) -> List[HealthFinding]:
    findings: List[HealthFinding] = []
    where = source_file or "tools/ (function not found, renamed?)"
    failed = [c for c in calls if c.get("success") is False]

    bugs = [c for c in failed if c.get("error_code") == "UNEXPECTED_SYSTEM_ERROR"]
    if bugs:
        messages = Counter(_cut(c.get("error_message"), 120) for c in bugs).most_common(2)
        findings.append(HealthFinding(
            function=function, category="CODE_BUG",
            evidence=f"{len(bugs)}x UNEXPECTED_SYSTEM_ERROR (an exception escaped our code): " + "; ".join(f"{m} ({n}x)" for m, n in messages),
            where_to_fix=f"{where}: {function}() — reproduce with the args of the examples, fix the cause, keep the typed error",
            examples=[_example(c) for c in bugs[:MAX_EXAMPLES]]))

    rejected = [c for c in failed if c.get("error_code") == "REQUEST_REJECTED"]
    if rejected:
        retried = _retried_after_rejection(rejected, calls)
        rules = Counter(_cut(c.get("error_message"), 120) for c in rejected).most_common(2)
        models = {c.get("request_model") for c in rejected if c.get("request_model")}
        model_files = [f"{m} in {_defining_file(m, SHIELD_DIR, 'models_*.py') or 'shield/models_*.py'}" for m in sorted(models)]
        findings.append(HealthFinding(
            function=function, category="UNCLEAR_CONTRACT",
            evidence=(f"{len(rejected)}x REQUEST_REJECTED, {retried} retried within {int(RETRY_WINDOW.total_seconds() // 60)} min "
                      f"(the agent learned the rule by failing): " + "; ".join(f"{m} ({n}x)" for m, n in rules)),
            where_to_fix=("State the rule up front: docstring of the MCP tool in server.py that calls "
                          f"{function}, and the field description / error message of " + (", ".join(model_files) or "its request model in shield/models_*.py")),
            examples=[_example(c) for c in rejected[:MAX_EXAMPLES]]))

    google_errors = defaultdict(list)
    for c in failed:
        code = c.get("error_code") or ""
        if "." in code and code not in OWN_CODES:
            google_errors[code].append(c)
    for code, items in sorted(google_errors.items(), key=lambda kv: -len(kv[1])):
        paths = Counter(".".join(map(str, c.get("field_path") or [])) or "-" for c in items).most_common(2)
        if code.startswith(GOOGLE_SIDE_PREFIXES):
            category, fix = "GOOGLE_SIDE", "No code change: retry later, check quota / account access; keep the request_id for Google support"
        elif items[0].get("action_type") == "MUTATION":
            category, fix = "MISSING_PREVALIDATION", (f"Check this in the Pydantic request model of {function} (shield/models_*.py) "
                                                       "so the call is rejected before it reaches Google")
        else:
            category, fix = "MISSING_PREVALIDATION", f"{where}: the GAQL query / arguments of {function}() — validate the input or fix the query"
        findings.append(HealthFinding(
            function=function, category=category,
            evidence=f"Google rejected {len(items)}x with {code} at " + ", ".join(f"{p} ({n}x)" for p, n in paths),
            where_to_fix=fix,
            examples=[_example(c) for c in items[:MAX_EXAMPLES]]))

    latencies = [float(c["latency_ms"]) for c in calls if c.get("latency_ms") and c.get("error_code") != "REQUEST_REJECTED"]
    p95 = _percentile(latencies, 95)
    degraded = [c for c in calls if c.get("sla_status") == "DEGRADED"]
    if (len(latencies) >= MIN_LATENCY_SAMPLES and p95 and p95 > SLA_MS) or len(degraded) >= 2:
        slowest = sorted(calls, key=lambda c: -float(c.get("latency_ms") or 0))[:MAX_EXAMPLES]
        findings.append(HealthFinding(
            function=function, category="SLOW",
            evidence=f"p95 {p95} ms vs SLA {int(SLA_MS)} ms, {len(degraded)} calls DEGRADED out of {len(calls)}",
            where_to_fix=(f"get_cloud_trace(<trace_id of the slowest example>) shows how many Google Ads API calls it makes; "
                          f"then merge queries / add LIMIT / narrow the date range in {where}"),
            examples=[_example(c) for c in slowest]))
    return findings

def _when(entry: Dict[str, Any]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(entry["timestamp"])
    except (KeyError, TypeError, ValueError):
        return None

def _is_failure_worth_a_rate(entry: Dict[str, Any]) -> bool:
    """Failures that are errors, not a caller's rejected input (those have REJECTION_BURST / UNCLEAR_CONTRACT)."""
    return entry.get("success") is False and entry.get("error_code") != "REQUEST_REJECTED"

def _anomaly_findings(entries: List[Dict[str, Any]], baseline: List[Dict[str, Any]]) -> List[HealthFinding]:
    findings: List[HealthFinding] = []

    # NEW_ERROR_CODE / ERROR_SPIKE: only with a baseline long enough to mean something
    if len(baseline) >= MIN_BASELINE_CALLS:
        seen_before = {(e.get("function"), e.get("error_code")) for e in baseline if _is_failure_worth_a_rate(e)}
        first_seen: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for e in entries:
            key = (e.get("function"), e.get("error_code"))
            if _is_failure_worth_a_rate(e) and key not in seen_before:
                first_seen[key].append(e)
        for (function, code), items in sorted(first_seen.items(), key=lambda kv: -len(kv[1])):
            findings.append(HealthFinding(
                function=function, category="NEW_ERROR_CODE",
                evidence=f"{code} appeared {len(items)}x in this window and never in the {len(baseline)} calls before it; first at {items[0].get('timestamp')}",
                where_to_fix=("Open an example: get_cloud_trace(trace_id) shows the failing Google Ads call, request_id goes to Google support. "
                              "If the input could have been refused earlier, add the check to the request model of the tool (shield/models_*.py)"),
                examples=[_example(c) for c in items[:MAX_EXAMPLES]]))

        for function in sorted({e["function"] for e in entries}):
            now_calls = [e for e in entries if e["function"] == function]
            before_calls = [e for e in baseline if e["function"] == function]
            now_errors = [e for e in now_calls if _is_failure_worth_a_rate(e)]
            if len(now_errors) < SPIKE_MIN_ERRORS or len(before_calls) < SPIKE_MIN_BASELINE_FUNCTION_CALLS:
                continue
            now_rate = 100 * len(now_errors) / len(now_calls)
            before_rate = 100 * sum(1 for e in before_calls if _is_failure_worth_a_rate(e)) / len(before_calls)
            if now_rate >= SPIKE_MIN_RATE_PCT and now_rate >= SPIKE_FACTOR * before_rate:
                findings.append(HealthFinding(
                    function=function, category="ERROR_SPIKE",
                    evidence=f"error rate {now_rate:.0f}% ({len(now_errors)} of {len(now_calls)} calls) against {before_rate:.0f}% in the window before",
                    where_to_fix="Compare with get_change_history / recent code changes of this tool; get_cloud_logs(function=..., severity=\"ERROR\") lists the failures",
                    examples=[_example(c) for c in now_errors[:MAX_EXAMPLES]]))

    # REJECTION_BURST: the same tool refused REJECTION_BURST_COUNT times within minutes = an agent stuck in a loop
    rejected_by_tool: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        if e.get("error_code") == "REQUEST_REJECTED" and _when(e):
            rejected_by_tool[(e["function"], e.get("operator"))].append(e)
    for (function, who), items in rejected_by_tool.items():
        items.sort(key=_when)
        for i in range(len(items) - REJECTION_BURST_COUNT + 1):
            burst = items[i:i + REJECTION_BURST_COUNT]
            if _when(burst[-1]) - _when(burst[0]) <= REJECTION_BURST_WINDOW:
                findings.append(HealthFinding(
                    function=function, category="REJECTION_BURST",
                    evidence=f"{REJECTION_BURST_COUNT}+ refusals by the shield within {int(REJECTION_BURST_WINDOW.total_seconds() // 60)} min "
                             f"(operator {who}) from {burst[0].get('timestamp')}: the agent keeps guessing the input",
                    where_to_fix="Make the rule visible before the call: docstring of the MCP tool in server.py and the type of the argument (Literal / Field description)",
                    examples=[_example(c) for c in burst]))
                break

    # MUTATION_CHAIN: account changes whose calls share one trace ran in one process = a script, not separate MCP calls
    by_trace: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        trace = e.get("logging.googleapis.com/trace")
        if e.get("action_type") == "MUTATION" and trace:
            by_trace[trace].append(e)
    for trace, items in by_trace.items():
        if len(items) >= 2:
            names = Counter(c["function"] for c in items).most_common()
            findings.append(HealthFinding(
                function=names[0][0], category="MUTATION_CHAIN",
                evidence=f"{len(items)} account-changing calls in one process at {items[0].get('timestamp')}: " + ", ".join(f"{n} x{c}" for n, c in names),
                where_to_fix="Not a tool bug: changes made by a script instead of separate MCP calls. Find who ran it (operator/host in the examples); the rule is: only MCP tools change the account",
                examples=[_example(c) for c in items[:MAX_EXAMPLES]]))

    # UNKNOWN_OPERATOR: an account change from a clone whose .env has no MCP_OPERATOR (entries older than the field are skipped)
    stamped = [t for e in entries + baseline if e.get("operator") not in UNKNOWN_OPERATORS for t in [_when(e)] if t]
    if stamped:
        operator_field_since = min(stamped)
        anonymous = [e for e in entries if e.get("action_type") == "MUTATION" and e.get("success")
                     and e.get("operator") in UNKNOWN_OPERATORS and (_when(e) or operator_field_since) >= operator_field_since]
        if anonymous:
            findings.append(HealthFinding(
                function=anonymous[0]["function"], category="UNKNOWN_OPERATOR",
                evidence=f"{len(anonymous)} account changes without a known operator (MCP_OPERATOR missing in that clone's .env), last at {anonymous[-1].get('timestamp')}, host {anonymous[-1].get('host')}",
                where_to_fix="Set MCP_OPERATOR in the .env of that machine so every change has an owner in the journal",
                examples=[_example(c) for c in anonymous[-MAX_EXAMPLES:]]))
    return findings

@handle_google_ads_errors
def analyze_tool_health(days: int = 7, operator: Optional[str] = None, since: Optional[str] = None, source: str = "auto"):
    """
    Tool health from the journal: per function calls, error rate, p50/p95 latency, error codes,
    and findings with what to fix and where, including anomalies against the window before (new error code,
    error spike, refusal burst, changes made by one process, changes without an operator). Online journal of every
    operator when the reader key is set, else this machine's audit.jsonl.
    """
    if not 1 <= days <= MAX_HEALTH_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_HEALTH_DAYS}; the online journal keeps 30 days.")
    now = datetime.now(timezone.utc)
    start = _parse_since(since) if since else now - timedelta(days=days)
    # one read of both windows: the baseline is the window of equal length right before the analysed one
    baseline_start = start - (now - start)

    try:
        source = journal_source(start, source)
        if source == "cloud":
            all_entries = read_cloud_audit_log(baseline_start, operator)
        else:
            all_entries = _local_entries(baseline_start, operator)
    except CloudReaderError as e:
        return cloud_error_result(e)
    # A refusal of the mandatory log check (PREFLIGHT_REQUIRED) is neither a call nor an error of the tool: left out
    all_entries = [e for e in all_entries if e.get("function") and e["function"] not in OBSERVABILITY_FUNCTIONS
                   and e["function"] not in TEST_FUNCTIONS and e.get("error_code") != PREFLIGHT_REFUSAL_CODE and _when(e)]
    baseline = [e for e in all_entries if _when(e) < start]
    entries = [e for e in all_entries if _when(e) >= start]

    by_function: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        by_function[e["function"]].append(e)

    functions: List[FunctionHealth] = []
    findings: List[HealthFinding] = []
    for function, calls in by_function.items():
        source_file = _defining_file(function, TOOLS_DIR, "*_tools.py")
        errors = [c for c in calls if c.get("success") is False]
        latencies = [float(c["latency_ms"]) for c in calls if c.get("latency_ms") and c.get("error_code") != "REQUEST_REJECTED"]
        functions.append(FunctionHealth(
            function=function,
            source_file=source_file,
            calls=len(calls),
            errors=len(errors),
            error_rate_pct=round(100 * len(errors) / len(calls), 1),
            rejected=sum(1 for c in errors if c.get("error_code") == "REQUEST_REJECTED"),
            p50_ms=_percentile(latencies, 50),
            p95_ms=_percentile(latencies, 95),
            degraded=sum(1 for c in calls if c.get("sla_status") == "DEGRADED"),
            error_codes=dict(Counter(c.get("error_code") or "-" for c in errors).most_common()),
            tools=sorted({c["tool"] for c in calls if c.get("tool")}),
        ))
        findings.extend(_function_findings(function, source_file, calls))

    auth = [e for e in entries if e.get("error_code") == "AUTH_REFRESH_FAILED"]
    if auth:
        findings.append(HealthFinding(
            function="*", category="AUTH",
            evidence=f"{len(auth)} calls failed with AUTH_REFRESH_FAILED, last at {auth[-1].get('timestamp')} by {auth[-1].get('operator')}",
            where_to_fix="Not a code fix: re-issue GOOGLE_ADS_REFRESH_TOKEN in that operator's .env",
            examples=[_example(e) for e in auth[-MAX_EXAMPLES:]]))

    findings.extend(_anomaly_findings(entries, baseline))

    functions.sort(key=lambda f: (-f.errors, -(f.p95_ms or 0)))
    findings.sort(key=lambda f: (CATEGORY_ORDER.index(f.category), -len(f.examples)))
    baseline_note = None
    if len(baseline) < MIN_BASELINE_CALLS:
        baseline_note = (f"The window before this one holds {len(baseline)} calls (need {MIN_BASELINE_CALLS}): NEW_ERROR_CODE and ERROR_SPIKE "
                         "are not evaluated yet. The other anomaly checks do not need a baseline.")
    return ToolHealthReport(
        source=source,
        period=f"{start.isoformat(timespec='seconds')} .. {now.isoformat(timespec='seconds')}",
        operators=dict(Counter(str(e.get("operator") or "unknown") for e in entries).most_common()),
        total_calls=len(entries),
        total_errors=sum(f.errors for f in functions),
        baseline_calls=len(baseline),
        baseline_note=baseline_note,
        functions=functions,
        findings=findings,
    )
