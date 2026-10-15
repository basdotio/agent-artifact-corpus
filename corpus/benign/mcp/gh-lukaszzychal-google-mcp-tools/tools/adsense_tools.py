"""
tools/adsense_tools.py – Narzędzia MCP dla Google AdSense.

Dostępne narzędzia:
  - adsense_account_info   Informacje o koncie AdSense
  - adsense_earnings       Przychody za wybrany okres
  - adsense_top_sites      Najlepiej zarabiające strony
"""

import logging
from datetime import date, timedelta
from auth import get_google_service

logger = logging.getLogger(__name__)


def register_adsense_tools(mcp) -> None:
    """Rejestruje narzędzia Google AdSense w serwerze MCP."""

    @mcp.tool()
    def adsense_account_info(account_id: str) -> str:
        """
        Pobiera informacje o koncie Google AdSense.

        Args:
            account_id: Nazwa konta Google powiązanego z AdSense

        Returns:
            Nazwa konta, waluta, status i dostępne strony.
        """
        try:
            service = get_google_service(account_id, "adsense", "v2")
            accounts = service.accounts().list().execute()
            items = accounts.get("accounts", [])

            if not items:
                return f"💰 Brak konta AdSense na koncie '{account_id}'."

            acc = items[0]
            return (
                f"💰 KONTO ADSENSE\n{'─' * 40}\n"
                f"Nazwa:     {acc.get('displayName', '—')}\n"
                f"ID:        {acc.get('name', '—')}\n"
                f"Waluta:    {acc.get('currencyCode', '—')}\n"
                f"Timezone:  {acc.get('timeZone', {}).get('id', '—')}\n"
                f"Status:    {acc.get('state', '—')}"
            )
        except Exception as e:
            logger.error(f"adsense_account_info [{account_id}]: {e}")
            return f"❌ Błąd AdSense ({account_id}): {str(e)}"

    @mcp.tool()
    def adsense_earnings(
        account_id: str,
        days: int = 30,
        currency: str = "PLN",
    ) -> str:
        """
        Pobiera przychody z Google AdSense za wybrany okres.

        Args:
            account_id: Nazwa konta Google
            days:       Liczba dni wstecz (domyślnie 30)
            currency:   Waluta wyświetlania (domyślnie PLN)

        Returns:
            Łączne przychody, liczba wyświetleń i kliknięć.
        """
        try:
            service = get_google_service(account_id, "adsense", "v2")
            accounts_resp = service.accounts().list().execute()
            accounts_list = accounts_resp.get("accounts", [])
            if not accounts_list:
                return f"💰 Brak konta AdSense na koncie '{account_id}'."

            account_name = accounts_list[0]["name"]
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            report = (
                service.accounts()
                .reports()
                .generate(
                    account=account_name,
                    dateRange="CUSTOM",
                    startDate_year=start_date.year,
                    startDate_month=start_date.month,
                    startDate_day=start_date.day,
                    endDate_year=end_date.year,
                    endDate_month=end_date.month,
                    endDate_day=end_date.day,
                    metrics=[
                        "ESTIMATED_EARNINGS",
                        "PAGE_VIEWS",
                        "CLICKS",
                        "PAGE_VIEWS_RPM",
                    ],
                )
                .execute()
            )

            totals = report.get("totals", {}).get("cells", [])
            if not totals:
                return f"💰 Brak danych przychodów za ostatnie {days} dni."

            earnings = float(totals[0].get("value", 0))
            pageviews = int(float(totals[1].get("value", 0)))
            clicks = int(float(totals[2].get("value", 0)))
            rpm = float(totals[3].get("value", 0))

            return (
                f"💰 PRZYCHODY ADSENSE – ostatnie {days} dni\n{'─' * 40}\n"
                f"Przychody:    {earnings:.2f} {currency}\n"
                f"Wyświetlenia: {pageviews:,}\n"
                f"Kliknięcia:   {clicks:,}\n"
                f"RPM strony:   {rpm:.2f} {currency}\n"
                f"CTR:          {(clicks/pageviews*100):.3f}%"
                if pageviews > 0
                else ""
            )
        except Exception as e:
            logger.error(f"adsense_earnings [{account_id}]: {e}")
            return f"❌ Błąd AdSense ({account_id}): {str(e)}"

    @mcp.tool()
    def adsense_top_sites(account_id: str, days: int = 30) -> str:
        """
        Pobiera najlepiej zarabiające strony w AdSense.

        Args:
            account_id: Nazwa konta Google
            days:       Liczba dni wstecz

        Returns:
            Ranking stron według przychodów.
        """
        try:
            service = get_google_service(account_id, "adsense", "v2")
            accounts_resp = service.accounts().list().execute()
            accounts_list = accounts_resp.get("accounts", [])
            if not accounts_list:
                return f"💰 Brak konta AdSense."

            account_name = accounts_list[0]["name"]
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            report = (
                service.accounts()
                .reports()
                .generate(
                    account=account_name,
                    dateRange="CUSTOM",
                    startDate_year=start_date.year,
                    startDate_month=start_date.month,
                    startDate_day=start_date.day,
                    endDate_year=end_date.year,
                    endDate_month=end_date.month,
                    endDate_day=end_date.day,
                    dimensions=["DOMAIN_NAME"],
                    metrics=["ESTIMATED_EARNINGS", "PAGE_VIEWS"],
                    orderBy=["-ESTIMATED_EARNINGS"],
                )
                .execute()
            )

            rows = report.get("rows", [])
            if not rows:
                return f"💰 Brak danych stron za ostatnie {days} dni."

            lines = [f"💰 TOP STRONY ADSENSE (ostatnie {days} dni):\n"]
            for i, row in enumerate(rows[:10], 1):
                cells = row.get("cells", [])
                domain = cells[0].get("value", "?") if len(cells) > 0 else "?"
                earnings = float(cells[1].get("value", 0)) if len(cells) > 1 else 0
                pageviews = (
                    int(float(cells[2].get("value", 0))) if len(cells) > 2 else 0
                )
                lines.append(
                    f"  {i:2}. {domain}\n"
                    f"       Przychody: {earnings:.2f} | Wyświetlenia: {pageviews:,}"
                )

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"adsense_top_sites [{account_id}]: {e}")
            return f"❌ Błąd AdSense ({account_id}): {str(e)}"
