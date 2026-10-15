"""
Parser for OCPP-J messages and payloads.
"""

import json
import re
from typing import Any
from src.models import OCPPLogEntry


def parse_ocpp_message(
    raw_message: str,
    event_name: str = "",
    event_type: str = "",
    message_type: str = "",
    timestamp: str = "",
    message_id_fallback: str = ""
) -> OCPPLogEntry:
    """
    Parses a raw OCPP-J message string into an OCPPLogEntry.
    Supports standard OCPP-J arrays:
      - [2, "<messageId>", "<Action>", <Payload>] (CALL)
      - [3, "<messageId>", <Payload>] (CALLRESULT)
      - [4, "<messageId>", "<errorCode>", "<errorDescription>", <errorDetails>] (CALLERROR)
    Also handles bare JSON dict payloads if the CMS exports only the payload.
    """
    cleaned = raw_message.strip()
    parsed_action = event_name or None
    parsed_payload: dict[str, Any] | list[Any] | None = None
    msg_id = message_id_fallback
    connector_id: int | None = None
    reason: str | None = None
    error_code: str | None = None
    info_val: str | None = None

    try:
        data = json.loads(cleaned)
        if isinstance(data, list) and len(data) >= 2:
            frame_type = data[0]
            msg_id = str(data[1])
            if frame_type == 2 and len(data) >= 4:
                parsed_action = str(data[2])
                parsed_payload = data[3]
            elif frame_type == 3 and len(data) >= 3:
                parsed_payload = data[2]
            elif frame_type == 4 and len(data) >= 5:
                error_code = str(data[2])
                parsed_payload = data[4]
        elif isinstance(data, dict):
            parsed_payload = data
    except Exception:
        # If not strict JSON, attempt regex fallback for common keys
        cid_match = re.search(r'["\']?connectorId["\']?\s*[:=]\s*(\d+)', cleaned, re.IGNORECASE)
        if cid_match:
            connector_id = int(cid_match.group(1))

        reason_match = re.search(r'["\']?reason["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)', cleaned, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1)

        err_match = re.search(r'["\']?errorCode["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)', cleaned, re.IGNORECASE)
        if err_match:
            error_code = err_match.group(1)

        info_match = re.search(r'["\']?info["\']?\s*[:=]\s*["\']([^"\']+)["\']', cleaned, re.IGNORECASE)
        if info_match:
            info_val = info_match.group(1).strip()
        else:
            info_val = None

    # Extract fields from parsed dictionary payload
    status_val: str | None = None
    vendor_err_val: str | None = None
    vendor_id_val: str | None = None

    if isinstance(parsed_payload, dict):
        # Look for connectorId
        if "connectorId" in parsed_payload:
            try:
                connector_id = int(parsed_payload["connectorId"])
            except (ValueError, TypeError):
                pass
        elif "connector_id" in parsed_payload:
            try:
                connector_id = int(parsed_payload["connector_id"])
            except (ValueError, TypeError):
                pass

        # Look for reason (e.g. StopTransaction)
        if "reason" in parsed_payload and parsed_payload["reason"]:
            reason = str(parsed_payload["reason"])

        # Look for errorCode (e.g. StatusNotification)
        if "errorCode" in parsed_payload and parsed_payload["errorCode"]:
            error_code = str(parsed_payload["errorCode"])

        # Look for status (e.g. StatusNotification status, or RemoteStart/Stop status)
        if "status" in parsed_payload and parsed_payload["status"]:
            status_val = str(parsed_payload["status"]).strip()

        # Look for info (e.g. StatusNotification info field)
        if "info" in parsed_payload and parsed_payload["info"]:
            info_val = str(parsed_payload["info"]).strip()

        # Look for vendorErrorCode and vendorId
        if "vendorErrorCode" in parsed_payload and parsed_payload["vendorErrorCode"]:
            vendor_err_val = str(parsed_payload["vendorErrorCode"]).strip()
        if "vendorId" in parsed_payload and parsed_payload["vendorId"]:
            vendor_id_val = str(parsed_payload["vendorId"]).strip()
    else:
        # Fallback regex search for status if not parsed as dict
        stat_match = re.search(r'["\']?status["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)', cleaned, re.IGNORECASE)
        if stat_match:
            status_val = stat_match.group(1).strip()
        vendor_err_match = re.search(r'["\']?vendorErrorCode["\']?\s*[:=]\s*["\']?([^"\',}]+)', cleaned, re.IGNORECASE)
        if vendor_err_match:
            vendor_err_val = vendor_err_match.group(1).strip()
        vendor_id_match = re.search(r'["\']?vendorId["\']?\s*[:=]\s*["\']?([^"\',}]+)', cleaned, re.IGNORECASE)
        if vendor_id_match:
            vendor_id_val = vendor_id_match.group(1).strip()

    return OCPPLogEntry(
        message_id=msg_id or "unknown",
        event_name=parsed_action or event_name or "Unknown",
        event_type=event_type,
        message_type=message_type,
        raw_message=raw_message,
        timestamp=timestamp,
        parsed_action=parsed_action,
        parsed_payload=parsed_payload,
        connector_id=connector_id,
        reason=reason,
        error_code=error_code,
        info=info_val,
        status=status_val,
        vendor_error_code=vendor_err_val,
        vendor_id=vendor_id_val
    )


