"""list_scans, start_scan, get_scan_status, delete_scan (PLAN.md §7.2-7.6, §10). Phases 1/3."""

import asyncio
import hashlib
import re
import uuid
import zipfile
import zlib
from xml.etree import ElementTree
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .auth import SCAN_PATH, auth_expired_error, fetch_page, on_portal, read_scans_remaining, require_login, \
    site_changed_error, site_errors
from .browser import human_delay, new_page, react_props, site_operation, snapshot
from .config import Settings
from .feedback import SUMMARY_APP, SUMMARY_PATH, check_scan_id, read_feedback
from .schemas import MEDALS, DeleteResult, ScanList, ScanState, ScanStatus, ScanSummary, StartScanResult, ToolError
from .storage import append_ledger, feedback_backup, ledger_key, load_ledger, update_ledger

SCANS_PATH = "/members/resume_assignments/scans"
# My Scans is a React app; its rows are embedded as JSON in this element's data-react-props
# (§9 amendment 2026-09-28: medal and ISO timestamps are only reliably available there).
SCANS_APP = "UserResumeAssignmentScansApp"
PAGE_SIZE = 10  # site's fixed page size; ?page=N selects the page server-side


def parse_my_scans(html: str) -> tuple[list[dict], dict]:
    """(rows, paginationData) from My Scans HTML. Raises ValueError/KeyError/TypeError if the shape changed."""
    props = react_props(html, SCANS_APP)
    rows, pagination = props["parsedResumes"]["data"], props["paginationData"]
    if not isinstance(rows, list) or not isinstance(pagination["count"], int):
        raise TypeError("unexpected My Scans props shape")
    return rows, pagination


def to_summary(row: dict, ledger: dict[str, dict]) -> ScanSummary:
    """Site row → ScanSummary. Hashes (and company/guide the row lacks) come only from the ledger (§7.2)."""
    a, scan_id = row["attributes"], str(row["id"])
    if not isinstance(a, dict):
        raise TypeError("row attributes is not an object")
    entry = ledger.get(scan_id, {})
    medal = a.get("highest_score")
    return ScanSummary(
        scan_id=scan_id,
        role_title=a.get("job_title") or "",
        company=entry.get("company"),
        scoring_guide=a.get("scoring_guide") or entry.get("scoring_guide"),
        scanned_at=a.get("created_at"),
        medal=medal if medal in MEDALS else None,
        resume_filename=a["document_file_name"],
        resume_sha256=entry.get("resume_sha256"),
        jd_sha256=entry.get("jd_sha256"),
    )


