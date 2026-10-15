"""
tools/youtube_tools.py – Narzędzia MCP dla YouTube Data & Analytics API.

Dostępne narzędzia:
  - youtube_channel_stats    Statystyki kanału (subskrypcje, wyświetlenia, filmy)
  - youtube_list_videos      Lista filmów na kanale z metadanymi
  - youtube_get_video_stats  Statystyki konkretnego wideo
  - youtube_search_videos    Wyszukiwanie wideo w YouTube
"""

import logging
from auth import get_google_service

logger = logging.getLogger(__name__)


def register_youtube_tools(mcp) -> None:
    """Rejestruje wszystkie narzędzia YouTube w serwerze MCP."""

    # ── 1. Statystyki kanału ──────────────────────────────────────────────────

    @mcp.tool()
    def youtube_channel_stats(account_id: str) -> str:
        """
        Pobiera statystyki Twojego kanału YouTube.

        Args:
            account_id: Nazwa konta Google powiązanego z kanałem

        Returns:
            Liczba subskrybentów, łączne wyświetlenia i liczba filmów.
        """
        try:
            service = get_google_service(account_id, "youtube", "v3")
            response = (
                service.channels()
                .list(
                    part="snippet,statistics,brandingSettings",
                    mine=True,
                )
                .execute()
            )

            channels = response.get("items", [])
            if not channels:
                return f"📺 Brak kanału YouTube na koncie '{account_id}'."

            ch = channels[0]
            snippet = ch["snippet"]
            stats = ch["statistics"]
            subs_hidden = stats.get("hiddenSubscriberCount", False)

            return (
                f"📺 KANAŁ YOUTUBE\n{'─' * 40}\n"
                f"Nazwa:         {snippet['title']}\n"
                f"Opis:          {snippet.get('description', '—')[:200]}\n"
                f"Kraj:          {snippet.get('country', '—')}\n"
                f"Data założenia:{snippet.get('publishedAt', '—')[:10]}\n"
                f"{'─' * 40}\n"
                f"Subskrybenci:  {'(ukryte)' if subs_hidden else _fmt_num(stats.get('subscriberCount', 0))}\n"
                f"Wyświetlenia:  {_fmt_num(stats.get('viewCount', 0))}\n"
                f"Filmy:         {_fmt_num(stats.get('videoCount', 0))}"
            )
        except Exception as e:
            logger.error(f"youtube_channel_stats [{account_id}]: {e}")
            return f"❌ Błąd YouTube ({account_id}): {str(e)}"

    # ── 2. Lista filmów ───────────────────────────────────────────────────────

    @mcp.tool()
    def youtube_list_videos(
        account_id: str,
        limit: int = 10,
        order: str = "date",
    ) -> str:
        """
        Pobiera listę filmów z Twojego kanału YouTube.

        Args:
            account_id: Nazwa konta Google
            limit:      Liczba filmów (domyślnie 10, max 50)
            order:      Sortowanie: 'date' (najnowsze), 'viewCount', 'rating', 'title'

        Returns:
            Lista filmów z wyświetleniami, polubieniami i komentarzami.
        """
        try:
            service = get_google_service(account_id, "youtube", "v3")

            # Pobierz ID kanału
            ch_response = service.channels().list(part="id", mine=True).execute()
            channels = ch_response.get("items", [])
            if not channels:
                return f"📺 Brak kanału YouTube na koncie '{account_id}'."
            channel_id = channels[0]["id"]

            # Pobierz filmy
            search_response = (
                service.search()
                .list(
                    part="id,snippet",
                    channelId=channel_id,
                    type="video",
                    order=order,
                    maxResults=min(limit, 50),
                )
                .execute()
            )

            items = search_response.get("items", [])
            if not items:
                return f"📺 Brak filmów na kanale '{account_id}'."

            # Pobierz statystyki dla wszystkich filmów naraz
            video_ids = [i["id"]["videoId"] for i in items]
            stats_response = (
                service.videos()
                .list(
                    part="statistics,contentDetails",
                    id=",".join(video_ids),
                )
                .execute()
            )
            stats_map = {v["id"]: v for v in stats_response.get("items", [])}

            lines = [f"📺 Filmy na kanale '{account_id}' ({len(items)}):\n"]
            for item in items:
                vid_id = item["id"]["videoId"]
                snippet = item["snippet"]
                stats = stats_map.get(vid_id, {}).get("statistics", {})

                lines.append(
                    f"🎬 {snippet['title']}\n"
                    f"   📅 {snippet.get('publishedAt', '')[:10]}"
                    f" | 👁 {_fmt_num(stats.get('viewCount', 0))}"
                    f" | 👍 {_fmt_num(stats.get('likeCount', 0))}"
                    f" | 💬 {_fmt_num(stats.get('commentCount', 0))}\n"
                    f"   🔗 https://youtu.be/{vid_id}"
                )

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"youtube_list_videos [{account_id}]: {e}")
            return f"❌ Błąd YouTube ({account_id}): {str(e)}"

    # ── 3. Statystyki wideo ───────────────────────────────────────────────────

    @mcp.tool()
    def youtube_get_video_stats(account_id: str, video_id: str) -> str:
        """
        Pobiera szczegółowe statystyki konkretnego wideo.

        Args:
            account_id: Nazwa konta Google
            video_id:   ID wideo (11-znakowy kod z URL, np. 'dQw4w9WgXcQ')

        Returns:
            Pełne statystyki: wyświetlenia, polubienia, komentarze, czas trwania.
        """
        try:
            service = get_google_service(account_id, "youtube", "v3")
            response = (
                service.videos()
                .list(
                    part="snippet,statistics,contentDetails",
                    id=video_id,
                )
                .execute()
            )

            items = response.get("items", [])
            if not items:
                return f"❌ Nie znaleziono wideo o ID '{video_id}'."

            video = items[0]
            snippet = video["snippet"]
            stats = video["statistics"]
            details = video["contentDetails"]

            duration = _parse_duration(details.get("duration", "PT0S"))

            return (
                f"🎬 STATYSTYKI WIDEO\n{'─' * 40}\n"
                f"Tytuł:        {snippet['title']}\n"
                f"Data publ.:   {snippet.get('publishedAt', '—')[:10]}\n"
                f"Czas trwania: {duration}\n"
                f"{'─' * 40}\n"
                f"Wyświetlenia: {_fmt_num(stats.get('viewCount', 0))}\n"
                f"Polubienia:   {_fmt_num(stats.get('likeCount', 0))}\n"
                f"Komentarze:   {_fmt_num(stats.get('commentCount', 0))}\n"
                f"Ulubione:     {_fmt_num(stats.get('favoriteCount', 0))}\n"
                f"Link:         https://youtu.be/{video_id}"
            )
        except Exception as e:
            logger.error(f"youtube_get_video_stats [{account_id}/{video_id}]: {e}")
            return f"❌ Błąd YouTube ({account_id}): {str(e)}"

    # ── 4. Wyszukiwanie wideo ─────────────────────────────────────────────────

    @mcp.tool()
    def youtube_search_videos(
        account_id: str,
        query: str,
        limit: int = 10,
        order: str = "relevance",
    ) -> str:
        """
        Wyszukuje wideo w YouTube.

        Args:
            account_id: Nazwa konta Google
            query:      Fraza wyszukiwania
            limit:      Liczba wyników (domyślnie 10, max 50)
            order:      Sortowanie: 'relevance', 'date', 'viewCount', 'rating'

        Returns:
            Lista wideo z linkami i metadanymi.
        """
        try:
            service = get_google_service(account_id, "youtube", "v3")
            response = (
                service.search()
                .list(
                    part="id,snippet",
                    q=query,
                    type="video",
                    order=order,
                    maxResults=min(limit, 50),
                )
                .execute()
            )

            items = response.get("items", [])
            if not items:
                return f"🔍 Brak wyników YouTube dla '{query}'."

            lines = [f"🔍 YouTube: wyniki dla '{query}' ({len(items)}):\n"]
            for item in items:
                vid_id = item["id"]["videoId"]
                snippet = item["snippet"]
                lines.append(
                    f"🎬 {snippet['title']}\n"
                    f"   👤 {snippet.get('channelTitle', '—')}"
                    f" | 📅 {snippet.get('publishedAt', '')[:10]}\n"
                    f"   🔗 https://youtu.be/{vid_id}"
                )

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"youtube_search_videos [{account_id}]: {e}")
            return f"❌ Błąd YouTube ({account_id}): {str(e)}"


# ── Pomocnicze funkcje ────────────────────────────────────────────────────────


def _fmt_num(value) -> str:
    """Formatuje dużą liczbę z separatorem tysięcy."""
    try:
        return f"{int(value):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(value)


def _parse_duration(iso_duration: str) -> str:
    """Konwertuje czas ISO 8601 (PT1H2M3S) na czytelny format HH:MM:SS."""
    import re

    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, iso_duration)
    if not match:
        return iso_duration
    h, m, s = (int(x or 0) for x in match.groups())
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
