"""
ElectreeFi Single Booking RCA Deep Dive & Investigation Engine
Searches for specific Cancelled bookings or Completed bookings (<1 kWh),
retrieves transaction details, correlates OCPP logs, and generates a descriptive,
attribution-focused Root Cause Analysis (Vehicle vs Charger vs User vs Network).
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

from src.models import OCPPLogEntry
from src.config import SESSION_STORAGE_PATH
from src.rca.ocpp_parser import parse_ocpp_message, is_remote_start_status_rejected, is_remote_start_status_accepted


def get_cookie_header() -> str:
    cookie_path = str(SESSION_STORAGE_PATH) if SESSION_STORAGE_PATH.exists() else "data/session_state.json"
    if not os.path.exists(cookie_path):
        return ""
    try:
        with open(cookie_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = data.get("cookies", [])
        return "; ".join([f"{c['name']}={c['value']}" for c in cookies if "electreefi.com" in c.get("domain", "")])
    except Exception:
        return ""


def parse_flexible_dt(t_str: str | None) -> datetime | None:
    if not t_str or not t_str.strip():
        return None
    cleaned = t_str.strip()
    for fmt in [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %I:%M %p",
        "%d-%m-%Y %I:%M:%S %p",
        "%d-%m-%Y %I:%M %p",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y"
    ]:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def fetch_cancelled_booking(booking_id: str, start_date: str, end_date: str, cookie_header: str) -> tuple[dict | None, int]:
    """Queries the Cancelled bookings endpoint for a specific booking ID with exact server filtering."""
    url = f"https://emonitoring.electreefi.com/ChargingStationManagement/AdminBookingDetails/CancelledBookingDataThroughAjax?StationId=&StartDate={start_date}&Enddate={end_date}&stateId=&cityId=&transactionTypeId=-1&Id=0&vin=&chargerCode=&user=&vehicleNumber="
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_header
    }

    try:
        payload = urllib.parse.urlencode({
            "page": "1",
            "pageSize": "10",
            "sort": "",
            "group": "",
            "filter": f"ChargingStationBookingId~eq~{booking_id}"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("Data") or []
            for it in items:
                if str(it.get("ChargingStationBookingId")) == str(booking_id):
                    it["_SessionType"] = "Cancelled"
                    return it, 1
    except Exception:
        pass

    return None, 1


def fetch_completed_booking(booking_id: str, start_date: str, end_date: str, cookie_header: str) -> tuple[dict | None, int]:
    """Queries the Past/Completed bookings endpoint for a specific booking ID with exact server filtering."""
    url = f"https://emonitoring.electreefi.com/ChargingStationManagement/AdminBookingDetails/PastBookingDataThroughAjax?StartDate={start_date}&Enddate={end_date}&transactionTypeId=-1&Id=0&StationId=&stateId=&cityId=&vin=&chargerCode=&user=&vehicleNumber=&i="
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_header
    }

    try:
        payload = urllib.parse.urlencode({
            "page": "1",
            "pageSize": "10",
            "sort": "",
            "group": "",
            "filter": f"ChargingStationBookingId~eq~{booking_id}"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("Data") or []
            for it in items:
                if str(it.get("ChargingStationBookingId")) == str(booking_id):
                    it["_SessionType"] = "Completed (<1kWh)"
                    return it, 1
    except Exception:
        pass

    return None, 1


def fetch_roaming_booking(booking_id: str, cookie_header: str) -> tuple[dict | None, int]:
    """Queries Roaming OCPI reservation endpoint for bookings that originate via roaming protocols."""
    url = f"https://emonitoring.electreefi.com/Roaming/OCPIReservation/GetChargingStatusdetail?BookingId={booking_id}"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_header
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data and isinstance(data, dict):
                res_sec = data.get("reservation") or {}
                ss_sec = data.get("startSession") or {}
                sess_sec = data.get("session") or {}

                evse_uid = res_sec.get("evse_uid") or res_sec.get("evseid") or ""
                b_id = res_sec.get("booking_id") or booking_id

                # Parse OCPI start session
                res_str = ss_sec.get("response") or ""
                ocpi_result = "NA"
                ocpi_text = ""
                if res_str:
                    try:
                        parsed = json.loads(res_str)
                        if isinstance(parsed, list) and parsed:
                            parsed = parsed[0]
                        if isinstance(parsed, dict):
                            ocpi_result = parsed.get("result", "NA")
                            ocpi_text = parsed.get("message") or parsed.get("status_message") or parsed.get("text") or ""
                    except Exception:
                        pass

                kwh = 0.0
                try:
                    kwh = float(sess_sec.get("kwh") or 0.0)
                except Exception:
                    pass

                dur_s = 0
                ocpi_json_str = sess_sec.get("OcpiJson") or ""
                if ocpi_json_str:
                    try:
                        oj = json.loads(ocpi_json_str) if isinstance(ocpi_json_str, str) else ocpi_json_str
                        dur_s = int(oj.get("total_duration") or oj.get("duration") or 0)
                    except Exception:
                        pass

                sch_act = res_sec.get("schedular_action") or ""

                sess_type = "Roaming Session"
                if "cancel" in sch_act.lower() or "expire" in sch_act.lower() or ocpi_result == "REJECTED":
                    sess_type = "Cancelled"
                elif kwh < 1.0:
                    sess_type = "Completed (<1kWh)"
                else:
                    sess_type = "Completed"

                init_soc = sess_sec.get("initial_soc")
                fin_soc = sess_sec.get("final_soc")

                record = {
                    "ChargingStationBookingId": b_id,
                    "BookingInTime": res_sec.get("in_time") or "",
                    "BookingOutTime": res_sec.get("out_time") or "",
                    "EnergyConsumed_indecimal": kwh,
                    "StationName": res_sec.get("station_name") or f"Roaming Station ({evse_uid})",
                    "ChargingStationChargerId": evse_uid,
                    "ConnectorId": res_sec.get("connector_id") or 1,
                    "ChargerCode": evse_uid,
                    "SchedularAction": sch_act,
                    "_SessionType": sess_type,
                    "_OcpiResult": ocpi_result,
                    "_OcpiText": ocpi_text,
                    "_DurationSeconds": dur_s,
                    "_InitialSoc": init_soc,
                    "_FinalSoc": fin_soc,
                    "_IsRoaming": True
                }
                return record, 1
    except Exception:
        pass
    return None, 1


def fetch_ocpi_cancelled_reservation(booking_id: str, cookie_header: str) -> tuple[dict | None, int]:
    """Queries OCPI Cancelled Reservations grid for a specific booking ID."""
    url = "https://emonitoring.electreefi.com/Roaming/OCPIReservation/LoadOcpiCancelledReservationGridViewThroughAjax"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_header
    }
    try:
        payload = urllib.parse.urlencode({
            "page": "1",
            "pageSize": "10",
            "sort": "",
            "group": "",
            "filter": f"BookingId~eq~{booking_id}"
        }).encode("utf-8")
        req = urllib.request.Request(f"{url}?StartDate=&Enddate=&transactionTypeId=-1", data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("Data", [])
            for it in items:
                if str(it.get("BookingId")) == str(booking_id):
                    it["_SessionType"] = "Cancelled (OCPI Roaming)"
                    it["_IsRoaming"] = True
                    it["ChargingStationBookingId"] = it.get("BookingId")
                    it["StationName"] = it.get("StationName") or f"Roaming Station ({it.get('PartyId')})"
                    it["BookingInTime"] = it.get("BookingDate") or ""
                    it["SchedularAction"] = it.get("SchedularAction") or "Cancelled"
                    it["StopReason"] = it.get("SchedularAction") or "Cancelled"
                    it["ChargerCode"] = it.get("Connector") or it.get("ChargerId") or "N/A"
                    it["ConnectorId"] = it.get("ConnectorName") or 1
                    it["EnergyConsumed_indecimal"] = float(it.get("KWh") or 0.0)
                    it["Name"] = it.get("UserName") or "Roaming Driver"
                    it["PaymentRecieved"] = float(it.get("PaidAmount") or it.get("TotalAmount") or 0.0)
                    it["RefundedAmount"] = float(it.get("RefundAmount") or 0.0)
                    it["VehicleRegistrationNumber"] = it.get("VehicleNumber") or "-"
                    return it, 1
    except Exception:
        pass
    return None, 1


def fetch_ocpp_transaction(booking_id: str, start_date: str, end_date: str, cookie_header: str) -> tuple[dict | None, int]:
    """
    Queries the central OCPP Transactions table in a single targeted hit.
    Never downloads large multi-page scans when matching by ReservationId.
    """
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_header
    }
    tx_url = f"https://emonitoring.electreefi.com/OCPPManagement/TransactionDetail/LoadTransactionViewThroughAjaxForData/2?StartDate={start_date}&Enddate={end_date}"

    # Single targeted attempt: ReservationId filter (1 hit)
    try:
        payload = urllib.parse.urlencode({
            "page": "1",
            "pageSize": "10",
            "sort": "",
            "group": "",
            "filter": f"ReservationId~eq~{booking_id}"
        }).encode("utf-8")
        req = urllib.request.Request(tx_url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("Data", []) if data.get("Data") else []
            for it in items:
                if str(it.get("ReservationId")) == str(booking_id) or str(it.get("BookingId")) == str(booking_id):
                    return it, 1
    except Exception:
        pass

    return None, 1


def fetch_ocpp_logs_for_booking(
    ch_id: Any,
    booking_in_dt: datetime,
    booking_out_dt: datetime | int | None = None,
    cookie_header: str = "",
    window_minutes: int | None = None
) -> list[OCPPLogEntry]:
    """Fetches raw OCPP logs tightly bounded to the booking's active lifecycle."""
    if not ch_id:
        return []

    # Support legacy calls where 3rd argument was integer window_minutes
    out_dt: datetime | None = None
    if isinstance(booking_out_dt, datetime):
        out_dt = booking_out_dt
    elif isinstance(booking_out_dt, (int, float)):
        window_minutes = int(booking_out_dt)

    # If out time is available, tightly bound window to booking lifecycle
    # Default buffer: 2 minutes before InTime, 2 minutes after OutTime
    if out_dt and out_dt >= booking_in_dt:
        diff_mins = (out_dt - booking_in_dt).total_seconds() / 60.0
        w_start_dt = booking_in_dt - timedelta(minutes=2)
        w_end_dt = out_dt + timedelta(minutes=2)
    elif window_minutes:
        w_start_dt = booking_in_dt - timedelta(minutes=2)
        w_end_dt = booking_in_dt + timedelta(minutes=window_minutes)
    else:
        w_start_dt = booking_in_dt - timedelta(minutes=2)
        w_end_dt = booking_in_dt + timedelta(minutes=4)

    w_start = w_start_dt.strftime("%Y-%m-%d %H:%M:00")
    w_end = w_end_dt.strftime("%Y-%m-%d %H:%M:00")
    from_enc = w_start.replace(" ", "%20")
    to_enc = w_end.replace(" ", "%20")

    url = f"https://emonitoring.electreefi.com/GetOcppLogs?entityId={ch_id}&fromDate={from_enc}&toDate={to_enc}"
    payload = urllib.parse.urlencode({
        "page": "1",
        "pageSize": "100",
        "sort": "",
        "group": "",
        "filter": ""
    }).encode("utf-8")
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_header
    }

    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("Data", []) if data.get("Data") else []
            entries: list[OCPPLogEntry] = []
            for it in items:
                ev_name = str(it.get("EventName") or "")
                if ev_name.lower() in ("heartbeat", "metervalues"):
                    continue
                entries.append(parse_ocpp_message(
                    raw_message=str(it.get("Message") or ""),
                    event_name=ev_name,
                    message_type=str(it.get("MessageTypeName") or ""),
                    timestamp=str(it.get("Date") or it.get("Timestamp") or ""),
                    message_id_fallback=str(it.get("MessageId") or "")
                ))
            return entries
    except Exception:
        return []


