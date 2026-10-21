"""Spond MCP server — service layer, tool definitions, and formatting."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from spond.spond import Spond

logger = logging.getLogger(__name__)

WEEKDAYS_NO = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
LOCAL_TZ = ZoneInfo("Europe/Oslo")


class SpondService:
    """Wraps the Spond library with TTL caching and family member resolution."""

    GROUPS_TTL = 3600.0  # 1 hour
    EVENTS_TTL = 300.0  # 5 minutes
    MEMBERS_TTL = 3600.0  # 1 hour

    def __init__(self, client: Spond, kids_config: list[dict] | None = None):
        self._client = client
        self._kids = kids_config or []
        self._cache: dict[str, tuple[Any, float]] = {}
        self._family_members: dict[str, str] | None = None
        self._group_map: dict[str, str] | None = None

    def _get_cached(self, key: str, ttl: float) -> Any | None:
        if key in self._cache:
            data, ts = self._cache[key]
            if time.monotonic() - ts < ttl:
                return data
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        self._cache[key] = (data, time.monotonic())

    def clear_cache(self) -> None:
        self._cache.clear()
        self._family_members = None
        self._group_map = None

    async def get_groups(self) -> list[dict]:
        cached = self._get_cached("groups", self.GROUPS_TTL)
        if cached is not None:
            return cached
        groups = await self._client.get_groups()
        self._set_cached("groups", groups)
        return groups

    async def get_group_map(self) -> dict[str, str]:
        if self._group_map is not None:
            return self._group_map
        groups = await self.get_groups()
        self._group_map = {g["id"]: g["name"] for g in groups}
        return self._group_map

    async def resolve_family_members(self) -> dict[str, str]:
        """Map Spond member IDs to kid names using configured groups + first name matching."""
        if self._family_members is not None:
            return self._family_members

        groups = await self.get_groups()
        family: dict[str, str] = {}

        for kid in self._kids:
            kid_name = kid["name"]
            kid_groups = kid.get("groups", [])

            for group in groups:
                if not fuzzy_match_group(group["name"], kid_groups):
                    continue
                for member in group.get("members", []):
                    if member.get("firstName", "").lower() == kid_name.lower():
                        family[member["id"]] = kid_name
                        break

        self._family_members = family
        return family

    def find_group_id(self, group_name: str, groups: list[dict]) -> str | None:
        name_lower = group_name.lower()
        for g in groups:
            if name_lower in g["name"].lower() or g["name"].lower() in name_lower:
                return g["id"]
        return None

    def get_kid_group_names(self, kid_name: str) -> list[str]:
        for kid in self._kids:
            if kid["name"].lower() == kid_name.lower():
                return kid.get("groups", [])
        return []

    async def get_events(self, days: int = 7, group_id: str | None = None, from_days: int = 0) -> list[dict]:
        cache_key = f"events:{days}:{from_days}:{group_id or 'all'}"
        cached = self._get_cached(cache_key, self.EVENTS_TTL)
        if cached is not None:
            return cached

        now = datetime.now(UTC)
        min_start = now + timedelta(days=from_days) if from_days > 0 else now
        events = await self._client.get_events(
            min_start=min_start,
            max_end=now + timedelta(days=from_days + days),
            group_id=group_id,
        )
        self._set_cached(cache_key, events)
        return events

    async def get_event(self, event_id: str) -> dict:
        return await self._client.get_event(event_id)

    async def change_response(self, event_id: str, member_id: str, accept: bool, decline_message: str = "") -> dict:
        payload = {"accepted": "true"} if accept else {"accepted": "false"}
        if not accept and decline_message:
            payload["declineMessage"] = decline_message
        result = await self._client.change_response(event_id, member_id, payload)
        self.clear_cache()
        if not isinstance(result, dict):
            raise ValueError(f"Unexpected API response type: {type(result).__name__}")
        logger.info(
            "change_response for member %s on event %s: accept=%s result_keys=%s",
            member_id,
            event_id,
            accept,
            list(result.keys()),
        )
        return result

    async def find_member_id(self, kid_name: str) -> str | None:
        family = await self.resolve_family_members()
        for member_id, name in family.items():
            if name.lower() == kid_name.lower():
                return member_id
        return None

    async def close(self) -> None:
        if hasattr(self._client, "clientsession") and self._client.clientsession:
            await self._client.clientsession.close()

    POSTS_TTL = 300.0  # 5 minutes

    async def get_posts(self, group_id: str | None = None, max_posts: int = 20) -> list[dict]:
        cache_key = f"posts:{group_id or 'all'}:{max_posts}"
        cached = self._get_cached(cache_key, self.POSTS_TTL)
        if cached is not None:
            return cached
        posts = await self._client.get_posts(group_id=group_id, max_posts=max_posts, include_comments=True)
        result = posts or []
        self._set_cached(cache_key, result)
        return result

    CHATS_TTL = 60.0  # 1 minute

    async def get_chats(self, max_chats: int = 20) -> list[dict]:
        cache_key = f"chats:{max_chats}"
        cached = self._get_cached(cache_key, self.CHATS_TTL)
        if cached is not None:
            return cached
        chats = await self._client.get_messages(max_chats=max_chats)
        result = chats or []
        self._set_cached(cache_key, result)
        return result

    async def get_chat_messages(self, chat_id: str, limit: int = 20) -> list[dict]:
        messages = await self._client.get_msg_history(chat_id, limit=limit)
        return messages or []


def fuzzy_match_group(group_name: str, configured_names: list[str]) -> bool:
    name_lower = group_name.lower()
    for configured in configured_names:
        if configured.lower() in name_lower or name_lower in configured.lower():
            return True
    return False


def parse_timestamp(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(LOCAL_TZ)
    except (ValueError, TypeError):
        return None


def norwegian_weekday(weekday: int) -> str:
    return WEEKDAYS_NO[weekday]


def format_event_summary(event: dict, family_members: dict[str, str] | None = None) -> str:
    heading = event.get("heading", "Ukjent")
    start_dt = parse_timestamp(event.get("startTimestamp", ""))
    end_dt = parse_timestamp(event.get("endTimestamp", ""))

    location = event.get("location", {})
    loc_name = location.get("feature", "")

    lines = []

    if start_dt:
        day_name = norwegian_weekday(start_dt.weekday())
        date_str = start_dt.strftime("%d.%m")
        time_str = start_dt.strftime("%H:%M")
        if end_dt:
            time_str += f"-{end_dt.strftime('%H:%M')}"
        lines.append(f"{heading} — {day_name} {date_str} kl. {time_str}")
    else:
        lines.append(heading)

    if loc_name:
        lines.append(f"Sted: {loc_name}")

    if event.get("description"):
        desc = event["description"].strip()
        if len(desc) > 200:
            desc = desc[:197] + "..."
        lines.append(desc)

    rsvp_dt = parse_timestamp(event.get("rsvpDate", ""))
    if rsvp_dt:
        deadline = rsvp_dt.strftime("%d.%m")
        time = rsvp_dt.strftime("%H:%M")
        lines.append(f"Svarfrist: {norwegian_weekday(rsvp_dt.weekday())} {deadline} kl. {time}")

    if family_members:
        responses = event.get("responses", {})
        accepted = set(responses.get("acceptedIds", []))
        declined = set(responses.get("declinedIds", []))
        unanswered = set(responses.get("unansweredIds", []))

        rsvp_parts = []
        for member_id, name in sorted(family_members.items(), key=lambda x: x[1]):
            if member_id in accepted:
                rsvp_parts.append(f"{name}: bekreftet")
            elif member_id in declined:
                rsvp_parts.append(f"{name}: avslått")
            elif member_id in unanswered:
                rsvp_parts.append(f"{name}: ikke svart")

        if rsvp_parts:
            lines.append("Svar: " + ", ".join(rsvp_parts))

    if event.get("cancelled"):
        lines.append("AVLYST")

    return "\n".join(lines)


def format_event_detail(event: dict, family_members: dict[str, str] | None = None) -> str:
    lines = [format_event_summary(event, family_members)]

    location = event.get("location", {})
    if location.get("address"):
        lines.append(f"Adresse: {location['address']}")
    if location.get("latitude") and location.get("longitude"):
        lines.append(f"Kart: {location['latitude']},{location['longitude']}")

    if event.get("description"):
        desc = event["description"].strip()
        if desc not in lines[0]:
            lines.append(f"\n{desc}")

    responses = event.get("responses", {})
    n_accepted = len(responses.get("acceptedIds", []))
    n_declined = len(responses.get("declinedIds", []))
    n_unanswered = len(responses.get("unansweredIds", []))
    total = n_accepted + n_declined + n_unanswered
    if total > 0:
        lines.append(f"\nPåmelding: {n_accepted} ja, {n_declined} nei, {n_unanswered} ikke svart (av {total})")

    return "\n".join(lines)


def format_group_summary(group: dict) -> str:
    name = group.get("name", "Ukjent")
    members = group.get("members", [])
    return f"{name} ({len(members)} medlemmer)"


def format_chat_summary(chat: dict) -> str:
    title = chat.get("title") or "Privat chat"
    last_msg = chat.get("lastMessage", {})
    last_text = (last_msg.get("body") or "").strip()
    if len(last_text) > 50:
        last_text = last_text[:47] + "..."

    ts = parse_timestamp(last_msg.get("timestamp", ""))
    ts_str = ts.strftime("%d.%m %H:%M") if ts else ""

    sender = last_msg.get("sender", {}).get("firstName", "Ukjent")

    line = f"{title}"
    if ts_str:
        line += f" ({ts_str})"
    if last_text:
        line += f": {sender}: {last_text}"

    line += f" [id: {chat['id']}]"
    return line


def format_message_summary(msg: dict) -> str:
    body = (msg.get("body") or "").strip()
    sender = msg.get("sender", {}).get("firstName", "Ukjent")
    ts = parse_timestamp(msg.get("timestamp", ""))
    ts_str = ts.strftime("%d.%m %H:%M") if ts else ""

    header = f"[{ts_str}] {sender}" if ts_str else sender
    return f"{header}: {body}"


def format_post_summary(post: dict, group_map: dict[str, str] | None = None) -> str:
    body = (post.get("body") or "").strip()
    if len(body) > 300:
        body = body[:297] + "..."

    ts = parse_timestamp(post.get("timestamp", ""))
    author = post.get("createdByProfile", {}).get("firstName", "Ukjent")
    group_id = post.get("groupId", "")
    group_name = (group_map or {}).get(group_id, "")

    lines = []
    header = f"Fra {author}"
    if group_name:
        header += f" i {group_name}"
    if ts:
        header += f" — {norwegian_weekday(ts.weekday())} {ts.strftime('%d.%m kl. %H:%M')}"
    lines.append(header)

    if body:
        lines.append(body)

    comments = post.get("comments", [])
    if comments:
        lines.append(f"({len(comments)} kommentar{'er' if len(comments) != 1 else ''})")

    return "\n".join(lines)


# --- Tool definitions ---

TOOLS = [
    {
        "name": "list_groups",
        "description": "List alle Spond-grupper med navn og antall medlemmer.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_upcoming_events",
        "description": (
            "Hent kommende aktiviteter fra Spond. Kan filtreres på barn eller gruppe. Standard: 7 dager frem."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Antall dager å inkludere (standard: 7). Vindu = [from_days, from_days+days].",
                    "default": 7,
                },
                "from_days": {
                    "type": "integer",
                    "description": (
                        "Start fra N dager frem i tid (standard: 0 = fra nå). F.eks. from_days=7, days=56 gir uke 2-9."
                    ),
                    "default": 0,
                },
                "group_name": {
                    "type": "string",
                    "description": "Filtrér på gruppenavn (delvis treff, f.eks. 'Fjordvik')",
                },
                "kid_name": {
                    "type": "string",
                    "description": "Filtrér på barnets navn (viser kun aktiviteter i barnets grupper)",
                },
            },
        },
    },
    {
        "name": "get_event_details",
        "description": "Hent detaljer for en spesifikk aktivitet, inkludert beskrivelse, sted og påmeldingsstatus.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Aktivitetens ID (fra get_upcoming_events)",
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_attendance",
        "description": ("Vis påmeldingsstatus for kommende aktiviteter. Viser hvilke aktiviteter som mangler svar."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kid_name": {
                    "type": "string",
                    "description": "Barnets navn (valgfritt — viser alle hvis ikke satt)",
                },
                "days": {
                    "type": "integer",
                    "description": "Antall dager å inkludere (standard: 14). Vindu = [from_days, from_days+days].",
                    "default": 14,
                },
                "from_days": {
                    "type": "integer",
                    "description": (
                        "Start fra N dager frem i tid (standard: 0 = fra nå). F.eks. from_days=7, days=56 gir uke 2-9."
                    ),
                    "default": 0,
                },
            },
        },
    },
    {
        "name": "respond_to_event",
        "description": "Svar på en aktivitet — aksepter eller avslå for et familiemedlem.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Aktivitetens ID",
                },
                "kid_name": {
                    "type": "string",
                    "description": "Barnets navn",
                },
                "accept": {
                    "type": "boolean",
                    "description": "true = aksepter, false = avslå",
                },
                "decline_message": {
                    "type": "string",
                    "description": "Melding ved avslag (valgfritt)",
                },
            },
            "required": ["event_id", "kid_name", "accept"],
        },
    },
    {
        "name": "search_events",
        "description": "Søk i kommende aktiviteter etter tekst i tittel eller beskrivelse.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Søketekst (f.eks. 'cup', 'dugnad', 'kamp')",
                },
                "days": {
                    "type": "integer",
                    "description": "Antall dager å søke i (standard: 30). Vindu = [from_days, from_days+days].",
                    "default": 30,
                },
                "from_days": {
                    "type": "integer",
                    "description": (
                        "Start fra N dager frem i tid (standard: 0 = fra nå). F.eks. from_days=7, days=56 gir uke 2-9."
                    ),
                    "default": 0,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_posts",
        "description": (
            "Hent innlegg fra gruppeveggen i Spond. "
            "Innlegg er beskjeder fra trenere/ledere til gruppa — "
            "ikke chat-meldinger eller aktiviteter."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_name": {
                    "type": "string",
                    "description": "Filtrér på gruppenavn (delvis treff). Viser alle grupper hvis tom.",
                },
                "max_posts": {
                    "type": "integer",
                    "description": "Maks antall innlegg å hente (standard: 10).",
                    "default": 10,
                },
            },
        },
    },
    {
        "name": "get_chats",
        "description": (
            "Hent en oversikt over nylige chat-samtaler (både gruppechat og private meldinger). "
            "Bruk id herfra for å hente selve meldingene i en chat med get_chat_messages."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_chats": {
                    "type": "integer",
                    "description": "Maks antall samtaler å hente (standard: 10).",
                    "default": 10,
                },
            },
        },
    },
    {
        "name": "get_chat_messages",
        "description": "Hent meldingshistorikken for en spesifikk chat-samtale.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "ID for samtalen (fra get_chats).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maks antall meldinger å hente (standard: 20).",
                    "default": 20,
                },
            },
            "required": ["chat_id"],
        },
    },
]


async def handle_list_groups(service: SpondService) -> str:
    groups = await service.get_groups()
    if not groups:
        return "Ingen grupper funnet."
    lines = [f"Spond-grupper ({len(groups)} stk):"]
    for g in sorted(groups, key=lambda x: x.get("name", "")):
        lines.append(f"  {format_group_summary(g)}")
    return "\n".join(lines)


async def handle_get_upcoming_events(
    service: SpondService, days: int = 7, group_name: str = "", kid_name: str = "", from_days: int = 0
) -> str:
    group_id = None

    if kid_name:
        kid_group_names = service.get_kid_group_names(kid_name)
        if not kid_group_names:
            return f"Ukjent barn: {kid_name}"
        groups = await service.get_groups()
        all_events: list[dict] = []
        seen_ids: set[str] = set()
        for gname in kid_group_names:
            gid = service.find_group_id(gname, groups)
            if gid:
                events = await service.get_events(days=days, group_id=gid, from_days=from_days)
                for e in events:
                    eid = e.get("id", "")
                    if eid not in seen_ids:
                        seen_ids.add(eid)
                        all_events.append(e)
        events = sorted(all_events, key=lambda e: e.get("startTimestamp", ""))
    elif group_name:
        groups = await service.get_groups()
        group_id = service.find_group_id(group_name, groups)
        if not group_id:
            return f"Fant ingen gruppe som matcher '{group_name}'"
        events = await service.get_events(days=days, group_id=group_id, from_days=from_days)
    else:
        events = await service.get_events(days=days, from_days=from_days)

    if not events:
        scope = f" for {kid_name}" if kid_name else (f" i {group_name}" if group_name else "")
        return f"Ingen aktiviteter de neste {days} dagene{scope}."

    family = await service.resolve_family_members()
    lines = []
    for event in sorted(events, key=lambda e: e.get("startTimestamp", "")):
        lines.append(format_event_summary(event, family))
        lines.append("")

    header = f"Aktiviteter neste {days} dager"
    if kid_name:
        header += f" for {kid_name}"
    elif group_name:
        header += f" i {group_name}"
    header += f" ({len(events)} stk):"

    return header + "\n\n" + "\n".join(lines).strip()


async def handle_get_event_details(service: SpondService, event_id: str) -> str:
    event = await service.get_event(event_id)
    family = await service.resolve_family_members()
    return format_event_detail(event, family)


async def handle_get_attendance(service: SpondService, kid_name: str = "", days: int = 14, from_days: int = 0) -> str:
    if kid_name:
        kid_group_names = service.get_kid_group_names(kid_name)
        if not kid_group_names:
            return f"Ukjent barn: {kid_name}"
        groups = await service.get_groups()
        all_events: list[dict] = []
        seen_ids: set[str] = set()
        for gname in kid_group_names:
            gid = service.find_group_id(gname, groups)
            if gid:
                for e in await service.get_events(days=days, group_id=gid, from_days=from_days):
                    if e.get("id", "") not in seen_ids:
                        seen_ids.add(e["id"])
                        all_events.append(e)
        events = all_events
    else:
        events = await service.get_events(days=days, from_days=from_days)

    if not events:
        return "Ingen kommende aktiviteter."

    family = await service.resolve_family_members()
    if not family:
        return "Ingen familiemedlemmer funnet i Spond-grupper."

    unanswered_events = []
    for event in sorted(events, key=lambda e: e.get("startTimestamp", "")):
        responses = event.get("responses", {})
        unanswered_ids = set(responses.get("unansweredIds", []))
        missing = []
        for mid, name in sorted(family.items(), key=lambda x: x[1]):
            if kid_name and name.lower() != kid_name.lower():
                continue
            if mid in unanswered_ids:
                missing.append(name)
        if missing:
            heading = event.get("heading", "Ukjent")
            start_dt = parse_timestamp(event.get("startTimestamp", ""))
            date_str = ""
            if start_dt:
                day_name = norwegian_weekday(start_dt.weekday())
                date_str = f" — {day_name} {start_dt.strftime('%d.%m')}"
            unanswered_events.append(
                f"{heading}{date_str}: mangler svar fra {', '.join(missing)} (id: {event.get('id', '')})"
            )

    if not unanswered_events:
        scope = f" for {kid_name}" if kid_name else ""
        return f"Alle aktiviteter{scope} er besvart de neste {days} dagene."

    header = f"Ubesvarte aktiviteter ({len(unanswered_events)} stk):"
    return header + "\n" + "\n".join(f"  {e}" for e in unanswered_events)


async def handle_respond_to_event(
    service: SpondService,
    event_id: str,
    kid_name: str,
    accept: bool,
    decline_message: str = "",
) -> str:
    member_id = await service.find_member_id(kid_name)
    if not member_id:
        return f"Fant ikke {kid_name} i noen Spond-gruppe."

    try:
        result = await service.change_response(event_id, member_id, accept, decline_message)
    except Exception as e:
        logger.error("change_response failed for %s event %s: %s", kid_name, event_id, e)
        return f"Feil ved svar for {kid_name}: {e}"

    if isinstance(result, dict) and "error" in result:
        logger.error("Spond API error for %s event %s: %s", kid_name, event_id, result)
        return f"Spond returnerte feil for {kid_name}: {result.get('error', result)}"

    accepted_ids = set()
    declined_ids = set()
    if isinstance(result, dict):
        accepted_ids = set(result.get("acceptedIds", []))
        declined_ids = set(result.get("declinedIds", []))

    if accept and member_id in accepted_ids:
        return f"Aktivitet akseptert for {kid_name}."
    elif not accept and member_id in declined_ids:
        return f"Aktivitet avslått for {kid_name}."
    else:
        action = "akseptert" if accept else "avslått"
        logger.warning(
            "Response may not have been saved for %s (member %s) on event %s. API returned: %s",
            kid_name,
            member_id,
            event_id,
            result,
        )
        return f"Svar sendt for {kid_name}, men kunne ikke bekrefte at det ble {action}. Sjekk Spond-appen."


async def handle_search_events(service: SpondService, query: str, days: int = 30, from_days: int = 0) -> str:
    events = await service.get_events(days=days, from_days=from_days)
    query_lower = query.lower()

    matches = []
    for event in events:
        heading = event.get("heading", "").lower()
        description = event.get("description", "").lower()
        if query_lower in heading or query_lower in description:
            matches.append(event)

    if not matches:
        return f"Ingen aktiviteter matcher '{query}' de neste {days} dagene."

    family = await service.resolve_family_members()
    lines = []
    for event in sorted(matches, key=lambda e: e.get("startTimestamp", "")):
        lines.append(format_event_summary(event, family))
        lines.append("")

    header = f"Søkeresultat for '{query}' ({len(matches)} treff):"
    return header + "\n\n" + "\n".join(lines).strip()


async def handle_get_posts(service: SpondService, group_name: str = "", max_posts: int = 10) -> str:
    group_id = None
    if group_name:
        groups = await service.get_groups()
        for g in groups:
            if group_name.lower() in g.get("name", "").lower():
                group_id = g["id"]
                break
        if not group_id:
            return f"Fant ingen gruppe som matcher '{group_name}'."

    posts = await service.get_posts(group_id=group_id, max_posts=max_posts)
    if not posts:
        return "Ingen innlegg funnet."

    group_map = await service.get_group_map()
    lines = [f"Innlegg ({len(posts)} stk):"]
    for post in posts:
        lines.append("")
        lines.append(format_post_summary(post, group_map))
    return "\n".join(lines)


async def handle_get_chats(service: SpondService, max_chats: int = 10) -> str:
    chats = await service.get_chats(max_chats=max_chats)
    if not chats:
        return "Ingen chat-samtaler funnet."

    lines = [f"Nylige samtaler ({len(chats)} stk):"]
    for chat in chats:
        lines.append(f"  • {format_chat_summary(chat)}")
    return "\n".join(lines)


async def handle_get_chat_messages(service: SpondService, chat_id: str, limit: int = 20) -> str:
    messages = await service.get_chat_messages(chat_id, limit=limit)
    if not messages:
        return "Ingen meldinger funnet i denne samtalen."

    lines = [f"Meldinger i samtalen ({len(messages)} stk):"]
    # Usually we want newest at bottom for history
    for msg in reversed(messages):
        lines.append(format_message_summary(msg))
    return "\n".join(lines)


async def handle_tool_call(service: SpondService, name: str, arguments: dict | None) -> str:
    args = arguments or {}

    if name == "list_groups":
        return await handle_list_groups(service)
    elif name == "get_upcoming_events":
        return await handle_get_upcoming_events(
            service,
            days=args.get("days", 7),
            group_name=args.get("group_name", ""),
            kid_name=args.get("kid_name", ""),
            from_days=args.get("from_days", 0),
        )
    elif name == "get_event_details":
        event_id = args.get("event_id", "")
        if not event_id:
            return "event_id er påkrevd."
        return await handle_get_event_details(service, event_id)
    elif name == "get_attendance":
        return await handle_get_attendance(
            service,
            kid_name=args.get("kid_name", ""),
            days=args.get("days", 14),
            from_days=args.get("from_days", 0),
        )
    elif name == "respond_to_event":
        event_id = args.get("event_id", "")
        kid_name = args.get("kid_name", "")
        accept = args.get("accept")
        if not event_id or not kid_name or accept is None:
            return "event_id, kid_name og accept er påkrevd."
        return await handle_respond_to_event(
            service,
            event_id=event_id,
            kid_name=kid_name,
            accept=accept,
            decline_message=args.get("decline_message", ""),
        )
    elif name == "search_events":
        query = args.get("query", "")
        if not query:
            return "query er påkrevd."
        return await handle_search_events(
            service,
            query=query,
            days=args.get("days", 30),
            from_days=args.get("from_days", 0),
        )
    elif name == "get_posts":
        return await handle_get_posts(
            service,
            group_name=args.get("group_name", ""),
            max_posts=args.get("max_posts", 10),
        )
    elif name == "get_chats":
        return await handle_get_chats(
            service,
            max_chats=args.get("max_chats", 10),
        )
    elif name == "get_chat_messages":
        chat_id = args.get("chat_id", "")
        if not chat_id:
            return "chat_id er påkrevd."
        return await handle_get_chat_messages(
            service,
            chat_id=chat_id,
            limit=args.get("limit", 20),
        )
    else:
        return f"Ukjent verktøy: {name}"
