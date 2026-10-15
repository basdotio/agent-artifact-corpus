---
name: cheap-multi-city-trips
description: Plan the cheapest multi-city trip for any destination ("I don't care where"), given dates or a date window, trip length and home airports. Searches low-cost flights plus trains/buses and returns 3-5 priced itineraries with booking links.
---

# Cheap Multi-City Trip Finder

The traveler does not care where they go. Your job is to find the cheapest **sensible** chain of cities, for example `Home → Catania → Malta → Home` or `Home → Kraków → Budapest → Kraków → Home`, that fits their dates. Present it with real, re-checked prices and booking links.

Write all output in English.

## 1. Ask first, then search

**Before any search, ask which airports to use.** Never assume home airports, even if you think you know where the user lives. Ask in one round, using a multiple-choice question tool if one is available, otherwise in plain text:

1. **Departure and return airports.** Which airports can the trip start and end at? Can the return be to a different airport than the departure?
2. **Starting or ending by train or bus.** Is it OK to begin or end the trip overland from the home city (for example, a bus from home to Prague, then fly onward)? If yes, which home city?
3. Anything still missing from the request:
   - **Dates:** exact dates, preferred dates, or a window (earliest departure / latest return).
   - **Trip length:** in days or nights.
   - **Passengers:** default 2 adults.
   - **Baggage:** default cabin bag only (no checked bags).
   - **Regions:** any wanted or excluded regions or countries.
   - **Visas:** countries the traveler cannot enter. Ask this explicitly, because it silently invalidates whole regions (for example, no UK visa rules out London Stansted, a major low-cost hub).

Defaults when the user doesn't say:

| Setting | Default |
|---|---|
| Nights per city | 1–2 |
| Trains/buses between cities | Allowed |
| Passengers | 2 adults |
| Baggage | Cabin bag only |

A trip of N days means N−1 nights. Do not stop to ask about anything that has a default.

## 2. Tools and sources

Live fares are rendered dynamically, so use a browser (built-in browser or browser extension). Use plain web search only for background such as route maps, transfer times and rail prices.

- **Bulk search (recommended):** `ryanair_search.js`. Run it in the browser on any `ryanair.com` page. It walks the whole Ryanair network day by day, combines flights with the ground links you configure, applies the timing rules below, and ranks results. See the header of the file for usage.
- **Other airlines and cross-checks:** Google Flights (`https://www.google.com/travel/flights?q=Flights%20to%20{TO}%20from%20{FROM}%20on%20{YYYY-MM-DD}%20oneway&hl=en&curr=EUR`), Skyscanner, Kiwi.com, and airline sites (Wizz Air, easyJet, Eurowings, airBaltic, etc.). Skyscanner often blocks automated browsers; move on if it does.
- **Ground legs:** Omio, FlixBus, Deutsche Bahn, ÖBB, PKP Intercity, Lux Express, national rail operators.

Decline cookie banners (choose "Reject all"). If a site needs a captcha, ask the user once to solve it, or switch sources.

## 3. Search method

1. **Configure the search** with the user's answers: home airports, optional home city for overland start/end, date window, nights, nights per stop, price caps, allowed and excluded countries, and must-visit cities if the user wants a region (for example, Baltic or Nordic airports).
2. **Run the bulk search**, then print the top results. If nothing comes back, loosen constraints one at a time (price caps first, then time rules) and say what you loosened.
3. **Add ground links** where flights are thin. When few flights connect home to a region, plan loops:
   - Fly into a hub, travel overland, return to the hub, fly home.
   - Or start or end the trip by train or bus from the home city.
4. **Cross-check** the top chains against other airlines on Google Flights when a home airport is served by more than Ryanair.
5. **Re-price every leg for the real passenger count** using `repriceLeg(from, to, date, adults)` or the booking page (`bookingUrl(...)`). The cheapest fare often has only one seat left, so the price for 2 is frequently higher than 2 × the single fare.
6. **Rank** by total cost, then by comfort: penalize early departures, long overland legs and remote airports.