def generate_descriptive_rca(
    session_type: str,
    booking_data: dict,
    tx_data: dict | None,
    logs: list[OCPPLogEntry],
    target_connector: int | None = None
) -> dict:
    """
    Synthesizes all booking data, transaction status, and OCPP logs into a comprehensive,
    plain-English RCA report that pinpoints fault attribution and technical root cause.
    """
    connector_id = target_connector or booking_data.get("ConnectorId") or 1
    station_name = booking_data.get("ChargingStationName") or "Unknown Station"
    charger_code = booking_data.get("ChargerCode") or "Unknown Charger"
    vehicle_model = booking_data.get("ModelName") or "EV"
    vehicle_make = booking_data.get("ManufacturerName") or ""
    vehicle_str = f"{vehicle_make} {vehicle_model}".strip() if vehicle_make else vehicle_model
    energy_consumed = float(booking_data.get("EnergyConsumed_indecimal") or booking_data.get("EnergyConsumed") or 0.0)

    # Relevant logs filtered by connector
    relevant_logs = []
    for e in logs:
        if e.connector_id is None or e.connector_id == 0:
            relevant_logs.append(e)
        elif str(e.connector_id) == str(connector_id):
            relevant_logs.append(e)

    # Key state flags
    has_preparing = any(
        (e.status or "").lower() == "preparing" or
        "preparing" in (e.raw_message or "").lower()
        for e in relevant_logs
    )
    has_remote_start = any(
        "remotestart" in (e.event_name or "").lower() or
        "remotestart" in (e.raw_message or "").lower()
        for e in relevant_logs
    )
    has_remote_start_rejected = is_remote_start_status_rejected(relevant_logs) or any(
        ("remotestart" in (e.event_name or "").lower() or "remotestart" in (e.raw_message or "").lower()) and
        ('"rejected"' in (e.raw_message or "").lower() or 'status": "rejected"' in (e.raw_message or "").lower() or (e.status or "").lower() == "rejected")
        for e in relevant_logs
    )
    has_remote_start_accepted = is_remote_start_status_accepted(relevant_logs) or any(
        ("remotestart" in (e.event_name or "").lower() or "remotestart" in (e.raw_message or "").lower()) and
        ('"accepted"' in (e.raw_message or "").lower() or 'status": "accepted"' in (e.raw_message or "").lower() or (e.status or "").lower() == "accepted")
        for e in relevant_logs
    )
    # Strictly check for StartTransaction without matching RemoteStartTransaction
    has_start_transaction = any(
        (e.event_name or "").lower() == "starttransaction" or
        ('"starttransaction"' in (e.raw_message or "").lower() and '"remotestarttransaction"' not in (e.raw_message or "").lower())
        for e in relevant_logs
    )
    booking_status_lower = str(booking_data.get("Status", "")).lower()
    is_remote_start_blocked = has_remote_start_rejected and (
        not has_remote_start_accepted or booking_status_lower in ("rejected", "cancelled")
    ) and not has_start_transaction
    stop_transaction_entry = next(
        (e for e in relevant_logs if (e.event_name or "").lower() == "stoptransaction" or "stoptransaction" in (e.raw_message or "").lower()),
        None
    )

    # 1. SuspendedEV entry (Vehicle side refusal or pause)
    suspended_ev_entry = next(
        (e for e in relevant_logs if (e.status or "").lower() == "suspendedev" or '"suspendedev"' in (e.raw_message or "").lower()),
        None
    )

    # 2. SuspendedEVSE entry (Charger side pause or throttle)
    suspended_evse_entry = next(
        (e for e in relevant_logs if (e.status or "").lower() == "suspendedevse" or '"suspendedevse"' in (e.raw_message or "").lower()),
        None
    )

    # 3. Faulted state entry
    faulted_entry = next(
        (e for e in relevant_logs if (e.status or "").lower() == "faulted" or '"faulted"' in (e.raw_message or "").lower()),
        None
    )

    # 4. Meaningful info tags (exclude cellular/GSM telemetry, bare numbers, benign words)
    meaningful_info_entry = None
    for e in relevant_logs:
        info_str = (e.info or "").strip()
        if info_str and info_str.lower() not in ("none", "null", "noerror", "normal", "other", "-", ""):
            if not info_str.isdigit() and "gsm" not in info_str.lower() and "db" not in info_str.lower():
                meaningful_info_entry = e
                break

    # 5. Hardware error codes (excluding NoError, None, "")
    hw_error_entry = next(
        (e for e in relevant_logs if e.error_code and e.error_code.strip().lower() not in ("none", "null", "noerror", "")),
        None
    )

    # 6. Vendor error code entry
    vendor_error_entry = None
    for e in relevant_logs:
        verr = (e.vendor_error_code or "").strip()
        if verr and verr.lower() not in ("none", "null", "noerror", "noalarm", "0000000", "0x0000000000000000", "-"):
            vendor_error_entry = e
            break

    # Stop reasons from transaction or booking
    tx_stop_reason = (tx_data.get("stop_reason") if tx_data else None) or booking_data.get("StopReason") or ""
    srv_stop_trigger = (tx_data.get("ResponseMessage") if tx_data else None) or booking_data.get("StopTriggerMessage") or ""

    if stop_transaction_entry and stop_transaction_entry.reason:
        if not tx_stop_reason or tx_stop_reason.lower() == "other":
            tx_stop_reason = stop_transaction_entry.reason.strip()

    # -------------------------------------------------------------
    # ATTRIBUTION & NARRATIVE SYNTHESIS (Determining clearest error field)
    # -------------------------------------------------------------
    attribution = "UNCLASSIFIED"
    root_cause = "Indeterminate"
    confidence = "Medium"
    detected_field = "-"
    error_location = "-"
    error_value = "-"
    narrative = ""
    evidence = []
    action_item = ""

    # Build rich evidence list for frontend
    for e in relevant_logs[:12]:
        status_disp = e.status or "-"
        err_disp = e.error_code or "NoError"
        info_disp = e.info or "-"
        evidence.append({
            "timestamp": e.timestamp,
            "event": e.event_name,
            "type": e.message_type,
            "connector_id": e.connector_id,
            "status": e.status,
            "error_code": e.error_code,
            "info": e.info,
            "vendor_error_code": e.vendor_error_code,
            "summary": f"[{e.timestamp}] {e.event_name} (Gun #{e.connector_id or '-'}) - status: '{status_disp}', error: '{err_disp}', info: '{info_disp}'"
        })
    # -------------------------------------------------------------
    # RULE 0: Roaming OCPI Sessions (Direct OCPI Telemetry & Timing)
    # -------------------------------------------------------------
    if booking_data.get("_IsRoaming"):
        ocpi_res = booking_data.get("_OcpiResult", "NA")
        ocpi_txt = booking_data.get("_OcpiText", "")
        sch_act = booking_data.get("SchedularAction", "")
        dur_s = booking_data.get("_DurationSeconds", 0)
        init_soc = booking_data.get("_InitialSoc")
        fin_soc = booking_data.get("_FinalSoc")
        kwh = energy_consumed

        txt_l = ocpi_txt.lower()
        if "ev not connected" in txt_l or "not connected" in txt_l:
            attribution = "USER / OPERATOR ACTION"
            root_cause = "EV Not Connected (Cable Not Plugged In)"
            confidence = "High (98%)"
            detected_field = "ocpi_start_session.status_message"
            error_location = "StartSession Response"
            error_value = ocpi_txt
            action_item = "Advise driver to latch charging gun into EV inlet before tapping start in app."
        elif "already booked" in txt_l or "occupied" in txt_l:
            attribution = "CHARGER HARDWARE / STATION FAULT"
            root_cause = f"Connector Occupied / Already Booked ({ocpi_txt})"
            confidence = "High (95%)"
            detected_field = "ocpi_start_session.status_message"
            error_location = "StartSession Response"
            error_value = ocpi_txt
            action_item = "Inspect gun parking sensor; verify connector availability status synchronization."
        elif "scheduler" in sch_act.lower() or "expire" in sch_act.lower():
            attribution = "USER / OPERATOR ACTION"
            root_cause = "Reservation Expired by Scheduler on CMS (Driver Holding Window Elapsed)"
            confidence = "High (98%)"
            detected_field = "schedular_action"
            error_location = "CMS Reservation Table"
            error_value = sch_act
            action_item = "Send automated push notification 5m prior to reservation window expiry."
        elif "user" in sch_act.lower() or "driver" in sch_act.lower():
            attribution = "USER / OPERATOR ACTION"
            root_cause = "Cancelled by User on CMS (Prior to Session Initiation)"
            confidence = "High (98%)"
            detected_field = "schedular_action"
            error_location = "CMS Reservation Table"
            error_value = sch_act
            action_item = "Operational cancellation; no hardware intervention required."
        elif init_soc is not None and init_soc >= 80:
            attribution = "VEHICLE BMS / PREMATURE STOP"
            root_cause = f"High Battery SOC BMS Cutoff (Initial SOC: {init_soc}%, {kwh:.2f} kWh Delivered)"
            confidence = "High (95%)"
            detected_field = "session.initial_soc"
            error_location = "OCPI Session Telemetry"
            error_value = f"{init_soc}%"
            action_item = "Vehicle BMS commanded charging stop due to pack saturation limit (>80%)."
        elif 0 < dur_s <= 30 and kwh == 0.0:
            attribution = "VEHICLE BMS / PREMATURE STOP"
            root_cause = f"Immediate Pre-Charge Abort (Duration: {dur_s}s, 0.0 kWh Delivered)"
            confidence = "High (90%)"
            detected_field = "session.duration"
            error_location = "OCPI Session Telemetry"
            error_value = f"{dur_s}s"
            action_item = "Vehicle BMS opened contactors during pre-charge initialization; inspect EV inlet."
        elif 30 < dur_s <= 90 and kwh == 0.0:
            attribution = "VEHICLE BMS / PREMATURE STOP"
            root_cause = f"BMS Handshake Timeout (~60s Protocol Window, 0.0 kWh Delivered)"
            confidence = "High (90%)"
            detected_field = "session.duration"
            error_location = "OCPI Session Telemetry"
            error_value = f"{dur_s}s"
            action_item = "Inspect vehicle CP/PP line impedance and EV charging port lock engagement."
        elif 90 < dur_s <= 180 and kwh == 0.0:
            attribution = "CHARGER HARDWARE / STATION FAULT"
            root_cause = f"Charger Controller Initiation Timeout (~120s Standby, 0.0 kWh Delivered)"
            confidence = "High (90%)"
            detected_field = "session.duration"
            error_location = "OCPI Session Telemetry"
            error_value = f"{dur_s}s"
            action_item = "Update charger controller firmware; tune DC contactor timeout parameters."
        elif dur_s > 180 and kwh == 0.0:
            attribution = "USER / OPERATOR ACTION"
            root_cause = f"Connector Latched but Charging Not Activated (Duration: {dur_s//60}m, 0.0 kWh)"
            confidence = "High (88%)"
            detected_field = "session.duration"
            error_location = "OCPI Session Telemetry"
            error_value = f"{dur_s}s"
            action_item = "Driver plugged in gun but session was never confirmed or started."
        elif 0.0 < kwh < 1.0:
            attribution = "VEHICLE BMS / PREMATURE STOP"
            root_cause = f"Early Pre-Charge BMS Termination ({kwh:.3f} kWh Delivered in {dur_s}s)"
            confidence = "High (92%)"
            detected_field = "session.kwh"
            error_location = "OCPI Session Telemetry"
            error_value = f"{kwh} kWh"
            action_item = "Vehicle BMS abruptly ended session during initial power delivery."
        elif ocpi_res == "REJECTED":
            attribution = "CMS / NETWORK PROTOCOL ERROR"
            root_cause = f"Roaming StartSession Rejected ({ocpi_txt or 'OCPI Error'})"
            confidence = "High (95%)"
            detected_field = "ocpi_start_session.result"
            error_location = "StartSession Response"
            error_value = ocpi_res
            action_item = "Review CPO roaming gateway connectivity and OCPI token authorization."
        else:
            attribution = "SUCCESSFUL DELIVERY"
            root_cause = f"Normal Charging Session ({kwh:.2f} kWh Delivered)"
            confidence = "High (95%)"
            action_item = "No action required."

        narrative = (
            f"Forensic investigation of Roaming Booking #{booking_data.get('ChargingStationBookingId')}: "
            f"Session initiated at {station_name}. Schedular action: '{sch_act or 'None'}'. "
            f"OCPI StartSession returned status '{ocpi_res}' (Message: '{ocpi_txt or 'None'}'). "
            f"Delivered energy: {kwh:.3f} kWh over {dur_s}s (Initial SOC: {init_soc or 'N/A'}%, Final SOC: {fin_soc or 'N/A'}%). "
            f"Attribution: {attribution} | Identified Root Cause: {root_cause}."
        )

        return {
            "session_type": session_type,
            "attribution": attribution,
            "root_cause": root_cause,
            "confidence": confidence,
            "narrative": narrative,
            "action_item": action_item,
            "detected_field": detected_field,
            "error_location": error_location,
            "error_value": error_value,
            "evidence": evidence
        }

    # -------------------------------------------------------------
    # RULE 1: Critical Safety Alarms / Physical Interlocks
    # (Emergency Stop button, Low Insulation Resistance, Ground Fault)
    # -------------------------------------------------------------
    critical_safety_entry = None
    if meaningful_info_entry and any(k in (meaningful_info_entry.info or "").lower() for k in ("insulation", "emergency")):
        critical_safety_entry = ("info", meaningful_info_entry.info.strip())
    elif hw_error_entry and any(k in (hw_error_entry.error_code or "").lower() for k in ("ground", "emergencystop")):
        critical_safety_entry = ("errorCode", hw_error_entry.error_code.strip())

    if critical_safety_entry:
        src_type, src_val = critical_safety_entry
        if "emergency" in src_val.lower():
            attribution = "USER / OPERATOR ACTION"
            root_cause = f'Emergency Stop Button Activated ({src_type}: "{src_val}")'
            confidence = "High (98%)"
            detected_field = f'{src_type}: "{src_val}"'
            error_location = f"StatusNotification [{src_type}]"
            error_value = src_val
            narrative = (
                f"The physical red Emergency Stop push-button on charger '{charger_code}' was engaged, "
                f"immediately cutting off all control circuits and preventing charging."
            )
            action_item = "Inspect the physical Emergency Stop button on the charger front panel and ensure it has been rotated and released."
        elif "insulation" in src_val.lower():
            attribution = "CHARGER HARDWARE / ISOLATION FAULT"
            root_cause = f'Low Insulation Resistance Fault ({src_type}: "{src_val}")'
            confidence = "High (95%)"
            detected_field = f'{src_type}: "{src_val}"'
            error_location = f"StatusNotification [{src_type}]"
            error_value = src_val
            narrative = (
                f"Prior to closing the main DC contactors, charger '{charger_code}' measured the insulation resistance "
                f"between the DC bus and Earth. The measured resistance fell below the safety threshold (< 100 kΩ), "
                f"triggering an insulation isolation abort."
            )
            action_item = "Check DC cable harness and connector gun head for ingress of moisture, rain droplets, or cracked insulation."
        elif "ground" in src_val.lower():
            attribution = "CHARGER HARDWARE / STATION FAULT"
            root_cause = f'Earth / Ground Fault Detected ({src_type}: "{src_val}")'
            confidence = "High (95%)"
            detected_field = f'{src_type}: "{src_val}"'
            error_location = f"StatusNotification [{src_type}]"
            error_value = src_val
            narrative = (
                f"Charging station '{charger_code}' detected an electrical grounding anomaly or leakage current tripping "
                f"its safety residual current device (RCD). The charger immediately blocked energy delivery."
            )
            action_item = "High priority: Dispatch station electrical technician to inspect grounding rods, earth pit resistance, and RCD relays."

    # -------------------------------------------------------------
    # RULE 2: RemoteStart Rejected by Controller (Charging blocked upfront)
    # (Charging was never allowed to start because station refused remote start)
    # -------------------------------------------------------------
    elif is_remote_start_blocked:
        booking_id_disp = booking_data.get("ChargingStationBookingId") or booking_data.get("BookingId") or booking_data.get("booking_id") or "Unknown"
        attribution = "CHARGER / NETWORK GATEWAY FAULT"
        root_cause = 'Remote Start Transaction Rejected by Charger (status: "Rejected")'
        confidence = "High (98%)"
        detected_field = 'status: "Rejected"'
        error_location = "RemoteStartTransaction [status]"
        error_value = "Rejected"
        narrative = (
            f"The ElectreeFi CMS backend dispatched a RemoteStartTransaction command for Booking #{booking_id_disp}, "
            f"requesting session initiation on Gun #{connector_id} for vehicle {vehicle_str}. "
            f"However, the charger controller ('{charger_code}') immediately returned status: 'Rejected' in its CALLRESULT response. "
            f"Because the charger controller actively rejected the remote initiation command, energy transfer never commenced. "
            f"Common causes include: (1) Charger controller was in an unready internal state (such as busy or unavailable), "
            f"(2) Controller firmware communication glitch between gateway and power controller, or "
            f"(3) Connector was occupied or not locked in position when the start command was processed."
        )
        action_item = (
            "Verify charger online connectivity and ensure connector status is reported as 'Available' in CMS before "
            "initiating remote start. If rejections persist, execute a soft reset on charger via CMS or dispatch a technician."
        )

    # -------------------------------------------------------------
    # RULE 3: SuspendedEV in status (Clear vehicle-side suspension)
    # (Only evaluated when RemoteStart was NOT rejected by the charger)
    # -------------------------------------------------------------
    elif suspended_ev_entry:
        attribution = "VEHICLE SIDE FAULT"
        root_cause = 'Vehicle Suspended Charging (status: "SuspendedEV")'
        confidence = "High (95%)"
        detected_field = 'status: "SuspendedEV"'
        error_location = "StatusNotification [status]"
        error_value = "SuspendedEV"
        narrative = (
            f"The vehicle ({vehicle_str}) connected to Gun #{connector_id} and remote authorization was Accepted. "
            f"However, the vehicle controller transitioned the connector into status: 'SuspendedEV'. "
            f"Per the OCPP 1.6 / IEC 61851 specification, 'SuspendedEV' confirms that the electric vehicle's Battery "
            f"Management System (BMS) does not allow energy transfer (Control Pilot State B1/B2 instead of C/D). "
            f"The EV actively withheld closing its high-voltage charging contactors. Most frequent causes include: "
            f"(1) Vehicle ignition was left ON, (2) Gear selector was not shifted into Park (P), (3) A scheduled charging "
            f"timer or target battery limit was active on the vehicle dashboard / OEM app, or (4) Internal vehicle BMS pre-charge isolation hold."
        )
        action_item = (
            "Advise driver to: (1) Ensure vehicle ignition is completely switched OFF, (2) Verify gear is in Park (P), "
            "(3) Disable any charging timer or SOC limit in the vehicle's dashboard / app, and (4) Firmly re-insert the gun."
        )

    # -------------------------------------------------------------
    # RULE 4: SuspendedEVSE in status (Charger-side standby/throttle)
    # -------------------------------------------------------------
    elif suspended_evse_entry:
        attribution = "CHARGER HARDWARE / STATION FAULT"
        root_cause = 'Charger Station Suspended Energy Delivery (status: "SuspendedEVSE")'
        confidence = "High (95%)"
        detected_field = 'status: "SuspendedEVSE"'
        error_location = "StatusNotification [status]"
        error_value = "SuspendedEVSE"
        narrative = (
            f"The vehicle ({vehicle_str}) was plugged in, but charging station '{charger_code}' placed the connector "
            f"into status: 'SuspendedEVSE'. Per OCPP specifications, 'SuspendedEVSE' indicates that the vehicle is ready and "
            f"requesting energy, but the charging station temporarily withheld power delivery (due to local load shedding, "
            f"input supply voltage/frequency imbalance, or internal power module standby)."
        )
        action_item = "Inspect station electrical supply, power module health, grid input phase voltages, and local load management configuration."

    # -------------------------------------------------------------
    # RULE 5: Meaningful Info Tag with specific fault signature
    # (Evaluated before generic hardware errors because info often holds exact root cause)
    # -------------------------------------------------------------
    elif meaningful_info_entry and any(k in (meaningful_info_entry.info or "").lower() for k in ("connection_lost", "evconnection")):
        info_val = meaningful_info_entry.info.strip()
        error_location = "StatusNotification [info]"
        error_value = info_val
        attribution = "VEHICLE / USER ACTION"
        root_cause = f'Vehicle Pilot Connection Lost (info: "{info_val}")'
        confidence = "High (90%)"
        detected_field = f'info: "{info_val}"'
        narrative = (
            f"The Control Pilot line connection between vehicle ({vehicle_str}) inlet and connector gun #{connector_id} was unexpectedly dropped "
            f"(reported under info: '{info_val}'). The driver may have pulled the gun prematurely or the vehicle inlet latch released contact."
        )
        action_item = "Inspect gun latch mechanism and advise driver to hold the connector securely until charging initiates."

    # -------------------------------------------------------------
    # RULE 6: Hardware Error Code Present in StatusNotification
    # -------------------------------------------------------------
    elif hw_error_entry:
        err_code = hw_error_entry.error_code.strip()
        error_location = "StatusNotification [errorCode]"
        error_value = err_code
        detected_field = f'errorCode: "{err_code}"'

        if "high" in err_code.lower() and "temp" in err_code.lower():
            attribution = "CHARGER HARDWARE / STATION FAULT"
            root_cause = f'Thermal Limit Exceeded (errorCode: "{err_code}")'
            confidence = "High (95%)"
            narrative = (
                f"The temperature sensors on the power converter modules or connector {connector_id} exceeded maximum safety thresholds. "
                f"The charger thermal protection system aborted charging to prevent cable overheating or terminal damage."
            )
            action_item = "Clean charger air intake filters, check operational status of internal cooling exhaust fans, and inspect connector pin oxidation."

        elif "evcommunication" in err_code.lower() or "comm" in err_code.lower():
            attribution = "VEHICLE SIDE FAULT"
            root_cause = f'Pre-Charge EV Communication Handshake Abort (errorCode: "{err_code}")'
            confidence = "High (90%)"
            narrative = (
                f"The vehicle ({vehicle_str}) and charger '{charger_code}' failed the digital handshake protocol over the Control Pilot line "
                f"(PLC/CAN communication). The EV's Battery Management System (BMS) did not respond with required ready parameters within "
                f"the protocol timeout window. Charging was never initiated."
            )
            action_item = "Advise the vehicle driver to ensure ignition is completely OFF and vehicle is in Park (P). Inspect vehicle inlet port pins for dust or moisture."

        elif "lock" in err_code.lower():
            attribution = "CHARGER HARDWARE / STATION FAULT"
            root_cause = f'Connector Solenoid Lock Failure (errorCode: "{err_code}")'
            confidence = "High (95%)"
            narrative = (
                f"The mechanical locking solenoid on connector {connector_id} failed to engage or confirm secure latching with the vehicle inlet. "
                f"Per IEC 61851 / ISO 15118 safety requirements, charging cannot commence without confirmed mechanical locking."
            )
            action_item = "Lubricate and test the solenoid locking pin on connector gun. Verify that the latch pin moves smoothly into locked state."

        else:
            if vendor_error_entry and vendor_error_entry.vendor_error_code:
                detected_field = f'vendorErrorCode: "{vendor_error_entry.vendor_error_code}"'
                error_location = "StatusNotification [vendorErrorCode]"
                error_value = vendor_error_entry.vendor_error_code
                root_cause = f'Station Hardware Alarm ({err_code} / {vendor_error_entry.vendor_error_code})'
            else:
                root_cause = f'Station Hardware Fault (errorCode: "{err_code}")'

            attribution = "CHARGER HARDWARE / STATION FAULT"
            confidence = "High (90%)"
            narrative = f"The charger raised hardware alert '{err_code}' during the pre-charge sequence, aborting session initialization."
            action_item = "Review controller error register and execute soft reset via CMS portal."

    # -------------------------------------------------------------
    # RULE 7: Meaningful Info Tag (General)
    # -------------------------------------------------------------
    elif meaningful_info_entry:
        info_val = meaningful_info_entry.info.strip()
        attribution = "CHARGER HARDWARE / STATION FAULT"
        root_cause = f'Charger Diagnostic Alert (info: "{info_val}")'
        confidence = "High (85%)"
        detected_field = f'info: "{info_val}"'
        error_location = "StatusNotification [info]"
        error_value = info_val
        narrative = f"The charger internal controller aborted the session reporting diagnostic status: '{info_val}'."
        action_item = f"Inspect charger vendor telemetry logs corresponding to event '{info_val}'."

    # -------------------------------------------------------------
    # RULE 7: Preparing + RemoteStart Accepted + No StartTransaction (BMS Timeout)
    # -------------------------------------------------------------
    elif (has_preparing or has_remote_start_accepted) and not has_start_transaction:
        attribution = "VEHICLE SIDE FAULT"
        root_cause = "Start Transaction Not Received (BMS Handshake Timeout)"
        confidence = "High (90%)"
        detected_field = 'status: "Preparing" (No StartTransaction)'
        error_location = "StatusNotification [status] & RemoteStartTransaction [CALLRESULT]"
        error_value = "Preparing"
        narrative = (
            f"The user connected the EV gun and connector {connector_id} transitioned into 'Preparing'. "
            f"The CMS dispatched RemoteStartTransaction, which the charger confirmed as 'Accepted'. "
            f"However, the vehicle ({vehicle_str}) never closed its charging contactors, and no StartTransaction was generated. "
            f"Most common causes include the vehicle ignition being kept ON, BMS pre-charge isolation delay, or premature user abandonment."
        )
        action_item = "Advise user to follow vehicle start guidelines: Turn vehicle completely OFF, insert gun firmly until click, and initiate via QR code."

    # -------------------------------------------------------------
    # RULE 8: Preparing but RemoteStart never arrived
    # -------------------------------------------------------------
    elif has_preparing and not has_remote_start:
        attribution = "NETWORK / CMS BACKEND FAULT"
        root_cause = "Remote Start Command Not Received by Charger"
        confidence = "High (85%)"
        detected_field = 'status: "Preparing" (RemoteStart Never Sent)'
        error_location = "StatusNotification [status]"
        error_value = "Preparing"
        narrative = (
            f"Connector {connector_id} registered 'Preparing' when the gun was plugged in, but the charger never received a "
            f"RemoteStartTransaction command from the CMS server within the session timeout window. This points to a WebSocket "
            f"latency lag or CMS payment gateway holding the transaction."
        )
        action_item = "Check ElectreeFi CMS OCPP gateway connectivity and latency for charger."

    # -------------------------------------------------------------
    # RULE 9: StopTransaction / Low-Consumption (<1kWh) Analysis
    # -------------------------------------------------------------
    elif session_type != "Cancelled" or has_start_transaction:
        if tx_stop_reason:
            error_location = "StopTransaction [reason]"
            error_value = tx_stop_reason
            detected_field = f'reason: "{tx_stop_reason}"'

            if tx_stop_reason.lower() in ("evdisconnected", "ev disconnected"):
                attribution = "VEHICLE / USER ACTION"
                root_cause = f'Premature Vehicle Disconnection (reason: "{tx_stop_reason}")'
                confidence = "High (95%)"
                narrative = (
                    f"The session started successfully and transferred {energy_consumed:.3f} kWh. "
                    f"Charging was terminated prematurely with StopReason '{tx_stop_reason}'. "
                    f"Either the vehicle BMS unexpectedly released its inlet lock and cut off current, or the user unplugged the connector "
                    f"gun before meaningful charging could occur."
                )
                action_item = "Advise driver not to force pull connector while session is actively ramping up current."

            elif tx_stop_reason.lower() in ("emergencystop", "emergency stop"):
                attribution = "USER / OPERATOR ACTION"
                root_cause = f'Emergency Stop Button Pressed (reason: "{tx_stop_reason}")'
                confidence = "High (98%)"
                narrative = "The session was interrupted after starting because the Emergency Stop button on the charger was activated."
                action_item = "Ensure E-stop button is unlocked on the charging unit."

            elif tx_stop_reason.lower() in ("remote", "remote stop"):
                attribution = "USER / APP ACTION"
                root_cause = f'Remotely Stopped via Mobile App / CMS (reason: "{tx_stop_reason}")'
                confidence = "High (90%)"
                narrative = (
                    f"The session transferred {energy_consumed:.3f} kWh before receiving a RemoteStopTransaction command. "
                    f"The driver manually pressed 'Stop Charging' in their mobile application shortly after starting."
                )
                action_item = "User-initiated termination; verify with customer if session was cancelled intentionally."

            elif tx_stop_reason.lower() in ("deauthorized", "de-authorized"):
                attribution = "AUTHENTICATION / WALLET FAULT"
                root_cause = f'User Authorization Revoked (reason: "{tx_stop_reason}")'
                confidence = "High (90%)"
                narrative = (
                    f"The server revoked authorization during initial charging ramp-up (Energy: {energy_consumed:.3f} kWh). "
                    f"Common causes include wallet balance depletion or authorization token expiration."
                )
                action_item = "Check user app wallet balance and transaction deduction rules."

            elif tx_stop_reason.lower() in ("hardreset", "softreset", "reboot"):
                attribution = "CHARGER HARDWARE FAULT"
                root_cause = f'Charger Unexpectedly Rebooted (reason: "{tx_stop_reason}")'
                confidence = "High (95%)"
                narrative = f"The charger hardware executed a system reboot while actively charging (Energy: {energy_consumed:.3f} kWh)."
                action_item = "Check station internal power supply unit (PSU) and schedule firmware stability review."

            else:
                attribution = "CHARGER / OPERATIONAL REASON"
                root_cause = f'Stop Reason: {tx_stop_reason}'
                confidence = "Medium (75%)"
                narrative = (
                    f"The transaction stopped with reported reason '{tx_stop_reason}' after delivering {energy_consumed:.3f} kWh. "
                    f"Server trigger message: {srv_stop_trigger or 'None'}."
                )
                action_item = "Review charger detailed controller logs for vendor sub-codes."
        else:
            attribution = "VEHICLE / USER SIDE FAULT"
            root_cause = "Early Cutoff with Low Energy (< 1 kWh)"
            confidence = "Medium (70%)"
            detected_field = f'Energy Consumed: {energy_consumed:.3f} kWh (< 1 kWh)'
            error_location = "Transaction Meter Reading"
            error_value = f"{energy_consumed:.3f} kWh"
            narrative = (
                f"The session closed with only {energy_consumed:.3f} kWh consumed. No explicit stop reason was reported by the charger. "
                f"Likely vehicle BMS cutoff or early user termination."
            )
            action_item = "Check if vehicle reached target charge limit or if BMS triggered early ramp-down."

    # -------------------------------------------------------------
    # RULE 10: No logs at all around timestamp
    # -------------------------------------------------------------
    elif not relevant_logs:
        attribution = "USER / OPERATOR ACTION"
        root_cause = "Gun Not Connected / User Did Not Connect in Time"
        confidence = "High (90%)"
        detected_field = "No Telemetry Logs Recorded"
        error_location = "GetOcppLogs (No Records)"
        error_value = "NoLogs"
        narrative = (
            f"There are no OCPP telemetry messages recorded for charger '{charger_code}' around this booking's timestamp. "
            f"The user created a booking or scanned QR, but never physically plugged the connector into the vehicle, "
            f"causing the booking reservation to automatically expire and cancel."
        )
        action_item = "Advise driver that bookings expire if connector gun is not plugged into the vehicle within 5 minutes."

    else:
        attribution = "UNCLASSIFIED / NOISE"
        root_cause = "Indeterminate from Log Telemetry"
        confidence = "Low (50%)"
        detected_field = "Telemetry Inconclusive"
        error_location = "OCPP Event Stream"
        error_value = "-"
        narrative = "The logs do not contain conclusive error codes or stop reasons. Further manual inspection of station raw logs is advised."
        action_item = "Inspect full charger raw OCPP logs via the CMS logs viewer."

    return {
        "attribution": attribution,
        "root_cause": root_cause,
        "confidence": confidence,
        "detected_field": detected_field,
        "error_location": error_location,
        "error_value": error_value,
        "narrative": narrative,
        "action_item": action_item,
        "evidence_logs": evidence
    }


