"""Page navigation and element interaction helpers."""

import logging
import sys
from typing import Optional

from playwright.async_api import Page

from ..exceptions import NavigationError

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)


async def navigate_to(page: Page, url: str, wait_selector: Optional[str] = None) -> None:
    """Navigate to a URL (SPA-safe: uses wait_until='load')."""
    try:
        await page.goto(url, wait_until="load", timeout=30_000)
        if wait_selector:
            await page.wait_for_selector(wait_selector, timeout=10_000)
    except Exception as e:
        raise NavigationError(f"Navigation to {url} failed: {e}", "NAV_ERROR")


async def try_click(page: Page, selectors: list[str], timeout: int = 3_000) -> bool:
    """Try clicking each selector in order; return True on first success."""
    for sel in selectors:
        try:
            await page.locator(sel).first.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False


async def try_fill(page: Page, selectors: list[str], value: str, timeout: int = 3_000) -> bool:
    """Try filling each selector in order; return True on first success."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.clear(timeout=timeout)
            await loc.fill(value, timeout=timeout)
            return True
        except Exception:
            continue
    return False


async def find_visible(page: Page, selectors: list[str], timeout: int = 5_000) -> Optional[str]:
    """Return the first selector that becomes visible within timeout."""
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, state="visible", timeout=timeout)
            return sel
        except Exception:
            continue
    return None
