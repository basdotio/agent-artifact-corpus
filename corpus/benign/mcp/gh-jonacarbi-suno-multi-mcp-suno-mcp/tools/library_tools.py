"""Library and studio tools for Suno MCP — real suno.com UI automation."""

import asyncio
import json
import logging
import sys
from typing import Optional

from ..browser.manager import BrowserManager
from ..browser.navigator import navigate_to
from ..exceptions import SunoError

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)

# JS: click a button/element by matching its text content (case-insensitive).
_JS_CLICK_TEXT = """
(targetText) => {
    const candidates = [...document.querySelectorAll(
        'button, [role="menuitem"], [role="option"], li, a, div[class*="item"], div[class*="Item"]'
    )];
    const el = candidates.find(e => {
        const txt = (e.textContent || e.innerText || '').trim().toLowerCase();
        return txt === targetText.toLowerCase() && e.offsetParent !== null;
    });
    if (el) { el.click(); return el.textContent.trim(); }
    return null;
}
"""

# JS: open the "⋯" / "More Actions" context menu on a track/song page.
_JS_OPEN_MORE = """
() => {
    const buttons = [...document.querySelectorAll('button, [role="button"]')];
    // Match by aria-label or typical ellipsis text
    const moreBtn = buttons.find(b => {
        const label = (b.getAttribute('aria-label') || '').toLowerCase();
        const txt = (b.textContent || b.innerText || '').trim();
        return (
            txt === '⋯' || txt === '...' || txt === '•••' ||
            label.includes('more') || label.includes('option') || label.includes('action')
        ) && b.offsetParent !== null;
    });
    if (moreBtn) { moreBtn.click(); return 'more_opened'; }
    // Fallback: SVG icon buttons with "more"-like class names
    const svgBtns = [...document.querySelectorAll('[class*="more" i], [class*="action" i], [class*="menu" i]')]
        .filter(b => b.offsetParent !== null && (b.tagName === 'BUTTON' || b.getAttribute('role') === 'button'));
    if (svgBtns[0]) { svgBtns[0].click(); return 'svg_more_opened'; }
    return null;
}
"""

# JS: fill a textarea/input by index among visible ones; triggers React synthetic events.
_JS_FILL_BY_INDEX = """
({index, text}) => {
    const els = [...document.querySelectorAll('textarea, input[type="text"]')]
        .filter(e => e.offsetParent !== null);
    const el = els[index];
    if (!el) return null;
    el.focus();
    const proto = el.tagName === 'TEXTAREA'
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
    if (desc && desc.set) desc.set.call(el, text);
    else el.value = text;
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    return el.placeholder || ('filled-' + index);
}
"""

# JS: list recent clips via Suno's API (runs in the page, so it uses the session cookies).
_JS_FETCH_CLIPS = r"""
async (limit) => {
    try {
        // Suno's feed API wants the session JWT (the __session cookie) as a bearer token.
        const tok = (document.cookie.match(/(?:^|; )__session=([^;]+)/) || [])[1];
        if (!tok) return { source: 'no_session', clips: [] };
        const r = await fetch('https://studio-api-prod.suno.com/api/feed/v3', {
            method: 'POST',
            headers: { Authorization: 'Bearer ' + tok, 'Content-Type': 'application/json' },
            body: JSON.stringify({ cursor: null, limit, filters: { disliked: 'False', trashed: 'False' } }),
        });
        if (r.ok) {
            const data = await r.json();
            return { source: 'api', clips: data.clips || [] };
        }
        return { source: 'api_error', status: r.status, clips: [] };
    } catch(e) {
        return { source: 'fetch_error', error: String(e), clips: [] };
    }
}
"""


async def clip_ids(page, limit: int = 20) -> Optional[list[str]]:
    """Recent clip ids without navigating; None when the API is unreachable."""
    result = await page.evaluate(_JS_FETCH_CLIPS, limit)
    return [c["id"] for c in result["clips"]] if result.get("source") == "api" else None