def is_remote_start_status_rejected(logs: list[OCPPLogEntry]) -> bool:
    """
    Returns True ONLY when RemoteStartTransaction status is found to be 'rejected'.
    Checks direct event payload and correlated CALL / CALLRESULT by messageId.
    """
    if not logs:
        return False

    rs_call_msg_ids: set[str] = set()
    for e in logs:
        ev = (e.event_name or "").lower()
        act = (e.parsed_action or "").lower()
        raw = (e.raw_message or "").lower()
        if "remotestart" in ev or "remotestart" in act or "remotestarttransaction" in raw:
            mid = str(e.message_id).strip()
            if mid and mid.lower() not in ("unknown", "none", ""):
                rs_call_msg_ids.add(mid)

    for e in logs:
        ev = (e.event_name or "").lower()
        act = (e.parsed_action or "").lower()
        raw = e.raw_message or ""
        raw_lower = raw.lower()
        mid = str(e.message_id).strip() if e.message_id else ""

        is_rs_by_name = ("remotestart" in ev or "remotestart" in act or "remotestarttransaction" in raw_lower)
        is_rs_by_id = bool(mid and mid in rs_call_msg_ids)

        if is_rs_by_name or is_rs_by_id:
            if isinstance(e.parsed_payload, dict):
                st = str(e.parsed_payload.get("status") or "").strip().lower()
                if st == "rejected":
                    return True
            if re.search(r'["\']?status["\']?\s*[:=]\s*["\']?rejected["\']?', raw, re.IGNORECASE):
                return True

    return False


def is_remote_start_status_accepted(logs: list[OCPPLogEntry]) -> bool:
    """
    Returns True when RemoteStartTransaction status is found to be 'accepted'.
    Checks direct event payload and correlated CALL / CALLRESULT by messageId.
    """
    if not logs:
        return False

    rs_call_msg_ids: set[str] = set()
    for e in logs:
        ev = (e.event_name or "").lower()
        act = (e.parsed_action or "").lower()
        raw = (e.raw_message or "").lower()
        if "remotestart" in ev or "remotestart" in act or "remotestarttransaction" in raw:
            mid = str(e.message_id).strip()
            if mid and mid.lower() not in ("unknown", "none", ""):
                rs_call_msg_ids.add(mid)

    for e in logs:
        ev = (e.event_name or "").lower()
        act = (e.parsed_action or "").lower()
        raw = e.raw_message or ""
        raw_lower = raw.lower()
        mid = str(e.message_id).strip() if e.message_id else ""

        is_rs_by_name = ("remotestart" in ev or "remotestart" in act or "remotestarttransaction" in raw_lower)
        is_rs_by_id = bool(mid and mid in rs_call_msg_ids)

        if is_rs_by_name or is_rs_by_id:
            if isinstance(e.parsed_payload, dict):
                st = str(e.parsed_payload.get("status") or "").strip().lower()
                if st == "accepted":
                    return True
            if re.search(r'["\']?status["\']?\s*[:=]\s*["\']?accepted["\']?', raw, re.IGNORECASE):
                return True

    return False

