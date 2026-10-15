"""
Hourly Root Cause Analysis Engine with 15-minute Overlap for ElectreeFi CMS.
Analyzes the last 24 hours hour-by-hour with a 15-minute overlap window.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from pydantic import BaseModel, Field

from src.models import BookingDetails, RCAResult, mask_string
from src.scraper.browser import BrowserSession
from src.scraper.bookings import fetch_bookings_list
from src.scraper.booking_details import fetch_booking_details
from src.scraper.ocpp_logs import fetch_charger_logs_beta
from src.server import compute_time_window
from src.rca.engine import analyze_booking_rca

logger = logging.getLogger(__name__)


class HourlyWindowReport(BaseModel):
    """Report for an hourly slice with 15-minute overlap."""
    slot_index: int
    window_label: str  # e.g. "03:00 - 04:15"
    window_start: str
    window_end: str
    total_incidents: int
    cancelled_count: int
    low_consumption_count: int
    category_breakdown: dict[str, int] = Field(default_factory=dict)
    affected_chargers: list[str] = Field(default_factory=list)
    incidents: list[RCAResult] = Field(default_factory=list)


class Full24HourReport(BaseModel):
    """Comprehensive 24-hour analysis report."""
    analysis_start: str
    analysis_end: str
    total_incidents_analyzed: int
    total_cancelled: int
    total_low_consumption: int
    overall_category_breakdown: dict[str, int]
    hourly_slots: list[HourlyWindowReport]


def parse_flexible_dt(dt_str: str | None) -> datetime | None:
    """Parses various datetime string formats from the portal."""
    if not dt_str or not dt_str.strip():
        return None
    cleaned = dt_str.strip()
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
        "%Y-%m-%d",
        "%d-%m-%Y",
    ]:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


async def run_24hour_hourly_analysis(
    max_bookings_per_tab: int = 150,
    overlap_minutes: int = 15,
    low_consumption_threshold_kw: float = 1.0
) -> Full24HourReport:
    """
    Pulls all cancelled and low-consumption (<1 kWh) bookings from the last 24 hours,
    queries charger OCPP logs with a 15-minute overlap window, and produces an
    hour-by-hour breakdown with a 15-minute overlap.
    """
    now = datetime.now()
    start_24h = now - timedelta(hours=24)
    start_date_str = start_24h.strftime("%Y-%m-%d")
    end_date_str = now.strftime("%Y-%m-%d")

    logger.info(f"Starting 24h Hourly Analysis: {start_24h.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%Y-%m-%d %H:%M')}")

    all_rca_results: list[tuple[datetime, RCAResult]] = []

    async with BrowserSession(headless=True) as page:
        # 1. Fetch Cancelled bookings for date range
        logger.info(f"Fetching Cancelled bookings for {start_date_str} to {end_date_str}...")
        cancelled_records = await fetch_bookings_list(
            page=page,
            start_date=start_date_str,
            end_date=end_date_str,
            tab="Cancelled",
            max_rows=max_bookings_per_tab
        )

        # 2. Fetch Completed bookings for date range
        logger.info(f"Fetching Completed bookings to check < 1 kWh consumption...")
        completed_records = await fetch_bookings_list(
            page=page,
            start_date=start_date_str,
            end_date=end_date_str,
            tab="Completed",
            max_rows=max_bookings_per_tab
        )

        candidates = []
        for r in cancelled_records:
            candidates.append({"record": r, "type": "Cancelled"})
        for r in completed_records:
            candidates.append({"record": r, "type": "Completed"})

        logger.info(f"Total candidate bookings to evaluate: {len(candidates)}")

        for idx, item in enumerate(candidates, 1):
            rec = item["record"]
            try:
                details = await fetch_booking_details(
                    page=page,
                    booking_id=rec.booking_id,
                    row_selector=rec.details_link_selector
                )

                # Filter completed sessions: only keep if < 1 kWh (or 0)
                if item["type"] == "Completed":
                    if details.units_consumed_kw is not None and details.units_consumed_kw >= low_consumption_threshold_kw:
                        continue  # Normal completed charging, skip

                # Parse booking timestamp
                ref_time_str = details.booking_in_time or details.scheduled_in_time or rec.booking_start_time
                b_dt = parse_flexible_dt(ref_time_str) or now

                # Only include if within the 24h window
                if b_dt < (start_24h - timedelta(minutes=overlap_minutes)):
                    continue

                # Query OCPP logs with 15-minute overlap window
                start_win = (b_dt - timedelta(minutes=overlap_minutes)).strftime("%Y-%m-%d %H:%M")
                end_win = (b_dt + timedelta(minutes=overlap_minutes)).strftime("%Y-%m-%d %H:%M")

                logs = []
                if details.charger_code:
                    logs = await fetch_charger_logs_beta(
                        page=page,
                        charger_code=details.charger_code,
                        start_time=start_win,
                        end_time=end_win
                    )

                rca = analyze_booking_rca(
                    booking=details,
                    logs=logs,
                    low_consumption_threshold_kw=low_consumption_threshold_kw
                )
                all_rca_results.append((b_dt, rca))
                logger.info(f"[{idx}/{len(candidates)}] Booking {rec.booking_id} ({b_dt.strftime('%H:%M')}) -> {rca.category}: {rca.root_cause}")

            except Exception as e:
                logger.error(f"Error analyzing booking {rec.booking_id}: {e}")

    # 3. Construct Hourly Windows with 15-minute overlap
    # We slice the 24-hour range into 24 intervals, each covering [Hour_T, Hour_T + 1h + 15m overlap]
    hourly_slots: list[HourlyWindowReport] = []
    overall_categories: dict[str, int] = {}
    total_canc = 0
    total_low = 0

    curr_start = start_24h.replace(minute=0, second=0, microsecond=0)
    slot_idx = 1

    while curr_start < now:
        # Window of 1 hour + 15 minute overlap: [curr_start, curr_start + 75 minutes]
        curr_end = curr_start + timedelta(minutes=60 + overlap_minutes)
        window_label = f"{curr_start.strftime('%d-%b %H:%M')} to {curr_end.strftime('%H:%M')} (+{overlap_minutes}m)"

        slot_incidents: list[RCAResult] = []
        slot_categories: dict[str, int] = {}
        slot_chargers: set[str] = set()
        slot_canc = 0
        slot_low = 0

        for b_dt, rca in all_rca_results:
            if curr_start <= b_dt <= curr_end:
                slot_incidents.append(rca)
                slot_categories[rca.category] = slot_categories.get(rca.category, 0) + 1
                if rca.charger_code:
                    slot_chargers.add(rca.charger_code)
                if rca.units_consumed_kw is not None and rca.units_consumed_kw < low_consumption_threshold_kw:
                    slot_low += 1
                else:
                    slot_canc += 1

        if slot_incidents:
            hourly_slots.append(
                HourlyWindowReport(
                    slot_index=slot_idx,
                    window_label=window_label,
                    window_start=curr_start.strftime("%Y-%m-%d %H:%M"),
                    window_end=curr_end.strftime("%Y-%m-%d %H:%M"),
                    total_incidents=len(slot_incidents),
                    cancelled_count=slot_canc,
                    low_consumption_count=slot_low,
                    category_breakdown=slot_categories,
                    affected_chargers=list(slot_chargers),
                    incidents=slot_incidents
                )
            )

        curr_start += timedelta(hours=1)
        slot_idx += 1

    for _, rca in all_rca_results:
        overall_categories[rca.category] = overall_categories.get(rca.category, 0) + 1
        if rca.units_consumed_kw is not None and rca.units_consumed_kw < low_consumption_threshold_kw:
            total_low += 1
        else:
            total_canc += 1

    return Full24HourReport(
        analysis_start=start_24h.strftime("%Y-%m-%d %H:%M"),
        analysis_end=now.strftime("%Y-%m-%d %H:%M"),
        total_incidents_analyzed=len(all_rca_results),
        total_cancelled=total_canc,
        total_low_consumption=total_low,
        overall_category_breakdown=overall_categories,
        hourly_slots=hourly_slots
    )
