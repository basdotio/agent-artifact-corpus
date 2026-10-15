"""
Data models for ElectreeFi bookings, OCPP logs, and RCA analysis.
"""

from typing import Any
from pydantic import BaseModel, Field


def mask_string(val: str | None, prefix_len: int = 2, suffix_len: int = 2) -> str:
    """Helper to mask sensitive PII while leaving hints for recognition."""
    if not val:
        return ""
    val_str = str(val).strip()
    length = len(val_str)
    if length <= (prefix_len + suffix_len):
        return "***"
    return f"{val_str[:prefix_len]}{'*' * (length - prefix_len - suffix_len)}{val_str[-suffix_len:]}"


class BookingRecord(BaseModel):
    """Represents a row in the AdminBookingDetails table."""
    booking_id: str
    booking_start_time: str | None = None
    booking_stop_time: str | None = None
    connector_id: str | None = None
    user_status: str | None = None  # Note: ignored for RCA as it shows "Activated" even when cancelled
    station_organization: str | None = None
    user_organization: str | None = None
    user_state: str | None = None
    user_name_masked: str | None = None
    mobile_number_masked: str | None = None
    booking_mode: str | None = None
    payment_method: str | None = None
    payment_pending: str | None = None
    refund_amount: str | None = None
    payment_mode: str | None = None
    is_subscriber: str | None = None
    source_party: str | None = None
    manufacturer_name: str | None = None
    model_name: str | None = None
    battery_capacity: str | None = None
    tab: str = "Cancelled"
    details_link_selector: str | None = None


class BookingDetails(BaseModel):
    """Represents the rich data inside the Booking Details popup modal."""
    booking_id: str
    # User Details
    user_name_masked: str | None = None
    mobile_number_masked: str | None = None
    vehicle_number_masked: str | None = None
    vin_number_masked: str | None = None
    # Booking Details
    booking_mode: str | None = None
    booking_type: str | None = None
    connector_type: str | None = None
    booking_date: str | None = None
    created_on: str | None = None
    booking_in_time: str | None = None
    booking_out_time: str | None = None
    scheduled_in_time: str | None = None
    scheduled_out_time: str | None = None
    actual_in_time: str | None = None
    actual_out_time: str | None = None
    # Station Details
    station_name: str | None = None
    charger_code: str | None = None
    connector_sequence_id: int | None = None
    is_quick_charge: str | None = None
    # Session Details
    initial_soc: str | None = None
    final_soc: str | None = None
    units_consumed_kw: float | None = None
    charging_amount: str | None = None
    start_reading: str | None = None
    stop_reading: str | None = None
    stop_reason_from_charger: str | None = None
    blocked_out_time: str | None = None
    stop_triggered_condition_from_server: str | None = None
    authentication_status: str | None = None
    authentication_reason: str | None = None
    id_tag_used: str | None = None
    transaction_stopped_on: str | None = None
    # Payment Details
    total_payable: str | None = None
    payment_status: str | None = None
    invoice_generated: str | None = None


class OCPPLogEntry(BaseModel):
    """Represents an OCPP message row from Charger Logs (Beta)."""
    message_id: str
    event_name: str
    event_type: str
    message_type: str  # e.g. CALL, CALLRESULT, CALLERROR
    raw_message: str
    timestamp: str
    parsed_action: str | None = None
    parsed_payload: dict[str, Any] | list[Any] | None = None
    connector_id: int | None = None
    reason: str | None = None
    error_code: str | None = None
    info: str | None = None
    status: str | None = None
    vendor_error_code: str | None = None
    vendor_id: str | None = None


class RCAResult(BaseModel):
    """Detailed root cause analysis for an individual booking."""
    booking_id: str
    charger_code: str | None = None
    connector_sequence_id: int | None = None
    booking_time: str | None = None
    units_consumed_kw: float | None = None
    category: str  # USER_ACTION, HARDWARE_FAULT, GRID_FAULT, EV_COMMUNICATION, etc.
    root_cause: str  # Human readable diagnosis
    confidence: str = "High"  # High, Medium, Low
    explanation: str
    recommendation: str
    evidence_logs: list[dict[str, Any]] = Field(default_factory=list)


class RCAReport(BaseModel):
    """Aggregated summary of multiple booking root causes."""
    date_range: str
    total_analyzed: int
    cancelled_count: int
    low_consumption_count: int
    category_breakdown: dict[str, int]
    top_affected_chargers: list[dict[str, Any]]
    results: list[RCAResult]
