"""
Process evals: does an agent session follow the working order written in the google-ads-mcp skill?
The Pydantic shield judges one call; these rules judge a whole session from the journal, deterministically
(no model involved, the same journal always gives the same verdicts). Advisory only: nothing is blocked,
violations are listed for the owner. Rules mirror the skill's "Порядок работы":

  READ_FIRST      step 2  get_change_history was read before the session's first account change
  ONE_LEVER       step 6  changes made together touch one lever group only (LEVER_GROUPS)
  AUTO_FIX_ALONE  step 6  auto_fix_collisions_and_dupes runs alone, never "along the way"
  VERIFY_AFTER    step 7  verify_changes_logged by the same operator 15 min to 24 h after the changes
"""
import hashlib
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import cloud_sink
from shield.error_shield import handle_google_ads_errors
from shield.telemetry import trace_resource
from shield.models_observability import ProcessVerdict, RuleCounts, RecordResult, ProcessEvalReport
from tools.history_tools import CHANGE_EVENT_LAG_MINUTES
from tools.observability_tools import (
    CloudReaderError, cloud_error_result, journal_source, read_cloud_audit_log, read_cloud_entries,
    _local_entries, _reader, _parse_since, _iso, explorer_url, trace_id_of, MAX_HEALTH_DAYS
)

RULES = ("READ_FIRST", "ONE_LEVER", "AUTO_FIX_ALONE", "VERIFY_AFTER")
SOURCES = ("auto", "cloud", "local")
EVAL_TYPE = "deterministic_guardrail"
READ_FIRST_TOOL = "get_change_history"
VERIFY_TOOL = "verify_changes_logged"
AUTO_FIX_TOOL = "auto_fix_collisions_and_dupes"

# Changes made within this gap of each other are one batch ("one change type per test" is judged per batch)
BATCH_GAP = timedelta(minutes=10)
# Old journal entries carry no session_id: one operator's calls with a gap above this are a new session
SESSION_GAP = timedelta(hours=2)
# change_event lags behind the API, so an earlier verify cannot confirm anything (same constant as verify_changes_logged)
VERIFY_MIN = timedelta(minutes=CHANGE_EVENT_LAG_MINUTES)
VERIFY_MAX = timedelta(hours=24)
MAX_VIOLATIONS = 100

# Lever groups: the owner edits this. One group = one kind of change per test.
LEVER_GROUPS: Dict[str, Tuple[str, ...]] = {
    "bid": ("step_campaign_cpc_ceiling", "update_ad_group_bid"),
    "budget": ("update_campaign_budget",),
    "status": ("update_campaign_status", "update_keyword_status"),
    "negatives": ("apply_negative_shield", "add_negative_keywords", "remove_negative_keyword"),
    "ads": ("deploy_golden_rsa",),
    "assets": ("link_asset_to_entity", "unlink_asset_from_entity"),
}

def _group_of(function: str) -> str:
    for group, functions in LEVER_GROUPS.items():
        if function in functions:
            return group
    # A tool nobody assigned counts as its own lever: mixing it with another one is flagged
    return f"other:{function}"

