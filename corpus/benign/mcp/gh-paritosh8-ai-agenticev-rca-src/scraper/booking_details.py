"""
Scraper for the Booking Details popup modal in ElectreeFi CMS.
Uses direct function invocation and form input inspection.
"""

import re
import logging
from playwright.async_api import Page

from src.models import BookingDetails, mask_string

logger = logging.getLogger(__name__)


async def fetch_booking_details(page: Page, booking_id: str, row_selector: str | None = None) -> BookingDetails:
    """
    Opens the Details popup modal for a specific booking and extracts all fields.
    """
    clean_id = str(booking_id).strip()

    # Wait for the modal content endpoint when calling LoadBookingDetailsView
    try:
        async with page.expect_response(lambda r: "LoadBookingDetails" in r.url, timeout=15000):
            await page.evaluate(f"window.LoadBookingDetailsView && window.LoadBookingDetailsView('{clean_id}')")
        await page.wait_for_timeout(1000)
    except Exception as e:
        logger.warning(f"Response wait timed out or failed, checking modal directly: {e}")
        await page.evaluate(f"window.LoadBookingDetailsView && window.LoadBookingDetailsView('{clean_id}')")
        await page.wait_for_timeout(2000)

    # Extract all inputs/selects/textareas inside the modal
    kv: dict[str, str] = await page.evaluate('''() => {
        const result = {};
        const modal = document.querySelector('#ChargingStationBookingDetailsView') || document;
        const inputs = modal.querySelectorAll('input, textarea, select');
        inputs.forEach(el => {
            const title = el.getAttribute('title') || '';
            const label = el.closest('div')?.querySelector('label')?.innerText || '';
            const key = (title || label).trim().toLowerCase();
            const val = (el.value || el.getAttribute('value') || '').trim();
            if (key) result[key] = val;
        });
        return result;
    }''')

    def get_val(*keywords: str) -> str | None:
        for kw in keywords:
            kw_low = kw.lower()
            for k, v in kv.items():
                if kw_low in k:
                    return v
        return None

    # Parse Units Consumed
    units_raw = get_val("units consumed", "units (kw)", "units")
    units_float: float | None = None
    if units_raw:
        try:
            cleaned = re.sub(r"[^\d.]", "", units_raw)
            if cleaned:
                units_float = float(cleaned)
        except ValueError:
            pass

    # Parse Connector Sequence Id
    conn_seq_raw = get_val("connector sequence id", "connector sequence", "connector id")
    conn_seq_int: int | None = None
    if conn_seq_raw:
        try:
            m = re.search(r"\d+", conn_seq_raw)
            if m:
                conn_seq_int = int(m.group(0))
        except ValueError:
            pass

    details = BookingDetails(
        booking_id=clean_id,
        user_name_masked=mask_string(get_val("name", "user name")),
        mobile_number_masked=mask_string(get_val("mobile number", "mobile", "phone")),
        vehicle_number_masked=mask_string(get_val("vehicle number", "vehicle")),
        vin_number_masked=mask_string(get_val("vin number", "vin")),
        booking_mode=get_val("booking mode"),
        booking_type=get_val("booking type"),
        connector_type=get_val("connector type"),
        booking_date=get_val("booking date"),
        created_on=get_val("created on"),
        booking_in_time=get_val("booking in time"),
        booking_out_time=get_val("booking out time"),
        scheduled_in_time=get_val("scheduled in time"),
        scheduled_out_time=get_val("scheduled out time"),
        actual_in_time=get_val("actual in time"),
        actual_out_time=get_val("actual out time"),
        station_name=get_val("station name", "station"),
        charger_code=get_val("charger code", "charger"),
        connector_sequence_id=conn_seq_int,
        is_quick_charge=get_val("is quick charge"),
        initial_soc=get_val("initial soc"),
        final_soc=get_val("final soc"),
        units_consumed_kw=units_float,
        charging_amount=get_val("charging amount"),
        start_reading=get_val("start reading"),
        stop_reading=get_val("stop reading"),
        stop_reason_from_charger=get_val("stop reason"),
        blocked_out_time=get_val("blocked out time"),
        stop_triggered_condition_from_server=get_val("stop triggered condition"),
        authentication_status=get_val("authentication status"),
        authentication_reason=get_val("authentication reason"),
        id_tag_used=get_val("id tag used"),
        transaction_stopped_on=get_val("transaction stopped on"),
        total_payable=get_val("total amount", "total payable"),
        payment_status=get_val("payment status"),
        invoice_generated=get_val("invoice generated")
    )

    # Close modal
    try:
        await page.evaluate('''() => {
            const modal = document.querySelector('#ChargingStationBookingDetailsView');
            if (modal) {
                const closeBtn = modal.querySelector('button.close, [data-dismiss="modal"], .btn-close');
                if (closeBtn) closeBtn.click();
            }
        }''')
        await page.wait_for_timeout(500)
    except Exception:
        pass

    return details