Count the full cost:

- Fares for all passengers, including the cabin bag if needed. Basic low-cost fares usually include only a small under-seat bag; a trolley needs Priority, which costs extra.
- Mandatory fees.
- Getting to and from the home airports.
- Transfers from remote airports (Stansted, Beauvais, Charleroi, Skavsta, Torp, Hahn, Modlin…).
- Estimated train and bus fares, labeled as estimates.

## 4. Timing rules (common sense, not perfection)

The point is to see each city. A full day per city is not required, but each stop must leave meaningful time.

- Count usable time between 08:00 and 22:00 only, minus about 1 hour after landing and 2 hours before a flight (less for trains).
- Aim for at least ~8 usable hours for a 1-night stop and ~18 for a 2-night stop.
- Reject stops that are effectively zero time, such as an evening arrival followed by a morning departure.
- Reject arrivals after midnight: the night is lost and the date shifts.
- Avoid first departures from home before ~08:00 (it means leaving home before dawn). Avoid city departures before ~07:00. Flag any early leg you include.
- Late arrivals home are fine, but check that public transport home is still running.
- A slightly cheaper option with clearly worse timing ranks below a sensible one.

## 5. Output

Present results as tables in the chat. Give 3–5 options, cheapest sensible first.

For each option:

**Option N: City A → City B → City C, dates, ≈ Total € for N adults**

| # | Date | From → To | Dep – Arr | Carrier / mode | Price (all pax) | Link |
|---|---|---|---|---|---|---|

After each table, 1–2 lines covering: nights per city, usable time in each city, and caveats (early starts, few seats left, local-currency charging, remote airports).

End with:
- a comparison table (route, dates, total, main trade-off),
- a line stating when prices were checked and that low-cost fares change quickly,
- what was **not** searched (for example, "Ryanair only; Wizz Air not covered").

### Links

Every leg needs a link that opens the search or booking page with date and passenger count prefilled. Never invent a URL. Test the pattern once per session.

- **Ryanair:** `https://www.ryanair.com/de/en/trip/flights/select?adults=2&teens=0&children=0&infants=0&dateOut={YYYY-MM-DD}&isConnectedFlight=false&isReturn=false&discount=0&originIata={FROM}&destinationIata={TO}&tpAdults=2&tpTeens=0&tpChildren=0&tpInfants=0&tpStartDate={YYYY-MM-DD}&tpDiscount=0&tpOriginIata={FROM}&tpDestinationIata={TO}`
- **Google Flights:** `https://www.google.com/travel/flights?q=Flights%20to%20{TO}%20from%20{FROM}%20on%20{YYYY-MM-DD}%20oneway&hl=en&curr=EUR`
- **Ground legs:** the operator's homepage (FlixBus, bahn.de, oebb.at, intercity.pl, luxexpress.eu, vy.no), unless you have a verified deep link.

## 6. Pitfalls (learned the hard way)

Read `pitfalls.md` before the first search. In short:

- Request prices with `currency=EUR`. Otherwise flights from Poland, the UK, Scandinavia, Czechia and Hungary come back in local currency and look 4–400× more expensive.
- Allow a trip to return to the airport it started from. Treating "home" as an already-visited city silently removes every round trip.
- Allow one return to the entry city. When only one city connects home to a region, loops through that hub are the only valid trips.
- Reject legs that arrive after midnight. Otherwise night counts and dates drift.
- Re-price for the real passenger count before presenting anything.
- Flights from non-euro countries are charged in local currency (GBP, PLN, CZK, HUF, SEK, DKK, NOK). Say so and convert approximately.

## 7. Final checks before answering

- [ ] Every flight price was re-checked for the real passenger count on the exact date.
- [ ] Every chain starts and ends where the user allowed, and fits the date window and trip length.
- [ ] No excluded country (for example, visa restrictions) appears anywhere in the chain.
- [ ] No stop breaks the timing rules without a flag.
- [ ] Totals are recomputed; estimates are labeled.
- [ ] Everything is in English.
