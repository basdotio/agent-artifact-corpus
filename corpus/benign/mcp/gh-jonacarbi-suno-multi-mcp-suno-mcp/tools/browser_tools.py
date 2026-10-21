"""Browser lifecycle tools for Suno MCP."""

import logging
import sys
from typing import Any

from ..browser.manager import BrowserManager
from ..exceptions import BrowserError

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)


class BrowserTools:
    """Tools for managing the Playwright browser session."""

    def __init__(self, manager: BrowserManager) -> None:
        self.manager = manager

    async def open_browser(self, headless: bool = False) -> str:
        """Open Chrome browser with stealth mode."""
        try:
            components = await self.manager.ensure_browser(headless=headless)
            page = components["page"]
            await page.goto("https://suno.com", wait_until="load", timeout=30_000)
            title = await page.title()
            url = page.url
            return (
                f"✅ Browser opened successfully.\n"
                f"Page title: {title}\n"
                f"URL: {url}\n"
                f"Headless: {headless}\n"
                f"Session saved: {self.manager.session_store.exists()}"
            )
        except Exception as e:
            logger.error("Browser open failed: %s", e)
            raise BrowserError(f"Browser initialization failed: {e}", "BROWSER_INIT_ERROR")

    async def get_status(self) -> str:
        """Get current browser and session status."""
        status = await self.manager.get_status()
        return (
            f"📊 Suno MCP Status:\n"
            f"Browser Open: {status.get('browser_open', False)}\n"
            f"Context Ready: {status.get('context_ready', False)}\n"
            f"Page Ready: {status.get('page_ready', False)}\n"
            f"Current URL: {status.get('current_url', 'None')}\n"
            f"Page Title: {status.get('page_title', 'None')}\n"
            f"In Studio: {status.get('in_studio', False)}\n"
            f"Session Saved: {status.get('session_saved', False)}"
        )

    async def close_browser(self) -> str:
        """Close the browser session."""
        await self.manager.close()
        return "✅ Browser closed successfully."
