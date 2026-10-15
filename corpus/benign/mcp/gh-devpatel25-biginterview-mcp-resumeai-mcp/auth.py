"""Login-state detection and auth_status (PLAN.md §6.2, §7.1)."""

import re
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import ValidationError

from .browser import goto, human_delay, new_page, site_operation, snapshot
from .config import Settings
from .schemas import AuthStatus, ToolError

SCAN_PATH = "/members/resume_assignments/scan"
# §9: the scan page is ready when this heading is visible.
SCAN_LANDMARK = "Select Scoring Guide"
# §9 allowance counter; live page shows the heading "5 scans left today.".
REMAINING_RE = re.compile(r"(\d+)\s*(?:scans?\s+)?(?:remaining|left)", re.I)

LOGGED_IN = "logged_in"
AUTH_EXPIRED = "auth_expired"  # §13
SITE_CHANGED = "site_changed"  # §13


def on_portal(url: str, settings: Settings) -> bool:
    """True when `url` is an authenticated portal page (not the IdP / login page)."""
    u = urlparse(url)
    return u.hostname == urlparse(settings.base_url).hostname and u.path.startswith("/members/")


def sso_redirect(url: str, settings: Settings) -> bool:
    """True when the browser sits on some other web host (IdP / login page), not on a browser error page."""
    u = urlparse(url)
    return u.scheme in ("http", "https") and not on_portal(url, settings)


def network_error(e: PlaywrightError) -> ToolError:
    """§13 network_error (amendment 2026-09-28): transport failure, not an auth or selector problem."""
    detail = (e.message or type(e).__name__).splitlines()[0][:200]  # e.g. net::ERR_NAME_NOT_RESOLVED + portal URL
    return ToolError("network_error", f"Portal unreachable or navigation failed: {detail}",
                     "Retry up to 2x with the 2-5 s delay; if it persists, stop and report.")


def auth_expired_error() -> ToolError:
    return ToolError("auth_expired", "Big Interview session expired (SSO login required).",
                     "Stop. Ask the user to run scripts/login.py, then retry.")


@asynccontextmanager
async def site_errors(page: Page, settings: Settings):
    """Browser boundary for any Playwright call after the pre-check: a Playwright error (incl. timeout)
    becomes auth_expired if the page has moved to an SSO/login host, else network_error.
    Callers that classify timeouts themselves catch PlaywrightTimeoutError inside this block."""
    try:
        yield
    except PlaywrightError as e:
        if sso_redirect(page.url, settings):
            raise auth_expired_error() from e
        raise network_error(e) from e


async def login_state(page: Page, settings: Settings) -> str:
    """Load the scan page; return LOGGED_IN, AUTH_EXPIRED or SITE_CHANGED.

    Playwright timeouts are classified, never raised. Other Playwright errors (connection, DNS,
    browser closed) become AUTH_EXPIRED if the browser is on an SSO/login host, else ToolError
    network_error.
    The portal's own session cookie is session-scoped, so a fresh browser is bounced
    through SAML SSO, which re-authenticates silently while the IdP session is alive and
    then lands on the dashboard rather than the requested page. So: wait for the redirect
    chain to settle back on the portal, re-open the scan page, then check the landmark.
    On any navigation/wait timeout the final URL decides: still off the portal (stalled on
    the IdP/login page) → AUTH_EXPIRED; on the portal but no landmark → SITE_CHANGED.
    """
    try:
        await goto(page, settings, SCAN_PATH)
        await page.wait_for_url(lambda url: on_portal(url, settings))
        if urlparse(page.url).path.rstrip("/") != SCAN_PATH:
            await goto(page, settings, SCAN_PATH)
        await page.get_by_role("heading", name=SCAN_LANDMARK, exact=True).wait_for(state="visible")
    except PlaywrightTimeoutError:
        return SITE_CHANGED if on_portal(page.url, settings) else AUTH_EXPIRED
    except PlaywrightError as e:
        if sso_redirect(page.url, settings):
            return AUTH_EXPIRED
        raise network_error(e) from e
    return LOGGED_IN if on_portal(page.url, settings) else AUTH_EXPIRED


