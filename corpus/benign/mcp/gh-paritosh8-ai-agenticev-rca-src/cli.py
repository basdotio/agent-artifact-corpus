"""
Command Line Interface (CLI) to run ElectreeFi RCA tasks directly.
"""

import sys
import json
import asyncio
import argparse
from typing import Any

from src.auth.session_manager import interactive_login, is_session_valid
from src.scraper.browser import BrowserSession
from src.scraper.bookings import fetch_bookings_list
from src.scraper.booking_details import fetch_booking_details
from src.scraper.ocpp_logs import fetch_charger_logs_beta
from src.server import compute_time_window
from src.rca.engine import analyze_booking_rca, generate_rca_report
from src.config import RCA_LOG_TIME_WINDOW_MINUTES, RCA_LOW_CONSUMPTION_THRESHOLD_KW


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


async def cmd_login(args) -> None:
    res = await interactive_login(force=args.force)
    print(res)


async def cmd_check_session(args) -> None:
    valid = await is_session_valid()
    if valid:
        print("SUCCESS: Session is active and valid!")
    else:
        print("EXPIRED / NOT LOGGED IN: Please run 'python -m src.cli login' to log in.")


async def cmd_bookings(args) -> None:
    async with BrowserSession(headless=True) as page:
        records = await fetch_bookings_list(
            page=page,
            start_date=args.date,
            tab=args.tab,
            max_rows=args.max
        )
        print(f"\n--- Retrieved {len(records)} Bookings ({args.tab}) ---")
        for r in records:
            print(f"[{r.booking_id}] Time: {r.booking_start_time} | Connector: {r.connector_id} | User: {r.user_name_masked} | Mode: {r.booking_mode}")


async def cmd_booking_details(args) -> None:
    async with BrowserSession(headless=True) as page:
        await fetch_bookings_list(page, max_rows=10)
        details = await fetch_booking_details(page, booking_id=args.id)
        print("\n--- Booking Details ---")
        print_json(details.model_dump())


async def cmd_charger_logs(args) -> None:
    exclude = [] if args.include_noise else ["Heartbeat", "MeterValues"]
    async with BrowserSession(headless=True) as page:
        entries = await fetch_charger_logs_beta(
            page=page,
            charger_code=args.charger,
            start_time=args.start,
            end_time=args.end,
            exclude_events=exclude,
            max_entries=args.max
        )
        print(f"\n--- Retrieved {len(entries)} OCPP Logs for Charger {args.charger} ---")
        for e in entries:
            print(f"[{e.timestamp}] {e.event_name} (MsgType: {e.message_type}) | Connector: {e.connector_id} | Reason: {e.reason} | Error: {e.error_code}")
            print(f"  Raw: {e.raw_message[:140]}")


