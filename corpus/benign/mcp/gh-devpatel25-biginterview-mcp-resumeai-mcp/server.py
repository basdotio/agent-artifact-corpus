"""FastMCP app and the six tool definitions (PLAN.md §7). Phase 4.

Every tool returns exactly the §7.0 envelope: {"ok": true, "data": ...} or {"ok": false, "error": {code, message,
hint}}. §13 errors come from ToolError; anything else becomes internal_error (type name only — no PII) with the
traceback on stderr, which stdio leaves free for logs.
"""

import json
import logging
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware
from fastmcp.tools.tool import ToolResult
from pydantic import BaseModel, ValidationError

from . import auth, feedback, scans
from .browser import close_context, human_delay
from .config import load_settings
from .schemas import ToolError
from .storage import purge_old_snapshots

log = logging.getLogger("resumeai_mcp")

HONESTY = ("Honesty rule: unmatched keywords are verification candidates, not a shopping list. Only add a keyword "
           "to the resume when it is backed by real experience, project, or coursework. Never fabricate skills, "
           "metrics, dates, degrees, or employment. A truthful Silver beats a fabricated Gold.")
PACING = ("Pacing: the server adds random 2-5 s human-like delays between UI actions and runs one tool at a time; "
          "never call tools in parallel.")
ERRORS = ("On ok=false follow error.hint (PLAN.md §13). Never retry auth_expired, site_changed, unknown_state, "
          "internal_error or profile_in_use blindly. Read tools already retry network_error twice themselves, and "
          "start_scan/delete_scan must be reconciled (get_scan_status / list_scans) before any retry; otherwise "
          "retry at most twice.")
READ_EXHAUSTED_HINT = "Stop and report: the server already retried this read twice (PLAN.md §13). Do not retry."
WRITE_NETWORK_HINT = ("Stop; do not retry blindly — the operation may have reached the site. Reconcile first with "
                      "list_scans / get_scan_status (a start_scan retry is deduplicated by the reuse key and recovery).")


READ_RETRIES = 2  # §13 retry policy: at most 2 retries, 2–5 s apart


async def envelope(call, retry_network: bool = False) -> dict:
    """Run one tool call (a zero-arg callable returning a coroutine) and wrap it in the §7.0 envelope.

    retry_network: read-only tools retry network_error up to twice with the human delay (§13). Write tools never
    retry here — a repeated start_scan/delete_scan must stay the agent's explicit decision."""
    attempts = 1 + (READ_RETRIES if retry_network else 0)
    for attempt in range(attempts):
        try:
            data = await call()
            break
        except ToolError as e:
            if e.code == "network_error" and attempt + 1 < attempts:
                await human_delay(settings)
                continue
            hint = e.hint
            if e.code == "network_error":  # the generic "retry 2x" would multiply retries or repeat a write
                hint = READ_EXHAUSTED_HINT if retry_network else WRITE_NETWORK_HINT
            return {"ok": False, "error": {"code": e.code, "message": e.message, "hint": hint}}
        except Exception as e:  # §7.0: no bare exceptions reach the agent
            log.exception("unexpected failure in tool call")
            return {"ok": False, "error": {"code": "internal_error",
                                           "message": f"Unexpected failure ({type(e).__name__}).",
                                           "hint": "Stop and report to the user; see the MCP server log for details."}}
    return {"ok": True, "data": data.model_dump(mode="json") if isinstance(data, BaseModel) else data}


class ArgumentErrorsAsEnvelope(Middleware):
    """FastMCP validates argument types before our code runs; keep those failures inside the envelope too."""

    async def on_call_tool(self, context, call_next):
        try:
            return await call_next(context)
        except ValidationError as e:
            fields = sorted({str(err["loc"][0]) for err in e.errors() if err.get("loc")})  # names only, no values
            body = {"ok": False, "error": {"code": "invalid_input",
                                           "message": f"Invalid argument(s): {', '.join(fields) or 'unknown'}.",
                                           "hint": "Fix the argument types per the tool schema and retry once."}}
            return ToolResult(content=json.dumps(body), structured_content=body)


@asynccontextmanager
async def lifespan(app):
    purge_old_snapshots(settings)  # §14 retention also runs at every server start, not only on the next save
    try:
        yield
    finally:
        await close_context()  # release the persistent profile so scripts/login.py can use it


