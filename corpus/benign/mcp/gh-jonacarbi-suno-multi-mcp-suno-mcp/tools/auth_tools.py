"""Authentication tools for Suno MCP — Google OAuth via Clerk."""

import asyncio
import logging
import sys
from typing import Optional

from playwright.async_api import Page

from ..browser.manager import BrowserManager
from ..browser.navigator import find_visible, navigate_to, try_click, try_fill
from ..exceptions import AuthError

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)

SUNO_HOME = "https://suno.com"


class AuthTools:
    """Handles Suno AI authentication via Google OAuth."""

    def __init__(self, manager: BrowserManager) -> None:
        self.manager = manager

    async def login(self, email: str, password: str) -> str:
        """Login to Suno AI via Google OAuth. Saves session on success."""
        try:
            components = await self.manager.ensure_browser(headless=False)
            page = components["page"]
            context = components["context"]

            # Check if already logged in
            if await self._is_logged_in(page):
                return "✅ Already logged in. Session is active."

            # Navigate to suno.com
            await navigate_to(page, SUNO_HOME)
            await asyncio.sleep(1)

            # Click "Sign In" button
            sign_in_selectors = [
                'button:has-text("Sign In")',
                'button:has-text("Sign in")',
                'a:has-text("Sign In")',
                'a:has-text("Sign in")',
                '[data-testid="sign-in-button"]',
                'a[href*="sign-in"]',
            ]
            clicked = await try_click(page, sign_in_selectors, timeout=8_000)
            if not clicked:
                raise AuthError("Sign In button not found", "SIGNIN_BUTTON_NOT_FOUND")

            # Wait for Clerk dialog to render
            await asyncio.sleep(2)

            # Set up popup/new-page listener BEFORE clicking Google button
            popup_future: asyncio.Future[Page] = asyncio.get_event_loop().create_future()

            def _on_page(new_page: Page) -> None:
                if not popup_future.done():
                    popup_future.set_result(new_page)

            context.on("page", _on_page)

            # Click Google button via JS (most reliable across Clerk variants)
            google_clicked = False
            for _attempt in range(12):
                google_clicked = await page.evaluate("""() => {
                    const els = [
                        ...document.querySelectorAll('button'),
                        ...document.querySelectorAll('a'),
                    ];
                    for (const el of els) {
                        const txt = (el.textContent || '').toLowerCase();
                        const prov = (el.getAttribute('data-provider') || '').toLowerCase();
                        const key = (el.getAttribute('data-localization-key') || '').toLowerCase();
                        if (txt.includes('google') || prov.includes('google') || key.includes('google')) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if google_clicked:
                    break
                await asyncio.sleep(1)

            if not google_clicked:
                context.remove_listener("page", _on_page)
                raise AuthError("Google login button not found", "GOOGLE_BUTTON_NOT_FOUND")

            # Determine whether Google OAuth opened in a popup or navigated the main page
            google_page = await self._resolve_google_page(page, popup_future)
            context.remove_listener("page", _on_page)

            # Fill Google credentials
            await self._handle_google_oauth(google_page, email, password)

            # Wait for suno.com to come back (main page)
            try:
                await page.wait_for_url("**/suno.com/**", timeout=30_000)
            except Exception:
                await asyncio.sleep(3)

            if not await self._is_logged_in(page):
                raise AuthError(
                    "Login failed — still not authenticated after OAuth flow",
                    "LOGIN_FAILED",
                )

            await self.manager.save_session()
            return (
                f"✅ Login successful!\n"
                f"Current URL: {page.url}\n"
                f"Session saved for future use."
            )

        except AuthError:
            raise
        except Exception as e:
            logger.error("Login failed: %s", e)
            raise AuthError(f"Login failed: {e}", "LOGIN_ERROR")

    async def _resolve_google_page(
        self, main_page: Page, popup_future: "asyncio.Future[Page]"
    ) -> Page:
        """Wait and determine whether Google OAuth is in a popup or main page."""
        await asyncio.sleep(1)

        # Try to get a popup that opened
        try:
            popup = await asyncio.wait_for(asyncio.shield(popup_future), timeout=4.0)
            logger.info("Google OAuth opened in popup: %s", popup.url)
            await asyncio.sleep(1)  # Let the popup page load
            return popup
        except asyncio.TimeoutError:
            pass  # No popup — check if main page navigated to Google

        # Check if main page navigated to accounts.google.com
        try:
            await main_page.wait_for_url("**/accounts.google.com/**", timeout=5_000)
            logger.info("Google OAuth on main page: %s", main_page.url)
            return main_page
        except Exception:
            pass

        # Default: try main page anyway
        logger.warning("Could not confirm Google OAuth location, using main page")
        return main_page

    async def _handle_google_oauth(self, page: Page, email: str, password: str) -> None:
        """Fill Google OAuth email and password forms on the given page."""
        await asyncio.sleep(1)

        # Email step
        email_selectors = [
            'input[type="email"]',
            'input[name="identifier"]',
            '#identifierInput',
            '#Email',
        ]
        filled = await try_fill(page, email_selectors, email, timeout=8_000)
        if not filled:
            raise AuthError("Google email field not found", "GOOGLE_EMAIL_NOT_FOUND")

        await try_click(
            page,
            ['#identifierNext', 'button:has-text("Next")', 'input[value="Next"]'],
            timeout=5_000,
        )
        await asyncio.sleep(1)

        # Password step
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            '#passwordInput',
            '#Passwd',
        ]
        filled = await try_fill(page, password_selectors, password, timeout=10_000)
        if not filled:
            raise AuthError("Google password field not found", "GOOGLE_PASSWORD_NOT_FOUND")

        await try_click(
            page,
            ['#passwordNext', 'button:has-text("Next")', 'input[value="Next"]'],
            timeout=5_000,
        )

    async def _is_logged_in(self, page: Page) -> bool:
        """Check if the user is currently logged in to Suno."""
        try:
            url = page.url or ""
            if "suno.com" not in url:
                return False
            logged_in_sel = await find_visible(
                page,
                [
                    '[data-testid="user-avatar"]',
                    '[data-testid="account-menu"]',
                    'button[aria-label*="account" i]',
                    'img[alt*="avatar" i]',
                    'a[href="/me"]',
                    'a[href*="/profile"]',
                ],
                timeout=3_000,
            )
            return logged_in_sel is not None
        except Exception:
            return False
