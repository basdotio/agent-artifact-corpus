"""Browser lifecycle management with stealth mode and session persistence."""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from ..exceptions import BrowserError
from ..session.store import SessionStore

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)

BRAVE_PATH = os.environ.get("SUNO_BROWSER_PATH", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
BRAVE_PROFILE = Path.home() / ".suno-mcp" / "brave-profile"
BRAVE_CDP_PORT = int(os.environ.get("SUNO_CDP_PORT", "9333"))


class BrowserManager:
    """Manages Playwright browser with stealth mode and session persistence."""

    def __init__(self, session_store: Optional[SessionStore] = None) -> None:
        self.session_store = session_store or SessionStore()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def ensure_browser(self, headless: bool = False) -> dict[str, Any]:
        """Initialize browser if not already running. Returns browser components."""
        try:
            if not self._playwright:
                self._playwright = await async_playwright().start()

            if not self._browser or not self._browser.is_connected():
                self._browser = await self._launch_browser(headless)

            if not self._context:
                self._context = await self._create_context()

            if not self._page:
                pages = self._context.pages
                self._page = pages[0] if pages else await self._context.new_page()
                self._page.set_default_timeout(30_000)
                self._page.set_default_navigation_timeout(30_000)
                await self._apply_stealth(self._page)

            return {
                "playwright": self._playwright,
                "browser": self._browser,
                "context": self._context,
                "page": self._page,
            }
        except Exception as e:
            logger.error("Browser initialization failed: %s", e)
            # Reset stale state so next call retries cleanly
            self._page = None
            self._context = None
            self._browser = None
            raise BrowserError(f"Browser initialization failed: {e}", "BROWSER_INIT_ERROR")

    async def _launch_browser(self, headless: bool) -> Browser:
        """Attach to real Brave over CDP (Google blocks automated Chromium login);
        fall back to Playwright's bundled Chromium if Brave isn't installed."""
        assert self._playwright is not None
        if Path(BRAVE_PATH).exists():
            return await self._connect_brave()
        return await self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

    async def _connect_brave(self) -> Browser:
        """Start Brave with a dedicated profile + debug port (no automation flags), then attach."""
        assert self._playwright is not None
        cdp = f"http://127.0.0.1:{BRAVE_CDP_PORT}"
        try:
            return await self._playwright.chromium.connect_over_cdp(cdp)
        except Exception:
            pass  # not running yet
        BRAVE_PROFILE.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(
            [BRAVE_PATH, f"--user-data-dir={BRAVE_PROFILE}",
             f"--remote-debugging-port={BRAVE_CDP_PORT}", "--no-first-run", "https://suno.com"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
        for _ in range(30):
            await asyncio.sleep(1)
            try:
                return await self._playwright.chromium.connect_over_cdp(cdp)
            except Exception:
                continue
        raise BrowserError("Brave did not open its debug port", "BRAVE_CDP_ERROR")

    async def _create_context(self) -> BrowserContext:
        """Create a browser context, restoring saved session if available."""
        assert self._browser is not None
        if self._browser.contexts:  # Brave over CDP: reuse its persistent profile
            context = self._browser.contexts[0]
            saved = self.session_store.load()  # e.g. cookies from brave_import
            if saved and saved.get("cookies"):
                await context.add_cookies(saved["cookies"])
            return context

        ctx_kwargs: dict[str, Any] = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "accept_downloads": True,
        }

        saved = self.session_store.load()
        if saved:
            ctx_kwargs["storage_state"] = saved
            logger.info("Restored browser session from storage")

        context = await self._browser.new_context(**ctx_kwargs)

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

        context.on("page", self._on_new_page)
        return context

    def _on_new_page(self, page: Page) -> None:
        """Called when any new page/popup opens in the context."""
        asyncio.ensure_future(self._apply_stealth(page))
        logger.info("Stealth applied to new page: %s", page.url)

    async def _apply_stealth(self, page: Page) -> None:
        """Apply playwright-stealth patches to evade bot detection."""
        try:
            from playwright_stealth import Stealth  # type: ignore[import]
            await Stealth().apply_stealth_async(page)
        except ImportError:
            logger.warning("playwright-stealth not installed; skipping stealth mode")
        except Exception as e:
            logger.warning("Stealth apply failed: %s", e)

    async def save_session(self) -> None:
        """Save current browser session state to disk."""
        if self._context:
            state = await self._context.storage_state()
            self.session_store.save(state)

    async def close(self) -> None:
        """Close browser and clean up all resources."""
        try:
            if self._page:
                await self._page.close()
                self._page = None
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            logger.info("Browser session closed")
        except Exception as e:
            logger.error("Error closing browser: %s", e)
            raise BrowserError(f"Browser cleanup failed: {e}", "BROWSER_CLOSE_ERROR")

    async def get_status(self) -> dict[str, Any]:
        """Return current browser/session status dict."""
        status: dict[str, Any] = {
            "browser_open": self._context is not None,
            "context_ready": self._context is not None,
            "page_ready": self._page is not None,
            "current_url": None,
            "page_title": None,
            "in_studio": False,
            "session_saved": self.session_store.exists(),
        }
        if self._page:
            try:
                status["current_url"] = self._page.url
                status["page_title"] = await self._page.title()
                status["in_studio"] = "/studio" in (self._page.url or "")
            except Exception:
                pass
        return status
