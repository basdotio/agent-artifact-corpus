"""Calendar MCP server (workflow 5): the date and time, your events, and adding new ones.

No account login: calendars are iCalendar (.ics) data, which every calendar app can export or
publish.
  - Files in the shared folder's calendar/ (E:\\ai-files\\calendar): drop exports there.
  - Feeds in ICS_URLS (optional, Secret agent/calendar-feeds): e.g. Google Calendar's "secret
    address in iCal format" or an Outlook published calendar, read-only, cached for 5 minutes.
  - Events the agent adds go to calendar/agent.ics, so they show up in the same place.

    now()                         today's date and the time (CALENDAR_TZ)
    list_events(when, days)       events from that day for N days ("today", "friday", "2026-10-12")
    add_event(title, start, ...)  a new event ("tomorrow 3pm", "2026-10-12 09:30")
Plain HTTP for n8n's daily briefing: GET /events?days=1 -> {"text": ..., "events": [...]}.
Served over MCP streamable HTTP at http://<host>:8000/mcp, like the other MCP servers.
"""

import os
import re
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import dateparser
import httpx
import recurring_ical_events
from icalendar import Calendar, Event
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

TZ = ZoneInfo(os.environ.get("CALENDAR_TZ", "Asia/Dubai"))
CAL_DIR = Path(os.environ.get("CALENDAR_DIR", "/data/calendar"))
OWN = CAL_DIR / "agent.ics"  # where add_event writes
ICS_URLS = [u for u in re.split(r"[\s,]+", os.environ.get("ICS_URLS", "")) if u]
FEED_TTL = 300
MAX_DAYS = 31

mcp = FastMCP(
    "calendar",
    instructions="The current date and time, the user's calendar events, and adding events.",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8000")),
    stateless_http=True,
)
_feeds: dict[str, tuple[float, bytes]] = {}


def now() -> datetime:
    return datetime.now(TZ)


def parse_when(text: str, base: datetime | None = None) -> datetime | None:
    """"today", "tomorrow 3pm", "friday", "next monday 9:30", "2026-10-12 14:00" -> aware datetime."""
    base = base or now()
    text = text.strip().lower()
    if text in ("", "now", "today"):
        return base
    if text in ("this week", "week"):
        return base
    if text == "next week":
        return base + timedelta(days=7 - base.weekday())
    weekday = re.fullmatch(r"(?:on |this |next )?(mon|tue|wed|thu|fri|sat|sun)[a-z]*(.*)", text)
    if weekday:  # dateparser reads a bare weekday as the past one; here it means the next one
        target = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(weekday.group(1))
        ahead = (target - base.weekday()) % 7 or (7 if text.startswith("next") else 0)
        day = base + timedelta(days=ahead)
        rest = weekday.group(2).strip(" ,at")
        if not rest:
            return day
        t = dateparser.parse(rest, settings={"RELATIVE_BASE": base.replace(tzinfo=None)})
        return day.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0) if t else day
    parsed = dateparser.parse(
        text,
        settings={"RELATIVE_BASE": base.replace(tzinfo=None), "PREFER_DATES_FROM": "future",
                  "TIMEZONE": str(TZ), "RETURN_AS_TIMEZONE_AWARE": True},
    )
    return parsed.astimezone(TZ) if parsed else None


def calendars() -> list[tuple[str, Calendar]]:
    """Every calendar: the .ics files in CAL_DIR, then the feeds."""
    out = []
    for f in sorted(CAL_DIR.glob("*.ics")) if CAL_DIR.is_dir() else []:
        try:
            out.append((f.stem, Calendar.from_ical(f.read_bytes())))
        except Exception:
            continue  # one broken export shouldn't hide the others
    for url in ICS_URLS:
        cached = _feeds.get(url)
        if not cached or time.time() - cached[0] > FEED_TTL:
            try:
                r = httpx.get(url, timeout=15, follow_redirects=True)
                r.raise_for_status()
                _feeds[url] = cached = (time.time(), r.content)
            except httpx.HTTPError:
                if not cached:
                    continue
        try:
            out.append(("feed", Calendar.from_ical(cached[1])))
        except Exception:
            continue
    return out


def as_dt(value) -> tuple[datetime, bool]:
    """An event's DTSTART/DTEND as an aware datetime, and whether it was an all-day date."""
    if isinstance(value, datetime):
        return (value.replace(tzinfo=TZ) if value.tzinfo is None else value).astimezone(TZ), False
    return datetime(value.year, value.month, value.day, tzinfo=TZ), True


