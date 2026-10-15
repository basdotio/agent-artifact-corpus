"""get_scan_feedback: extract + parse → ScanFeedback (PLAN.md §7.5, §8).

§7.5/§9 amendment 2026-09-28: the review_summary page embeds everything the detailed tabs render (medal,
category badges, every criterion's gold/silver/bronze score and advice, org importance, keyword data) as
JSON in ResumeAssignmentReviewSummaryApp's data-react-props, so one page load replaces walking the tabs.
"""

import html
import re
from urllib.parse import urlparse

from .auth import fetch_page, require_login, site_changed_error, site_errors
from .browser import new_page, react_props, site_operation, snapshot
from .config import Settings
from .schemas import MEDALS, ActionItem, AtsFitCategory, Categories, Category, Criterion, ScanFeedback, ToolError
from .storage import backup_feedback, load_ledger, update_ledger

SUMMARY_APP = "ResumeAssignmentReviewSummaryApp"
SUMMARY_PATH = "/members/resume_assignments/review_summary/{}"
CATEGORIES = ("readability", "credibility", "ats_fit", "format")
# Site score type → (§8 status, label the site shows for it).
STATUS = {"gold": ("perfect", "Good Work!"), "silver": ("warning", "Almost There"), "bronze": ("needs_work", "Needs Work!")}
PRIORITIES = ("high", "medium", "low")


