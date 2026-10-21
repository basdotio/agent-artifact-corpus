"""
The mandatory log check before any analysis of the ad account (skill google-ads-mcp, step 0).

preflight_log_check runs the three journal checks the owner would otherwise have to remember, over the time since the
last accepted check, and decides whether the ad tools may run (the gate itself lives in shield/preflight.py):

  TOOL_HEALTH      analyze_tool_health: errors and anomalies of the tool
  OUTSIDE_CHANGES  verify_changes_logged: account changes made around the MCP (script, another agent, the interface)
  AGENT_PROCESS    evaluate_agent_process: sessions that broke the working order

OK opens the gate and moves the checkpoint. ATTENTION (or a check that could not run) keeps the gate shut: the agent shows
the findings to the owner and, on their word, calls preflight_log_check(acknowledge=True), which opens it.
The three tools are called through __wrapped__ (the function without its journal decorator), so one check is one journal entry.
"""
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import preflight
from shield.error_shield import handle_google_ads_errors, ServiceResult, ApiError, Telemetry
from shield.telemetry import operator_name
from shield.models_observability import PreflightCheck, PreflightReport
from tools import observability_tools, history_tools, eval_tools

DEFAULT_DAYS = 7
MAX_DAYS = 30
MAX_ITEMS = 10
MAX_ITEM_CHARS = 240
# analyze_tool_health findings the owner has to see; the others (SLOW, UNCLEAR_CONTRACT, MISSING_PREVALIDATION) are hints
HEALTH_ATTENTION = frozenset({"CODE_BUG", "AUTH", "NEW_ERROR_CODE", "ERROR_SPIKE", "MUTATION_CHAIN", "REJECTION_BURST",
                              "UNKNOWN_OPERATOR", "GOOGLE_SIDE"})
STOPPING = ("ATTENTION", "UNAVAILABLE")