# In-memory LRU cache for rapid repeated queries (TTL: 5 minutes)
_INVESTIGATION_CACHE: dict[str, tuple[dict, float]] = {}


def clear_investigation_cache() -> None:
    """Clears the in-memory investigation cache."""
    global _INVESTIGATION_CACHE
    _INVESTIGATION_CACHE.clear()


def investigate_booking(booking_id: str, start_date: str = "", end_date: str = "") -> dict:
    """
    Main entry point: searches for a booking ID in ElectreeFi CMS with maximum efficiency,
    reaching the desired result in the least amount of hits possible.
    Bypasses transaction lookups for Cancelled bookings and caches results for zero-latency retrieval.
    """
    import time
    t0 = time.perf_counter()

    clean_id = str(booking_id).strip()
    if not clean_id:
        return {"success": False, "message": "Booking ID is required."}

    # 1. Check in-memory cache first (0 hits, 0.1ms)
    now_ts = time.time()
    if clean_id in _INVESTIGATION_CACHE:
        cached_entry, cached_at = _INVESTIGATION_CACHE[clean_id]
        if (now_ts - cached_at) < 300:  # 5 min TTL
            cached_copy = json.loads(json.dumps(cached_entry))
            cached_copy["cached"] = True
            cached_copy["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            cached_copy["hits_count"] = 0
            return cached_copy

    cookie_header = get_cookie_header()
    if not cookie_header:
        return {"success": False, "message": "No active session found. Please run login first."}

    today_str = datetime.now().strftime("%Y-%m-%d")
    s_date = start_date.strip() if start_date and start_date.strip() else "2024-01-01"
    e_date = end_date.strip() if end_date and end_date.strip() else today_str

    total_hits = 0

    # 2. Search in Cancelled Bookings (Hit 1: Unconstrained index search covers full history in 250ms)
    booking_record, c_hits = fetch_cancelled_booking(clean_id, "", "", cookie_header)
    total_hits += c_hits
    session_type = "Cancelled"
    tx_record = None

    # 3. If not found in Cancelled, search in Completed (<1kW) Bookings (Hit 2)
    if not booking_record:
        booking_record, comp_hits = fetch_completed_booking(clean_id, "", "", cookie_header)
        total_hits += comp_hits
        if booking_record:
            session_type = "Completed (<1kWh)"
            # Extract actual booking date for targeted transaction query
            t_str = booking_record.get("BookingInTime") or booking_record.get("DateForBooking")
            b_in_dt_temp = parse_flexible_dt(t_str)
            target_date = b_in_dt_temp.strftime("%Y-%m-%d") if b_in_dt_temp else s_date
            # For Completed bookings only: query transaction record (Hit 3)
            tx_record, tx_hits = fetch_ocpp_transaction(clean_id, target_date, target_date, cookie_header)
            total_hits += tx_hits

    # 4. If still not found, search in Roaming OCPI Reservation Endpoint (Hit 3)
    if not booking_record:
        booking_record, roam_hits = fetch_roaming_booking(clean_id, cookie_header)
        total_hits += roam_hits
        if booking_record:
            session_type = booking_record.get("_SessionType", "Roaming Session")

    # 4b. If still not found, search in Roaming OCPI Cancelled Reservations (Hit 4)
    if not booking_record:
        booking_record, ocpi_c_hits = fetch_ocpi_cancelled_reservation(clean_id, cookie_header)
        total_hits += ocpi_c_hits
        if booking_record:
            session_type = booking_record.get("_SessionType", "Cancelled (OCPI Roaming)")

    if not booking_record:
        return {
            "success": False,
            "found": False,
            "hits_count": total_hits,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "cached": False,
            "message": f"Booking ID '{clean_id}' was not found in Cancelled, Completed (<1kWh), or Roaming records between {s_date} and {e_date}. Try expanding the date range."
        }

    # 5. Fetch OCPP logs strictly bounded to the session lifecycle (Hit 2 or 3)
    t_str = booking_record.get("BookingInTime") or booking_record.get("DateForBooking")
    out_str = booking_record.get("BookingOutTime")
    b_in_dt = parse_flexible_dt(t_str) or datetime.now()
    b_out_dt = parse_flexible_dt(out_str)
    ch_id = booking_record.get("ChargingStationChargerId")

    logs = fetch_ocpp_logs_for_booking(ch_id, b_in_dt, b_out_dt, cookie_header=cookie_header)
    total_hits += 1

    # 6. Run descriptive RCA engine (0 hits - purely deterministic in-memory synthesis)
    rca_analysis = generate_descriptive_rca(
        session_type=session_type,
        booking_data=booking_record,
        tx_data=tx_record,
        logs=logs,
        target_connector=booking_record.get("ConnectorId")
    )

    # Format output fields for frontend
    units_val = float(booking_record.get("EnergyConsumed_indecimal") or booking_record.get("EnergyConsumed") or 0.0)

    # Resolve ID Tag from: (1) booking details page record, (2) transaction record, or (3) correlated OCPP logs
    resolved_id_tag = str(booking_record.get("IdTag") or booking_record.get("Id_Tag") or "").strip()
    if not resolved_id_tag and tx_record:
        resolved_id_tag = str(tx_record.get("id_tag") or "").strip()
    if not resolved_id_tag:
        for e in logs:
            if isinstance(e.parsed_payload, dict):
                cand = e.parsed_payload.get("idTag") or e.parsed_payload.get("id_tag")
                if cand:
                    resolved_id_tag = str(cand).strip()
                    break
            raw_msg = e.raw_message or ""
            m = re.search(r'["\']?idTag["\']?\s*[:=]\s*["\']?([^"\',}\s]+)', raw_msg, re.IGNORECASE)
            if m:
                resolved_id_tag = m.group(1).strip()
                break
    final_id_tag = resolved_id_tag if resolved_id_tag else "-"

    formatted_booking = {
        "booking_id": clean_id,
        "session_type": session_type,
        "station_name": booking_record.get("ChargingStationName") or booking_record.get("StationName") or "Unknown Station",
        "station_address": booking_record.get("ChargingStationAddress") or "",
        "city": booking_record.get("ChargingStationCity") or "",
        "state": booking_record.get("ChargingStationState") or "",
        "charger_code": booking_record.get("ChargerCode") or "",
        "charger_name": booking_record.get("ChargerName") or "",
        "charger_id": ch_id,
        "connector_id": booking_record.get("ConnectorId") or 1,
        "connector_type": booking_record.get("ConnectorType") or "CCS (DC)",
        "booking_mode": booking_record.get("BookingMode") or "QR CODE",
        "user_name": (booking_record.get("Name") or "End User").strip(),
        "mobile": booking_record.get("MobileNumber") or "-",
        "vehicle_number": booking_record.get("VehicleRegistrationNumber") or "-",
        "vehicle_model": booking_record.get("ModelName") or "-",
        "vehicle_make": booking_record.get("ManufacturerName") or "-",
        "battery_capacity": booking_record.get("BatteryCapacity") or "-",
        "booking_in_time": booking_record.get("BookingInTime") or "-",
        "booking_out_time": booking_record.get("BookingOutTime") or "-",
        "status": booking_record.get("Status") or session_type,
        "id_tag": final_id_tag,
        "energy_consumed_kwh": units_val,
        "payment_received": float(booking_record.get("PaymentRecieved_Excel") or booking_record.get("PaymentRecieved") or 0.0),
        "refunded_amount": float(booking_record.get("RefundedAmount") or 0.0),
        "initial_soc": booking_record.get("InitialSOC") or booking_record.get("_InitialSoc") or 0,
        "final_soc": booking_record.get("FinalSOC") or booking_record.get("_FinalSoc") or 0,
        "stop_reason_booking": booking_record.get("StopReason") or booking_record.get("SchedularAction") or "-",
        "stop_trigger_booking": booking_record.get("StopTriggerMessage") or "-"
    }

    formatted_tx = None
    if tx_record:
        formatted_tx = {
            "transaction_pk": tx_record.get("transaction_pk") or tx_record.get("TransactionID") or "-",
            "connector_pk": tx_record.get("connector_pk") or "-",
            "id_tag": str(tx_record.get("id_tag") or final_id_tag or "-").strip(),
            "start_timestamp": tx_record.get("start_timestamp_string") or tx_record.get("start_timestamp") or "-",
            "stop_timestamp": tx_record.get("stop_timestamp_string") or tx_record.get("stop_timestamp") or "-",
            "start_value": tx_record.get("start_value") or "0",
            "stop_value": tx_record.get("stop_value") or "0",
            "stop_reason": tx_record.get("stop_reason") or "-",
            "response_message": tx_record.get("ResponseMessage") or "-",
            "soc": tx_record.get("Soc") or "-",
            "initial_soc": tx_record.get("IntialSoc") or "-",
            "energy_consumed": tx_record.get("EnergyConsumed") or "-"
        }

    formatted_logs = []
    for e in logs:
        formatted_logs.append({
            "timestamp": e.timestamp,
            "event": e.event_name,
            "type": e.message_type,
            "connector_id": e.connector_id,
            "status": e.status,
            "error_code": e.error_code,
            "info": e.info,
            "vendor_error_code": e.vendor_error_code,
            "reason": e.reason,
            "raw": e.raw_message
        })

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    result_payload = {
        "success": True,
        "found": True,
        "booking": formatted_booking,
        "transaction": formatted_tx,
        "rca": rca_analysis,
        "logs_count": len(formatted_logs),
        "logs": formatted_logs,
        "hits_count": total_hits,
        "latency_ms": elapsed_ms,
        "cached": False
    }

    # Cache result
    _INVESTIGATION_CACHE[clean_id] = (result_payload, time.time())

    return result_payload
