"""Music generation tools for Suno MCP."""

import asyncio
import logging
import sys
import time
from typing import Optional

from ..browser.manager import BrowserManager
from ..browser.navigator import navigate_to
from ..exceptions import SunoError
from .library_tools import clip_ids

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)

CREATE_URL = "https://suno.com/create"
CHALLENGE_WAIT_MS = 180_000
SUBMIT_WAIT_S = CHALLENGE_WAIT_MS / 1000 + 60  # time for a person to tick the check(s) + Suno to accept


class GenerateTools:
    """Tools for generating music with Suno AI (Advanced tab of suno.com/create)."""

    def __init__(self, manager: BrowserManager) -> None:
        self.manager = manager

    async def generate_track(
        self,
        prompt: str,
        style: str = "synthwave",
        lyrics: Optional[str] = None,
        duration: str = "auto",
        title: Optional[str] = None,
    ) -> str:
        """Generate a new music track using Suno AI.

        Always specify `title` (so generated tracks are identifiable in library),
        and `duration` appropriate for the intended use.
        """
        try:
            page = (await self.manager.ensure_browser())["page"]
            await navigate_to(page, CREATE_URL)
            await page.get_by_role("tab", name="Advanced", exact=True).click()

            # Placeholders rotate, so go by position: unlabeled textareas are [Style, Description].
            # Fill these first; the description box hides once the lyrics editor takes focus.
            boxes = page.locator("textarea:not([aria-label]):visible")
            await boxes.nth(0).wait_for()
            if await boxes.count() > 1:
                await boxes.nth(1).fill(prompt)
                await boxes.nth(0).fill(style)
            else:
                await boxes.nth(0).fill(f"{style}, {prompt}")

            # Real keystrokes (fill) so React state updates; clear first to drop stale drafts.
            if title:
                await page.locator('input[placeholder="Song Title (Optional)"]:visible').first.fill(title)
            if lyrics:
                await page.locator('[aria-label="Lyrics editor"]:visible').first.click()
                await page.keyboard.press("ControlOrMeta+a")
                await page.keyboard.insert_text(lyrics)

            create = page.get_by_role("button", name="Create song")
            await create.wait_for()
            if await create.is_disabled():
                raise SunoError("Create song button stayed disabled after filling the form", "GENERATE_ERROR")
            before = await clip_ids(page)
            # Click ONCE: every click starts a new Cloudflare check, so never re-press while one is pending.
            await create.click()
            if before is not None and not await self._submitted(page, set(before)):
                raise SunoError("Suno never accepted the song (Cloudflare check not passed?)", "CREATE_TIMEOUT")

            return (
                f"Track generation initiated!\n"
                f"Title: {title or '(auto)'}\n"
                f"Style: {style}\n"
                f"Duration: {duration} (not settable in the current Suno UI)\n"
                f"{'Lyrics: ' + str(len(lyrics)) + ' chars' if lyrics else 'No lyrics (Suno may auto-write them)'}\n"
                f"IMPORTANT: Wait for both tracks to appear in suno_library_list before calling generate_track again."
            )

        except SunoError:
            raise
        except Exception as e:
            logger.error("Track generation failed: %s", e)
            raise SunoError(f"Track generation failed: {e}", "GENERATE_ERROR")

    async def _submitted(self, page, before: set[str]) -> bool:
        """Wait (without clicking) until a new clip exists; a person ticks any Cloudflare check meanwhile."""
        deadline, warned = time.monotonic() + SUBMIT_WAIT_S, False
        while time.monotonic() < deadline:
            if set(await clip_ids(page) or []) - before:
                return True
            # The Turnstile iframe lives in a closed shadow root, so look at frames, not the DOM.
            if not warned and any("challenges.cloudflare.com" in f.url for f in page.frames):
                logger.warning("Cloudflare check shown — tick 'Verify you are human' in the Brave window")
                warned = True
            await asyncio.sleep(3)
        return False