async def cmd_rca(args) -> None:
    print(f"\n[RCA] Starting analysis for date: '{args.date or 'Today'}' (max: {args.max})...")
    candidates = []

    async with BrowserSession(headless=True) as page:
        # Pull Cancelled
        print("Fetching Cancelled bookings...")
        cancelled = await fetch_bookings_list(page, start_date=args.date, tab="Cancelled", max_rows=args.max)
        for r in cancelled:
            candidates.append({"record": r, "type": "Cancelled"})

        # Pull Completed if needed
        if not args.no_low_consumption and len(candidates) < args.max:
            rem = args.max - len(candidates)
            print("Fetching Completed bookings (checking for low consumption)...")
            completed = await fetch_bookings_list(page, start_date=args.date, tab="Completed", max_rows=rem)
            for r in completed:
                candidates.append({"record": r, "type": "Completed"})

        results = []
        print(f"Processing {len(candidates)} candidates...")
        for idx, item in enumerate(candidates, 1):
            rec = item["record"]
            print(f"[{idx}/{len(candidates)}] Inspecting booking {rec.booking_id}...")
            try:
                details = await fetch_booking_details(page, booking_id=rec.booking_id, row_selector=rec.details_link_selector)
                if item["type"] == "Completed":
                    if details.units_consumed_kw is not None and details.units_consumed_kw >= RCA_LOW_CONSUMPTION_THRESHOLD_KW:
                        continue

                ref_time = details.booking_in_time or details.scheduled_in_time or rec.booking_start_time
                start_win, end_win = compute_time_window(ref_time, window_mins=RCA_LOG_TIME_WINDOW_MINUTES)

                logs = []
                if details.charger_code:
                    logs = await fetch_charger_logs_beta(page, charger_code=details.charger_code, start_time=start_win, end_time=end_win)

                rca = analyze_booking_rca(details, logs, low_consumption_threshold_kw=RCA_LOW_CONSUMPTION_THRESHOLD_KW)
                results.append(rca)
                print(f"  -> Category: {rca.category} | Cause: {rca.root_cause}")
            except Exception as e:
                print(f"  -> Error: {e}")

        report = generate_rca_report(date_range=args.date or "Today", results=results)

        print("\n" + "=" * 60)
        print("ROOT CAUSE ANALYSIS EXECUTIVE SUMMARY")
        print("=" * 60)
        print(f"Date Range: {report.date_range}")
        print(f"Total Sessions Analyzed: {report.total_analyzed}")
        print(f"Cancelled: {report.cancelled_count} | Low Consumption (<1 kW): {report.low_consumption_count}")
        print("\nBreakdown by Failure Category:")
        for cat, count in report.category_breakdown.items():
            pct = (count / report.total_analyzed * 100) if report.total_analyzed else 0
            print(f"  - {cat:28s}: {count:2d} ({pct:.1f}%)")

        print("\nTop Affected Chargers:")
        for ch in report.top_affected_chargers:
            print(f"  - {ch['charger_code']}: {ch['incident_count']} incident(s)")

        print("\nIndividual Incident Breakdown:")
        for r in report.results:
            print(f"\nBooking #{r.booking_id} | Charger: {r.charger_code} (Conn: {r.connector_sequence_id})")
            print(f"  Time: {r.booking_time} | Consumed: {r.units_consumed_kw} kW")
            print(f"  Root Cause: {r.root_cause} [{r.category}] (Confidence: {r.confidence})")
            print(f"  Explanation: {r.explanation}")
            print(f"  Recommendation: {r.recommendation}")


async def cmd_hourly_rca(args) -> None:
    from src.rca.hourly_engine import run_24hour_hourly_analysis
    print(f"\n[HOURLY RCA] Running 24-hour analysis with {args.overlap}m overlap (max: {args.max})...")
    report = await run_24hour_hourly_analysis(
        max_bookings_per_tab=args.max,
        overlap_minutes=args.overlap
    )

    print("\n" + "=" * 70)
    print("ELECTREEFI 24-HOUR HOURLY ROOT CAUSE ANALYSIS (WITH 15-MIN OVERLAP)")
    print("=" * 70)
    print(f"Time Range: {report.analysis_start}  -->  {report.analysis_end}")
    print(f"Total Incidents Analyzed: {report.total_incidents_analyzed}")
    print(f"Cancelled: {report.total_cancelled} | Low Consumption (<1 kWh): {report.total_low_consumption}")

    print("\nOverall Category Distribution:")
    for cat, count in report.overall_category_breakdown.items():
        pct = (count / report.total_incidents_analyzed * 100) if report.total_incidents_analyzed else 0
        print(f"  - {cat:28s}: {count:2d} ({pct:.1f}%)")

    print("\n" + "-" * 70)
    print("HOURLY BREAKDOWN SLOTS (15-MIN OVERLAP WINDOWS)")
    print("-" * 70)
    for slot in report.hourly_slots:
        print(f"\n[Slot #{slot.slot_index:02d}] Window: {slot.window_label} | Total: {slot.total_incidents} (Canc: {slot.cancelled_count}, Low: {slot.low_consumption_count})")
        print(f"  Affected Chargers: {', '.join(slot.affected_chargers)}")
        print("  Failure Categories:")
        for cat, count in slot.category_breakdown.items():
            print(f"    * {cat}: {count}")
        print("  Incidents in window:")
        for inc in slot.incidents:
            print(f"    - Booking #{inc.booking_id} ({inc.booking_time}) | Charger: {inc.charger_code} (Gun {inc.connector_sequence_id}) | Consumed: {inc.units_consumed_kw} kW")
            print(f"      Root Cause: {inc.root_cause} [{inc.category}]")
            print(f"      Action: {inc.recommendation}")


