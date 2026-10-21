from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class CloudLogEntryRecord(BaseModel):
    timestamp: str = Field(..., description="Call start, ISO-8601 UTC")
    severity: str = Field(..., description="INFO, WARNING (rejected by the Pydantic shield) or ERROR")
    operator: Optional[str] = Field(None, description="Who ran the MCP (MCP_OPERATOR of that clone)")
    host: Optional[str] = Field(None, description="Machine the call came from")
    session_id: Optional[str] = Field(None, description="One MCP server process = one agent session; get_cloud_logs(session_id=...) shows everything it did")
    function: Optional[str] = Field(None, description="Python function behind the tool, e.g. step_campaign_cpc_ceiling")
    tool: Optional[str] = Field(None, description="MCP tool the agent called, e.g. step_bid_threshold (entries from 06.10.2026 on)")
    action_type: Optional[str] = Field(None, description="READ or MUTATION")
    success: Optional[bool] = Field(None, description="Call outcome")
    error_code: Optional[str] = Field(None, description="REQUEST_REJECTED, Google error code by name, AUTH_REFRESH_FAILED, ...")
    error_message: Optional[str] = Field(None, description="Error message, cut to 200 chars")
    field_path: List[str] = Field(default_factory=list, description="Path of the invalid field")
    request_id: Optional[str] = Field(None, description="Google Ads request_id (for Google support)")
    latency_ms: Optional[float] = Field(None, description="Call duration")
    args: Optional[str] = Field(None, description="Call arguments as JSON, cut to 300 chars")
    result: Optional[str] = Field(None, description="Mutation outcome, cut to 300 chars")
    trace_id: Optional[str] = Field(None, description="Cloud Trace ID: get_cloud_trace(trace_id) shows where the time went")
    explorer_url: Optional[str] = Field(None, description="This entry in Logs Explorer")

class CloudLogsSummary(BaseModel):
    project: str = Field(..., description="GCP project of the online journal")
    log_filter: str = Field(..., description="Logging query used; paste into Logs Explorer to see the same entries")
    explorer_url: str = Field(..., description="Logs Explorer with this query")
    period_hours: int = Field(..., description="Look-back window")
    matched: int = Field(..., description="Entries matching the filter (counted up to the scan cap)")
    scan_capped: bool = Field(False, description="True if more entries matched than were scanned; counts are a lower bound")
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_operator: Dict[str, int] = Field(default_factory=dict)
    by_function: Dict[str, int] = Field(default_factory=dict)
    by_error_code: Dict[str, int] = Field(default_factory=dict)
    entries: List[CloudLogEntryRecord] = Field(default_factory=list, description="Newest entries first, up to limit")

class TraceSpanRecord(BaseModel):
    span_id: str = Field(..., description="16-hex span ID")
    parent_span_id: Optional[str] = Field(None, description="Parent span; None for the tool call itself")
    name: str = Field(..., description="Tool function, or the Google Ads gRPC method for API calls")
    start_offset_ms: float = Field(..., description="Start relative to the trace start")
    duration_ms: float = Field(..., description="Span duration")
    labels: Dict[str, str] = Field(default_factory=dict, description="Span attributes: function, success, error_code, latency_ms, request_id, operator")

class TraceRecord(BaseModel):
    trace_id: str = Field(..., description="32-hex trace ID")
    total_ms: float = Field(..., description="Duration of the root span (the whole tool call)")
    google_ads_api_calls: int = Field(..., description="Child spans that are Google Ads API calls")
    google_ads_api_ms: float = Field(..., description="Time spent inside Google Ads API calls")
    journal_reads: int = Field(0, description="Child spans that read the journal (Cloud Logging, Cloud Trace, local file)")
    journal_read_ms: float = Field(0.0, description="Time spent reading the journal")
    own_code_ms: float = Field(..., description="total_ms - google_ads_api_ms - journal_read_ms: our code, auth, serialization")
    spans: List[TraceSpanRecord] = Field(default_factory=list, description="Spans ordered by start time")
    logs_url: str = Field(..., description="Journal entries of this trace in Logs Explorer")

class HealthFinding(BaseModel):
    function: str = Field(..., description="Tool function the finding is about")
    category: str = Field(..., description=(
        "CODE_BUG, AUTH, UNCLEAR_CONTRACT, MISSING_PREVALIDATION, GOOGLE_SIDE, SLOW; anomalies against the window before: "
        "NEW_ERROR_CODE (code never seen in the baseline), ERROR_SPIKE (error rate at least doubled), REJECTION_BURST (agent looping on the shield), "
        "MUTATION_CHAIN (account changes made by one process = a script), UNKNOWN_OPERATOR (change from a clone without MCP_OPERATOR)"))
    evidence: str = Field(..., description="What the journal shows: counts, codes, latency")
    where_to_fix: str = Field(..., description="File and place to change")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="Up to 3 entries: timestamp, operator, error_code, message, field_path, request_id, trace_id")

class FunctionHealth(BaseModel):
    function: str
    source_file: Optional[str] = Field(None, description="tools/*.py that defines it")
    calls: int
    errors: int
    error_rate_pct: float
    rejected: int = Field(0, description="REQUEST_REJECTED by the Pydantic shield")
    p50_ms: Optional[float] = None
    p95_ms: Optional[float] = None
    degraded: int = Field(0, description="Calls over the 2500 ms SLA")
    error_codes: Dict[str, int] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list, description="MCP tool names seen for this function (entries from 06.10.2026 on)")

