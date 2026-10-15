"""
tools/calendar_tools.py – Narzędzia MCP dla Google Calendar.

Dostępne narzędzia:
  - calendar_list_events    Nadchodzące lub przeszłe wydarzenia
  - calendar_get_event      Szczegóły konkretnego wydarzenia
  - calendar_create_event   Tworzenie nowego wydarzenia
  - calendar_list_calendars Lista wszystkich kalendarzy na koncie
"""

import logging
from datetime import datetime, timedelta, timezone

from auth import get_google_service

logger = logging.getLogger(__name__)


def register_calendar_tools(mcp) -> None:
    """Rejestruje wszystkie narzędzia Google Calendar w serwerze MCP."""

    # ── 1. Lista wydarzeń ─────────────────────────────────────────────────────

    @mcp.tool()
    def calendar_list_events(
        account_id: str,
        days_ahead: int = 7,
        days_back: int = 0,
        days: int = 0,
        limit: int = 20,
        calendar_id: str = "primary",
        search_query: str = "",
    ) -> str:
        """
        Pobiera listę wydarzeń z Google Calendar.

        Args:
            account_id:   Nazwa konta Google (np. 'praca', 'prywatne')
            days_ahead:   Liczba dni do przodu (domyślnie 7)
            days_back:    Liczba dni wstecz (domyślnie 0)
            limit:        Maksymalna liczba wydarzeń (domyślnie 20)
            calendar_id:  ID kalendarza (domyślnie 'primary' = główny)
            search_query: Filtr po tytule lub opisie wydarzeń

        Returns:
            Sformatowana lista wydarzeń z czasem, tytułem i lokalizacją.
        """
        try:
            if days > 0:
                days_ahead = days
            service = get_google_service(account_id, "calendar", "v3")

            now = datetime.now(timezone.utc)
            time_min = (now - timedelta(days=days_back)).isoformat()
            time_max = (now + timedelta(days=days_ahead)).isoformat()

            kwargs = {
                "calendarId": calendar_id,
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": min(limit, 100),
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if search_query:
                kwargs["q"] = search_query

            events_result = service.events().list(**kwargs).execute()
            events = events_result.get("items", [])

            if not events:
                return (
                    f"📅 Brak wydarzeń na koncie '{account_id}' w podanym zakresie dat."
                )

            lines = [
                f"📅 Konto: {account_id} | Kalendarz: {calendar_id} | {len(events)} wydarzeń:\n"
            ]
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date", "?"))
                end = event["end"].get("dateTime", event["end"].get("date", "?"))
                title = event.get("summary", "(bez tytułu)")
                location = event.get("location", "")
                attendees = event.get("attendees", [])
                status = event.get("status", "confirmed")

                status_icon = {
                    "confirmed": "✅",
                    "tentative": "❓",
                    "cancelled": "❌",
                }.get(status, "📌")
                loc_str = f"\n   📍 {location}" if location else ""
                att_str = f"\n   👥 {len(attendees)} uczestników" if attendees else ""

                lines.append(
                    f"{status_icon} {title}\n"
                    f"   🕒 {_format_datetime(start)} → {_format_datetime(end)}"
                    f"{loc_str}{att_str}"
                )

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"calendar_list_events [{account_id}]: {e}")
            return f"❌ Błąd Calendar ({account_id}): {str(e)}"

    # ── 2. Szczegóły wydarzenia ───────────────────────────────────────────────

    @mcp.tool()
    def calendar_get_event(
        account_id: str,
        event_id: str,
        calendar_id: str = "primary",
    ) -> str:
        """
        Pobiera szczegóły konkretnego wydarzenia.

        Args:
            account_id:  Nazwa konta Google
            event_id:    ID wydarzenia
            calendar_id: ID kalendarza (domyślnie 'primary')

        Returns:
            Pełne szczegóły: uczestnicy, opis, konferencja (Meet/Zoom).
        """
        try:
            service = get_google_service(account_id, "calendar", "v3")
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )

            start = event["start"].get("dateTime", event["start"].get("date", "?"))
            end = event["end"].get("dateTime", event["end"].get("date", "?"))
            attendees = event.get("attendees", [])
            conf_data = event.get("conferenceData", {})
            meet_link = ""
            for ep in conf_data.get("entryPoints", []):
                if ep.get("entryPointType") == "video":
                    meet_link = ep.get("uri", "")
                    break

            att_lines = "\n".join(
                f"     • {a.get('email', '?')} ({a.get('responseStatus', '?')})"
                for a in attendees
            )

            return (
                f"📅 SZCZEGÓŁY WYDARZENIA\n{'─' * 40}\n"
                f"Tytuł:       {event.get('summary', '(brak)')}\n"
                f"Kiedy:       {_format_datetime(start)} → {_format_datetime(end)}\n"
                f"Lokalizacja: {event.get('location', '—')}\n"
                f"Opis:        {event.get('description', '—')[:300]}\n"
                f"Status:      {event.get('status', '—')}\n"
                f"Meet:        {meet_link or '—'}\n"
                f"Uczestnicy ({len(attendees)}):\n{att_lines or '   —'}"
            )
        except Exception as e:
            logger.error(f"calendar_get_event [{account_id}/{event_id}]: {e}")
            return f"❌ Błąd Calendar ({account_id}): {str(e)}"

    # ── 3. Tworzenie wydarzenia ───────────────────────────────────────────────

    @mcp.tool()
    def calendar_create_event(
        account_id: str,
        title: str,
        start_datetime: str,
        end_datetime: str,
        description: str = "",
        location: str = "",
        attendees: str = "",
        add_google_meet: bool = False,
        calendar_id: str = "primary",
    ) -> str:
        """
        Tworzy nowe wydarzenie w Google Calendar.

        Args:
            account_id:      Nazwa konta Google
            title:           Tytuł wydarzenia
            start_datetime:  Data i czas rozpoczęcia (format ISO: '2026-09-28T10:00:00')
            end_datetime:    Data i czas zakończenia  (format ISO: '2026-09-28T11:00:00')
            description:     Opis wydarzenia (opcjonalnie)
            location:        Lokalizacja (opcjonalnie)
            attendees:       Adresy e-mail uczestników oddzielone przecinkami (opcjonalnie)
            add_google_meet: Czy dołączyć link do Google Meet (domyślnie False)
            calendar_id:     ID kalendarza (domyślnie 'primary')

        Returns:
            Potwierdzenie z linkiem do utworzonego wydarzenia.
        """
        try:
            service = get_google_service(account_id, "calendar", "v3")

            event_body = {
                "summary": title,
                "start": {"dateTime": start_datetime, "timeZone": "Europe/Warsaw"},
                "end": {"dateTime": end_datetime, "timeZone": "Europe/Warsaw"},
            }

            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location
            if attendees:
                event_body["attendees"] = [
                    {"email": e.strip()} for e in attendees.split(",") if e.strip()
                ]
            if add_google_meet:
                event_body["conferenceData"] = {
                    "createRequest": {"requestId": f"mcp-{datetime.now().timestamp()}"}
                }

            kwargs = {
                "calendarId": calendar_id,
                "body": event_body,
                "sendUpdates": "all",
            }
            if add_google_meet:
                kwargs["conferenceDataVersion"] = 1

            created = service.events().insert(**kwargs).execute()
            link = created.get("htmlLink", "brak linku")
            return (
                f"✅ Wydarzenie utworzone!\n"
                f"   Tytuł: {title}\n"
                f"   Kiedy: {start_datetime} → {end_datetime}\n"
                f"   Link:  {link}"
            )
        except Exception as e:
            logger.error(f"calendar_create_event [{account_id}]: {e}")
            return f"❌ Błąd tworzenia wydarzenia ({account_id}): {str(e)}"

    # ── 4. Lista kalendarzy ───────────────────────────────────────────────────

    @mcp.tool()
    def calendar_list_calendars(account_id: str) -> str:
        """
        Pobiera listę wszystkich kalendarzy dostępnych na koncie.

        Args:
            account_id: Nazwa konta Google

        Returns:
            Lista kalendarzy z ich ID (potrzebne do filtrowania w calendar_list_events).
        """
        try:
            service = get_google_service(account_id, "calendar", "v3")
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])

            if not calendars:
                return f"📅 Brak kalendarzy na koncie '{account_id}'."

            lines = [f"📅 Kalendarze na koncie '{account_id}' ({len(calendars)}):\n"]
            for cal in calendars:
                primary = " 🏠 (główny)" if cal.get("primary") else ""
                lines.append(
                    f"  📅 {cal.get('summary', '(brak nazwy)')}{primary}\n"
                    f"     ID: {cal['id']}"
                )

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"calendar_list_calendars [{account_id}]: {e}")
            return f"❌ Błąd Calendar ({account_id}): {str(e)}"

    # ── 5. Edycja wydarzenia ──────────────────────────────────────────────────

    @mcp.tool()
    def calendar_update_event(
        account_id: str,
        event_id: str,
        calendar_id: str = "primary",
        title: str = "",
        start_datetime: str = "",
        end_datetime: str = "",
        description: str = "",
        location: str = "",
        attendees: str = "",
    ) -> str:
        """
        Aktualizuje istniejące wydarzenie w kalendarzu Google.
        Zmienia tylko te pola, które zostały przekazane (niepuste).

        Args:
            account_id:     Nazwa konta Google
            event_id:       ID wydarzenia do modyfikacji
            calendar_id:    ID kalendarza (domyślnie 'primary')
            title:          Nowy tytuł spotkania (opcjonalnie)
            start_datetime: Nowy czas startu (ISO, np. '2026-09-28T14:00:00+02:00')
            end_datetime:   Nowy czas końca (ISO, np. '2026-09-28T15:00:00+02:00')
            description:    Nowy opis (opcjonalnie)
            location:       Nowa lokalizacja (opcjonalnie)
            attendees:      Nowe adresy uczestników oddzielone przecinkami (opcjonalnie)

        Returns:
            Potwierdzenie aktualizacji wydarzenia.
        """
        try:
            service = get_google_service(account_id, "calendar", "v3")
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )

            if title:
                event["summary"] = title
            if description:
                event["description"] = description
            if location:
                event["location"] = location
            if start_datetime:
                event["start"] = (
                    {"dateTime": start_datetime}
                    if "T" in start_datetime
                    else {"date": start_datetime}
                )
            if end_datetime:
                event["end"] = (
                    {"dateTime": end_datetime}
                    if "T" in end_datetime
                    else {"date": end_datetime}
                )
            if attendees:
                event["attendees"] = [
                    {"email": e.strip()} for e in attendees.split(",") if e.strip()
                ]

            updated = (
                service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event,
                    sendUpdates="all" if attendees else "none",
                )
                .execute()
            )

            link = updated.get("htmlLink", "")
            return (
                f"✅ Wydarzenie zaktualizowane pomyślnie!\n"
                f"   Tytuł: {updated.get('summary', title)}\n"
                f"   ID:    {event_id}\n"
                f"   Link:  {link}"
            )
        except Exception as e:
            logger.error(f"calendar_update_event [{account_id}/{event_id}]: {e}")
            return f"❌ Błąd edycji wydarzenia ({account_id}): {str(e)}"

    # ── 6. Usuwanie wydarzenia ────────────────────────────────────────────────

    @mcp.tool()
    def calendar_delete_event(
        account_id: str,
        event_id: str,
        calendar_id: str = "primary",
        notify_attendees: bool = True,
    ) -> str:
        """
        Usuwa wydarzenie z kalendarza Google.

        Args:
            account_id:       Nazwa konta Google
            event_id:         ID wydarzenia do usunięcia
            calendar_id:      ID kalendarza (domyślnie 'primary')
            notify_attendees: Czy powiadomić uczestników o odwołaniu (domyślnie True)

        Returns:
            Potwierdzenie usunięcia.
        """
        try:
            service = get_google_service(account_id, "calendar", "v3")
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates="all" if notify_attendees else "none",
            ).execute()
            return f"✅ Wydarzenie {event_id} zostało pomyślnie usunięte z kalendarza '{calendar_id}'."
        except Exception as e:
            logger.error(f"calendar_delete_event [{account_id}/{event_id}]: {e}")
            return f"❌ Błąd usuwania wydarzenia ({account_id}): {str(e)}"


# ── Pomocnicze funkcje ────────────────────────────────────────────────────────


def _format_datetime(dt_str: str) -> str:
    """Formatuje datę ISO do czytelnej postaci."""
    try:
        if "T" in dt_str:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y %H:%M")
        return dt_str  # Całodniowe wydarzenie – zostaw datę
    except Exception:
        return dt_str
