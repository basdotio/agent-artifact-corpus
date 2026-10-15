"""Build ``am start`` arguments for Android's standard intent verbs. Pure functions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote

from .shell import q

VERBS = (
    "set_alarm",
    "set_timer",
    "show_alarms",
    "dial",
    "compose_sms",
    "add_calendar_event",
    "share_text",
    "navigate",
)
TRAVEL_MODES = {"drive": "driving", "walk": "walking", "bike": "bicycling", "transit": "transit"}
_PHONE_CLEAN = re.compile(r"[^\d+*#]")
EXTRA = "android.intent.extra"


@dataclass(frozen=True)
class IntentSpec:
    args: str
    summary: str


def epoch_ms(iso: str) -> int:
    """ISO 8601 (``2026-07-10T15:00``) to epoch milliseconds; naive times are host-local."""
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def _need(params: dict, *names: str) -> None:
    missing = [n for n in names if params.get(n) in (None, "")]
    if missing:
        raise ValueError(f"missing required parameter(s): {', '.join(missing)}")


def build_intent(verb: str, params: dict) -> IntentSpec:
    if verb not in VERBS:
        raise ValueError(f"unknown verb {verb!r}; choose from {', '.join(VERBS)}")
    if verb == "set_alarm":
        _need(params, "hour")
        hour, minute = int(params["hour"]), int(params.get("minute") or 0)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("hour must be 0-23 and minute 0-59")
        args = (
            f"-a android.intent.action.SET_ALARM --ei {EXTRA}.alarm.HOUR {hour} "
            f"--ei {EXTRA}.alarm.MINUTES {minute} --es {EXTRA}.alarm.MESSAGE {q(params.get('label') or '')}"
            f" --ez {EXTRA}.alarm.SKIP_UI {'true' if params.get('skip_ui', True) else 'false'}"
        )
        return IntentSpec(args, f"alarm at {hour:02d}:{minute:02d}")
    if verb == "set_timer":
        _need(params, "seconds")
        seconds = int(params["seconds"])
        if not 1 <= seconds <= 86400:
            raise ValueError("seconds must be 1-86400")
        args = (
            f"-a android.intent.action.SET_TIMER --ei {EXTRA}.alarm.LENGTH {seconds} "
            f"--es {EXTRA}.alarm.MESSAGE {q(params.get('label') or '')} "
            f"--ez {EXTRA}.alarm.SKIP_UI {'true' if params.get('skip_ui', True) else 'false'}"
        )
        return IntentSpec(args, f"timer for {seconds}s")
    if verb == "show_alarms":
        return IntentSpec("-a android.intent.action.SHOW_ALARMS", "alarm list")
    if verb == "dial":
        _need(params, "phone_number")
        number = _PHONE_CLEAN.sub("", params["phone_number"])
        if not number:
            raise ValueError("phone_number has no digits")
        return IntentSpec(
            f"-a android.intent.action.DIAL -d {q('tel:' + number)}", f"dialer with {number}"
        )
    if verb == "compose_sms":
        number = _PHONE_CLEAN.sub("", params.get("phone_number") or "")
        args = f"-a android.intent.action.SENDTO -d {q('smsto:' + number)} --es sms_body {q(params.get('body') or '')}"
        return IntentSpec(args, f"SMS composer to {number}")
    if verb == "add_calendar_event":
        _need(params, "title", "start")
        begin = epoch_ms(params["start"])
        end = (
            epoch_ms(params["end"])
            if params.get("end")
            else int(
                (datetime.fromisoformat(params["start"]) + timedelta(hours=1)).timestamp() * 1000
            )
        )
        args = (
            "-a android.intent.action.INSERT -d content://com.android.calendar/events "
            "-t vnd.android.cursor.dir/event "
            f"--es title {q(params['title'])} --el beginTime {begin} --el endTime {end} "
            f"--es eventLocation {q(params.get('location') or '')} --es description {q(params.get('notes') or '')}"
        )
        return IntentSpec(args, f"calendar event {params['title']!r}")
    if verb == "share_text":
        _need(params, "text")
        args = (
            f"-a android.intent.action.SEND -t text/plain --es {EXTRA}.TEXT {q(params['text'])} "
            f"--es {EXTRA}.SUBJECT {q(params.get('subject') or '')}"
        )
        return IntentSpec(args, "share sheet")
    _need(params, "destination")
    mode = TRAVEL_MODES.get(params.get("mode") or "drive")
    if mode is None:
        raise ValueError(f"mode must be one of {', '.join(TRAVEL_MODES)}")
    url = (
        "https://www.google.com/maps/dir/?api=1&destination="
        f"{quote(params['destination'])}&travelmode={mode}"
    )
    return IntentSpec(
        f"-a android.intent.action.VIEW -d {q(url)}", f"directions to {params['destination']}"
    )
