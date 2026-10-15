# Pitfalls

These bugs and surprises came up in real searches. Each one silently produced wrong or missing results.

## 1. Local-currency prices

**Symptom:** whole regions such as Poland, Scandinavia and the UK look absurdly expensive or disappear from results.

**Cause:** the Ryanair fare-finder returns prices in the departure country's currency. For example, a 65.55 PLN fare from Kraków looks like €65.55 when it's really about €15.

**Fix:** always add `currency=EUR` to fare-finder requests. When presenting results, remember that the booking is still **charged** in local currency (GBP, PLN, CZK, HUF, SEK, DKK, NOK), so say so and give an approximate conversion.

## 2. Round trips silently excluded

**Symptom:** there are no results that start and end at the same airport, even though `A → B → C → A` is the most common shape.

**Cause:** the "no revisits" check treated the home airport, the `from` of the first leg, as already visited.

**Fix:** exempt home airports from the revisit check.

## 3. Hub loops excluded

**Symptom:** zero results for a region that only one city connects to home. Example: from Memmingen, Kraków is the only non-UK, non-Irish northern destination.

**Cause:** the trip has to be `Home → Hub → X → Hub → Home`, which revisits the hub.

**Fix:** allow exactly one return to the entry city.

## 4. After-midnight arrivals

**Symptom:** itineraries that run past the end date, or "1-night" stops with no night.

**Cause:** a 23:05 departure arriving at 00:50 moves the arrival date, so night counting drifts.

**Fix:** only accept legs that arrive on the day they depart. Also reject very late arrivals (after about 23:00) at intermediate cities.

## 5. One cheap seat

**Symptom:** a fare of 14.99 per person becomes 21.78 per person, or "no fare", when searching for 2.

**Cause:** the cheapest fare bucket often has only one seat left.

**Fix:** re-price every shortlisted leg with the real passenger count (`adultPaxCount=2`, or the booking page). The fare-finder returns the **total for all passengers** when `adultPaxCount > 1`. If it returns nothing, check the booking page: there is often still a fare, just higher.

## 6. Only one flight per destination per day

**Symptom:** a chain is rejected for bad timing even though a slightly dearer flight at a better time exists.

**Cause:** the fare-finder endpoint returns only the cheapest flight per destination per day.

**Fix:** for promising city pairs, open the booking page or Google Flights to see every flight that day.

## 7. Home airport not served

**Symptom:** a major hub returns nothing. For example, Munich (MUC) has no Ryanair flights.

**Fix:** check other airlines on Google Flights. If they cost much more, start or end the trip overland (train or bus) from the home city instead.

## 8. Visa constraints

**Symptom:** the best results all route through London Stansted or Dublin, which are big low-cost hubs.

**Fix:** ask about visas up front and put those countries in `excludeCountries`.

## 9. Blocked sites

Skyscanner tends to show an endless loading screen to automated browsers, and Google Flights sometimes says "Oops, something went wrong" on the first load (clicking Reload usually fixes it). Ryanair's booking-availability API returns HTTP 409 without a browser session, but the fare-finder endpoint and the booking pages work.
