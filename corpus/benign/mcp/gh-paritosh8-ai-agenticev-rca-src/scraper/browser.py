"""
Browser manager and network response interceptor for ElectreeFi scraping.
"""

import json
import logging
from typing import Any
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from src.config import SESSION_STORAGE_PATH, BROWSER_TIMEOUT_MS

logger = logging.getLogger(__name__)

# In-memory captured JSON endpoints for performance sniffing
CAPTURED_JSON_RESPONSES: list[dict[str, Any]] = []


async def setup_network_sniffer(page: Page) -> None:
    """Listens for AJAX/fetch responses that return JSON payloads."""
    async def on_response(response):
        try:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                url = response.url
                # Only log internal portal endpoints, not third-party telemetry/fonts
                if "ev-charge-network.com" in url:
                    try:
                        data = await response.json()
                        CAPTURED_JSON_RESPONSES.append({
                            "url": url,
                            "status": response.status,
                            "sample": data if isinstance(data, list) else list(data.keys()) if isinstance(data, dict) else None
                        })
                        logger.info(f"Captured JSON API response from: {url}")
                    except Exception:
                        pass
        except Exception:
            pass

    page.on("response", on_response)


class BrowserSession:
    """Context manager for Playwright browser and page lifecycle."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> Page:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )

        storage_state = str(SESSION_STORAGE_PATH) if Path(SESSION_STORAGE_PATH).exists() else None
        self.context = await self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        self.context.set_default_timeout(BROWSER_TIMEOUT_MS)

        self.page = await self.context.new_page()
        await setup_network_sniffer(self.page)
        return self.page

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
