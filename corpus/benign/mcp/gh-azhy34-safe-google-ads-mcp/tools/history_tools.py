import sys
import enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.client import get_ads_client
from core.config import CUSTOMER_ID
from shield.error_shield import handle_google_ads_errors, AUDIT_FILE
from shield.models_campaign import ChangeEventRecord
from shield import cloud_sink
from tools.observability_tools import CloudReaderError, cloud_error_result, read_cloud_audit_log, cloud_journal_start, journal_source

# change_event only covers the last 30 days and requires a LIMIT (max 10000)
MAX_DAYS = 30
# get_change_history output is read by an agent: 500 rows of 8 fields were ~380 000 characters, more than a chat takes in
DEFAULT_ROWS = 200
MAX_ROWS = 500
MAX_VERIFY_ROWS = 2000
MAX_FIELDS_PER_CHANGE = 6
MAX_VALUE_CHARS = 80
# A change lands in change_event within the logged call's latency; allow a few seconds of clock skew.
# A wider window would wrongly credit unrelated changes made a minute later to an earlier MCP call.
CLOCK_SKEW_SECONDS = 5
# change_event shows API changes only after a delay; unmatched calls younger than this are "pending", not "no change"
CHANGE_EVENT_LAG_MINUTES = 15

def _render(name: str, value) -> str:
    if isinstance(value, enum.Enum):
        return value.name
    if name.endswith("_micros") and isinstance(value, int):
        return f"{value / 1_000_000:.2f} EUR"
    text = " ".join(str(value).split())
    return text if len(text) <= MAX_VALUE_CHARS else text[:MAX_VALUE_CHARS] + "..."

def _field_value(resource, path: str):
    value = resource
    for part in path.split("."):
        value = getattr(value, part)
    return value

def _describe_fields(event, resource_attr: str) -> List[str]:
    paths = list(event.changed_fields.paths)
    new_res = getattr(event.new_resource, resource_attr, None)
    old_res = getattr(event.old_resource, resource_attr, None)
    if event.resource_change_operation.name == "REMOVE":
        # nothing is "new" after a removal (its fields read as empty defaults): show what was removed
        new_res, old_res = old_res, None
    lines = []
    for path in paths[:MAX_FIELDS_PER_CHANGE]:
        name = path.split(".")[-1]
        try:
            new_val = _render(name, _field_value(new_res, path)) if new_res is not None else "?"
        except AttributeError:
            new_val = "?"
        if event.resource_change_operation.name == "UPDATE" and old_res is not None:
            try:
                lines.append(f"{path}: {_render(name, _field_value(old_res, path))} -> {new_val}")
                continue
            except AttributeError:
                pass
        lines.append(f"{path}: {new_val}")
    if len(paths) > MAX_FIELDS_PER_CHANGE:
        lines.append(f"... +{len(paths) - MAX_FIELDS_PER_CHANGE} more fields")
    return lines

def _check_days(days: int) -> None:
    if not 1 <= days <= MAX_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_DAYS}; change_event only keeps the last 30 days.")

def _search_change_events(ga_service, customer_id: str, days: int, campaign_id: Optional[str], limit: int, order: str):
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    end = date.today().isoformat()
    where = f"change_event.change_date_time >= '{start}' AND change_event.change_date_time <= '{end} 23:59:59'"
    if campaign_id:
        where += f" AND campaign.id = {campaign_id}"

    query = f"""
        SELECT
            change_event.change_date_time,
            change_event.client_type,
            change_event.user_email,
            change_event.change_resource_type,
            change_event.change_resource_name,
            change_event.resource_change_operation,
            change_event.changed_fields,
            change_event.new_resource,
            change_event.old_resource,
            campaign.name
        FROM change_event
        WHERE {where}
        ORDER BY change_event.change_date_time {order}
        LIMIT {limit}
    """
    return ga_service.search(customer_id=customer_id, query=query)

def _keyword(event) -> Optional[str]:
    resource_type = event.change_resource_type.name
    if not resource_type.endswith("CRITERION"):
        return None
    criterion = getattr(event.new_resource, resource_type.lower(), None)
    if criterion is None or not criterion.keyword.text:
        # a removed criterion has no new resource: its keyword is in the old one
        criterion = getattr(event.old_resource, resource_type.lower(), None)
    if criterion is None or not criterion.keyword.text:
        return None
    return criterion.keyword.text + (" (negative)" if criterion.negative else "")