async def is_logged_in(page: Page, settings: Settings) -> bool:
    return await login_state(page, settings) == LOGGED_IN


async def require_login(page: Page, settings: Settings, step: str) -> None:
    """§6.2 pre-check for every site-touching tool: raise auth_expired / site_changed (+ snapshot)."""
    await raise_for_state(page, settings, await login_state(page, settings), step)


async def raise_for_state(page: Page, settings: Settings, state: str, step: str) -> None:
    if state == AUTH_EXPIRED:
        raise auth_expired_error()
    if state == SITE_CHANGED:
        async with site_errors(page, settings):
            path = await snapshot(page, settings, step)
        raise ToolError("site_changed", f"Scan page landmark '{SCAN_LANDMARK}' not found.",
                        f"Stop. Inspect snapshot {path.name}; selectors need a fix.")


async def fetch_page(page: Page, settings: Settings, path: str, step: str) -> str:
    """Human-paced navigation to a portal page after the pre-check; returns its HTML.

    Timeouts fall through to the URL check; other Playwright errors go through site_errors. The URL is
    checked *after* the read: a redirect that lands mid-read must be auth_expired, not a login page
    misparsed as site_changed by the caller."""
    await human_delay(settings)
    async with site_errors(page, settings):
        try:
            await goto(page, settings, path)
        except PlaywrightTimeoutError:
            pass  # classified below: off-portal → auth_expired; on-portal → caller's parser decides
    async with site_errors(page, settings):  # page may redirect/close while being read
        content = await page.content()
    if not on_portal(page.url, settings):  # session died after the pre-check (SSO redirect)
        await raise_for_state(page, settings, AUTH_EXPIRED, step)
    return content


async def site_changed_error(page: Page, settings: Settings, step: str, what: str,
                             cause: Exception | None = None) -> ToolError:
    """§13 site_changed with the snapshot already saved; names what is missing (§9 change-detection)."""
    async with site_errors(page, settings):
        path = await snapshot(page, settings, step)
    # Our own ValueError/KeyError texts name the missing landmark/field; pydantic errors echo page values (PII).
    reason = "" if cause is None else f" ({type(cause).__name__ if isinstance(cause, ValidationError) else str(cause)[:120]})"
    return ToolError("site_changed", f"{what} not readable{reason}.",
                     f"Stop. Inspect snapshot {path.name}; the parser needs a fix.")


def parse_scans_remaining(text: str) -> int | None:
    m = REMAINING_RE.search(text)
    return int(m.group(1)) if m else None


async def read_scans_remaining(page: Page, settings: Settings) -> int | None:
    """The scan page's "N scans left today." counter (null when not rendered — never guessed)."""
    counter = page.get_by_role("heading", name=REMAINING_RE)
    async with site_errors(page, settings):
        if await counter.count():
            return parse_scans_remaining(await counter.first.inner_text())
    return None


@site_operation
async def auth_status(settings: Settings) -> AuthStatus:
    """§7.1. logged_in=false is data, not an error; the counter is null when not rendered."""
    page = await new_page(settings)
    state = await login_state(page, settings)
    if state == SITE_CHANGED:
        await raise_for_state(page, settings, state, "auth-status")
    remaining = None
    if state == LOGGED_IN:
        remaining = await read_scans_remaining(page, settings)
        if not on_portal(page.url, settings):  # redirected to SSO during the read → not logged in
            state, remaining = AUTH_EXPIRED, None
    return AuthStatus(
        logged_in=state == LOGGED_IN,
        scans_remaining=remaining,
        account_email=None,  # not rendered on the scan page; §7.1 says null when not visible
        checked_at=datetime.now().astimezone(),
    )