class ToolHealthReport(BaseModel):
    source: str = Field(..., description="cloud (all operators) or local (this machine's audit.jsonl)")
    period: str = Field(..., description="Analysed window, UTC")
    operators: Dict[str, int] = Field(default_factory=dict, description="Calls per operator")
    total_calls: int
    total_errors: int
    baseline_calls: int = Field(0, description="Calls in the window of equal length right before this one: what NEW_ERROR_CODE and ERROR_SPIKE compare against")
    baseline_note: Optional[str] = Field(None, description="Set when the baseline is too short to compare against")
    functions: List[FunctionHealth] = Field(default_factory=list, description="Worst first: errors, then p95")
    findings: List[HealthFinding] = Field(default_factory=list, description="What to improve in the tool, most severe first")

class ProcessVerdict(BaseModel):
    rule: str = Field(..., description="READ_FIRST, ONE_LEVER, AUTO_FIX_ALONE or VERIFY_AFTER")
    verdict: Literal["PASS", "FAIL", "PENDING"] = Field(..., description="PENDING: the batch is still open or the 24 h verification window has not closed yet")
    session_id: str = Field(..., description="Recorded session_id, or 'inferred-<operator>-<start>' for old entries without one")
    session_source: Literal["recorded", "inferred"] = Field(..., description="inferred = old journal entries; sessions split by a gap of more than 2 h")
    operator: str
    timestamp: str = Field(..., description="First account change of the batch (of the session for READ_FIRST), UTC")
    trace_id: Optional[str] = Field(None, description="Trace of that first change: get_cloud_trace(trace_id)")
    detail: str = Field(..., description="Which tools, which levers, how many minutes were missing")
    eval_key: str = Field(..., description="Stable ID of the verdict: record=True never writes the same one twice")

class RuleCounts(BaseModel):
    rule: str
    passed: int = 0
    failed: int = 0
    pending: int = 0

class RecordResult(BaseModel):
    written: int = Field(..., description="New verdicts written to the log google-ads-mcp-evals")
    skipped_existing: int = Field(0, description="Verdicts already recorded earlier (same eval_key)")
    skipped_pending: int = Field(0, description="PENDING verdicts are not recorded: they can still change")
    error: Optional[str] = Field(None, description="Why the write stopped, if it did")
    logs_url: str = Field(..., description="The recorded verdicts in Logs Explorer")

class ProcessEvalReport(BaseModel):
    source: str = Field(..., description="cloud (all operators) or local (this machine's audit.jsonl)")
    period: str = Field(..., description="Account changes made in this window were evaluated, UTC")
    sessions: int = Field(..., description="Agent sessions with at least one successful account change")
    batches: int = Field(..., description="Groups of changes made within 10 minutes of each other")
    mutations: int = Field(..., description="Successful account changes")
    rules: List[RuleCounts] = Field(default_factory=list)
    violations: List[ProcessVerdict] = Field(default_factory=list, description="FAIL and PENDING, newest first; PASS is only counted")
    violations_truncated: bool = Field(False, description="True if more FAIL/PENDING exist than listed")
    recorded: Optional[RecordResult] = Field(None, description="Present only with record=True")

class PreflightCheck(BaseModel):
    name: Literal["TOOL_HEALTH", "OUTSIDE_CHANGES", "AGENT_PROCESS"] = Field(..., description="TOOL_HEALTH = errors and anomalies of the tool (analyze_tool_health), OUTSIDE_CHANGES = account changes made around the MCP (verify_changes_logged), AGENT_PROCESS = sessions that broke the working order (evaluate_agent_process)")
    status: Literal["OK", "INFO", "ATTENTION", "UNAVAILABLE"] = Field(..., description="ATTENTION and UNAVAILABLE (could not be checked) stop the analysis until the owner has seen them; INFO is for the record")
    summary: str = Field(..., description="One line: what was found, or why it could not be checked")
    items: List[str] = Field(default_factory=list, description="The first findings, one line each (at most 10)")

class PreflightReport(BaseModel):
    verdict: Literal["OK", "ATTENTION", "ACKNOWLEDGED"] = Field(..., description="OK: nothing needs the owner. ATTENTION: show the findings to the owner and wait. ACKNOWLEDGED: the owner has seen them")
    gate_open: bool = Field(..., description="True when the ad tools answer again; False while they refuse with PREFLIGHT_REQUIRED")
    gate_enforced: bool = Field(True, description="False when MCP_PREFLIGHT_REQUIRED=0 switched the refusal off")
    checked_at: str = Field(..., description="When this check started, UTC; the next check looks only at what is newer")
    window: str = Field(..., description="What time span was checked and why")
    source: Optional[str] = Field(None, description="cloud (all operators) or local (this machine) journal")
    checks: List[PreflightCheck] = Field(default_factory=list)
    accepted: List[str] = Field(default_factory=list, description="ACKNOWLEDGED: what the owner saw and let pass, one line per check that had stopped the analysis")
    next_step: str = Field(..., description="What the agent does now")