@site_operation
async def list_scans(settings: Settings, limit: int = 20, cursor: str | None = None) -> ScanList:
    """§7.2 / §10.3. cursor is the absolute row offset as a string (opaque to the agent)."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ToolError("invalid_input", "limit must be an integer 1-50.", "Retry with 1 <= limit <= 50.")
    if cursor is not None and not (
        isinstance(cursor, str) and cursor.isascii() and cursor.isdigit() and len(cursor) <= 9
    ):
        raise ToolError("invalid_input", "Malformed cursor.", "Pass next_cursor exactly as returned, or null.")
    offset = int(cursor or 0)
    page = await new_page(settings)
    await require_login(page, settings, "list-scans")  # §6.2: auth gate before any other work
    ledger = load_ledger(settings)

    scans: list[ScanSummary] = []
    total = None
    while len(scans) < limit and (total is None or offset + len(scans) < total):
        n = offset + len(scans)
        page_num = n // PAGE_SIZE + 1
        step = f"list-scans-p{page_num}"
        content = await fetch_page(page, settings, f"{SCANS_PATH}?page={page_num}", step)
        try:
            site_rows, pagination = parse_my_scans(content)
            if site_rows and pagination.get("from") != (page_num - 1) * PAGE_SIZE + 1:
                raise ValueError("page size changed")
            chunk = site_rows[n - (page_num - 1) * PAGE_SIZE:][: limit - len(scans)]
            chunk = [to_summary(r, ledger) for r in chunk]  # pydantic ValidationError is a ValueError
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise await site_changed_error(page, settings, step, "My Scans data", e) from e
        total = pagination["count"]
        if not chunk:
            break
        scans += chunk

    end = offset + len(scans)
    return ScanList(
        scans=scans,
        next_cursor=str(end) if total is not None and end < total else None,
    )


# --- Phase 3: reuse key, input validation, status mapping (pure) ------------------------------------------------

MAX_RESUME_BYTES = 5 * 1024 * 1024  # §2 #9
CAPTURE_WINDOW_S = 60  # §9: poll My Scans up to 60 s for the new row
RECOVERY_WINDOW = timedelta(minutes=10)  # §10.2
# Server-vs-local clock allowance for created_at comparisons. Safe only because rows that existed before the
# click are excluded by id (known_ids), so an older same-file/same-title row can never be captured.
CLOCK_SKEW = timedelta(seconds=60)
DAILY_OP_BUDGET = 12  # §12: scan operations (starts + deletes) per local calendar day
IN_FLIGHT_WINDOW = timedelta(minutes=15)  # §12: one scan in flight; older unfinished entries are stale
# My Scans row `status` → §7.4 state. Observed live 2026-09-28 (scan 690156): "parsing" → "analyzing" →
# "success" in ~1 min. "failed"/"error" are the site's explicit failure words (not yet observed). The other
# in-progress words are defensive. Anything else → unknown (never silently failed, §7.4).
ROW_STATES: dict[str, ScanState] = {"success": "complete", "failed": "failed", "error": "failed",
                                    "parsing": "scanning", "analyzing": "scanning", "processing": "scanning",
                                    "scanning": "scanning", "pending": "queued", "queued": "queued"}
# §7.3 heuristic JD cleanup: drop paragraphs that are EO / benefits / legal boilerplate, keep everything else.
BOILERPLATE_RE = re.compile(
    r"equal (employment )?opportunity|\beeo\b|affirmative action|without regard to (race|sex|gender)|"
    r"reasonable accommodation|e-verify|background check|401\(?k\)?|paid time off|\bpto\b|health insurance|"
    r"dental|vision insurance|benefits package|pay transparency|salary range|compensation range", re.I)


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_jd(jd: str) -> str:
    """§10.1: lowercase, collapsed whitespace, stripped."""
    return " ".join(jd.lower().split())


def jd_sha256(jd: str) -> str:
    return "sha256:" + hashlib.sha256(normalize_jd(jd).encode()).hexdigest()


def reuse_key(resume_sha: str, jd_sha: str, guide: str, title: str, company: str) -> tuple:
    """§10.1 full tuple. Title/company/guide compared trimmed + case-insensitive (the site shows them as typed)."""
    return (resume_sha, jd_sha, guide.strip().lower(), title.strip().lower(), company.strip().lower())


def entry_key(e: dict) -> tuple | None:
    if not (e.get("scan_id") and e.get("resume_sha256") and e.get("jd_sha256")):
        return None  # site-created / pending entries are never reusable
    return reuse_key(e["resume_sha256"], e["jd_sha256"], e.get("scoring_guide") or "", e.get("role_title") or "",
                     e.get("company") or "")


def strip_boilerplate(jd: str) -> str:
    kept = [p for p in re.split(r"\n\s*\n", jd.strip()) if not BOILERPLATE_RE.search(p)]
    return "\n\n".join(kept) or jd.strip()  # never send an empty JD because the heuristic ate it


# A text-showing operator with a non-empty operand: (literal) Tj/'/", <hex> Tj/'/", or a TJ array holding one.
PDF_TEXT_OP = re.compile(
    rb"(?:\((?:\\.|[^\\)])+\)|<\s*[0-9A-Fa-f][0-9A-Fa-f\s]*>)\s*(?:Tj|'|\")"
    rb"|\[[^\]]*(?:\((?:\\.|[^\\)])+\)|<\s*[0-9A-Fa-f][0-9A-Fa-f\s]*>)[^\]]*\]\s*TJ")
W_T = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"


def has_extractable_text(path: Path) -> bool:
    """Text-layer check without extra deps (§7.3: image-only PDFs break the site's extraction).

    PDF: some (Flate-decoded) content stream shows a non-empty string (literal or hex; glyph encodings are not
    decoded, since the question is "is there a text layer", not "what does it say"). DOCX: some w:t text node has
    non-whitespace text.
    ponytail: streams using filters other than Flate are skipped; add pypdf if real resumes get false negatives."""
    if path.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(path) as z:
                root = ElementTree.fromstring(z.read("word/document.xml"))
        except (zipfile.BadZipFile, KeyError, OSError, ElementTree.ParseError):
            return False
        return any((node.text or "").strip() for node in root.iter(W_T))
    data = path.read_bytes()
    for raw in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass
        if any(_shows_something(m.group(0)) for m in PDF_TEXT_OP.finditer(raw)):
            return True
    return False


BLANK = set(b" \t\r\n\f\b\x00")
PDF_ESCAPES = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}


def _decode_literal(body: bytes) -> bytes:
    """PDF literal-string escapes (ISO 32000 §7.3.4.2): \\n \\r \\t \\b \\f \\( \\) \\\\, octal \\ddd,
    backslash-newline continuation."""
    def repl(m):
        esc = m.group(1)
        if esc[:1].isdigit():
            return bytes([int(esc, 8) & 0xFF])
        if esc in (b"\n", b"\r", b"\r\n"):
            return b""
        return PDF_ESCAPES.get(esc, esc)
    return re.sub(rb"\\([0-7]{1,3}|\r\n|.)", repl, body, flags=re.S)


def _decode_hex(body: bytes) -> bytes:
    digits = re.sub(rb"\s", b"", body)
    return bytes.fromhex((digits + b"0" * (len(digits) % 2)).decode())  # odd length: trailing 0 nibble (§7.3.4.3)


def _shows_something(op: bytes) -> bool:
    """A text operation that draws more than whitespace: some decoded string byte is not NUL/whitespace (applies to
    single-byte and CID-padded encodings alike)."""
    strings = [_decode_literal(b) for b in re.findall(rb"\(((?:\\.|[^\\)])*)\)", op, re.S)]
    strings += [_decode_hex(b) for b in re.findall(rb"<([0-9A-Fa-f\s]*)>", op)]
    return any(byte not in BLANK for s in strings for byte in s)


def validate_inputs(resume_path, job_title, company, job_description, scoring_guide) -> Path:
    """§7.3 step 1 — before any browser work."""
    def bad(msg: str, hint: str = "Fix the input and retry once."):
        return ToolError("invalid_input", msg, hint)
    for name, v in (("job_title", job_title), ("company", company), ("job_description", job_description),
                    ("scoring_guide", scoring_guide), ("resume_path", resume_path)):
        if not isinstance(v, str) or not v.strip():
            raise bad(f"{name} must be a non-empty string.")
    path = Path(resume_path)
    if not path.is_absolute():
        raise bad("resume_path must be an absolute path.")
    if path.suffix.lower() not in (".pdf", ".docx"):
        raise bad("Resume must be a .pdf or .docx file.")
    if not path.is_file():
        raise bad("Resume file not found.", "Check resume_path.")
    if path.stat().st_size > MAX_RESUME_BYTES:
        raise bad("Resume exceeds the site's 5 MB limit.")
    if not has_extractable_text(path):
        raise bad("Resume has no extractable text (image-only PDF?).", "Export a text-based PDF/DOCX and retry.")
    return path


def row_state(attrs: dict) -> ScanState:
    return ROW_STATES.get(str(attrs.get("status")).lower(), "unknown")


def site_filename(name: str) -> str:
    """The site stores uploads with spaces as underscores ("Resume (1).pdf" → "Resume_(1).pdf")."""
    return name.replace(" ", "_").lower()


def displayed_name_matches(displayed: str, basename: str) -> bool:
    """The upload's filename heading. Live (2026-09-28) the site shortens long names with a trailing "..."
    ("2026-09-26__Resume_InternDataScientis..."), so a shortened display must be a prefix of the real name."""
    shown = displayed.strip()
    for ellipsis in ("...", "…"):
        if shown.endswith(ellipsis) and len(shown) > len(ellipsis):
            return basename.startswith(shown[: -len(ellipsis)])
    return shown == basename


def find_new_row(rows: list[dict], basename: str, title: str, since: datetime,
                 known_ids: set[str]) -> dict | None:
    """Newest My Scans row for this upload: not listed before the click (`known_ids`), same (site-normalized)
    filename and title, created at/after `since` within CLOCK_SKEW."""
    for row in rows:  # My Scans lists newest first
        if str(row.get("id")) in known_ids:
            continue
        a = row.get("attributes") or {}
        try:
            created = datetime.fromisoformat(str(a.get("created_at")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if (site_filename(str(a.get("document_file_name", ""))) == site_filename(basename)
                and str(a.get("job_title", "")).strip().lower() == title.strip().lower()
                and created >= since - CLOCK_SKEW):
            return row
    return None


def ops_today(ledger: dict, today=None) -> int:
    """§12 budget count for the local day: attempt entries, which are written durably *before* each SCAN RESUME
    or DELETE click — so an operation counts even if everything after the click fails."""
    today = today or datetime.now().astimezone().date()

    def on_today(value) -> bool:
        ts = _utc(value)
        return bool(ts) and ts.astimezone().date() == today
    attempts = [e for k, e in ledger.items() if k.startswith("attempt:") and on_today(e.get("started_at"))]
    attempted_deletes = {str(e.get("target_scan_id")) for e in attempts if e.get("kind") == "delete"}
    # Ledgers written before delete attempts existed (≤ 619abff) record a deletion only as deleted_at: count those
    # once, unless a delete attempt for the same scan already counted it.
    legacy_deletes = sum(1 for e in ledger.values() if e.get("scan_id") and on_today(e.get("deleted_at"))
                         and str(e["scan_id"]) not in attempted_deletes)
    return len(attempts) + legacy_deletes


def check_budget(ledger: dict) -> None:
    if ops_today(ledger) >= DAILY_OP_BUDGET:
        raise ToolError("limit_reached", f"Daily scan-operation budget reached ({DAILY_OP_BUDGET} starts + deletes).",
                        "Stop for today (account-safety rule, PLAN.md §12); resume tomorrow.")


def _utc(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# --- Phase 3: browser flows ---------------------------------------------------------------------------------------

async def _my_scans(page: Page, settings: Settings, step: str, page_num: int = 1) -> list[dict]:
    content = await fetch_page(page, settings, f"{SCANS_PATH}?page={page_num}", step)
    try:
        return parse_my_scans(content)[0]
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise await site_changed_error(page, settings, step, "My Scans data", e) from e


async def _state_of(page: Page, settings: Settings, scan_id: str, rows: list[dict], ledger: dict,
                    step: str) -> tuple[ScanState, str | None]:
    """State of `scan_id` from My Scans page 1 `rows`, falling back to its review_summary page for older scans.
    not_found when neither the site nor the ledger knows the id; unknown when only the ledger does (§7.4)."""
    for row in rows:
        if str(row.get("id")) == scan_id:
            attrs = row.get("attributes") or {}
            return row_state(attrs), attrs.get("highest_score")
    ids = [int(r["id"]) for r in rows if str(r.get("id", "")).isdigit()]
    if ids and int(scan_id) < min(ids):  # older than page 1: its summary page carries the same status field
        content = await fetch_page(page, settings, SUMMARY_PATH.format(scan_id), step)
        if urlparse(page.url).path.rstrip("/") == SUMMARY_PATH.format(scan_id):
            try:
                props = react_props(content, SUMMARY_APP)["parsedResume"]["data"]
                if str(props["id"]) == scan_id:
                    return row_state(props["attributes"]), props["attributes"].get("highest_score")
            except (ValueError, KeyError, TypeError, AttributeError):
                return "unknown", None
    if scan_id in ledger:
        return "unknown", None  # we created it, but the site no longer shows it readably
    raise ToolError("not_found", f"Scan {scan_id} not found.", "Re-run list_scans; the id may be a typo or deleted.")


async def _remaining_on_scan_page(page: Page, settings: Settings, step: str) -> int | None:
    await fetch_page(page, settings, SCAN_PATH, step)
    remaining = await read_scans_remaining(page, settings)
    if not on_portal(page.url, settings):
        raise auth_expired_error()
    return remaining


def _record_completion(settings: Settings, ledger: dict, scan_id: str, medal: str | None) -> None:
    entry = ledger.get(scan_id)
    if entry and not entry.get("completed_at"):
        update_ledger(settings, scan_id, completed_at=datetime.now(timezone.utc).isoformat(),
                      medal=medal if medal in MEDALS else entry.get("medal"))


@site_operation
async def get_scan_status(settings: Settings, scan_id: str) -> ScanStatus:
    """§7.4. Cheap: the pre-check lands on the scan page (counter), then one My Scans page."""
    check_scan_id(scan_id)
    step = f"{scan_id}-status"
    page = await new_page(settings)
    await require_login(page, settings, step)
    remaining = await read_scans_remaining(page, settings)
    ledger = load_ledger(settings)
    rows = await _my_scans(page, settings, step)
    state, medal = await _state_of(page, settings, scan_id, rows, ledger, step)
    if state == "complete":
        _record_completion(settings, ledger, scan_id, medal)
    hint = None
    if state == "unknown":  # §7.4: snapshot + a hint to inspect it; unknown is "stop and investigate", not failure
        async with site_errors(page, settings):
            path = await snapshot(page, settings, step)
        hint = f"Stop and investigate (not a failure): inspect snapshot {path.name} and My Scans."
    return ScanStatus(scan_id=scan_id, state=state, scans_remaining=remaining,
                      checked_at=datetime.now().astimezone(), hint=hint)


def _recover_attempts(settings: Settings, ledger: dict, rows: list[dict]) -> list[str]:
    """§10.2: adopt the site row for each pending attempt; return attempt keys still unresolved.

    An unmatched attempt stays pending (the row may still appear) and blocks new submissions via unknown_state.
    Only once its whole 10-min window has passed with no row is it marked `abandoned` — the safe resolution:
    §10.2 would never adopt a later row for it anyway."""
    unresolved = []
    claimed = {k for k in ledger if not k.startswith("attempt:")}
    now = datetime.now(timezone.utc)
    for key, a in list(ledger.items()):
        if (not key.startswith("attempt:") or a.get("kind") == "delete" or a.get("resolved_scan_id")
                or a.get("abandoned")):
            continue
        since = _utc(a.get("started_at")) or now
        known = {str(i) for i in a.get("known_ids") or []}
        row = next((r for r in rows if str(r.get("id")) not in claimed | known
                    and (created := _utc((r.get("attributes") or {}).get("created_at")))
                    and since - CLOCK_SKEW <= created <= since + RECOVERY_WINDOW
                    and site_filename(str((r.get("attributes") or {}).get("document_file_name", "")))
                    == site_filename(a.get("resume_filename", ""))), None)
        if row is None:
            if now - since > RECOVERY_WINDOW + CLOCK_SKEW:
                update_ledger(settings, key, abandoned=True)
            unresolved.append(key)
            continue
        scan_id = str(row["id"])
        claimed.add(scan_id)
        append_ledger(settings, {**a, "scan_id": scan_id, "recovered": True})
        update_ledger(settings, key, resolved_scan_id=scan_id)
    return unresolved


@site_operation
async def start_scan(settings: Settings, resume_path: str, job_title: str, company: str, job_description: str,
                     scoring_guide: str = "Graduate - STEM Focus") -> StartScanResult:
    """§7.3: idempotent on the full reuse key; otherwise the §9 workflow, then capture the id and ledger it."""
    path = validate_inputs(resume_path, job_title, company, job_description, scoring_guide)
    resume_sha, jd_sha = sha256_file(path), jd_sha256(job_description)
    key = reuse_key(resume_sha, jd_sha, scoring_guide, job_title, company)
    step = "start-scan"
    page = await new_page(settings)
    await require_login(page, settings, step)
    remaining = await read_scans_remaining(page, settings)
    ledger = load_ledger(settings)
    rows = await _my_scans(page, settings, step)

    if unresolved := _recover_attempts(settings, ledger, rows):
        raise ToolError("unknown_state", f"{len(unresolved)} earlier scan submission(s) not yet matched to a My Scans row.",
                        "Stop; do not rescan. Retry start_scan later (the row may still appear) or check My Scans "
                        "manually. After its 10-minute window an unmatched submission is marked abandoned.")
    ledger = load_ledger(settings)

    now = datetime.now(timezone.utc)
    for scan_id, e in ledger.items():  # §12: one scan in flight
        started = _utc(e.get("started_at"))
        if (e.get("scan_id") and not e.get("completed_at") and not e.get("deleted_at") and started
                and now - started < IN_FLIGHT_WINDOW
                and (await _state_of(page, settings, scan_id, rows, ledger, step))[0] in ("queued", "scanning")):
            raise ToolError("invalid_input", f"Scan {scan_id} is still in flight.",
                            "Poll get_scan_status until it completes; only one scan may run at a time.")

    for e in sorted(ledger.values(), key=lambda e: e.get("started_at") or "", reverse=True):  # §10.1 reuse
        if entry_key(e) == key and not e.get("deleted_at"):
            if (await _state_of(page, settings, str(e["scan_id"]), rows, ledger, step))[0] == "complete":
                return StartScanResult(scan_id=str(e["scan_id"]), reused=True, state="complete",
                                       scans_remaining=remaining)

    check_budget(ledger)  # reuse above costs nothing; a fresh submission counts
    if remaining == 0:
        raise ToolError("limit_reached", "Daily scan allowance exhausted (0 scans left today).",
                        "Stop. Resume after local midnight or ask the user to request a reset.")
    known_ids = {str(r.get("id")) for r in rows}
    scan_id, state = await _submit(page, settings, path, job_title, company, strip_boilerplate(job_description),
                                   scoring_guide, resume_sha, jd_sha, step, known_ids)
    return StartScanResult(scan_id=scan_id, reused=False, state=state,
                           scans_remaining=await _remaining_on_scan_page(page, settings, step))


async def _shows_filename(headings, basename: str, timeout_s: float = 10.0) -> bool:
    """§9 filename check, polled until the (possibly truncated) name shows up or the landmark timeout passes."""
    deadline = asyncio.get_running_loop().time() + timeout_s
    while True:
        if any(displayed_name_matches(t, basename) for t in await headings.all_inner_texts()):
            return True
        if asyncio.get_running_loop().time() >= deadline:
            return False
        await asyncio.sleep(0.25)


async def _visible(locator, timeout_ms: int = 10_000) -> bool:
    try:
        await locator.wait_for(state="visible", timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


async def _submit(page: Page, settings: Settings, path: Path, title: str, company: str, jd: str, guide: str,
                  resume_sha: str, jd_sha: str, step: str, known_ids: set[str]) -> tuple[str, ScanState]:
    """§9 workflow on the scan page. Every control is asserted visible before use (missing → site_changed +
    snapshot, never a Playwright timeout); nothing is clicked blindly."""
    await fetch_page(page, settings, SCAN_PATH, step)

    async def landmark(locator, what: str):
        if not await _visible(locator):
            if not on_portal(page.url, settings):
                raise auth_expired_error()
            raise await site_changed_error(page, settings, step, what)
        return locator

    async with site_errors(page, settings):
        await human_delay(settings)
        search = await landmark(page.get_by_role("searchbox", name="Search for a score guide"), "Scoring guide search box")
        await search.fill(guide)
        await human_delay(settings)
        select = page.get_by_role("button", name=f"Select {guide}", exact=True)
        if not await _visible(select):
            raise ToolError("invalid_input", f"Scoring guide '{guide}' not found.",
                            "Use a guide name exactly as shown on the site (default 'Graduate - STEM Focus').")
        await select.click()
        await landmark(page.get_by_role("heading", name=guide, exact=True), "Selected scoring guide heading")
        await landmark(page.get_by_role("button", name="Remove", exact=True), "Scoring guide Remove control")

        await human_delay(settings)
        radio = await landmark(page.get_by_role("radio", name="Add Job Description"), "Add Job Description option")
        await radio.check()
        for label, value in (("Role / Position", title), ("Company Name", company), ("Job Description", jd)):
            box = await landmark(page.get_by_role("textbox", name=label), f"{label} field")
            await box.fill(value)
            await human_delay(settings)

        upload = page.locator("input[type=file]")  # no accessible name on the file input
        if not await upload.count():
            raise await site_changed_error(page, settings, step, "Resume file input")
        await upload.first.set_input_files(str(path))
        remove = await landmark(page.get_by_role("button", name="Remove file", exact=True),
                                "Uploaded file (Remove file control)")
        # The filename h3 is the Remove button's sibling; it may render a beat later, so wait like other landmarks.
        if not await _shows_filename(remove.locator("xpath=..").get_by_role("heading", level=3), path.name):
            raise await site_changed_error(page, settings, step, f"Uploaded filename '{path.name}' (not displayed)")
        scan_button = await landmark(page.get_by_role("button", name="Scan Resume", exact=True), "Scan Resume button")

        # §10.2: record the attempt *before* clicking, so a crash after the click is recoverable.
        attempt = {"scan_id": None, "attempt_id": uuid.uuid4().hex, "resume_filename": path.name,
                   "resume_sha256": resume_sha, "jd_sha256": jd_sha, "role_title": title, "company": company,
                   "scoring_guide": guide, "started_at": datetime.now(timezone.utc).isoformat(),
                   "known_ids": sorted(known_ids), "completed_at": None, "medal": None, "ats_badge": None,
                   "credibility_badge": None, "recovered": False, "deleted_at": None}
        append_ledger(settings, attempt)
        await human_delay(settings)
        clicked_at = datetime.now(timezone.utc)
        await scan_button.click()

    deadline = clicked_at + timedelta(seconds=CAPTURE_WINDOW_S)
    while datetime.now(timezone.utc) < deadline:
        rows = await _my_scans(page, settings, step)  # fetch_page includes the 2–5 s human delay
        if row := find_new_row(rows, path.name, title, clicked_at, known_ids):
            scan_id = str(row["id"])
            append_ledger(settings, {**attempt, "scan_id": scan_id})  # §10.2: immediately after capture
            update_ledger(settings, ledger_key(attempt), resolved_scan_id=scan_id)
            state = row_state(row.get("attributes") or {})
            if state == "failed":
                raise ToolError("scan_failed", f"Scan {scan_id} was submitted but the site reports it failed.",
                                f"Keep scan id {scan_id}; retry once with a fresh upload, then stop (§13).")
            if state == "unknown":
                raise ToolError("unknown_state", f"Scan {scan_id} was submitted but its site status is unreadable.",
                                f"Do not rescan. Inspect scan {scan_id} in My Scans / via get_scan_status.")
            return scan_id, state
    raise ToolError("unknown_state", "Scan submitted but its id did not appear in My Scans within 60 s.",
                    "Do not rescan. The next start_scan recovers it from My Scans (§10.2), or check manually.")


@site_operation
async def delete_scan(settings: Settings, scan_id: str, confirm: bool = False) -> DeleteResult:
    """§7.6 — order matters: backup first, latest-result guard, UI delete, verify, re-read the counter."""
    check_scan_id(scan_id)
    if not isinstance(confirm, bool):
        raise ToolError("invalid_input", "confirm must be a boolean.", "Pass confirm=true or omit it.")
    step = f"{scan_id}-delete"
    page = await new_page(settings)
    await require_login(page, settings, step)
    before = await read_scans_remaining(page, settings)
    ledger = load_ledger(settings)

    backup = feedback_backup(settings, scan_id)  # §7.6 step 1 (always first): re-verified backup, else fetch now
    if backup is None:
        await read_feedback(page, settings, scan_id, ledger)
        backup = feedback_backup(settings, scan_id)
        if backup is None:
            raise ToolError("storage_error", "Feedback backup could not be verified.", "Stop. Deletion aborted.")

    latest = max((e for e in ledger.values() if e.get("scan_id") and not e.get("deleted_at")),
                 key=lambda e: e.get("started_at") or "", default=None)
    if latest and str(latest["scan_id"]) == scan_id and not confirm:  # §7.6 step 2
        raise ToolError("invalid_input", f"Scan {scan_id} is the latest loop result (feedback backed up).",
                        "Pass confirm=true to delete it anyway.")

    check_budget(ledger)  # §7.6 backup is done; the deletion itself counts
    page_num = await _find_page(page, settings, scan_id, step)
    href = SUMMARY_PATH.format(scan_id)
    row = page.locator("li").filter(has=page.locator(f'a[href="{href}"]')).first
    async with site_errors(page, settings):
        if not await _visible(row):
            raise await site_changed_error(page, settings, step, f"My Scans row for {scan_id}")
        await human_delay(settings)
        await row.locator("[data-toggle=dropdown]").click()  # the row menu toggle has no accessible name
        delete = row.get_by_role("button", name="DELETE")
        if not await _visible(delete, 5_000):
            raise await site_changed_error(page, settings, step, "Row DELETE control")
        # §12: count the deletion before clicking, so a failure after the click can't let the budget be exceeded.
        delete_attempt = {"scan_id": None, "attempt_id": uuid.uuid4().hex, "kind": "delete",
                          "target_scan_id": scan_id, "started_at": datetime.now(timezone.utc).isoformat()}
        append_ledger(settings, delete_attempt)

        async def accept(dialog):  # native confirm(), if the site uses one
            await dialog.accept()

        page.once("dialog", accept)
        try:
            await human_delay(settings)
            await delete.click()
            # Verified live 2026-09-28 (scan 376501) through this path; accepts a native confirm or an ARIA dialog button.
            dialog = page.get_by_role("dialog")
            if await _visible(dialog, 3_000):
                await human_delay(settings)
                await dialog.get_by_role("button", name=re.compile(r"^(delete|yes|confirm|ok)", re.I)).first.click()
        finally:
            page.remove_listener("dialog", accept)  # never auto-accept anything later

    rows = await _my_scans(page, settings, step, page_num)  # verify on reload
    if any(str(r.get("id")) == scan_id for r in rows):
        raise await site_changed_error(page, settings, step, f"Deletion of {scan_id} (row still listed)")
    deleted_at = datetime.now(timezone.utc).isoformat()
    update_ledger(settings, ledger_key(delete_attempt), verified=True)
    update_ledger(settings, scan_id, scan_id=scan_id, deleted_at=deleted_at)  # site-created scans too
    after = await _remaining_on_scan_page(page, settings, step)
    return DeleteResult(deleted=True, backup_path=str(backup), scans_remaining=after,
                        allowance_restored=None if before is None or after is None else after > before)


async def _find_page(page: Page, settings: Settings, scan_id: str, step: str) -> int:
    """My Scans page number listing `scan_id` (ids descend with time); leaves the browser on that page."""
    page_num, target = 1, int(scan_id)
    while True:
        rows = await _my_scans(page, settings, step, page_num)
        ids = [int(r["id"]) for r in rows if str(r.get("id", "")).isdigit()]
        if target in ids:
            return page_num
        if not ids or target > max(ids) or len(ids) < PAGE_SIZE or target > min(ids):
            raise ToolError("not_found", f"Scan {scan_id} not found in My Scans.", "Re-run list_scans.")
        page_num += 1