def _cut(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= MAX_ITEM_CHARS else text[:MAX_ITEM_CHARS - 3] + "..."

def _check_tool_health(start: datetime, now: datetime, source: str) -> PreflightCheck:
    report = observability_tools.analyze_tool_health.__wrapped__(since=start.isoformat(), source=source)
    if isinstance(report, ServiceResult):
        return PreflightCheck(name="TOOL_HEALTH", status="UNAVAILABLE",
                              summary=f"journal not readable: {report.error.code}: {_cut(report.error.message)}")
    attention = [f for f in report.findings if f.category in HEALTH_ATTENTION]
    hints = [f for f in report.findings if f.category not in HEALTH_ATTENTION]
    note = " (baseline too short for NEW_ERROR_CODE / ERROR_SPIKE)" if report.baseline_note else ""
    if attention:
        kinds = ", ".join(sorted({f.category for f in attention}))
        return PreflightCheck(
            name="TOOL_HEALTH", status="ATTENTION",
            summary=f"{len(attention)} finding(s) in {report.total_calls} calls ({report.source} journal): {kinds}{note}",
            items=[_cut(f"{f.category} {f.function}: {f.evidence}") for f in attention[:MAX_ITEMS]])
    if hints:
        return PreflightCheck(
            name="TOOL_HEALTH", status="INFO",
            summary=f"no errors or anomalies in {report.total_calls} calls ({report.source} journal); {len(hints)} improvement hint(s){note}",
            items=[_cut(f"{f.category} {f.function}: {f.evidence}") for f in hints[:MAX_ITEMS]])
    return PreflightCheck(name="TOOL_HEALTH", status="OK",
                          summary=f"no errors or anomalies in {report.total_calls} calls ({report.source} journal){note}")

def _describe_change(item: dict) -> str:
    what = " ".join(p for p in (item.get("operation"), item.get("resource_type")) if p)
    return _cut(f"{item.get('changed_at', '?')[:19]} (account time) {what}, {item.get('campaign') or 'no campaign'}"
                + (f", {item['keyword']}" if item.get("keyword") else ""))

def _check_outside_changes(start: datetime, now: datetime, source: str) -> PreflightCheck:
    days = min(max(math.ceil((now - start).total_seconds() / 86400) + 1, 1), MAX_DAYS)
    result = history_tools.verify_changes_logged.__wrapped__(days=days, source=source)
    if isinstance(result, ServiceResult):
        return PreflightCheck(name="OUTSIDE_CHANGES", status="UNAVAILABLE",
                              summary=f"journal not readable: {result.error.code}: {_cut(result.error.message)}")
    if result["verdict"] == "NO_AUDIT_LOG":
        return PreflightCheck(name="OUTSIDE_CHANGES", status="UNAVAILABLE",
                              summary="no journal to compare Google's change history with: changes made around the MCP cannot be seen")
    tz = ZoneInfo(result["account_time_zone"])

    def in_window(item: dict) -> bool:
        return history_tools._parse_account_time(item["changed_at"], tz) >= start

    outside = [i for i in result["not_in_log_changes"] if in_window(i)]
    interface = [i for i in result["changes_by_other_clients"] if in_window(i)]
    if outside:
        return PreflightCheck(
            name="OUTSIDE_CHANGES", status="ATTENTION",
            summary=f"{len(outside)} API change(s) in the account that no MCP call made (a script or another agent); the stats of the period may describe a changed account",
            items=[_describe_change(i) for i in outside[:MAX_ITEMS]])
    if interface:
        return PreflightCheck(
            name="OUTSIDE_CHANGES", status="INFO",
            summary=f"{len(interface)} change(s) made in the Google Ads interface, not through the MCP",
            items=[_describe_change(i) for i in interface[:MAX_ITEMS]])
    if result["verdict"] == "NOT_VERIFIABLE_BEFORE_JOURNAL":
        return PreflightCheck(name="OUTSIDE_CHANGES", status="INFO",
                              summary=_cut(result.get("coverage_note") or "the changes of the period predate the journal and could not be checked"))
    return PreflightCheck(name="OUTSIDE_CHANGES", status="OK",
                          summary=f"every API change of the window matches an MCP call ({result['source']} journal)")

def _check_agent_process(start: datetime, now: datetime, source: str) -> PreflightCheck:
    days = min(max(math.ceil((now - start).total_seconds() / 86400), 1), MAX_DAYS)
    report = eval_tools.evaluate_agent_process.__wrapped__(days=days, since=start.isoformat(), source=source)
    if isinstance(report, ServiceResult):
        return PreflightCheck(name="AGENT_PROCESS", status="UNAVAILABLE",
                              summary=f"journal not readable: {report.error.code}: {_cut(report.error.message)}")
    failed = [v for v in report.violations if v.verdict == "FAIL"]
    pending = [v for v in report.violations if v.verdict == "PENDING"]

    def line(v) -> str:
        return _cut(f"{v.rule} ({v.operator}, {v.timestamp[:16]} UTC): {v.detail}")

    if failed:
        return PreflightCheck(name="AGENT_PROCESS", status="ATTENTION",
                              summary=f"{len(failed)} rule(s) of the working order broken in {report.sessions} session(s) that changed the account",
                              items=[line(v) for v in failed[:MAX_ITEMS]])
    if pending:
        return PreflightCheck(name="AGENT_PROCESS", status="INFO",
                              summary=f"{len(pending)} verdict(s) still open (a batch is running or the verification is not due yet)",
                              items=[line(v) for v in pending[:MAX_ITEMS]])
    if report.sessions == 0:
        return PreflightCheck(name="AGENT_PROCESS", status="OK", summary="no session changed the account in the window")
    return PreflightCheck(name="AGENT_PROCESS", status="OK",
                          summary=f"{report.sessions} session(s) that changed the account followed the working order")

def _guarded(name: str, run: Callable[[], object]):
    """A check that cannot run is UNAVAILABLE, not a crash of the whole preflight: it stops the analysis too."""
    try:
        return run()
    except Exception as e:
        return PreflightCheck(name=name, status="UNAVAILABLE", summary=_cut(f"could not be checked: {type(e).__name__}: {e}"))

def _window(now: datetime, days: Optional[int]) -> Tuple[datetime, str]:
    if days is not None:
        return now - timedelta(days=days), f"the last {days} day(s), as asked"
    checkpoint = preflight.read_checkpoint()
    if checkpoint is None:
        return now - timedelta(days=DEFAULT_DAYS), f"no earlier accepted check: the last {DEFAULT_DAYS} days"
    checkpoint = min(checkpoint, now)
    limit = now - timedelta(days=MAX_DAYS)
    if checkpoint < limit:
        return limit, f"the journal keeps {MAX_DAYS} days; the last accepted check was {checkpoint:%Y-%m-%d} UTC"
    return checkpoint, f"since the last accepted check ({checkpoint:%Y-%m-%d %H:%M} UTC)"

def _choose_source(start: datetime) -> Tuple[str, str]:
    """
    One journal for all three checks (05.10.2026: two checks read the online journal from 05.10, the third the local
    one from 01.10, and the agent-process check missed five violations). Returns (source, what it covers).
    """
    note = ""
    try:
        source = observability_tools.journal_source(start, "auto")
    except Exception as e:
        source, note = "local", f"; online journal not readable ({type(e).__name__}), this machine's journal used"
    if source == "cloud":
        return source, "online journal of every operator" + note
    begins = observability_tools.local_journal_start()
    covered = (f", it begins {begins:%Y-%m-%d %H:%M} UTC: calls before that are not checked"
               if begins is not None and begins > start else "")
    if begins is None:
        covered = ", which is empty: nothing could be checked"
    return source, "this machine's journal (the online one does not reach back to the window start)" + covered + note

def _stopping_lines(checks: List[PreflightCheck]) -> List[str]:
    return [_cut(f"{c.name} {c.status}: {c.summary}") for c in checks if c.status in STOPPING]

def _acknowledge(now: datetime):
    pending = preflight.pending_check()
    if pending is None:
        return ServiceResult(
            success=False,
            error=ApiError(code="NOTHING_TO_ACKNOWLEDGE",
                           message="Nothing to acknowledge: no check of this session found anything that is still open. Run preflight_log_check() first."),
            telemetry=Telemetry(latency_ms=0.0))
    verdict, checked_at, findings = pending
    preflight.open_gate()
    preflight.save_checkpoint(checked_at, "ACKNOWLEDGED", operator_name(), accepted=findings)
    return PreflightReport(
        verdict="ACKNOWLEDGED", gate_open=True, gate_enforced=preflight.required(), checked_at=checked_at.isoformat(),
        window="accepted: the next check looks only at what is newer than this moment",
        accepted=findings,
        next_step="The ad tools are open again. Continue the analysis; mention the accepted findings where they affect a conclusion.")

@handle_google_ads_errors
def preflight_log_check(acknowledge: bool = False, days: Optional[int] = None):
    """
    The mandatory log check before any analysis of the ad account. Runs the tool-health, outside-changes and
    agent-process checks over the time since the last accepted check and opens the gate for the ad tools on OK.
    On ATTENTION the gate stays shut until acknowledge=True, which the agent calls only after the owner has seen the findings.
    """
    now = datetime.now(timezone.utc)
    if acknowledge:
        return _acknowledge(now)
    if days is not None and not 1 <= days <= MAX_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_DAYS}; the online journal keeps {MAX_DAYS} days.")

    start, why = _window(now, days)
    source, coverage = _choose_source(start)
    checks: List[PreflightCheck] = [
        _guarded("TOOL_HEALTH", lambda: _check_tool_health(start, now, source)),
        _guarded("OUTSIDE_CHANGES", lambda: _check_outside_changes(start, now, source)),
        _guarded("AGENT_PROCESS", lambda: _check_agent_process(start, now, source)),
    ]

    stopped = any(c.status in STOPPING for c in checks)
    enforced = preflight.required()
    if stopped:
        preflight.close_gate("ATTENTION", now, _stopping_lines(checks))
        next_step = ("Show the owner the findings above (the summary of each check and its items), do not start the analysis, and wait for their "
                     "decision. When they say to continue, call preflight_log_check(acknowledge=True). The journal tools stay open to "
                     "investigate: get_cloud_logs, get_cloud_trace, analyze_tool_health, verify_changes_logged, get_change_history, evaluate_agent_process.")
        if not enforced:
            next_step += " (MCP_PREFLIGHT_REQUIRED=0: the ad tools are not locked, but the findings must still be shown.)"
    else:
        preflight.open_gate()
        preflight.save_checkpoint(now, "OK", operator_name())
        next_step = "Nothing needs the owner. Continue with the analysis; the ad tools are open."
    return PreflightReport(
        verdict="ATTENTION" if stopped else "OK",
        gate_open=preflight.is_open() or not enforced,
        gate_enforced=enforced,
        checked_at=now.isoformat(),
        window=f"{start:%Y-%m-%d %H:%M} .. {now:%Y-%m-%d %H:%M} UTC, {why}; read from {coverage}",
        source=source,
        checks=checks,
        next_step=next_step)