mcp = FastMCP("resumeai", lifespan=lifespan, middleware=[ArgumentErrorsAsEnvelope()], instructions=(
    "Big Interview ResumeAI scanner for the user's NEU account. Typical flow: auth_status → list_scans → "
    "start_scan → get_scan_status (no more often than every 20 s, max 10 min) → get_scan_feedback. " + PACING))
settings = load_settings()


@mcp.tool(description=(
    "Check the Big Interview login and the remaining daily scan allowance before starting any work. "
    "Returns logged_in (false is data, not an error), scans_remaining (null when not shown — never guessed), "
    "account_email (null when not visible), checked_at. If logged_in=false: stop and ask the user to run "
    "scripts/login.py. " + PACING + " " + ERRORS))
async def auth_status() -> dict:
    return await envelope(lambda: auth.auth_status(settings), retry_network=True)


@mcp.tool(description=(
    "List past scans (newest first) for reuse checks and deletion candidates. limit 1-50 (default 20); pass "
    "next_cursor from the previous response as cursor to continue; next_cursor=null means the last page. "
    "resume_sha256/jd_sha256 are only known for scans created by this server (null otherwise; such scans are never "
    "reused). " + PACING + " " + ERRORS))
async def list_scans(limit: int = 20, cursor: str | None = None) -> dict:
    return await envelope(lambda: scans.list_scans(settings, limit, cursor), retry_network=True)


@mcp.tool(description=(
    "Upload a resume + job description and start a scan (uses 1 of the 5 daily scans). Idempotent: if a completed "
    "scan exists for the same resume file, job description, scoring guide, job title and company, it is returned "
    "with reused=true and no allowance is used. resume_path must be an absolute path to a text-based .pdf/.docx "
    "(max 5 MB). Returns scan_id and state (queued/scanning; complete only when reused or already finished). Then "
    "poll get_scan_status no more often than every 20 s. Only one scan may be in flight; limit_reached means stop for the day. "
    + PACING + " " + ERRORS))
async def start_scan(resume_path: str, job_title: str, company: str, job_description: str,
                     scoring_guide: str = "Graduate - STEM Focus") -> dict:
    return await envelope(lambda: scans.start_scan(settings, resume_path, job_title, company, job_description,
                                                   scoring_guide))


@mcp.tool(description=(
    "Poll a scan's state: queued, scanning, complete, failed (the site explicitly reported failure) or unknown "
    "(unreadable — stop and investigate; it is NOT a failure; hint names the saved snapshot). Poll no more often "
    "than once every 20 s; give up after 10 minutes (treat as scan_timeout and keep the scan_id). Also returns scans_remaining. "
    + PACING + " " + ERRORS))
async def get_scan_status(scan_id: str) -> dict:
    return await envelope(lambda: scans.get_scan_status(settings, scan_id), retry_network=True)


@mcp.tool(description=(
    "Structured feedback for a completed scan: overall medal, the four category badges (readability, credibility, "
    "ats_fit, format), each criterion's status (perfect / needs_work / warning) with the site's advice, action "
    "items (flagged items are listed even under a Gold badge), and ATS keywords matched/unmatched. partial=true "
    "means only the summary badges were readable. A local backup is written. " + HONESTY + " " + PACING + " "
    + ERRORS))
async def get_scan_feedback(scan_id: str) -> dict:
    return await envelope(lambda: feedback.get_scan_feedback(settings, scan_id), retry_network=True)


@mcp.tool(description=(
    "Delete a scan from My Scans (optional history tidying; NOT a way to get more scans — never plan on "
    "allowance_restored). Feedback is always backed up locally first; the deletion is aborted if that fails. "
    "Deleting the latest result of the current loop requires confirm=true. " + PACING + " " + ERRORS))
async def delete_scan(scan_id: str, confirm: bool = False) -> dict:
    return await envelope(lambda: scans.delete_scan(settings, scan_id, confirm))


def main() -> None:
    logging.basicConfig(level=logging.WARNING)  # stderr; never page HTML (§14)
    mcp.run(show_banner=False)  # stdio transport (§4); keep stderr for real logs


if __name__ == "__main__":
    main()
