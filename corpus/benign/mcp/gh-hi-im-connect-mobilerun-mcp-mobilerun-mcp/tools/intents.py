"""system_intent verbs and contact lookup."""

from __future__ import annotations

from difflib import SequenceMatcher

from fastmcp import FastMCP

from ..errors import fail
from ..intents import VERBS, build_intent
from ..observe import mutate
from ..parsers.system import is_chooser, parse_contacts
from ..policy import check_app
from ..session import Runtime
from .apps import COLD_START_TIMEOUT, resolve_component, start_intent
from .common import Device, enforce, get_session

CONTACT_URI = "content://com.android.contacts/data/phones"


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(tags={"write"})
    async def system_intent(
        action: str | None = None,
        verb: str | None = None,
        hour: int | None = None,
        minute: int | None = None,
        seconds: int | None = None,
        label: str = "",
        phone_number: str = "",
        body: str = "",
        title: str = "",
        start: str = "",
        end: str = "",
        location: str = "",
        notes: str = "",
        text: str = "",
        subject: str = "",
        destination: str = "",
        mode: str = "drive",
        skip_ui: bool = True,
        device: Device = None,
    ) -> dict:
        """One-call Android actions (action = the verb; verb= is accepted too). Verbs: set_alarm(hour, minute, label), set_timer(seconds,
        label), dial(phone_number), compose_sms(phone_number, body), add_calendar_event(title,
        start, end, location, notes; ISO datetimes), share_text(text, subject), navigate(
        destination, mode drive|walk|bike|transit). dial/compose_sms only prefill; the user sends."""
        verb = action or verb
        if not verb:
            fail("invalid_argument", "give action", f"one of: {', '.join(VERBS)}")
        params = {
            "hour": hour,
            "minute": minute,
            "seconds": seconds,
            "label": label,
            "phone_number": phone_number,
            "body": body,
            "title": title,
            "start": start,
            "end": end,
            "location": location,
            "notes": notes,
            "text": text,
            "subject": subject,
            "destination": destination,
            "mode": mode,
            "skip_ui": skip_ui,
        }
        try:
            spec = build_intent(verb, params)
        except ValueError as exc:
            fail("invalid_argument", str(exc), f"verbs: {', '.join(VERBS)}")
        session = get_session(rt, device)
        component = await resolve_component(session, spec.args)
        if not component:
            fail(
                "unsupported",
                f"no installed app handles {verb}",
                "install an app that does, or use taps",
            )
        if not is_chooser(component):
            enforce(check_app(rt.config.policy, component.split("/")[0]))
        return await mutate(
            session,
            lambda: start_intent(session, spec.args),
            {
                "action": "system_intent",
                "verb": verb,
                "summary": spec.summary,
                "handled_by": component,
            },
            settle_timeout=COLD_START_TIMEOUT,
            expect_package=component.split("/")[0],
        )

    @mcp.tool(tags={"read"})
    async def resolve_contact(name: str, limit: int = 5, device: Device = None) -> dict:
        """Find contacts by (partial) name and return their phone numbers."""
        session = get_session(rt, device)
        raw = await session.shell(
            f"content query --uri {CONTACT_URI} --projection display_name:data1",
            timeout=60,
            check=False,
        )
        want = name.strip().lower()
        scored = []
        for contact in parse_contacts(raw):
            got = contact.name.lower()
            score = (
                1.0
                if got == want
                else 0.9
                if want in got
                else SequenceMatcher(None, want, got).ratio()
            )
            if score >= 0.6:
                scored.append((score, contact))
        scored.sort(key=lambda s: -s[0])
        return {
            "query": name,
            "matches": [{**c.to_dict(), "score": round(s, 2)} for s, c in scored[:limit]],
        }
