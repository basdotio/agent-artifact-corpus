# Mode: Obligations and Key Dates

## Goal
Turn a signed contract into a usable register entry: who owes what, by when, and which deadlines can cost money if missed.

## Step-by-Step

**Step 1 — Confirm the document set.** Main agreement, all amendments, order forms, SOWs, schedules. Amendments override the base text, so apply them in date order and say which version governs each term.

**Step 2 — Extract key dates.** Effective date, initial term end, renewal mechanics, **notice deadline** (expiry minus notice period, calculated explicitly), price-review dates, minimum-commitment true-up dates, audit windows, insurance certificate renewals, and SLA reporting cycles.

**Step 3 — Extract obligations by party.**
- **Supplier:** service levels, reporting, certifications to maintain, security controls, breach notification, insurance, subcontractor approvals.
- **Us:** payment timing, minimum volume or spend commitments, forecast or ordering rules, cooperation duties, data we must supply, notice duties.

For each: clause reference, description, owner (role), trigger or frequency, consequence of failure.

**Step 4 — Flag money-at-risk items.** Auto-renewal windows, minimum-spend shortfalls, early-termination fees, indexation uplifts, service credits we must claim within a time limit (claims are often forfeited if not made).

**Step 5 — Build the register entry.**

| Field | Content |
|---|---|
| Supplier / contract ID / type | |
| Value (annual / total) and currency | |
| Effective / expiry / **notice deadline** | |
| Renewal type | Auto / manual / evergreen |
| Business owner / procurement owner | |
| Obligations table | party, obligation, clause, due, owner |
| Money-at-risk table | item, amount or formula, deadline |
| Open issues | ambiguities, missing documents |

**Step 6 — Set alerts.** List the dates that need reminders, starting at the configured lead time (default 120 days before the notice deadline). Offer a calendar-ready list; do not create calendar events unless the user asks.

## Output Rules
- Show the date arithmetic for every notice deadline.
- If a date is ambiguous (for example "annual anniversary" with no start date), flag it instead of guessing.
- Mark anything derived from an unreviewed amendment as unconfirmed.