def _prepare(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Adds _t (aware datetime), _op (operator, 'unknown' for old entries), _sid and _src (session id and where it came from)."""
    prepared = []
    for entry in entries:
        try:
            t = datetime.fromisoformat(entry["timestamp"])
        except (KeyError, TypeError, ValueError):
            continue
        prepared.append({**entry, "_t": t if t.tzinfo else t.replace(tzinfo=timezone.utc),
                         "_op": str(entry.get("operator") or "unknown")})
    prepared.sort(key=lambda e: e["_t"])
    last_seen: Dict[str, Tuple[datetime, str]] = {}
    for entry in prepared:
        if entry.get("session_id"):
            entry["_sid"], entry["_src"] = str(entry["session_id"]), "recorded"
            continue
        previous = last_seen.get(entry["_op"])
        if previous and entry["_t"] - previous[0] <= SESSION_GAP:
            sid = previous[1]
        else:
            sid = f"inferred-{entry['_op']}-{entry['_t']:%Y%m%dT%H%M%SZ}"
        last_seen[entry["_op"]] = (entry["_t"], sid)
        entry["_sid"], entry["_src"] = sid, "inferred"
    return prepared

def _batches(mutations: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    batches: List[List[Dict[str, Any]]] = []
    for mutation in mutations:
        if batches and mutation["_t"] - batches[-1][-1]["_t"] <= BATCH_GAP:
            batches[-1].append(mutation)
        else:
            batches.append([mutation])
    return batches

def _eval_key(rule: str, session_id: str, anchor: Dict[str, Any]) -> str:
    anchor_id = trace_id_of(anchor) or anchor["timestamp"]
    return hashlib.sha1(f"{rule}|{session_id}|{anchor_id}".encode()).hexdigest()[:20]

def _verdict(rule: str, verdict: str, anchor: Dict[str, Any], detail: str) -> ProcessVerdict:
    return ProcessVerdict(
        rule=rule, verdict=verdict, session_id=anchor["_sid"], session_source=anchor["_src"], operator=anchor["_op"],
        timestamp=anchor["_t"].isoformat(), trace_id=trace_id_of(anchor), detail=detail,
        eval_key=_eval_key(rule, anchor["_sid"], anchor))

def _clock(t: datetime) -> str:
    return f"{t:%Y-%m-%d %H:%M:%S}"

def _span(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds} s" if seconds < 120 else f"{seconds // 60} min {seconds % 60} s"

def _names(batch: List[Dict[str, Any]]) -> str:
    counts: Dict[str, int] = defaultdict(int)
    for m in batch:
        counts[m["function"]] += 1
    return ", ".join(f"{f} x{n}" if n > 1 else f for f, n in counts.items())

def _read_first(session: List[Dict[str, Any]], first: Dict[str, Any]) -> ProcessVerdict:
    reads = [e for e in session if e.get("function") == READ_FIRST_TOOL and e.get("success") is not False and e["_t"] < first["_t"]]
    if reads:
        return _verdict("READ_FIRST", "PASS", first, f"{READ_FIRST_TOOL} at {_clock(reads[-1]['_t'])}, before the first change")
    return _verdict("READ_FIRST", "FAIL", first,
                    f"first change {first['function']} at {_clock(first['_t'])} with no {READ_FIRST_TOOL} earlier in the session "
                    "(stats may describe an account that was already changed)")

def _one_lever(batch: List[Dict[str, Any]], now: datetime) -> Optional[ProcessVerdict]:
    plain = [m for m in batch if m["function"] != AUTO_FIX_TOOL]
    if not plain:
        return None
    first = plain[0]
    by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for m in plain:
        by_group[_group_of(m["function"])].append(m)
    if len(by_group) > 1:
        detail = "; ".join(f"{group} ({_names(items)})" for group, items in by_group.items())
        return _verdict("ONE_LEVER", "FAIL", first,
                        f"{len(by_group)} levers changed within {_span((plain[-1]['_t'] - first['_t']).total_seconds())}: {detail}")
    if now - plain[-1]["_t"] < BATCH_GAP:
        return _verdict("ONE_LEVER", "PENDING", first, "batch is still open: more changes may join it")
    group = next(iter(by_group))
    return _verdict("ONE_LEVER", "PASS", first, f"only {group} ({_names(plain)})")

def _auto_fix_alone(batch: List[Dict[str, Any]], now: datetime) -> Optional[ProcessVerdict]:
    fixes = [m for m in batch if m["function"] == AUTO_FIX_TOOL]
    if not fixes:
        return None
    others = [m for m in batch if m["function"] != AUTO_FIX_TOOL]
    if others:
        return _verdict("AUTO_FIX_ALONE", "FAIL", fixes[0],
                        f"{AUTO_FIX_TOOL} ran together with {_names(others)}: it pauses keywords with no dry-run, never 'along the way'")
    if now - batch[-1]["_t"] < BATCH_GAP:
        return _verdict("AUTO_FIX_ALONE", "PENDING", fixes[0], "batch is still open: more changes may join it")
    return _verdict("AUTO_FIX_ALONE", "PASS", fixes[0], f"{AUTO_FIX_TOOL} ran alone")

def _verify_after(batch: List[Dict[str, Any]], verifies: List[Dict[str, Any]], now: datetime) -> ProcessVerdict:
    first, last = batch[0], batch[-1]
    mine = [v for v in verifies if v["_op"] == last["_op"] and v["_t"] > last["_t"] and v.get("success") is not False]
    due_from, due_to = last["_t"] + VERIFY_MIN, last["_t"] + VERIFY_MAX
    good = [v for v in mine if due_from <= v["_t"] <= due_to]
    if good:
        minutes = int((good[0]["_t"] - last["_t"]).total_seconds() // 60)
        return _verdict("VERIFY_AFTER", "PASS", first, f"{VERIFY_TOOL} {minutes} min after the last change")
    early = [v for v in mine if v["_t"] < due_from]
    early_note = (f"; the only check was {_span((early[0]['_t'] - last['_t']).total_seconds())} after the change, "
                  f"too early: change_event lags ~{CHANGE_EVENT_LAG_MINUTES} min") if early else ""
    if now < due_to:
        return _verdict("VERIFY_AFTER", "PENDING", first,
                        f"no {VERIFY_TOOL} yet: due {due_from:%Y-%m-%d %H:%M} to {due_to:%Y-%m-%d %H:%M} UTC{early_note}")
    return _verdict("VERIFY_AFTER", "FAIL", first,
                    f"no {VERIFY_TOOL} between {VERIFY_MIN.seconds // 60} min and 24 h after the changes of {_clock(last['_t'])}{early_note}")

def evaluate_entries(entries: List[Dict[str, Any]], now: datetime, since: Optional[datetime] = None,
                     session_id: Optional[str] = None) -> Tuple[List[ProcessVerdict], Dict[str, int]]:
    """
    Verdicts for the journal entries (already read, any source). Entries before `since` are context only: they
    can make a session known, but only changes from `since` on are judged and counted. Returns the verdicts and
    the counts of sessions, batches and mutations that were judged.
    """
    prepared = _prepare(entries)
    sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in prepared:
        sessions[entry["_sid"]].append(entry)
    verifies = [e for e in prepared if e.get("function") == VERIFY_TOOL]

    verdicts: List[ProcessVerdict] = []
    judged_sessions = set()
    stats = {"sessions": 0, "batches": 0, "mutations": 0}
    for sid, session in sessions.items():
        if session_id and sid != session_id:
            continue
        mutations = [e for e in session if e.get("action_type") == "MUTATION" and e.get("success") is True]
        if not mutations:
            continue
        in_window = [m for m in mutations if since is None or m["_t"] >= since]
        if not in_window:
            continue
        judged_sessions.add(sid)
        stats["mutations"] += len(in_window)
        if since is None or mutations[0]["_t"] >= since:
            verdicts.append(_read_first(session, mutations[0]))
        for batch in _batches(mutations):
            if since is not None and batch[-1]["_t"] < since:
                continue
            stats["batches"] += 1
            for verdict in (_one_lever(batch, now), _auto_fix_alone(batch, now), _verify_after(batch, verifies, now)):
                if verdict:
                    verdicts.append(verdict)
    stats["sessions"] = len(judged_sessions)
    return verdicts, stats

def _record(verdicts: List[ProcessVerdict], project: str, evaluated_at: datetime) -> RecordResult:
    """Writes the final verdicts to the log google-ads-mcp-evals once: an eval_key already there is skipped."""
    final = [v for v in verdicts if v.verdict != "PENDING"]
    pending = len(verdicts) - len(final)
    logs_url = explorer_url(project, f'logName="projects/{project}/logs/{cloud_sink.EVALS_LOG_NAME}"')
    if not cloud_sink.writer_ready():
        raise CloudReaderError("CLOUD_WRITER_NOT_CONFIGURED",
            "record=True needs the writer key too: set MCP_CLOUD_LOG_CREDENTIALS (mcp-log-writer) next to the reader key in .env.")
    if not final:
        return RecordResult(written=0, skipped_pending=pending, logs_url=logs_url)
    oldest = min(datetime.fromisoformat(v.timestamp) for v in final)
    existing_filter = (f'logName="projects/{project}/logs/{cloud_sink.EVALS_LOG_NAME}" AND timestamp>="{_iso(oldest - timedelta(minutes=1))}"')
    existing, _ = read_cloud_entries(existing_filter)
    seen = {e.get("eval_key") for e in existing}
    fresh = [v for v in final if v.eval_key not in seen]
    records = []
    for v in fresh:
        records.append({
            "payload": {**v.model_dump(), "eval_type": EVAL_TYPE, "mutation_timestamp": v.timestamp,
                        "evaluated_at": evaluated_at.isoformat()},
            "insert_id": v.eval_key,
            "timestamp": datetime.fromisoformat(v.timestamp),
            "severity": "WARNING" if v.verdict == "FAIL" else "INFO",
            "labels": {"eval_type": EVAL_TYPE, "rule": v.rule, "verdict": v.verdict, "operator": v.operator, "session_id": v.session_id},
            "trace": trace_resource(v.trace_id) if v.trace_id else None,
        })
    written, error = cloud_sink.write_evals(records)
    return RecordResult(written=written, skipped_existing=len(final) - len(fresh), skipped_pending=pending, error=error, logs_url=logs_url)

@handle_google_ads_errors
def evaluate_agent_process(days: int = 7, since: Optional[str] = None, session_id: Optional[str] = None,
                           operator: Optional[str] = None, source: str = "auto", record: bool = False):
    """
    Judges agent sessions against the skill's working order (READ_FIRST, ONE_LEVER, AUTO_FIX_ALONE, VERIFY_AFTER)
    from the journal. Online journal of every operator when the reader key is set, else this machine's audit.jsonl.
    record=True also writes the final verdicts to the cloud log google-ads-mcp-evals (each verdict once).
    """
    if not 1 <= days <= MAX_HEALTH_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_HEALTH_DAYS}; the online journal keeps 30 days.")
    if source not in SOURCES:
        raise ValueError(f"source must be one of {', '.join(SOURCES)}.")
    now = datetime.now(timezone.utc)
    # A session id names a whole run, whenever it happened: look back the full retention
    if session_id:
        start = now - timedelta(days=MAX_HEALTH_DAYS)
    elif since:
        start = _parse_since(since)
    else:
        start = now - timedelta(days=days)
    # Context before the window: the session of a change may have begun (and read the history) shortly earlier
    load_from = start - SESSION_GAP

    try:
        # the same rule as every other reader of the journal: auto = cloud only when it reaches back to the window start
        use_cloud = journal_source(start, source) == "cloud"
        if use_cloud:
            entries, label = read_cloud_audit_log(load_from, operator, session_id if session_id and not session_id.startswith("inferred-") else None), "cloud"
        else:
            entries, label = _local_entries(load_from, operator), "local"
        verdicts, stats = evaluate_entries(entries, now, since=start, session_id=session_id)
        recorded = _record(verdicts, _reader()[0], now) if record else None
    except CloudReaderError as e:
        return cloud_error_result(e)

    counts = {rule: RuleCounts(rule=rule) for rule in RULES}
    for v in verdicts:
        row = counts[v.rule]
        if v.verdict == "PASS":
            row.passed += 1
        elif v.verdict == "FAIL":
            row.failed += 1
        else:
            row.pending += 1
    problems = sorted((v for v in verdicts if v.verdict != "PASS"), key=lambda v: v.timestamp, reverse=True)
    return ProcessEvalReport(
        source=label,
        period=f"{start.isoformat(timespec='seconds')} .. {now.isoformat(timespec='seconds')}",
        sessions=stats["sessions"],
        batches=stats["batches"],
        mutations=stats["mutations"],
        rules=[counts[rule] for rule in RULES],
        violations=problems[:MAX_VIOLATIONS],
        violations_truncated=len(problems) > MAX_VIOLATIONS,
        recorded=recorded,
    )
