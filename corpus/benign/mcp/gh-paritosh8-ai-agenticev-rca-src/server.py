"""
FastMCP Server for ElectreeFi CMS Booking Root Cause Analysis (RCA).
Exposes tools to log in, scrape bookings, retrieve charger logs, and run automated RCA.
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import Any
from mcp.server.mcpserver import MCPServer

from src.config import (
    SESSION_STORAGE_PATH,
    RCA_LOG_TIME_WINDOW_MINUTES,
    RCA_LOW_CONSUMPTION_THRESHOLD_KW
)
from src.auth.session_manager import interactive_login, is_session_valid
from src.scraper.browser import BrowserSession, CAPTURED_JSON_RESPONSES
from src.scraper.bookings import fetch_bookings_list
from src.scraper.booking_details import fetch_booking_details
from src.scraper.ocpp_logs import fetch_charger_logs_beta
from src.rca.engine import analyze_booking_rca, generate_rca_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("electreefi_server")

# Initialize MCP Server
app = MCPServer(
    name="electreefi-rca",
    instructions=(
        "ElectreeFi CMS RCA Server connects to the ElectreeFi Charging Management System. "
        "Use `login()` to initiate semi-automated authentication (CAPTCHA + OTP). "
        "Use `get_bookings()` to retrieve cancelled or completed bookings. "
        "Use `get_booking_details()` to view modal details. "
        "Use `get_charger_logs()` to retrieve raw OCPP-J logs for a charger. "
        "Use `run_rca()` to run end-to-end root cause analysis across multiple bookings."
    )
)


def compute_time_window(time_str: str | None, window_mins: int = 10) -> tuple[str, str]:
    """Computes [time - window, time + window] formatted for the portal's date-time picker."""
    now = datetime.now()
    if not time_str or not time_str.strip():
        start = (now - timedelta(minutes=window_mins)).strftime("%Y-%m-%d %H:%M")
        end = (now + timedelta(minutes=window_mins)).strftime("%Y-%m-%d %H:%M")
        return start, end

    # Common formats used in Indian EV CMS portals (including 12-hr AM/PM)
    for fmt in [
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %I:%M %p",
        "%d-%m-%Y %I:%M:%S %p",
        "%d-%m-%Y %I:%M %p",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(time_str.strip(), fmt)
            start = (dt - timedelta(minutes=window_mins)).strftime("%Y-%m-%d %H:%M")
            end = (dt + timedelta(minutes=window_mins)).strftime("%Y-%m-%d %H:%M")
            return start, end
        except ValueError:
            continue

    # Fallback to now
    start = (now - timedelta(minutes=window_mins)).strftime("%Y-%m-%d %H:%M")
    end = (now + timedelta(minutes=window_mins)).strftime("%Y-%m-%d %H:%M")
    return start, end


@app.tool()
async def login(force: bool = False) -> str:
    """
    Launches a visible Google Chrome window to log into the ElectreeFi CMS portal.
    Prompts the user to manually solve the CAPTCHA and enter their email OTP.
    Once login completes, session cookies are securely stored for automated background reuse.

    Args:
        force: If True, forces a fresh login even if an existing session is still valid.
    """
    return await interactive_login(force=force)


@app.tool()
async def get_bookings(
    date_range: str = "",
    tab: str = "Cancelled",
    max_bookings: int = 50
) -> list[dict[str, Any]]:
    """
    Retrieves charging bookings from ElectreeFi AdminBookingDetails.

    Args:
        date_range: Optional date range filter (e.g. '2026-09-12 to 2026-09-13' or '12/09/2026'). Defaults to today.
        tab: Tab to pull from ('Cancelled', 'Completed', or 'New'). Defaults to 'Cancelled'.
        max_bookings: Maximum number of rows to retrieve (default: 50).
    """
    async with BrowserSession(headless=True) as page:
        records = await fetch_bookings_list(
            page=page,
            start_date=date_range,
            tab=tab,
            max_rows=max_bookings
        )
        return [r.model_dump() for r in records]


@app.tool()
async def get_booking_details(booking_id: str) -> dict[str, Any]:
    """
    Retrieves detailed modal popup data for a specific booking ID,
    including Charger Code, Connector Sequence Id, Units Consumed (kW), and Stop Reasons.

    Args:
        booking_id: The unique ID of the booking to look up.
    """
    async with BrowserSession(headless=True) as page:
        # First navigate to bookings page
        await fetch_bookings_list(page, max_rows=10)
        details = await fetch_booking_details(page, booking_id=booking_id)
        return details.model_dump()


@app.tool()
async def get_charger_logs(
    charger_code: str,
    start_time: str,
    end_time: str,
    exclude_noise: bool = True
) -> list[dict[str, Any]]:
    """
    Retrieves raw OCPP-J charger logs from the 'Charger Logs (Beta)' tab for a specific time window.

    Args:
        charger_code: The code of the charger (e.g. 'DL-04-01').
        start_time: Window start timestamp (e.g. '2026-09-13 14:00').
        end_time: Window end timestamp (e.g. '2026-09-13 14:20').
        exclude_noise: If True, excludes high-frequency Heartbeat and MeterValues messages (default: True).
    """
    exclude = ["Heartbeat", "MeterValues"] if exclude_noise else []
    async with BrowserSession(headless=True) as page:
        entries = await fetch_charger_logs_beta(
            page=page,
            charger_code=charger_code,
            start_time=start_time,
            end_time=end_time,
            exclude_events=exclude
        )
        return [e.model_dump() for e in entries]


@app.tool()
async def run_rca(
    date_range: str = "",
    include_low_consumption: bool = True,
    max_bookings: int = 20
) -> dict[str, Any]:
    """
    Orchestrates end-to-end Root Cause Analysis (RCA) on cancelled and low-consumption bookings.
    1. Pulls candidate cancelled bookings (and completed <1 kW bookings).
    2. Opens Details popup for each booking to identify Charger Code and Connector ID.
    3. Retrieves corresponding OCPP logs in a ±10 minute window around the event.
    4. Evaluates StopTransaction reasons and StatusNotification error codes.
    5. Returns an aggregated executive summary report and individual classifications.

    Args:
        date_range: Date range to analyze (e.g. '2026-09-12 - 2026-09-13').
        include_low_consumption: If True, also checks completed bookings with < 1 kW consumption.
        max_bookings: Limit on the number of bookings to analyze in this batch (default: 20).
    """
    logger.info(f"Starting RCA pipeline for date range: '{date_range}' (max: {max_bookings})")

    candidates: list[dict[str, Any]] = []

    async with BrowserSession(headless=True) as page:
        # 1. Pull Cancelled bookings
        cancelled_records = await fetch_bookings_list(
            page=page,
            start_date=date_range,
            tab="Cancelled",
            max_rows=max_bookings
        )
        for r in cancelled_records:
            candidates.append({"record": r, "type": "Cancelled"})

        # 2. Pull Completed bookings for low-consumption check if requested
        if include_low_consumption and len(candidates) < max_bookings:
            remaining = max_bookings - len(candidates)
            completed_records = await fetch_bookings_list(
                page=page,
                start_date=date_range,
                tab="Completed",
                max_rows=remaining
            )
            for r in completed_records:
                candidates.append({"record": r, "type": "Completed"})

        # 3. Process each candidate: get details & correlate with logs
        results = []
        for item in candidates:
            rec = item["record"]
            try:
                # Get modal details
                details = await fetch_booking_details(
                    page=page,
                    booking_id=rec.booking_id,
                    row_selector=rec.details_link_selector
                )

                # If from Completed tab, filter only if low consumption (< 1 kW)
                if item["type"] == "Completed":
                    if details.units_consumed_kw is not None and details.units_consumed_kw >= RCA_LOW_CONSUMPTION_THRESHOLD_KW:
                        continue  # Normal successful session, skip

                # Compute time window
                ref_time = details.booking_in_time or details.scheduled_in_time or rec.booking_start_time
                start_win, end_win = compute_time_window(ref_time, window_mins=RCA_LOG_TIME_WINDOW_MINUTES)

                # Fetch charger logs if charger code is available
                logs = []
                if details.charger_code:
                    logs = await fetch_charger_logs_beta(
                        page=page,
                        charger_code=details.charger_code,
                        start_time=start_win,
                        end_time=end_win
                    )

                # Analyze RCA
                rca = analyze_booking_rca(
                    booking=details,
                    logs=logs,
                    low_consumption_threshold_kw=RCA_LOW_CONSUMPTION_THRESHOLD_KW
                )
                results.append(rca)

            except Exception as e:
                logger.error(f"Error processing booking {rec.booking_id}: {e}")

        # Generate aggregated report
        report = generate_rca_report(
            date_range=date_range or "Today",
            results=results
        )

        return report.model_dump()


def main():
    """Main entrypoint running the stdio MCP server."""
    logger.info("Starting ElectreeFi RCA MCP Server (stdio transport)...")
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