class LibraryTools:
    """Tools for browsing and interacting with the Suno AI library."""

    def __init__(self, manager: BrowserManager) -> None:
        self.manager = manager

    async def library_list(self, limit: int = 20) -> str:
        """List tracks from the Suno AI library."""
        try:
            components = await self.manager.ensure_browser()
            page = components["page"]

            # Polling must not navigate away from /create (it would drop a pending song form).
            if not page.url.startswith("https://suno.com"):
                await navigate_to(page, "https://suno.com/me")
                await asyncio.sleep(3)

            # Try Suno internal API first (fetch runs in browser context with session cookies)
            api_result = await page.evaluate(_JS_FETCH_CLIPS, limit)

            clips = api_result.get("clips", [])
            logger.info("library_list API source=%s clips=%d", api_result.get("source"), len(clips))

            if clips:
                tracks = [
                    {
                        "id": c.get("id"),
                        "title": c.get("title") or c.get("display_name") or "Untitled",
                        "type": (c.get("metadata") or {}).get("type"),  # "preview" = free 60s teaser, not downloadable
                        "style": (c.get("metadata") or {}).get("tags", ""),
                        "duration": c.get("duration") or (c.get("metadata") or {}).get("duration"),
                        "created_at": c.get("created_at"),
                        "url": f"https://suno.com/song/{c.get('id')}",
                    }
                    for c in clips[:limit]
                ]
                return f"Library ({len(tracks)} tracks):\n```json\n{json.dumps(tracks, ensure_ascii=False, indent=2)}\n```"

            # Fallback: scrape song links from the library page DOM
            logger.info("API fallback — scraping song links from DOM")
            if not page.url.startswith("https://suno.com/me"):
                await navigate_to(page, "https://suno.com/me")
                await asyncio.sleep(3)
            tracks = await page.evaluate("""
(limit) => {
    const seen = new Set();
    const results = [];
    document.querySelectorAll('a[href*="/song/"]').forEach(a => {
        const m = a.href.match(/\/song\/([a-zA-Z0-9_-]+)/);
        if (!m || seen.has(m[1])) return;
        seen.add(m[1]);
        // Walk up to find a card container with a title element
        const card = a.closest('div[class]') || a.parentElement;
        let title = '';
        if (card) {
            const titleEl = card.querySelector('p, h1, h2, h3, h4, span[class*="title" i]');
            title = (titleEl && titleEl.textContent.trim()) || a.textContent.trim();
        }
        results.push({ id: m[1], title: title.slice(0, 80) || 'Track', url: a.href });
        if (results.length >= limit) return;
    });
    return results;
}
""", limit)

            if not tracks:
                return "No tracks found in library, or not logged in."

            return f"Library ({len(tracks)} tracks, DOM scrape):\n```json\n{json.dumps(tracks, ensure_ascii=False, indent=2)}\n```"

        except SunoError:
            raise
        except Exception as e:
            logger.error("Library list failed: %s", e)
            raise SunoError(f"Library list failed: {e}", "LIBRARY_ERROR")

    async def track_info(self, track_id: str) -> str:
        """Get detailed information about a specific track."""
        try:
            components = await self.manager.ensure_browser()
            page = components["page"]

            await navigate_to(page, f"https://suno.com/song/{track_id}")
            await asyncio.sleep(2)

            # Primary: fetch from Suno's API within the browser context (has session cookies,
            # and suno.com -> studio-api.suno.ai CORS is permitted by Suno's own SPA).
            api_data = await page.evaluate("""
async (trackId) => {
    try {
        const r = await fetch(`https://studio-api.suno.ai/api/gen/v2/${trackId}/`, {
            credentials: 'include',
            headers: { 'Referer': 'https://suno.com/' }
        });
        if (r.ok) return { source: 'api', data: await r.json() };
        return { source: 'api_error', status: r.status };
    } catch(e) {
        return { source: 'fetch_error', error: String(e) };
    }
}
""", track_id)

            logger.info("track_info API source=%s", api_data.get("source"))

            if api_data.get("source") == "api":
                raw = api_data["data"]
                meta = raw.get("metadata") or {}
                result = {
                    "track_id": track_id,
                    "url": f"https://suno.com/song/{track_id}",
                    "title": raw.get("title") or raw.get("display_name"),
                    "style": meta.get("tags") or raw.get("model_version"),
                    "duration": raw.get("duration"),
                    "prompt": (meta.get("prompt") or "")[:200],
                    "lyrics": (meta.get("lyrics") or raw.get("lyrics") or "")[:600] or None,
                    "is_public": raw.get("is_public"),
                    "model_version": raw.get("model_version"),
                }
                return f"Track Info:\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"

            # Fallback: try __NEXT_DATA__ from the song page
            next_data = await page.evaluate("""
(trackId) => {
    const el = document.getElementById('__NEXT_DATA__');
    if (!el) return null;
    try {
        const parsed = JSON.parse(el.textContent);
        const props = parsed?.props?.pageProps;
        // Next.js may have clip/song in different keys depending on version
        const clip = props?.clip || props?.song || props?.initialClip || null;
        return clip;
    } catch(e) { return null; }
}
""", track_id)

            if next_data:
                meta = next_data.get("metadata") or {}
                result = {
                    "track_id": track_id,
                    "url": f"https://suno.com/song/{track_id}",
                    "title": next_data.get("title") or next_data.get("display_name"),
                    "style": meta.get("tags"),
                    "duration": next_data.get("duration"),
                    "prompt": (meta.get("prompt") or "")[:200],
                    "lyrics": (meta.get("lyrics") or next_data.get("lyrics") or "")[:600] or None,
                    "is_public": next_data.get("is_public"),
                }
                return f"Track Info (from page data):\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"

            # Last resort: scrape visible text
            title = await page.evaluate("() => document.title")
            return (
                f"Track Info (scrape only):\n"
                f"track_id: {track_id}\n"
                f"url: https://suno.com/song/{track_id}\n"
                f"page_title: {title}\n"
                f"API status: {api_data.get('status') or api_data.get('error') or 'unknown'}\n"
                f"Note: Could not retrieve full metadata. Check login status."
            )

        except SunoError:
            raise
        except Exception as e:
            logger.error("Track info failed: %s", e)
            raise SunoError(f"Track info failed: {e}", "TRACK_INFO_ERROR")

    async def track_extend(self, track_id: str, prompt: str, duration: int = 15) -> str:
        """Extend an existing track with additional content."""
        try:
            components = await self.manager.ensure_browser()
            page = components["page"]

            await navigate_to(page, f"https://suno.com/song/{track_id}")
            await asyncio.sleep(2)

            # Open the "⋯" More Actions menu via JS
            more_result = await page.evaluate(_JS_OPEN_MORE)
            logger.info("track_extend more menu: %s", more_result)
            if not more_result:
                raise SunoError("Could not open More Actions menu", "EXTEND_MENU_NOT_FOUND")

            await asyncio.sleep(0.8)

            # Click "Edit" submenu if present
            edit_clicked = await page.evaluate(_JS_CLICK_TEXT, "Edit")
            logger.info("track_extend edit clicked: %s", edit_clicked)
            if edit_clicked:
                await asyncio.sleep(0.5)

            # Click "Extend"
            extend_clicked = await page.evaluate(_JS_CLICK_TEXT, "Extend")
            if not extend_clicked:
                # Try partial match
                extend_clicked = await page.evaluate("""
() => {
    const el = [...document.querySelectorAll('button, [role="menuitem"], li, a')]
        .find(e => e.textContent.trim().toLowerCase().includes('extend') && e.offsetParent);
    if (el) { el.click(); return el.textContent.trim(); }
    return null;
}
""")
            logger.info("track_extend extend clicked: %s", extend_clicked)
            if not extend_clicked:
                raise SunoError("Extend option not found in menu", "EXTEND_NOT_FOUND")

            await asyncio.sleep(1.5)

            # Fill the extend prompt (first visible textarea after dialog opens)
            filled = await page.evaluate(
                _JS_FILL_BY_INDEX,
                {"index": 0, "text": prompt},
            )
            if not filled:
                raise SunoError("Extend prompt field not found", "EXTEND_PROMPT_NOT_FOUND")
            logger.info("Extend prompt filled: %s", filled)

            await asyncio.sleep(0.3)

            # Submit — look for "Extend", "Create", "Generate" button
            submitted = await page.evaluate("""
(keywords) => {
    const buttons = [...document.querySelectorAll('button')];
    for (const btn of buttons) {
        const txt = (btn.textContent || '').trim().toLowerCase();
        if (keywords.some(k => txt.includes(k)) && btn.offsetParent) {
            btn.click();
            return txt;
        }
    }
    return null;
}
""", ["extend", "create", "generate"])
            if not submitted:
                raise SunoError("Extend submit button not found", "EXTEND_SUBMIT_NOT_FOUND")

            await asyncio.sleep(2)
            return (
                f"Track extension initiated!\n"
                f"Track ID: {track_id}\n"
                f"Prompt: \"{prompt}\"\n"
                f"Duration: {duration}s\n"
                f"Check suno_library_list for the new extended track."
            )

        except SunoError:
            raise
        except Exception as e:
            logger.error("Track extend failed: %s", e)
            raise SunoError(f"Track extend failed: {e}", "EXTEND_ERROR")

    async def track_remix(self, track_id: str, prompt: str, style: str = "") -> str:
        """Remix/cover an existing track with a new prompt."""
        try:
            components = await self.manager.ensure_browser()
            page = components["page"]

            await navigate_to(page, f"https://suno.com/song/{track_id}")
            await asyncio.sleep(2)

            # Open the "⋯" More Actions menu
            more_result = await page.evaluate(_JS_OPEN_MORE)
            logger.info("track_remix more menu: %s", more_result)
            if not more_result:
                raise SunoError("Could not open More Actions menu", "REMIX_MENU_NOT_FOUND")

            await asyncio.sleep(0.8)

            # Click "Edit" submenu if present
            edit_clicked = await page.evaluate(_JS_CLICK_TEXT, "Edit")
            logger.info("track_remix edit clicked: %s", edit_clicked)
            if edit_clicked:
                await asyncio.sleep(0.5)

            # Click "Remix" or "Cover" (whichever is available)
            remix_clicked = await page.evaluate("""
() => {
    const candidates = ['Remix', 'Cover', 'Reuse Prompt'];
    for (const name of candidates) {
        const el = [...document.querySelectorAll('button, [role="menuitem"], li, a')]
            .find(e => e.textContent.trim() === name && e.offsetParent);
        if (el) { el.click(); return el.textContent.trim(); }
    }
    // Partial match fallback
    const el = [...document.querySelectorAll('button, [role="menuitem"], li, a')]
        .find(e => e.textContent.trim().toLowerCase().includes('remix') && e.offsetParent);
    if (el) { el.click(); return el.textContent.trim(); }
    return null;
}
""")
            logger.info("track_remix remix clicked: %s", remix_clicked)
            if not remix_clicked:
                raise SunoError("Remix/Cover option not found in menu", "REMIX_NOT_FOUND")

            await asyncio.sleep(1.5)

            # Fill remix prompt (first visible textarea in dialog)
            filled = await page.evaluate(
                _JS_FILL_BY_INDEX,
                {"index": 0, "text": prompt},
            )
            if not filled:
                raise SunoError("Remix prompt field not found", "REMIX_PROMPT_NOT_FOUND")

            # Fill style if provided (second visible textarea or input)
            if style:
                style_filled = await page.evaluate(
                    _JS_FILL_BY_INDEX,
                    {"index": 1, "text": style},
                )
                logger.info("Remix style fill: %s", style_filled)

            await asyncio.sleep(0.3)

            # Submit
            submitted = await page.evaluate("""
(keywords) => {
    const buttons = [...document.querySelectorAll('button')];
    for (const btn of buttons) {
        const txt = (btn.textContent || '').trim().toLowerCase();
        if (keywords.some(k => txt.includes(k)) && btn.offsetParent) {
            btn.click();
            return txt;
        }
    }
    return null;
}
""", ["remix", "create", "generate", "cover"])
            if not submitted:
                raise SunoError("Remix submit button not found", "REMIX_SUBMIT_NOT_FOUND")

            await asyncio.sleep(2)
            return (
                f"Track remix initiated!\n"
                f"Original Track ID: {track_id}\n"
                f"Remix type: {remix_clicked}\n"
                f"Prompt: \"{prompt}\"\n"
                f"{f'Style: {style}' if style else ''}\n"
                f"Check suno_library_list for the new remix."
            )

        except SunoError:
            raise
        except Exception as e:
            logger.error("Track remix failed: %s", e)
            raise SunoError(f"Track remix failed: {e}", "REMIX_ERROR")
