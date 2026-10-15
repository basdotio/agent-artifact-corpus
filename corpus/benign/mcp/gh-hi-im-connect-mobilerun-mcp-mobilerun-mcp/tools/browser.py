"""Browser tools: CDP into the on-device browser (WebView Browser Tester) or an in-app WebView."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from ..browser import js
from ..browser.cdp import CdpError
from ..browser.manager import SHELL_ACTIVITY, SHELL_PACKAGE, Attached, BrowserManager
from ..browser.navigation import navigate
from ..errors import fail
from ..parsers.system import parse_content_rows
from ..policy import check_text
from ..session import DeviceSession, Runtime
from ..shell import q
from .common import Device, enforce, get_session

KEYS = {
    "Enter": (13, "Enter", "\r"),
    "Tab": (9, "Tab", ""),
    "Escape": (27, "Escape", ""),
    "Backspace": (8, "Backspace", ""),
    "ArrowDown": (40, "ArrowDown", ""),
    "ArrowUp": (38, "ArrowUp", ""),
    "ArrowLeft": (37, "ArrowLeft", ""),
    "ArrowRight": (39, "ArrowRight", ""),
    "Space": (32, "Space", " "),
}
ACTIONS = (
    "click",
    "type",
    "select",
    "submit",
    "scroll_down",
    "scroll_up",
    "back",
    "press",
    "focus",
    "hover",
    "check",
    "uncheck",
    "scroll",
    "scroll_into_view",
)
SCRATCH, MINE = "scratch", "mine"
SIGNED_IN_BROWSERS = (
    "com.android.chrome",
    "com.chrome.beta",
    "com.brave.browser",
    "com.microsoft.emmx",
    "com.sec.android.app.sbrowser",
)
TEXT_CAP, ELEMENT_CAP = 4000, 60
FIND_SCROLLS = 3
DEVICE_DOWNLOADS = "/sdcard/Download"
PAGE_TIMEOUT = 15.0


def manager(session: DeviceSession) -> BrowserManager:
    if session.browser is None:
        session.browser = BrowserManager(session)
    return session.browser


def normalize_url(url: str) -> str:
    if url.startswith(("http://", "https://", "about:", "data:", "file:", "javascript:")):
        return url
    return "https://" + url


def host_file(path: str) -> Path:
    p = Path(path).expanduser()
    if any(part.startswith(".") for part in p.parts[1:]) or not p.is_file():
        fail("not_permitted", f"{path} is not a readable regular file outside hidden directories")
    return p


async def bring_to_front(dev: DeviceSession, attached: Attached) -> None:
    """A backgrounded WebView renders no frames (screenshots hang), so foreground its app."""
    package = attached.target.package
    screen = await dev.capture()
    if screen.phone.package == package:
        return
    if package == SHELL_PACKAGE:
        await dev.shell(f"am start -n {SHELL_ACTIVITY}")
    else:
        await dev.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1", check=False)
    for _ in range(20):
        await asyncio.sleep(0.4)
        if (await dev.capture()).phone.package == package:
            await nudge_accessibility(attached)
            return


async def nudge_accessibility(attached: Attached) -> None:
    """A WebView that loaded while hidden exposes an empty accessibility tree once shown, until
    something fires an accessibility event: a short-lived DOM node plus a 1px scroll do that."""
    await asyncio.sleep(0.3)
    try:
        await attached.client.evaluate(
            "(() => { const n = document.createElement('div'); n.textContent = '\\u200b';"
            " n.setAttribute('aria-hidden', 'true'); (document.body || document.documentElement)"
            ".appendChild(n); window.scrollBy(0, 1);"
            " setTimeout(() => { n.remove(); window.scrollBy(0, -1); }, 150); return true; })()"
        )
    except CdpError:
        pass


async def page_info(client) -> dict:
    return await client.evaluate(js.SNAPSHOT)


def session_name(name: str | None) -> str:
    """AURA names: scratch (default, the server's own browser) and mine (the user's browser)."""
    return SCRATCH if name in (None, "", "default") else name


async def page_result(
    mgr: BrowserManager, name: str, attached: Attached, max_text_chars: int, max_elements: int
) -> dict:
    """AURA's page result: text, numbered elements (el_id) and a generation that changes
    whenever the page does, so stale el_ids are caught."""
    text = await run_js(attached, js.page_text(None, max(1, int(max_text_chars))))
    raw = await run_js(attached, js.interactives(max(1, int(max_elements))))
    elements = []
    for e in raw or []:
        ref = str(e.pop("ref", ""))
        elements.append({"el_id": int(ref[1:]) if ref[1:].isdigit() else ref, **e})
    text = text or {"title": "", "url": "", "text": "", "length": 0}
    sig = hash((text.get("url"), tuple((e["el_id"], e.get("text")) for e in elements)))
    last = mgr.generations.get(name)
    gen = last[1] if last and last[0] == sig else (last[1] + 1 if last else 1)
    mgr.generations[name] = (sig, gen)
    return {
        "session": name,
        "title": text.get("title"),
        "url": text.get("url"),
        "text": text.get("text", ""),
        "truncated": text.get("length", 0) > len(text.get("text", "")),
        "elements": elements,
        "element_count": len(elements),
        "generation": gen,
    }


def element_ref(el_id: int | str | None, ref: str | None) -> str | None:
    if el_id is not None:
        return el_id if isinstance(el_id, str) and el_id.startswith("e") else f"e{int(el_id)}"
    return ref


async def run_js(attached: Attached, expression: str, **kwargs):
    try:
        return await attached.client.evaluate(expression, **kwargs)
    except CdpError as exc:
        fail("unsupported", str(exc), "is the page still open? call browser_tabs")


def register(mcp: FastMCP, rt: Runtime) -> None:
    async def attach(device: Device, name: str | None, **kw) -> tuple[DeviceSession, Attached]:
        session = get_session(rt, device)
        await session.ensure_connected()
        name = session_name(name)
        mgr = manager(session)
        if name == MINE and not kw.get("app") and not kw.get("target_id"):
            cached = mgr._attached.get(MINE)
            if cached is None or cached.client.closed:
                present = {t.package for t in await mgr.targets()}
                app = next((b for b in SIGNED_IN_BROWSERS if b in present), None)
                if app is None:
                    installed = {a.package for a in await session.apps()}
                    app = next((b for b in SIGNED_IN_BROWSERS if b in installed), None)
                    if app is None:
                        fail(
                            "unsupported",
                            "no signed-in browser (Chrome, Brave, Edge, Samsung) is installed",
                            'use session="scratch"',
                        )
                    await session.shell(
                        f"monkey -p {app} -c android.intent.category.LAUNCHER 1", check=False
                    )
                    await asyncio.sleep(2.0)
                kw["app"] = app
        try:
            return session, await mgr.attach(name, **kw)
        except CdpError as exc:
            fail("device_unreachable", str(exc))

    async def page(
        dev: DeviceSession,
        name: str | None,
        attached: Attached,
        max_text_chars: int,
        max_elements: int,
    ) -> dict:
        return await page_result(
            manager(dev), session_name(name), attached, max_text_chars, max_elements
        )

    async def check_generation(dev, name, attached, generation, caps) -> dict | None:
        if generation is None:
            return None
        current = await page(dev, name, attached, *caps)
        if current["generation"] != int(generation):
            return {
                "ok": False,
                "stale_handles": True,
                "message": "the page changed since that generation; use the el_ids below",
                **current,
            }
        return None

    @mcp.tool(tags={"write"})
    async def browser_open(
        url: str | None = None,
        background: bool = False,
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        target_id: str | None = None,
        app: str | None = None,
        wait: bool = True,
        timeout: float = PAGE_TIMEOUT,
        device: Device = None,
    ) -> dict:
        """Open a web page; returns its text plus numbered elements (el_id) and a generation.
        session: scratch (default, this server's on-device browser, signed into nothing) |
        mine (the user's own signed-in browser, e.g. Chrome) | any name. The browser is brought
        to the front unless background=true. target_id / app attach to an existing page or an
        in-app WebView instead."""
        dev, attached = await attach(device, session, target_id=target_id, app=app)
        if url:
            try:
                await navigate(attached.client, normalize_url(url), timeout, wait)
            except CdpError as exc:
                fail("unsupported", str(exc), "check the URL and the device's network")
        if not background:
            await bring_to_front(dev, attached)
            await nudge_accessibility(attached)
        result = await page(dev, session, attached, max_text_chars, max_elements)
        ready = (await page_info(attached.client)).get("ready")
        return {"ok": True, "app": attached.target.package, "ready": ready, **result}

    @mcp.tool(tags={"write"})
    async def browser_tabs(
        action: str = "list",
        url: str | None = None,
        index: int | None = None,
        session: str = SCRATCH,
        device: Device = None,
    ) -> dict:
        """Several pages at once. action: list (default) | open (url; keeps the current page) |
        switch (index, makes it the active tab) | close (index). Other browser tools act on the
        active tab. The scratch browser has one real page, so its extra tabs are remembered URLs
        that reload on switch (reloaded=true); signed-in browsers keep real tabs."""
        if action not in ("list", "open", "switch", "close"):
            fail("invalid_argument", "action must be list, open, switch or close")
        dev, attached = await attach(device, session)
        mgr = manager(dev)
        name = session_name(session)
        port = attached.port
        package = attached.target.package
        pages = [t for t in await mgr.targets() if t.package == package]
        virtual = mgr.tabs.setdefault(name, [])
        real = package != SHELL_PACKAGE
        listing = (
            [t.to_dict() for t in pages]
            if real
            else [{"url": attached.target.url, "active": True}]
            + [{"url": u, "active": False} for u in virtual]
        )
        if action == "list":
            return {
                "session": name,
                "count": len(listing),
                "tabs": listing,
                "all_pages": [t.to_dict() for t in await mgr.targets()],
                "sessions": mgr.sessions(),
            }
        if action == "open":
            if not url:
                fail("invalid_argument", "open needs url")
            if real:
                resp = await mgr._http.put(f"http://127.0.0.1:{port}/json/new?{normalize_url(url)}")
                if resp.status_code >= 400:
                    fail("unsupported", f"{package} refused a new tab ({resp.status_code})")
                new_id = resp.json().get("id")
                attached = await mgr.attach(name, target_id=new_id)
            else:
                info = await page_info(attached.client)
                virtual.insert(0, info.get("url", ""))
                await navigate(attached.client, normalize_url(url), PAGE_TIMEOUT, True)
            return {"ok": True, **await page(dev, session, attached, TEXT_CAP, ELEMENT_CAP)}
        if index is None or not 0 <= index < len(listing):
            fail("invalid_argument", f"index must be 0..{len(listing) - 1}")
        if real:
            chosen = pages[index]
            if action == "close":
                await mgr._http.get(f"http://127.0.0.1:{port}/json/close/{chosen.id}")
                return {"ok": True, "closed": chosen.to_dict()}
            await mgr._http.get(f"http://127.0.0.1:{port}/json/activate/{chosen.id}")
            attached = await mgr.attach(name, target_id=chosen.id)
            return {
                "ok": True,
                "reloaded": False,
                **await page(dev, session, attached, TEXT_CAP, ELEMENT_CAP),
            }
        if index == 0:
            if action == "close":
                fail(
                    "invalid_argument", "the active scratch tab cannot be closed; use browser_close"
                )
            return {
                "ok": True,
                "reloaded": False,
                **await page(dev, session, attached, TEXT_CAP, ELEMENT_CAP),
            }
        target_url = virtual.pop(index - 1)
        if action == "close":
            return {"ok": True, "closed": {"url": target_url}}
        info = await page_info(attached.client)
        virtual.insert(0, info.get("url", ""))
        await navigate(attached.client, target_url, PAGE_TIMEOUT, True)
        return {
            "ok": True,
            "reloaded": True,
            **await page(dev, session, attached, TEXT_CAP, ELEMENT_CAP),
        }

    @mcp.tool(tags={"write"})
    async def browser_close(
        session: str = SCRATCH, close_app: bool = False, device: Device = None
    ) -> dict:
        """Close a browser session and free it (the page is blanked); close_app also stops the app."""
        dev = get_session(rt, device)
        mgr = manager(dev)
        name = session_name(session)
        cached = mgr._attached.get(name)
        package = cached.target.package if cached else None
        if cached and not cached.client.closed and package == SHELL_PACKAGE:
            try:
                await cached.client.send("Page.navigate", {"url": "about:blank"}, timeout=5)
            except CdpError:
                pass
        detached = await mgr.detach(name)
        mgr.tabs.pop(name, None)
        mgr.generations.pop(name, None)
        if close_app and package:
            await dev.shell(f"am force-stop {package}")
        return {"ok": True, "detached": detached, "closed_app": bool(close_app and package)}

    @mcp.tool(tags={"read"})
    async def browser_screenshot(
        session: str = SCRATCH,
        full_page: bool = False,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        device: Device = None,
    ) -> Image:
        """A picture of the open page, for what text cannot tell (charts, maps, images, popups).
        The browser is brought to the front first (a hidden page cannot render)."""
        dev, attached = await attach(device, session)
        await bring_to_front(dev, attached)
        params = {"format": "png", "captureBeyondViewport": full_page}
        try:
            result = await attached.client.send("Page.captureScreenshot", params, timeout=20)
        except CdpError as exc:
            fail("unsupported", str(exc))
        finally:
            if full_page:
                # captureBeyondViewport resizes the view; WebView keeps its accessibility tree
                # collapsed afterwards unless the override is cleared explicitly.
                try:
                    await attached.client.send(
                        "Emulation.clearDeviceMetricsOverride", {}, timeout=5
                    )
                except CdpError:
                    pass
        import base64

        return Image(data=base64.b64decode(result["data"]), format="png")

    @mcp.tool(tags={"read"})
    async def browser_read(
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        selector: str | None = None,
        max_chars: int | None = None,
        structure: bool = True,
        device: Device = None,
    ) -> dict:
        """Re-read the open page without navigating: text, numbered elements (el_id) and the
        generation. Call after anything that may have changed the page. selector limits the
        text to one element."""
        dev, attached = await attach(device, session)
        cap = max_chars or max_text_chars
        result = await page(dev, session, attached, cap, max_elements if structure else 1)
        if selector:
            data = await run_js(attached, js.page_text(selector, cap))
            if data is None:
                fail("element_not_found", f"no element matches {selector!r}")
            result.update(text=data["text"], truncated=data["length"] > len(data["text"]))
        if not structure:
            result.pop("elements")
        return result

    @mcp.tool(tags={"read"})
    async def browser_find(
        text: str | None = None,
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        query: str | None = None,
        limit: int = 10,
        device: Device = None,
    ) -> dict:
        """Find something on the page by its text; returns matches with el_id plus the page.
        Scrolls (infinite lists) only when the text is not loaded yet. found=true without an
        el_id on a match means the text is there but not interactive."""
        wanted = text or query
        if not wanted:
            fail("invalid_argument", "give text")
        dev, attached = await attach(device, session)
        matches: list = []
        for attempt in range(FIND_SCROLLS + 1):
            matches = await run_js(attached, js.find(wanted, min(max(limit, 1), 50)))
            if matches or attempt == FIND_SCROLLS:
                break
            await run_js(attached, "window.scrollBy(0, Math.round(window.innerHeight * 0.9))")
            await asyncio.sleep(0.6)
        result = await page(dev, session, attached, max_text_chars, max_elements)
        interactive = {e["el_id"] for e in result["elements"]}
        for m in matches:
            ref = str(m.pop("ref", ""))
            el_id = int(ref[1:]) if ref[1:].isdigit() else None
            if el_id in interactive or m.get("tag") in (
                "a",
                "button",
                "input",
                "select",
                "textarea",
            ):
                m["el_id"] = el_id
        first = next((m.get("el_id") for m in matches if m.get("el_id") is not None), None)
        return {
            "query": wanted,
            "found": bool(matches),
            "el_id": first,
            "count": len(matches),
            "matches": matches,
            **result,
        }

    @mcp.tool(tags={"read"})
    async def browser_wait(
        text: str | None = None,
        timeout_ms: int | None = None,
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        selector: str | None = None,
        url_contains: str | None = None,
        timeout: float | None = None,
        device: Device = None,
    ) -> dict:
        """Wait for text to appear on the page (or, without text, for it to settle), then return
        the page. timeout_ms 500-30000 (default 10000). selector / url_contains also wait."""
        dev, attached = await attach(device, session)
        limit = (
            min(max(timeout_ms, 500), 30000) / 1000
            if timeout_ms is not None
            else min(timeout, 120.0)
            if timeout is not None
            else 10.0
        )
        condition = js.wait_condition(text, selector, url_contains)
        started = time.monotonic()
        ok = False
        while time.monotonic() - started < limit:
            try:
                if await attached.client.evaluate(condition):
                    ok = True
                    break
            except CdpError:
                pass
            await asyncio.sleep(0.4)
        result = await page(dev, session, attached, max_text_chars, max_elements)
        return {
            "ok": ok,
            "timed_out": not ok,
            "elapsed": round(time.monotonic() - started, 2),
            **result,
        }

    @mcp.tool(tags={"read"})
    async def browser_extract(
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        kind: str = "items",
        selector: str | None = None,
        limit: int | None = None,
        device: Device = None,
    ) -> dict:
        """Pull repeated items off the page (search results, product cards, listings) as rows of
        text + link in one call, with the total found. kind: items (default) | table | links |
        text."""
        if kind not in ("items", "table", "links", "text"):
            fail("invalid_argument", "kind must be items, table, links or text")
        _, attached = await attach(device, session)
        cap = limit or max_elements
        if kind == "items":
            data = await run_js(attached, js.items(cap))
            info = await page_info(attached.client)
            return {
                "kind": kind,
                "url": info.get("url"),
                "total": data["total"],
                "count": len(data["items"]),
                "items": data["items"],
            }
        if kind == "text":
            data = await run_js(attached, js.page_text(selector, max(max_text_chars, 1)))
        else:
            builder = js.tables if kind == "table" else js.links
            data = await run_js(attached, builder(selector, min(max(cap, 1), 200)))
        if data is None:
            fail("element_not_found", f"no element matches {selector!r}")
        return {"kind": kind, "data": data}

    async def press_key(attached: Attached, key: str) -> None:
        if key not in KEYS:
            fail("invalid_argument", f"key must be one of {', '.join(KEYS)}")
        code, name, text = KEYS[key]
        base = {
            "key": key,
            "code": name,
            "windowsVirtualKeyCode": code,
            "nativeVirtualKeyCode": code,
        }
        await attached.client.send(
            "Input.dispatchKeyEvent",
            {**base, "type": "keyDown", **({"text": text} if text else {})},
        )
        await attached.client.send("Input.dispatchKeyEvent", {**base, "type": "keyUp"})

    @mcp.tool(tags={"write"})
    async def browser_act(
        action: str,
        el_id: int | None = None,
        value: str | None = None,
        generation: int | None = None,
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        ref: str | None = None,
        selector: str | None = None,
        text: str | None = None,
        key: str | None = None,
        clear: bool = False,
        submit: bool = False,
        amount: int = 600,
        device: Device = None,
    ) -> dict:
        """Act on the page and get the page back. Element actions (el_id from the latest page
        result, or ref / selector): click, type (value), select (value), submit, focus, hover,
        check, uncheck, scroll_into_view. Page actions: scroll_down, scroll_up, back,
        scroll (amount px), press (key: Enter, Tab, Escape, ...). Pass the generation your el_id
        came from: if the page changed you get stale_handles and the fresh page instead."""
        if action not in ACTIONS:
            fail("invalid_argument", f"action must be one of {', '.join(ACTIONS)}")
        dev, attached = await attach(device, session)
        caps = (max_text_chars, max_elements)
        stale = await check_generation(dev, session, attached, generation, caps)
        if stale:
            return stale
        client = attached.client
        ref = element_ref(el_id, ref)

        async def after(extra: dict) -> dict:
            await asyncio.sleep(0.3)
            return {
                "ok": True,
                "action": action,
                **extra,
                **await page(dev, session, attached, *caps),
            }

        if action in ("scroll", "scroll_down", "scroll_up"):
            delta = {
                "scroll_down": "Math.round(window.innerHeight * 0.8)",
                "scroll_up": "-Math.round(window.innerHeight * 0.8)",
            }.get(action, str(int(amount)))
            await run_js(attached, f"window.scrollBy(0, {delta})")
            return await after({})
        if action == "back":
            await run_js(attached, "history.back()")
            await asyncio.sleep(0.8)
            return await after({})
        if action == "press":
            if not key:
                fail("invalid_argument", "press needs key")
            await press_key(attached, key)
            return await after({"key": key})
        if not ref and not selector:
            fail("invalid_argument", f"{action} needs el_id")
        if action == "type":
            typed = value if value is not None else text
            if typed is None:
                fail("invalid_argument", "type needs value")
            prep = await run_js(attached, js.act("prepare_type", ref, selector, None, clear))
            if prep.get("error"):
                fail("element_not_found", prep["error"], "call browser_read for current el_ids")
            enforce(
                check_text(
                    rt.config.policy, typed, prep.get("hint", ""), prep.get("type") == "password"
                )
            )
            await client.send("Input.insertText", {"text": typed})
            if submit:
                await press_key(attached, "Enter")
            return await after({"chars": len(typed)})
        js_action = "check" if action in ("check", "uncheck") else action
        val = "false" if action == "uncheck" else value
        result = await run_js(attached, js.act(js_action, ref, selector, val))
        if result.get("error"):
            fail(
                "element_not_found",
                result["error"],
                "el_ids go stale after navigation; call browser_read",
            )
        return await after({k: v for k, v in result.items() if k != "ok"})

    @mcp.tool(tags={"write"})
    async def browser_handoff(
        prompt: str | None = None,
        check: bool = False,
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        message: str = "",
        device: Device = None,
    ) -> dict:
        """Let the person do a step you cannot (sign in, one-time code, CAPTCHA, payment
        confirmation): brings the page to the front and posts prompt as a device notification.
        Never ask for passwords. Call again with check=true to get the page as they left it."""
        dev, attached = await attach(device, session)
        name = session_name(session)
        mgr = manager(dev)
        if check:
            pending = mgr.handoffs.get(name)
            result = await page(dev, session, attached, max_text_chars, max_elements)
            return {
                "handoff": pending or None,
                "foreground": (await dev.capture()).phone.package,
                **result,
            }
        text = prompt or message or "Please finish this step in the browser"
        mgr.handoffs[name] = {"prompt": text, "started_url": attached.target.url, "at": time.time()}
        await bring_to_front(dev, attached)
        if dev.has_adb:
            await dev.shell(
                f"cmd notification post -S bigtext -t {q('Your turn')} mobilerun_handoff {q(text)}",
                check=False,
            )
        return {
            "ok": True,
            "prompt": text,
            "foreground": (await dev.capture()).phone.package,
            "next": "call browser_handoff(check=true) to see the page once the person is done",
        }

    @mcp.tool(tags={"write"})
    async def browser_upload(
        el_id: int | None = None,
        file: str | None = None,
        generation: int | None = None,
        session: str = SCRATCH,
        max_text_chars: int = TEXT_CAP,
        max_elements: int = ELEMENT_CAP,
        path: str | None = None,
        ref: str | None = None,
        selector: str | None = None,
        device: Device = None,
    ) -> dict:
        """Attach a file to an upload control (el_id). file: a content:// URI or path from
        find_files, a device path under /sdcard, or a host file (pushed to /sdcard/Download).
        Returns the page afterwards so you can confirm the file name appeared."""
        source = file or path
        ref = element_ref(el_id, ref)
        if not source:
            fail("invalid_argument", "give file")
        if not ref and not selector:
            fail("invalid_argument", "give the el_id of the file input")
        dev, attached = await attach(device, session)
        caps = (max_text_chars, max_elements)
        stale = await check_generation(dev, session, attached, generation, caps)
        if stale:
            return stale
        from .files import safe_path

        if source.startswith("content://"):
            rows = parse_content_rows(
                await dev.shell(f"content query --uri {q(source)} --projection _data", check=False),
                ("_data",),
            )
            if not rows or not rows[0].get("_data"):
                fail("element_not_found", f"{source} has no file path", "use find_files")
            device_path = rows[0]["_data"]
        elif source.startswith(("/sdcard/", "/storage/")):
            device_path = safe_path(source)
        else:
            local = host_file(source)
            device_path = f"{DEVICE_DOWNLOADS}/{local.name}"
            await dev.require_adb("uploading a host file").push(str(local), device_path)
        client = attached.client
        try:
            evaluated = await client.send(
                "Runtime.evaluate",
                {"expression": js.file_input(ref, selector), "returnByValue": False},
            )
            object_id = (evaluated.get("result") or {}).get("objectId")
            if not object_id:
                fail("element_not_found", "file input not found")
            node = await client.send("DOM.describeNode", {"objectId": object_id})
            await client.send(
                "DOM.setFileInputFiles",
                {"files": [device_path], "backendNodeId": node["node"]["backendNodeId"]},
            )
        except CdpError as exc:
            fail("unsupported", str(exc))
        await asyncio.sleep(0.3)
        return {"ok": True, "device_path": device_path, **await page(dev, session, attached, *caps)}