def _text(fragment: str | None) -> str:
    """Site advice HTML → plain text (the advice is simple <p>/<strong>/<ul> markup)."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def _medal(value) -> str | None:
    return value if value in MEDALS else None


def _criterion(crit: dict, score: dict, ai_score: dict) -> Criterion:
    score_type = score.get("score_type")
    status, label = STATUS.get(score_type, ("warning", f"Unknown score type {score_type!r}"))  # never throws (§8)
    targets = score.get("target_score") or [{}]
    gpt = ai_score.get(f"{crit['slug']}_gpt_data")
    # ponytail: suggestion only where the site ships improvement_advice; the other "How to improve" texts
    # (fonts, GPA, keywords) are computed client-side from raw data — port per criterion if the loop needs them.
    suggestion = gpt.get("improvement_advice") if isinstance(gpt, dict) else None
    return Criterion(name=crit["name"], status=status, detail=f"{label} {_text(targets[0].get('advice'))}".strip(),
                     suggestion=suggestion or None)


def parse_feedback(page_html: str, scan_id: str, ledger_entry: dict | None = None) -> ScanFeedback:
    """review_summary HTML → ScanFeedback. Raises ToolError(invalid_input) for an incomplete scan and
    ValueError/KeyError/TypeError/AttributeError when the page shape changed (caller → site_changed)."""
    props = react_props(page_html, SUMMARY_APP)
    if str(props["parsedResume"]["data"]["id"]) != scan_id:
        raise ValueError("page is for a different scan")  # never back up another scan's feedback under this id
    resume = props["parsedResume"]["data"]["attributes"]
    if resume.get("status") != "success":
        raise ToolError("invalid_input", f"Scan {scan_id} is not complete (site status: {resume.get('status')}).",
                        "Poll get_scan_status until state=complete, then retry.")
    ai_score = props.get("resumeAiScore") or {}
    job = props.get("job") or {}
    scores = props["resumeAiCriteriaScores"]
    crit_by_id = {str(i["id"]): i["attributes"] for i in scores["included"]}
    importance = {str(c["resume_ai_criterium_id"]): c.get("importance") for c in props.get("resumeAiCriteria") or []}

    rows = [(str(d["relationships"]["resume_ai_criterium"]["data"]["id"]), d["attributes"]) for d in scores["data"]]
    roots = {cid: crit_by_id[cid]["slug"] for cid, _ in rows if crit_by_id[cid]["parent_id"] is None}
    badges = {roots[cid]: _medal(s.get("score_type")) for cid, s in rows if cid in roots}
    if not any(badges.get(c) for c in CATEGORIES):
        # §8 partial needs readable summary badges; none at all = the summary landmark itself is missing
        raise ValueError("no category badges on the summary")
    # The site's per-category Action Items list = the categories' direct children (depth-2 sub-criteria such
    # as Body/Header Font Size roll up into their parent's score).
    children = sorted(
        ((roots[str(crit_by_id[cid]["parent_id"])], crit_by_id[cid], s, cid)
         for cid, s in rows if str(crit_by_id[cid]["parent_id"]) in roots),
        key=lambda t: t[1].get("index") or 0,
    )
    criteria = {c: [] for c in CATEGORIES}
    action_items = []
    for cat, crit, score, cid in children:
        if cat not in criteria:
            continue
        criterion = _criterion(crit, score, ai_score)
        criteria[cat].append(criterion)
        if criterion.status != "perfect":  # §8: every flagged item is surfaced, whatever the badge says
            note = " (flagged although the category badge is Gold)" if badges.get(cat) == "gold" else ""
            prio = importance.get(cid)
            action_items.append(ActionItem(category=cat, item=f"{criterion.name}{note}: {criterion.detail}",
                                           priority=prio if prio in PRIORITIES else "medium"))

    matched = [k for k in (ai_score.get("resume_keywords") or "").split("#") if k]
    matched_lower = {k.lower() for k in matched}
    job_keywords = (job.get("job_gpt_data") or {}).get("keywords") or []
    guide = next((i["attributes"].get("name") for i in (props.get("userResumeAssignment") or {}).get("included", [])
                  if i.get("type") == "resume_assignment"), None)

    def category(cat: str) -> dict:
        return {"badge": badges.get(cat), "criteria": criteria[cat]}

    return ScanFeedback(
        scan_id=scan_id,
        resume_filename=resume["document_file_name"],
        resume_sha256=(ledger_entry or {}).get("resume_sha256"),
        role_title=job.get("job_role") or resume.get("job_title") or "",
        company=job.get("company_name"),
        scoring_guide=guide or (ledger_entry or {}).get("scoring_guide"),
        scanned_at=resume.get("created_at"),
        medal=_medal(ai_score.get("score_type") or resume.get("highest_score")),
        partial=not children,  # §8: summary badges readable but no criteria → partial, not a failure
        categories=Categories(
            readability=Category(**category("readability")),
            credibility=Category(**category("credibility")),
            ats_fit=AtsFitCategory(**category("ats_fit"), keywords_matched=matched,
                                   keywords_unmatched=[k for k in job_keywords if k.lower() not in matched_lower]),
            format=Category(**category("format")),
        ),
        action_items=action_items,
    )


def check_scan_id(scan_id) -> None:
    if not (isinstance(scan_id, str) and scan_id.isascii() and scan_id.isdigit() and len(scan_id) <= 12):
        raise ToolError("invalid_input", "scan_id must be the numeric id from list_scans.", "Re-run list_scans.")


@site_operation
async def get_scan_feedback(settings: Settings, scan_id: str) -> ScanFeedback:
    """§7.5: read, parse, snapshot and back up the feedback of a completed scan."""
    check_scan_id(scan_id)
    page = await new_page(settings)
    await require_login(page, settings, f"{scan_id}-feedback")
    return await read_feedback(page, settings, scan_id, load_ledger(settings))


async def read_feedback(page, settings: Settings, scan_id: str, ledger: dict) -> ScanFeedback:
    """get_scan_feedback after the login pre-check (shared with delete_scan's backup-first step)."""
    step = f"{scan_id}-feedback"
    content = await fetch_page(page, settings, SUMMARY_PATH.format(scan_id), step)
    # ponytail: unknown ids assumed to leave the review_summary/<id> URL (redirect/404) — unverified live;
    # confirm with a bogus id once and tighten.
    if urlparse(page.url).path.rstrip("/") != SUMMARY_PATH.format(scan_id):
        raise ToolError("not_found", f"Scan {scan_id} not found.", "Re-run list_scans; the id may be a typo or deleted.")
    try:
        feedback = parse_feedback(content, scan_id, ledger.get(scan_id))
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise await site_changed_error(page, settings, step, "Feedback page data", e) from e
    async with site_errors(page, settings):
        await snapshot(page, settings, step)  # §7.5: raw HTML kept locally (0600, purged after 30 days per §14)
    backup_feedback(settings, feedback)
    if scan_id in ledger:  # §14 ledger columns
        update_ledger(settings, scan_id, medal=feedback.medal, ats_badge=feedback.categories.ats_fit.badge,
                      credibility_badge=feedback.categories.credibility.badge)
    return feedback