@handle_google_ads_errors
def get_change_history(days: int = 7, campaign_id: Optional[str] = None, limit: int = DEFAULT_ROWS, customer_id: str = CUSTOMER_ID) -> Dict[str, Any]:
    """
    Account change history from Google's change_event: every change made through the UI, the API
    (this MCP, scripts, other agents) or automated rules, with the old and new values of changed fields.
    Newest first; `truncated` says that older changes of the period exist beyond `limit`.
    """
    _check_days(days)
    if not 1 <= limit <= MAX_ROWS:
        raise ValueError(f"limit must be between 1 and {MAX_ROWS}.")
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")

    results = []
    # one row more than asked: tells whether the period holds older changes that were cut off
    for row in _search_change_events(ga_service, customer_id, days, campaign_id, limit + 1, "DESC"):
        event = row.change_event
        resource_type = event.change_resource_type.name
        resource_attr = resource_type.lower()
        keyword = _keyword(event)

        results.append(ChangeEventRecord(
            changed_at=event.change_date_time,
            client_type=event.client_type.name,
            user_email=event.user_email or None,
            resource_type=resource_type,
            operation=event.resource_change_operation.name,
            campaign_name=row.campaign.name or None,
            resource_name=event.change_resource_name,
            keyword=keyword,
            changes=_describe_fields(event, resource_attr)
        ))
    truncated = len(results) > limit
    results = results[:limit]
    return {
        "returned": len(results),
        "limit": limit,
        "truncated": truncated,
        "oldest_returned_at": results[-1].changed_at if results else None,
        "events": results,
    }

def _parse_account_time(value: str, tz: ZoneInfo) -> datetime:
    fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in value else "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(value, fmt).replace(tzinfo=tz).astimezone(timezone.utc)

