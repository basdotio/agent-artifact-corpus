"""
tools/analytics_tools.py – Narzędzia MCP dla Google Analytics (GA4).

Dostępne narzędzia:
  - analytics_get_overview     Podstawowe metryki za dany okres
  - analytics_top_pages        Najpopularniejsze strony
  - analytics_traffic_sources  Źródła ruchu
"""

import logging
from auth import get_google_service

logger = logging.getLogger(__name__)


def register_analytics_tools(mcp) -> None:
    """Rejestruje narzędzia Google Analytics w serwerze MCP."""

    @mcp.tool()
    def analytics_get_overview(
        account_id: str,
        property_id: str,
        days: int = 30,
    ) -> str:
        """
        Pobiera podstawowe metryki Google Analytics (GA4) za wybrany okres.

        Args:
            account_id:  Nazwa konta Google
            property_id: ID właściwości GA4 (np. '123456789', z panelu GA4)
            days:        Liczba dni wstecz (domyślnie 30)

        Returns:
            Sesje, użytkownicy, wyświetlenia stron, bounce rate.
        """
        try:
            service = get_google_service(account_id, "analyticsdata", "v1beta")
            response = (
                service.properties()
                .runReport(
                    property=f"properties/{property_id}",
                    body={
                        "dateRanges": [
                            {"startDate": f"{days}daysAgo", "endDate": "today"}
                        ],
                        "metrics": [
                            {"name": "sessions"},
                            {"name": "activeUsers"},
                            {"name": "screenPageViews"},
                            {"name": "bounceRate"},
                            {"name": "averageSessionDuration"},
                        ],
                    },
                )
                .execute()
            )

            rows = response.get("rows", [])
            if not rows:
                return f"📊 Brak danych Analytics dla property '{property_id}'."

            metrics = rows[0]["metricValues"]
            sessions = int(float(metrics[0]["value"]))
            users = int(float(metrics[1]["value"]))
            pageviews = int(float(metrics[2]["value"]))
            bounce = float(metrics[3]["value"]) * 100
            avg_session = float(metrics[4]["value"])
            avg_min = int(avg_session // 60)
            avg_sec = int(avg_session % 60)

            return (
                f"📊 GOOGLE ANALYTICS – ostatnie {days} dni\n{'─' * 40}\n"
                f"Property ID:        {property_id}\n"
                f"{'─' * 40}\n"
                f"Sesje:              {sessions:,}\n"
                f"Aktywni użytkow.:   {users:,}\n"
                f"Wyświetlenia stron: {pageviews:,}\n"
                f"Bounce rate:        {bounce:.1f}%\n"
                f"Śr. czas sesji:     {avg_min}m {avg_sec}s"
            )
        except Exception as e:
            logger.error(f"analytics_get_overview [{account_id}/{property_id}]: {e}")
            return f"❌ Błąd Analytics ({account_id}): {str(e)}"

    @mcp.tool()
    def analytics_top_pages(
        account_id: str,
        property_id: str,
        days: int = 30,
        limit: int = 10,
    ) -> str:
        """
        Pobiera listę najpopularniejszych stron.

        Args:
            account_id:  Nazwa konta Google
            property_id: ID właściwości GA4
            days:        Liczba dni wstecz
            limit:       Liczba wyników

        Returns:
            Ranking stron według wyświetleń.
        """
        try:
            service = get_google_service(account_id, "analyticsdata", "v1beta")
            response = (
                service.properties()
                .runReport(
                    property=f"properties/{property_id}",
                    body={
                        "dateRanges": [
                            {"startDate": f"{days}daysAgo", "endDate": "today"}
                        ],
                        "dimensions": [{"name": "pagePath"}],
                        "metrics": [
                            {"name": "screenPageViews"},
                            {"name": "activeUsers"},
                        ],
                        "orderBys": [
                            {"metric": {"metricName": "screenPageViews"}, "desc": True}
                        ],
                        "limit": limit,
                    },
                )
                .execute()
            )

            rows = response.get("rows", [])
            if not rows:
                return f"📄 Brak danych dla property '{property_id}'."

            lines = [f"📄 TOP {limit} STRON (ostatnie {days} dni):\n"]
            for i, row in enumerate(rows, 1):
                path = row["dimensionValues"][0]["value"]
                views = int(row["metricValues"][0]["value"])
                users = int(row["metricValues"][1]["value"])
                lines.append(
                    f"  {i:2}. {path}\n      Wyświetlenia: {views:,} | Użytkownicy: {users:,}"
                )

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"analytics_top_pages [{account_id}/{property_id}]: {e}")
            return f"❌ Błąd Analytics ({account_id}): {str(e)}"

    @mcp.tool()
    def analytics_traffic_sources(
        account_id: str,
        property_id: str,
        days: int = 30,
    ) -> str:
        """
        Pobiera źródła ruchu (organiczne, bezpośrednie, social media).

        Args:
            account_id:  Nazwa konta Google
            property_id: ID właściwości GA4
            days:        Liczba dni wstecz

        Returns:
            Rozkład ruchu według źródła/medium.
        """
        try:
            service = get_google_service(account_id, "analyticsdata", "v1beta")
            response = (
                service.properties()
                .runReport(
                    property=f"properties/{property_id}",
                    body={
                        "dateRanges": [
                            {"startDate": f"{days}daysAgo", "endDate": "today"}
                        ],
                        "dimensions": [{"name": "sessionDefaultChannelGrouping"}],
                        "metrics": [{"name": "sessions"}, {"name": "activeUsers"}],
                        "orderBys": [
                            {"metric": {"metricName": "sessions"}, "desc": True}
                        ],
                    },
                )
                .execute()
            )

            rows = response.get("rows", [])
            if not rows:
                return f"📊 Brak danych źródeł dla property '{property_id}'."

            lines = [f"📊 ŹRÓDŁA RUCHU (ostatnie {days} dni):\n"]
            total_sessions = sum(int(r["metricValues"][0]["value"]) for r in rows)

            for row in rows:
                channel = row["dimensionValues"][0]["value"]
                sessions = int(row["metricValues"][0]["value"])
                users = int(row["metricValues"][1]["value"])
                pct = (sessions / total_sessions * 100) if total_sessions > 0 else 0
                bar = "█" * int(pct / 5)
                lines.append(
                    f"  {channel}\n"
                    f"  {bar} {pct:.1f}% | Sesje: {sessions:,} | Użytkownicy: {users:,}"
                )

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"analytics_traffic_sources [{account_id}/{property_id}]: {e}")
            return f"❌ Błąd Analytics ({account_id}): {str(e)}"
