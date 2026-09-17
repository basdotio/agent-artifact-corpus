---
name: strava-next-week-planner
description: Generate a next-week training plan from weekly load + risk outputs (derived from Strava MCP data).
---

## Goal
Create a realistic next-week plan aligned with the user's goal and current risk level.

## Procedure
1) Fetch 4-week context via `weekly_stats(weeks=4, week_start=monday, tz_name=Asia/Tokyo)`.
2) Optionally call `detect_last_ride_and_comment()` to tailor tone and highlight the latest ride.
3) Ask/Infer goal:
   - default: base building (if not specified)
4) Output a 7-day plan:
   - 1 key session max (or none if risk=high)
   - 2-4 easy sessions (Z2)
   - at least 1 rest day
   - include a brief "why" for each day
5) Include guardrails:
   - cap weekly volume increase (e.g., ~10% heuristic)
   - if risk high: emphasize recovery

## Output format (Markdown)
- Weekly objective
- Day-by-day bullets (Mon..Sun)
- Safety notes
