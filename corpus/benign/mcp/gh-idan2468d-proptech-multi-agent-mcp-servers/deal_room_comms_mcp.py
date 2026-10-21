from datetime import datetime, timedelta, timezone
from typing import Any
from mcp_servers.proptech_mcp_server import FastMCP

mcp = FastMCP("PropTech-DealRoom-Comms-MCP")


@mcp.tool()
def mcp_generate_deal_share_package(
    run_id: str,
    property_address: str,
    recommendation: str,
    target_closing_price_ils: float,
    webhook_channel: str = "#proptech-deals",
) -> dict[str, Any]:
    """
    Generate a Slack/Webhook deal alert payload and an iCalendar (.ics) tour invitation.
    """
    tour_start = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y%m%dT090000Z")
    tour_end = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y%m%dT100000Z")

    ics_content = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//PropTech Multi-Agent Analyzer//HE\n"
        "BEGIN:VEVENT\n"
        f"UID:proptech-tour-{run_id}\n"
        f"DTSTART:{tour_start}\n"
        f"DTEND:{tour_end}\n"
        f"SUMMARY:סיור נכס ובדיקת שמאות - {property_address}\n"
        f"DESCRIPTION:המלצת מערכת: {recommendation} | מחיר יעד לסגירה: {target_closing_price_ils:,.0f} ILS\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )

    return {
        "dispatched": True,
        "run_id": run_id,
        "webhook_channel": webhook_channel,
        "slack_message_preview": (
            f"🏢 *הזדמנות נדל״ן חדשה נותחה ({recommendation})*\n"
            f"• נכס: {property_address}\n"
            f"• מחיר יעד מומלץ לסגירה במו״מ: ₪{target_closing_price_ils:,.0f}"
        ),
        "calendar_ics": ics_content,
    }


if __name__ == "__main__":
    mcp.run()