def cmd_export_report(args) -> None:
    from src.reports.generate_word_report import build_rca_report
    out = args.output or "ElectreeFi_24Hour_RCA_Report.docx"
    print(f"\n[EXPORT] Generating Word Document report at: {out}...")
    path = build_rca_report(out)
    print(f"SUCCESS: Report saved to:\n  {path}")


def main():
    parser = argparse.ArgumentParser(description="ElectreeFi CMS RCA CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # login
    p_login = sub.add_parser("login", help="Launch visible browser to complete CAPTCHA and OTP")
    p_login.add_argument("--force", action="store_true", help="Force login even if session exists")

    # check-session
    sub.add_parser("check-session", help="Check if current session is active")

    # bookings
    p_bk = sub.add_parser("bookings", help="Fetch bookings list")
    p_bk.add_argument("--date", default="", help="Date filter (e.g. 2026-09-12)")
    p_bk.add_argument("--tab", default="Cancelled", choices=["Cancelled", "Completed", "New"], help="Tab name")
    p_bk.add_argument("--max", type=int, default=20, help="Max rows")

    # booking-details
    p_det = sub.add_parser("details", help="Fetch booking popup details")
    p_det.add_argument("--id", required=True, help="Booking ID")

    # logs
    p_log = sub.add_parser("logs", help="Fetch OCPP charger logs")
    p_log.add_argument("--charger", required=True, help="Charger code (e.g. DL-04-01)")
    p_log.add_argument("--start", required=True, help="Start time (e.g. 2026-09-13 14:00)")
    p_log.add_argument("--end", required=True, help="End time (e.g. 2026-09-13 14:20)")
    p_log.add_argument("--max", type=int, default=50, help="Max rows")
    p_log.add_argument("--include-noise", action="store_true", help="Include Heartbeat/MeterValues")

    # rca
    p_rca = sub.add_parser("rca", help="Run end-to-end RCA analysis")
    p_rca.add_argument("--date", default="", help="Date filter (e.g. 2026-09-12)")
    p_rca.add_argument("--max", type=int, default=10, help="Max bookings to process")
    p_rca.add_argument("--no-low-consumption", action="store_true", help="Skip completed low-consumption check")

    # hourly-rca
    p_hrca = sub.add_parser("hourly-rca", help="Run 24-hour hourly RCA analysis with 15-min overlap")
    p_hrca.add_argument("--max", type=int, default=100, help="Max bookings to inspect per tab")
    p_hrca.add_argument("--overlap", type=int, default=15, help="Overlap window in minutes (default: 15)")

    # export-report
    p_exp = sub.add_parser("export-report", help="Generate Microsoft Word (.docx) RCA report")
    p_exp.add_argument("--output", default="ElectreeFi_24Hour_RCA_Report.docx", help="Target .docx file path")

    args = parser.parse_args()
    if args.command == "login":
        asyncio.run(cmd_login(args))
    elif args.command == "check-session":
        asyncio.run(cmd_check_session(args))
    elif args.command == "bookings":
        asyncio.run(cmd_bookings(args))
    elif args.command == "details":
        asyncio.run(cmd_booking_details(args))
    elif args.command == "logs":
        asyncio.run(cmd_charger_logs(args))
    elif args.command == "rca":
        asyncio.run(cmd_rca(args))
    elif args.command == "hourly-rca":
        asyncio.run(cmd_hourly_rca(args))
    elif args.command == "export-report":
        cmd_export_report(args)


if __name__ == "__main__":
    main()
