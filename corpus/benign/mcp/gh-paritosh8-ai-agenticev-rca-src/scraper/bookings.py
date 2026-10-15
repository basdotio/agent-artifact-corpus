"""
Scraper for ElectreeFi AdminBookingDetails table (Cancelled & Completed tabs).
Optimized for Kendo UI data grid and underlying AJAX responses.
"""

import logging
from typing import Any
from playwright.async_api import Page

from src.config import BOOKINGS_URL
from src.models import BookingRecord, mask_string

logger = logging.getLogger(__name__)


async def fetch_bookings_list(
    page: Page,
    start_date: str = "",
    end_date: str = "",
    tab: str = "Cancelled",
    max_rows: int = 50
) -> list[BookingRecord]:
    """
    Navigates to /ChargingStationManagement/AdminBookingDetails, switches to the requested tab,
    applies date filters if provided, and extracts booking rows from the Kendo UI grid.
    """
    await page.goto(BOOKINGS_URL, wait_until="domcontentloaded")

    if "/Account/Login" in page.url:
        raise PermissionError("ElectreeFi session expired or not logged in. Please run login first.")

    await page.wait_for_timeout(2000)

    # 1. Switch Tab (Upcoming / Completed / Cancelled)
    tab_name = tab.capitalize()
    tab_elem = page.locator(f"//a[contains(text(), '{tab_name}')]").first
    if await tab_elem.count() > 0:
        try:
            async with page.expect_response(
                lambda r: f"{tab_name}BookingDataThroughAjax" in r.url or "BookingDataThroughAjax" in r.url,
                timeout=15000
            ):
                await tab_elem.click()
            await page.wait_for_timeout(1500)
            logger.info(f"Switched to tab: {tab_name}")
        except Exception:
            # Fallback click without waiting for response
            await tab_elem.click()
            await page.wait_for_timeout(3000)

    # 2. Apply Date Range if provided
    if start_date or end_date:
        try:
            range_input = page.locator("#DateRange, input[name='DateRange'], input[id*='daterange' i]").first
            if await range_input.count() > 0 and await range_input.is_visible():
                date_str = f"{start_date} - {end_date}" if (start_date and end_date) else (start_date or end_date)
                await range_input.fill(date_str)
                await range_input.press("Enter")
                await page.wait_for_timeout(2500)
            else:
                if start_date:
                    from_input = page.locator("#StartDate, #FromDate, input[name*='From' i]").first
                    if await from_input.count() > 0 and await from_input.is_visible():
                        await from_input.fill(start_date)
                if end_date:
                    to_input = page.locator("#EndDate, #ToDate, input[name*='To' i]").first
                    if await to_input.count() > 0 and await to_input.is_visible():
                        await to_input.fill(end_date)
                search_btn = page.locator("//button[contains(text(), 'Search') or contains(text(), 'Filter') or contains(text(), 'Apply')]").first
                if await search_btn.count() > 0 and await search_btn.is_visible():
                    await search_btn.click()
                    await page.wait_for_timeout(3000)
        except Exception as e:
            logger.warning(f"Could not apply date filter: {e}")

    # 3. Read Kendo UI Grid Headers
    headers = await page.locator(".k-grid-header th").all_text_contents()
    clean_headers = [h.strip().lower() for h in headers if h.strip()]

    def find_col_idx(keyword: str, fallback_idx: int) -> int:
        for idx, h in enumerate(clean_headers):
            if keyword in h:
                return idx
        return fallback_idx

    id_col = find_col_idx("booking id", 0)
    start_time_col = find_col_idx("booking start time", 1)
    stop_time_col = find_col_idx("booking stop time", 2)
    connector_col = find_col_idx("connector id", 3)
    user_status_col = find_col_idx("user status", 4)
    station_org_col = find_col_idx("station organization", 5)
    user_name_col = find_col_idx("user name", 8)
    mobile_col = find_col_idx("mobile number", 9)
    charger_name_col = find_col_idx("charger name", 17)
    mode_col = find_col_idx("booking mode", 25)

    # 4. Read Data Rows
    data_table = page.locator("table.k-selectable, table:has(tbody tr td)").first
    rows = await data_table.locator("tbody tr").all()
    records: list[BookingRecord] = []

    for i, row in enumerate(rows):
        if i >= max_rows:
            break

        cells = await row.locator("td").all_text_contents()
        if not cells or len(cells) < 4:
            continue

        booking_id = cells[id_col].strip() if id_col < len(cells) else cells[0].strip()
        start_time = cells[start_time_col].strip() if start_time_col < len(cells) else None
        stop_time = cells[stop_time_col].strip() if stop_time_col < len(cells) else None
        connector_id = cells[connector_col].strip() if connector_col < len(cells) else None
        user_status = cells[user_status_col].strip() if user_status_col < len(cells) else None
        station_org = cells[station_org_col].strip() if station_org_col < len(cells) else None
        user_name = cells[user_name_col].strip() if user_name_col < len(cells) else None
        mobile = cells[mobile_col].strip() if mobile_col < len(cells) else None
        mode = cells[mode_col].strip() if mode_col < len(cells) else None

        records.append(
            BookingRecord(
                booking_id=booking_id,
                booking_start_time=start_time,
                booking_stop_time=stop_time,
                connector_id=connector_id,
                user_status=user_status,
                station_organization=station_org,
                user_name_masked=mask_string(user_name),
                mobile_number_masked=mask_string(mobile),
                booking_mode=mode,
                tab=tab_name,
                details_link_selector=f"LoadBookingDetailsView('{booking_id}')"
            )
        )

    logger.info(f"Fetched {len(records)} booking records from tab '{tab_name}'")
    return records
