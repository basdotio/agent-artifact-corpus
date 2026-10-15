"""
Scraper and fast JSON API fetcher for ElectreeFi Charger Logs (Beta).
Leverages direct underlying endpoints discovered via network sniffing:
- Resolves ChargerID & ConnectionID via LoadChargerStatusViewThroughAjaxFor_Data/3
- Pulls raw OCPP-J logs via GetOcppLogs
"""

import logging
from typing import Any
from urllib.parse import quote
from playwright.async_api import Page

from src.models import OCPPLogEntry
from src.rca.ocpp_parser import parse_ocpp_message

logger = logging.getLogger(__name__)

# Cache of ChargerCode -> (ChargerID, ConnectionID)
CHARGER_META_CACHE: dict[str, dict[str, Any]] = {}


async def resolve_charger_meta(page: Page, charger_code: str) -> dict[str, Any] | None:
    """
    Resolves ChargerID and ConnectionID for a given charger code using the fast Kendo grid endpoint.
    """
    clean_code = charger_code.strip()
    if clean_code in CHARGER_META_CACHE:
        return CHARGER_META_CACHE[clean_code]

    try:
        res = await page.evaluate(f'''async () => {{
            const params = new URLSearchParams();
            params.append('page', '1');
            params.append('pageSize', '5');
            params.append('filter', "ChargerCode~contains~'{clean_code}'");
            
            const r = await fetch('/OCPPManagement/OCPP/LoadChargerStatusViewThroughAjaxFor_Data/3', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                body: params.toString()
            }});
            return await r.json();
        }}''')

        if res and res.get("Data"):
            for item in res["Data"]:
                if item.get("ChargerCode", "").lower() == clean_code.lower():
                    meta = {
                        "charger_id": item.get("ChargerID"),
                        "connection_id": item.get("ConnectionID"),
                        "status": item.get("Status"),
                        "station_name": item.get("ChargingStationName")
                    }
                    CHARGER_META_CACHE[clean_code] = meta
                    logger.info(f"Resolved {clean_code} -> ChargerID: {meta['charger_id']}")
                    return meta

            # If exact match not found, take the first match
            first = res["Data"][0]
            meta = {
                "charger_id": first.get("ChargerID"),
                "connection_id": first.get("ConnectionID"),
                "status": first.get("Status"),
                "station_name": first.get("ChargingStationName")
            }
            CHARGER_META_CACHE[clean_code] = meta
            return meta
    except Exception as e:
        logger.warning(f"Failed to resolve charger meta via API for {clean_code}: {e}")

    return None


async def fetch_charger_logs_beta(
    page: Page,
    charger_code: str,
    start_time: str,
    end_time: str,
    exclude_events: list[str] | None = None,
    max_entries: int = 100
) -> list[OCPPLogEntry]:
    """
    Fetches raw OCPP log frames from the 'Charger Logs (Beta)' endpoint for a specific time window.
    Filters out noise events like 'Heartbeat' and 'MeterValues'.
    """
    if exclude_events is None:
        exclude_events = ["heartbeat", "metervalues"]
    else:
        exclude_events = [e.lower() for e in exclude_events]

    # Ensure page is on portal
    if "ev-charge-network.com" not in page.url:
        await page.goto("https://cms.ev-charge-network.com/OCPPManagement/OCPP/OCPPChargerStatus", wait_until="domcontentloaded")

    # 1. Resolve ChargerID
    meta = await resolve_charger_meta(page, charger_code)
    charger_id = meta.get("charger_id") if meta else None

    if not charger_id:
        logger.warning(f"Could not resolve ChargerID for {charger_code}. Cannot query OCPP logs.")
        return []

    # 2. Format timestamps (YYYY-MM-DD HH:MM:SS)
    from_str = start_time if len(start_time) == 19 else f"{start_time}:00" if len(start_time) == 16 else start_time
    to_str = end_time if len(end_time) == 19 else f"{end_time}:00" if len(end_time) == 16 else end_time

    # Space encoded as %20, colons unencoded
    from_enc = from_str.replace(" ", "%20")
    to_enc = to_str.replace(" ", "%20")

    endpoint = f"/GetOcppLogs?entityId={charger_id}&fromDate={from_enc}&toDate={to_enc}"

    logger.info(f"Querying GetOcppLogs for {charger_code} (entityId: {charger_id}) from {from_str} to {to_str}")

    try:
        raw_res = await page.evaluate(f'''async () => {{
            const formData = new URLSearchParams();
            formData.append('page', '1');
            formData.append('pageSize', '{max_entries}');
            formData.append('sort', '');
            formData.append('group', '');
            formData.append('filter', '');
            
            const r = await fetch('{endpoint}', {{
                method: 'POST',
                headers: {{
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
                }},
                body: formData.toString()
            }});
            return await r.json();
        }}''')

        log_items = raw_res.get("Data", []) if isinstance(raw_res, dict) else []
        entries: list[OCPPLogEntry] = []

        for item in log_items:
            ev_name = str(item.get("EventName") or "")
            if ev_name.lower() in exclude_events:
                continue

            raw_msg = str(item.get("Message") or "")
            msg_id = str(item.get("MessageId") or "")
            msg_type = str(item.get("MessageTypeName") or "")
            timestamp = str(item.get("Date") or item.get("Timestamp") or "")

            entry = parse_ocpp_message(
                raw_message=raw_msg,
                event_name=ev_name,
                message_type=msg_type,
                timestamp=timestamp,
                message_id_fallback=msg_id
            )
            entries.append(entry)

        logger.info(f"Retrieved {len(entries)} relevant non-noise OCPP logs for {charger_code}")
        return entries

    except Exception as e:
        logger.error(f"Error calling GetOcppLogs API: {e}")
        return []
