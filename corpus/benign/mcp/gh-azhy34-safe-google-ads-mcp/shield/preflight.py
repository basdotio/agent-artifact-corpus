"""
The mandatory log check before any analysis of the ad account (skill google-ads-mcp, step 0).

One MCP server process is one agent session. While the check has not passed in this process, every tool that reads or
changes the ad account answers PREFLIGHT_REQUIRED (error_shield._run asks refusal_for). The tools that read the journal
stay open so the findings can be investigated. tools/preflight_tools.py runs the check and opens the gate.

The checkpoint (last accepted check) lives in logs/preflight_state.json, next to audit.jsonl and outside git: the next
check looks only at what is newer, so findings the owner already accepted are not reported again.
MCP_PREFLIGHT_REQUIRED=0 in .env switches the gate off (tests, unattended runs); the check itself still works.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

STATE_FILE = Path(__file__).resolve().parent.parent / "logs" / "preflight_state.json"

# Tools that read the journal or compare it with Google: open while the gate is closed, so a finding can be investigated.
# keyword_volumes is market data from Keyword Planner: it reads no stats or settings of the account and changes nothing;
# it is the only tool of keyword_server.py (Grok), where there is no preflight_log_check to call.
PREFLIGHT_EXEMPT = frozenset({
    "preflight_log_check", "get_cloud_logs", "get_cloud_trace", "analyze_tool_health",
    "evaluate_agent_process", "verify_changes_logged", "get_change_history",
    "keyword_volumes",
})

REFUSAL = ("Mandatory log check first: call preflight_log_check() before any analysis or change of the ad account "
           "(skill google-ads-mcp, step 0). If it reports ATTENTION, show the findings to the owner and, once they say "
           "to continue, call preflight_log_check(acknowledge=True).")

# Per process = per agent session
_state: Dict[str, Any] = {"open": False, "pending_verdict": None, "pending_checked_at": None, "pending_findings": []}

def required() -> bool:
    """Read on every call: core.config loads .env after this module may already be imported."""
    return os.getenv("MCP_PREFLIGHT_REQUIRED", "1").strip().lower() not in ("0", "false", "no", "off")

def is_open() -> bool:
    return _state["open"]

def open_gate() -> None:
    _state["open"] = True
    _state["pending_verdict"] = None
    _state["pending_checked_at"] = None
    _state["pending_findings"] = []

def close_gate(verdict: str, checked_at: datetime, findings: Optional[List[str]] = None) -> None:
    """A check found something: the gate stays shut and the check is remembered, so it can be acknowledged."""
    _state["open"] = False
    _state["pending_verdict"] = verdict
    _state["pending_checked_at"] = checked_at
    _state["pending_findings"] = list(findings or [])

def pending_check() -> Optional[Tuple[str, datetime, List[str]]]:
    """(verdict, when it started, one line per check that stopped it) of this session's check not acknowledged yet."""
    if _state["pending_verdict"] is None:
        return None
    return _state["pending_verdict"], _state["pending_checked_at"], list(_state["pending_findings"])

def reset_for_tests() -> None:
    _state.update({"open": False, "pending_verdict": None, "pending_checked_at": None, "pending_findings": []})

MAX_JOURNAL_RESULT_CHARS = 1000

def journal_fields(function: str, data: Any) -> Optional[Dict[str, Any]]:
    """
    What the journal entry of a check says beyond DEBUG. An OK check stays a quiet observer read; a check that stopped
    the analysis is INFO with what it found; the owner's acceptance is NOTICE with what was accepted, so both show up
    in the default view (severity>=INFO) and the acceptance is never mistaken for noise.
    """
    if function != "preflight_log_check" or data is None:
        return None
    verdict = getattr(data, "verdict", None)
    if verdict == "ACKNOWLEDGED":
        text = "accepted by the owner: " + " | ".join(getattr(data, "accepted", []) or ["(nothing listed)"])
        return {"severity": "NOTICE", "result": text[:MAX_JOURNAL_RESULT_CHARS]}
    if verdict == "ATTENTION":
        stops = [f"{c.name} {c.status}: {c.summary}" for c in getattr(data, "checks", []) if c.status in ("ATTENTION", "UNAVAILABLE")]
        return {"severity": "INFO", "result": ("analysis stopped: " + " | ".join(stops))[:MAX_JOURNAL_RESULT_CHARS]}
    return None

def refusal_for(function: str) -> Optional[str]:
    """The refusal text when `function` must not run yet, else None."""
    if not required() or is_open() or function in PREFLIGHT_EXEMPT:
        return None
    return REFUSAL

def read_checkpoint() -> Optional[datetime]:
    """When the last accepted check started; None when there is none or the file is unreadable."""
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        at = datetime.fromisoformat(data["checked_at"])
        return at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    except (OSError, ValueError, KeyError, TypeError):
        return None

def save_checkpoint(checked_at: datetime, verdict: str, operator: str, accepted: Optional[List[str]] = None) -> None:
    """`accepted`: what the owner saw and let pass (one line per check that stopped the analysis)."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({"checked_at": checked_at.isoformat(), "verdict": verdict, "operator": operator,
                                          "accepted": list(accepted or [])}, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        # not saved: the next check simply looks further back; never fail the tool over it
        pass
