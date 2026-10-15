"""
RCA Engine for correlating booking sessions with OCPP charger logs.
"""

from typing import Any
from src.models import BookingDetails, OCPPLogEntry, RCAResult, RCAReport
from src.rca.mapper import classify_stop_reason, classify_error_code


def analyze_booking_rca(
    booking: BookingDetails,
    logs: list[OCPPLogEntry],
    low_consumption_threshold_kw: float = 1.0
) -> RCAResult:
    """
    Correlates a booking's details with relevant OCPP logs to produce an RCAResult.
    """
    booking_id = booking.booking_id
    charger_code = booking.charger_code
    connector_id = booking.connector_sequence_id
    units = booking.units_consumed_kw

    # Filter logs relevant to this connector (or station-level events where connector_id is 0 or None)
    relevant_logs: list[OCPPLogEntry] = []
    for entry in logs:
        if entry.connector_id is None or entry.connector_id == 0:
            relevant_logs.append(entry)
        elif connector_id is not None and entry.connector_id == connector_id:
            relevant_logs.append(entry)

    evidence: list[dict[str, Any]] = []
    for entry in relevant_logs:
        evidence.append({
            "message_id": entry.message_id,
            "event_name": entry.event_name,
            "timestamp": entry.timestamp,
            "connector_id": entry.connector_id,
            "reason": entry.reason,
            "error_code": entry.error_code,
            "raw": entry.raw_message[:200]  # truncate for brevity
        })

    # Step 1: Check for critical hardware/electrical error codes in StatusNotification
    error_entries = [e for e in relevant_logs if e.error_code and e.error_code.lower() not in ("noerror", "none", "null")]
    if error_entries:
        primary_err = error_entries[-1]  # Most recent error code
        rule = classify_error_code(primary_err.error_code)
        if rule:
            is_low = (units is not None and units < low_consumption_threshold_kw)
            explanation = rule["explanation"]
            if is_low:
                explanation += f" Booking terminated prematurely with only {units} kW consumed."
            return RCAResult(
                booking_id=booking_id,
                charger_code=charger_code,
                connector_sequence_id=connector_id,
                booking_time=booking.booking_in_time or booking.scheduled_in_time,
                units_consumed_kw=units,
                category=rule["category"],
                root_cause=rule["root_cause"],
                confidence="High",
                explanation=explanation,
                recommendation=rule["recommendation"],
                evidence_logs=evidence[-5:]
            )

    # Step 2: Check for StopTransaction reasons in logs
    stop_entries = [e for e in relevant_logs if e.reason]
    if stop_entries:
        primary_stop = stop_entries[-1]
        rule = classify_stop_reason(primary_stop.reason)
        if rule:
            is_low = (units is not None and units < low_consumption_threshold_kw)
            explanation = rule["explanation"]
            if is_low:
                explanation += f" Session aborted early resulting in low consumption ({units} kW)."
            return RCAResult(
                booking_id=booking_id,
                charger_code=charger_code,
                connector_sequence_id=connector_id,
                booking_time=booking.booking_in_time or booking.scheduled_in_time,
                units_consumed_kw=units,
                category=rule["category"],
                root_cause=rule["root_cause"],
                confidence="High",
                explanation=explanation,
                recommendation=rule["recommendation"],
                evidence_logs=evidence[-5:]
            )

    # Step 3: Check fallback fields from booking details modal
    if booking.stop_reason_from_charger and booking.stop_reason_from_charger.strip().lower() not in ("", "other"):
        rule = classify_stop_reason(booking.stop_reason_from_charger)
        if rule:
            return RCAResult(
                booking_id=booking_id,
                charger_code=charger_code,
                connector_sequence_id=connector_id,
                booking_time=booking.booking_in_time or booking.scheduled_in_time,
                units_consumed_kw=units,
                category=rule["category"],
                root_cause=rule["root_cause"],
                confidence="Medium",
                explanation=f"Identified from portal Details popup: {rule['explanation']}",
                recommendation=rule["recommendation"],
                evidence_logs=evidence[-3:]
            )

    if booking.stop_triggered_condition_from_server and booking.stop_triggered_condition_from_server.strip() and booking.stop_triggered_condition_from_server.strip() != "-":
        cond = booking.stop_triggered_condition_from_server.strip()
        return RCAResult(
            booking_id=booking_id,
            charger_code=charger_code,
            connector_sequence_id=connector_id,
            booking_time=booking.booking_in_time or booking.scheduled_in_time,
            units_consumed_kw=units,
            category="APP_OR_SERVER_ACTION",
            root_cause=f"Server Condition: {cond}",
            confidence="Medium",
            explanation=f"CMS server triggered session stop condition: {cond}",
            recommendation="Review server-side session watchdog or timeout configurations.",
            evidence_logs=evidence[-3:]
        )

    # Step 3b: Detect Pre-Charge Handshake Abort (Preparing -> Available without StartTransaction)
    preparing_events = [e for e in relevant_logs if "preparing" in e.raw_message.lower()]
    available_events = [e for e in relevant_logs if "available" in e.raw_message.lower()]
    has_start = any(e.event_name.lower() == "starttransaction" for e in relevant_logs)

    if (units is None or units < 0.1) and preparing_events and available_events and not has_start:
        return RCAResult(
            booking_id=booking_id,
            charger_code=charger_code,
            connector_sequence_id=connector_id,
            booking_time=booking.booking_in_time or booking.scheduled_in_time,
            units_consumed_kw=units,
            category="ABORTED_INITIATION",
            root_cause="Pre-Charge Handshake Abort (Never Started)",
            confidence="High",
            explanation="The connector was authorized and entered 'Preparing' state, but reverted to 'Available' in <60 seconds before power transfer could commence.",
            recommendation="Advise driver to verify the charging gun locking pin is engaged and retry connection.",
            evidence_logs=evidence[-5:]
        )

    # Step 4: Low consumption flag without explicit logs
    if units is not None and units < low_consumption_threshold_kw:
        return RCAResult(
            booking_id=booking_id,
            charger_code=charger_code,
            connector_sequence_id=connector_id,
            booking_time=booking.booking_in_time or booking.scheduled_in_time,
            units_consumed_kw=units,
            category="ABORTED_INITIATION",
            root_cause="Aborted Pre-Charge Handshake (< 1 kW)",
            confidence="Medium",
            explanation=f"Energy transferred was {units} kW. Handshake was likely cancelled before power stage energized.",
            recommendation="Check if connector was unplugged before authorization was completed or vehicle BMS rejected charge.",
            evidence_logs=evidence[-3:]
        )

    # Step 5: Unclassified fallback
    return RCAResult(
        booking_id=booking_id,
        charger_code=charger_code,
        connector_sequence_id=connector_id,
        booking_time=booking.booking_in_time or booking.scheduled_in_time,
        units_consumed_kw=units,
        category="UNCLASSIFIED_MANUAL_REVIEW",
        root_cause="Unclassified Cancellation / Missing Logs",
        confidence="Low",
        explanation="No matching error codes or stop reasons found in the OCPP logs within the ±10m window.",
        recommendation="Verify whether charger was online and communicating with CMS during this period, or expand log search window.",
        evidence_logs=evidence[-3:]
    )


def generate_rca_report(date_range: str, results: list[RCAResult]) -> RCAReport:
    """Aggregates individual RCA results into a comprehensive summary report."""
    total = len(results)
    category_counts: dict[str, int] = {}
    low_consumption_count = 0
    cancelled_count = 0
    charger_occurrences: dict[str, int] = {}

    for r in results:
        category_counts[r.category] = category_counts.get(r.category, 0) + 1
        if r.units_consumed_kw is not None and r.units_consumed_kw < 1.0:
            low_consumption_count += 1
        else:
            cancelled_count += 1
        if r.charger_code:
            charger_occurrences[r.charger_code] = charger_occurrences.get(r.charger_code, 0) + 1

    top_chargers = sorted(
        [{"charger_code": k, "incident_count": v} for k, v in charger_occurrences.items()],
        key=lambda x: x["incident_count"],
        reverse=True
    )

    return RCAReport(
        date_range=date_range,
        total_analyzed=total,
        cancelled_count=cancelled_count,
        low_consumption_count=low_consumption_count,
        category_breakdown=category_counts,
        top_affected_chargers=top_chargers[:10],
        results=results
    )