def events_between(start: datetime, end: datetime) -> list[dict]:
    found = []
    for name, cal in calendars():
        for ev in recurring_ical_events.of(cal).between(start, end):
            s, all_day = as_dt(ev.get("DTSTART").dt)
            e = as_dt(ev.get("DTEND").dt)[0] if ev.get("DTEND") else s + (timedelta(days=1) if all_day else timedelta(hours=1))
            found.append({"title": str(ev.get("SUMMARY", "(no title)")), "start": s.isoformat(), "end": e.isoformat(),
                          "all_day": all_day, "location": str(ev.get("LOCATION", "")), "calendar": name})
    return sorted(found, key=lambda x: (x["start"], x["title"]))


def describe(ev: dict) -> str:
    s, e = datetime.fromisoformat(ev["start"]), datetime.fromisoformat(ev["end"])
    when = f"{s:%a %d %b}, all day" if ev["all_day"] else f"{s:%a %d %b %H:%M}-{e:%H:%M}"
    return f"- {when}: {ev['title']}" + (f" @ {ev['location']}" if ev["location"] else "")


def day_range(when: str, days: int) -> tuple[datetime, datetime]:
    start = parse_when(when) or now()
    if when.strip().lower() in ("this week", "week", "next week") and days == 1:
        days = 7
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=max(1, min(days, MAX_DAYS)))


def listing(when: str = "today", days: int = 1) -> tuple[str, list[dict]]:
    start, end = day_range(when, days)
    evs = events_between(start, end)
    span = f"{start:%A %d %B %Y}" + (f" to {end - timedelta(days=1):%A %d %B}" if end - start > timedelta(days=1) else "")
    if not evs:
        return f"No events {span}.", evs
    return f"Events {span}:\n" + "\n".join(describe(e) for e in evs), evs


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


@mcp.custom_route("/events", methods=["GET"])
async def events_http(request: Request) -> JSONResponse:
    text, evs = listing(request.query_params.get("when", "today"), int(request.query_params.get("days", "1")))
    return JSONResponse({"text": text, "events": evs})


@mcp.tool(name="now")
def now_tool() -> str:
    """Today's date, the day of the week and the current time."""
    n = now()
    return f"{n:%A %d %B %Y, %H:%M} ({TZ.key}); ISO date {n.date().isoformat()}"


@mcp.tool()
def list_events(when: str = "today", days: int = 1) -> str:
    """The user's calendar events: what's on, meetings, appointments, whether they are free or busy.

    when: "today", "tomorrow", a weekday ("friday"), "this week", "next week" or a date
    ("2026-10-12"). days: how many days from then (1 = that day only).
    """
    return listing(when, days)[0]


@mcp.tool()
def add_event(title: str, start: str, duration_minutes: int = 60, location: str = "") -> str:
    """Add an event to the user's calendar.

    start: when it begins, e.g. "tomorrow 3pm", "friday 09:30", "2026-10-12 14:00".
    """
    begin = parse_when(start)
    if not begin or not title.strip():
        return f"Couldn't add it: I need a title and a start time I can read (got {start!r})."
    if begin.hour == 0 and begin.minute == 0 and not re.search(r"\d{1,2}[:.h]\d{2}|\d\s*(am|pm)|midnight", start, re.I):
        begin = begin.replace(hour=9)  # a date without a time: 09:00, not midnight
    end = begin + timedelta(minutes=max(5, min(duration_minutes, 24 * 60)))
    cal = Calendar.from_ical(OWN.read_bytes()) if OWN.exists() else Calendar()
    if not OWN.exists():
        cal.add("prodid", "-//Local AI Platform//agent//EN")
        cal.add("version", "2.0")
    ev = Event()
    ev.add("uid", f"{uuid.uuid4()}@ai.local")
    ev.add("summary", title.strip())
    ev.add("dtstart", begin)
    ev.add("dtend", end)
    ev.add("dtstamp", datetime.now(ZoneInfo("UTC")))
    if location.strip():
        ev.add("location", location.strip())
    cal.add_component(ev)
    CAL_DIR.mkdir(parents=True, exist_ok=True)
    OWN.write_bytes(cal.to_ical())
    clash = [e for e in events_between(begin, end) if e["title"] != title.strip() and not e["all_day"]]
    note = "" if not clash else "\nNote: it overlaps " + "; ".join(describe(e)[2:] for e in clash)
    return f"Added: {title.strip()}, {begin:%A %d %B %Y %H:%M}-{end:%H:%M}" + (f" @ {location.strip()}" if location.strip() else "") + note


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
