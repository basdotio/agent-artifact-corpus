# cheap-multi-city-trips

A Claude skill that plans the **cheapest multi-city trip to anywhere**. You give it your dates (exact or a window), trip length and home airports. It searches low-cost flights, plus trains and buses between cities, and returns 3–5 priced itineraries with booking links.

> "I have 5 days between 19 Oct and 13 Nov, flying from Memmingen. I don't care where."
>
> → `FMM → Catania (2 nights) → Malta (2 nights) → FMM`, €112 for two, all flights in daytime.

## What it does

- **Asks first** which airports to use (and whether a train or bus start or end is OK), then any missing dates, trip length, passengers, baggage, regions and visa restrictions.
- **Searches the whole Ryanair network** day by day with a browser-side script, and adds trains and buses where flights are thin.
- **Applies common-sense timing:** no evening-arrival-then-morning-departure stops, no after-midnight arrivals, and flags early starts.
- **Re-prices every leg for the real passenger count**, because the last cheap seat is often single.
- **Outputs tables** with dates, times, carriers, prices and booking links, plus a comparison of the options.

## Repository layout

```
cheap-multi-city-trips/
├── SKILL.md            # the skill: workflow, rules, output format
├── ryanair_search.js   # browser-console search engine (configurable)
├── pitfalls.md         # bugs and gotchas found in real searches
├── LICENSE
└── README.md
```

## Installation

**Claude (claude.ai / desktop / Cowork):** zip the `cheap-multi-city-trips` folder and upload it under *Settings → Capabilities → Skills*, or add it to a plugin.

**Claude Code:** copy the folder into `~/.claude/skills/` (personal) or `.claude/skills/` (project).

The skill needs a **browser tool**, such as the built-in browser or a browser extension, to read live fares.

## Using the search script on its own

1. Open any page on `https://www.ryanair.com`.
2. Edit `CONFIG` at the top of `ryanair_search.js`: home airports, optional home city, date window, nights, price caps, countries to include or exclude, ground links.
3. Paste the file into the DevTools console.
4. When `TRIP_SEARCH.status === 'done'`, run `printTrips(20)`.
5. Re-price shortlisted legs: `await repriceLeg('FMM', 'CTA', '2026-11-09', 2)`. Get a booking link with `bookingUrl('FMM', 'CTA', '2026-11-09', 2)`.

A typical run (one month window, 6 nights, rail links enabled) takes 1–3 minutes and makes a few hundred to ~2,000 cached requests.

## Limitations

- **Ryanair only:** the script covers one airline. Use Google Flights to cross-check other carriers.
- **Unofficial endpoints:** they may change or be rate-limited. The script keeps concurrency low (6) and caches results. Use it for personal trip planning, not scraping at scale.
- **Estimated ground prices:** train and bus prices in `groundLinks` are estimates. Verify them before booking.
- **Approximate conversion:** prices are compared in EUR, but bookings from non-euro countries are charged in local currency.

## License

MIT. See [LICENSE](LICENSE).