def _with_time(entries) -> List[Dict[str, Any]]:
    out = []
    for entry in entries:
        try:
            entry["_t"] = datetime.fromisoformat(entry["timestamp"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append(entry)
    return out

def _read_audit_log() -> List[Dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []
    entries = []
    with cloud_sink.child_span("journal.read_local"):
        text = AUDIT_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return _with_time(entries)

SOURCES = ("local", "cloud", "auto")

@handle_google_ads_errors
def verify_changes_logged(days: int = 2, source: str = "local", customer_id: str = CUSTOMER_ID) -> Dict[str, Any]:
    """
    Reconciles Google's change_event with the MCP audit trail: every API change in the account
    should match a logged MUTATION call. Reports changes made outside this MCP, logged calls that left
    no trace in the account, and calls chained in one process (parent_span_id = a script, not MCP).
    source="local" reads this machine's logs/audit.jsonl; source="cloud" reads the online journal of every operator,
    so another operator's MCP changes no longer look like changes outside the MCP; source="auto" takes the online
    journal when it reaches back over the whole period, else this machine's file.
    Changes older than the journal cannot be checked: they are counted in before_log_started, and when that is all
    there is the verdict is NOT_VERIFIABLE_BEFORE_JOURNAL, never ALL_API_CHANGES_LOGGED.
    """
    _check_days(days)
    if source not in SOURCES:
        raise ValueError(f"source must be one of {', '.join(SOURCES)}.")
    requested_source = source
    try:
        # the same rule as every other reader of the journal (observability_tools.journal_source)
        source = journal_source(datetime.now(timezone.utc) - timedelta(days=days), source)
    except CloudReaderError as e:
        return cloud_error_result(e)
    if source == "cloud":
        # The online journal is read before Google: a missing reader key costs no Ads API call
        try:
            # one extra day covers the account time zone offset of the window start
            audit = _with_time(read_cloud_audit_log(datetime.now(timezone.utc) - timedelta(days=days + 1)))
            log_start = cloud_journal_start()
        except CloudReaderError as e:
            return cloud_error_result(e)
    else:
        audit = _read_audit_log()
        log_start = min((e["_t"] for e in audit), default=None)

    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")

    tz_name = list(ga_service.search(customer_id=customer_id, query="SELECT customer.time_zone FROM customer LIMIT 1"))[0].customer.time_zone
    tz = ZoneInfo(tz_name)
    mutations = [e for e in audit if e.get("action_type") == "MUTATION" and e.get("success")]
    # MCP requests never share a trace; a shared trace_id means several calls ran in one process (a script)
    trace_counts: Dict[str, int] = {}
    for e in audit:
        trace = e.get("logging.googleapis.com/trace")
        if trace:
            trace_counts[trace] = trace_counts.get(trace, 0) + 1

    matched_counts: Dict[int, int] = {}
    not_in_log, before_log, other_clients = [], [], []
    api_changes = 0
    for row in _search_change_events(ga_service, customer_id, days, None, MAX_VERIFY_ROWS, "ASC"):
        event = row.change_event
        changed_utc = _parse_account_time(event.change_date_time, tz)
        item = {
            "changed_at": event.change_date_time,
            "client_type": event.client_type.name,
            "resource_type": event.change_resource_type.name,
            "operation": event.resource_change_operation.name,
            "campaign": row.campaign.name or None,
            "keyword": _keyword(event),
        }
        if event.client_type.name != "GOOGLE_ADS_API":
            other_clients.append(item)
            continue
        api_changes += 1
        if log_start is None or changed_utc < log_start:
            before_log.append(item)
            continue

        # The change must fall inside the call [start, start + latency]; outside it only within clock skew.
        best = None
        for i, entry in enumerate(mutations):
            start = entry["_t"]
            end = start + timedelta(milliseconds=entry.get("latency_ms", 0))
            outside = max((start - changed_utc).total_seconds(), (changed_utc - end).total_seconds(), 0.0)
            if outside > CLOCK_SKEW_SECONDS:
                continue
            score = (outside, abs((end - changed_utc).total_seconds()))
            if best is None or score < best[1]:
                best = (i, score)
        if best is None:
            not_in_log.append(item)
        else:
            matched_counts[best[0]] = matched_counts.get(best[0], 0) + 1

    window_start = datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
    lag_cutoff = datetime.now(timezone.utc) - timedelta(minutes=CHANGE_EVENT_LAG_MINUTES)
    matched_calls, logged_without_change, pending_in_change_history = [], [], []
    for i, entry in enumerate(mutations):
        if entry["_t"] < window_start:
            continue
        call = {
            "logged_at_utc": entry["timestamp"],
            "operator": entry.get("operator"),
            "function": entry.get("function"),
            "args": entry.get("args"),
            "script_suspected": bool(entry.get("parent_span_id"))
                                or trace_counts.get(entry.get("logging.googleapis.com/trace"), 0) > 1,
        }
        if i in matched_counts:
            matched_calls.append({**call, "account_changes": matched_counts[i]})
        elif entry["_t"] > lag_cutoff:
            pending_in_change_history.append(call)
        else:
            logged_without_change.append(call)

    matched = sum(matched_counts.values())
    if log_start is None:
        verdict = "NO_AUDIT_LOG"
    elif not_in_log:
        verdict = "CHANGES_OUTSIDE_MCP_LOG"
    elif api_changes and matched == 0 and before_log:
        # every API change of the period predates the journal: nothing was actually compared
        verdict = "NOT_VERIFIABLE_BEFORE_JOURNAL"
    else:
        verdict = "ALL_API_CHANGES_LOGGED"
    coverage_note = None
    if before_log:
        coverage_note = (f"{len(before_log)} of {api_changes} API changes predate the journal ({source}) and could not be checked; "
                         + ("try source=\"local\" or \"auto\", this machine's file may reach further back." if source == "cloud"
                            else "no older journal exists."))
    return {
        "source": source,
        **({"source_requested": requested_source} if requested_source != source else {}),
        "account_time_zone": tz_name,
        "period_days": days,
        "audit_log_starts_utc": log_start.isoformat() if log_start else None,
        "verdict": verdict,
        "coverage_note": coverage_note,
        "api_changes": api_changes,
        "matched_to_log": matched,
        "not_in_log": len(not_in_log),
        "before_log_started": len(before_log),
        "matched_calls": matched_calls,
        "not_in_log_changes": not_in_log,
        "logged_calls_without_account_change": logged_without_change,
        # change_event lags behind the API by a few minutes; re-run later to match these
        "pending_in_change_history": pending_in_change_history,
        "changes_by_other_clients": other_clients,
    }
