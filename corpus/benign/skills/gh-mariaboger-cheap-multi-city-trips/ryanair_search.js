/**
 * Multi-city low-cost itinerary search (Ryanair network + optional ground links).
 *
 * HOW TO RUN
 *   1. Open any page on https://www.ryanair.com in a browser (same-origin requests are required).
 *   2. Edit CONFIG below.
 *   3. Paste this whole file into the DevTools console, or run it through a browser
 *      automation tool's "execute JavaScript" action.
 *   4. Wait until `window.TRIP_SEARCH.status === 'done'`, then call `printTrips(30)`.
 *
 * WHAT IT DOES
 *   Depth-first search over (city, date) using Ryanair's public fare-finder endpoint, which
 *   returns the cheapest fare per destination for a given departure airport and day.
 *   Chains must start and end at a home airport (or the home city via a ground link),
 *   fill exactly CONFIG.nights nights, and respect time-in-city rules.
 *
 * LIMITATIONS
 *   - Ryanair only. Other airlines (Wizz Air, easyJet, Eurowings, etc.) are not covered.
 *   - The endpoint returns ONE flight per destination per day (the cheapest), so a slightly
 *     more expensive flight with better times may exist.
 *   - Prices are per person for 1 passenger. Always re-price shortlisted legs for the real
 *     passenger count (see `repriceLeg`), because the last cheap seat is often single.
 *   - Ground links are estimates you provide; verify them separately.
 *   - Unofficial endpoint: it may change or rate-limit. Keep concurrency low.
 */

const CONFIG = {
  // Example values below — replace with the user's answers.
  homeAirports: ['FMM'],          // airports where the trip may start/end by plane (IATA codes)
  homeCity: 'MUC',                // pseudo-node for starting/ending by train/bus (must appear in groundLinks), or null
  firstDepartureDate: '2026-10-19',
  lastReturnDate: '2026-11-13',
  nights: 6,                      // total nights away (trip of N days = N-1 nights)
  nightsPerStop: [1, 2],          // allowed nights in one city
  maxLegPrice: 75,                // EUR per person
  maxTotalPrice: 260,             // EUR per person
  includeCountries: null,         // e.g. ['poland', 'sweden'] (case-insensitive substring of country name); null = any
  excludeCountries: ['united kingdom', 'ireland'],
  requireAnyOf: [],               // e.g. ['RIX','VNO','CPH']: result must visit at least one of these
  earliestHomeDeparture: '08:00', // first flight from a home airport
  latestHomeArrival: '21:30',     // last flight into a home airport
  earliestCityDeparture: '07:00', // flights from intermediate cities
  latestCityArrival: '23:00',     // arrivals at intermediate cities (same day only)
  minWakingHours: { 1: 8, 2: 18 },// minimum usable hours (08:00–22:00, minus airport time) per stop length
  groundDeparture: '10:00',       // assumed departure time for ground legs between cities
  homeGroundDeparture: '08:00',   // assumed departure time for the first ground leg from homeCity
  maxLegs: 6,
  concurrency: 6,
  // [cityA, cityB, hours, EUR per person, label] — symmetric. Use Ryanair airport codes as city ids.
  groundLinks: [
    ['MUC', 'PRG', 4.5, 20, 'bus Munich–Prague'],
    ['MUC', 'BER', 4.5, 40, 'train Munich–Berlin'],
    ['MUC', 'VIE', 4, 35, 'train Munich–Vienna'],
    ['PRG', 'BER', 4.3, 25, 'train Prague–Berlin'],
    ['PRG', 'VIE', 4, 20, 'train Prague–Vienna'],
    ['PRG', 'WRO', 4.5, 20, 'bus Prague–Wrocław'],
    ['BER', 'HAM', 2, 25, 'train Berlin–Hamburg'],
    ['HAM', 'CPH', 4.7, 40, 'train Hamburg–Copenhagen'],
    ['BER', 'POZ', 2.5, 20, 'train Berlin–Poznań'],
    ['BER', 'WRO', 4, 20, 'bus Berlin–Wrocław'],
    ['VIE', 'BTS', 1, 12, 'train Vienna–Bratislava'],
    ['VIE', 'BUD', 2.7, 20, 'train Vienna–Budapest'],
    ['KRK', 'WMI', 2.5, 20, 'train Kraków–Warsaw'],
    ['KRK', 'KTW', 1, 6, 'train Kraków–Katowice'],
    ['KRK', 'WRO', 3.3, 18, 'train Kraków–Wrocław'],
    ['WMI', 'GDN', 3, 22, 'train Warsaw–Gdańsk'],
    ['WRO', 'POZ', 2.5, 15, 'train Wrocław–Poznań'],
    ['POZ', 'WMI', 2.8, 20, 'train Poznań–Warsaw'],
    ['GDN', 'POZ', 3.5, 20, 'train Gdańsk–Poznań'],
    ['WMI', 'VNO', 8, 25, 'bus Warsaw–Vilnius'],
    ['VNO', 'KUN', 1.3, 8, 'train Vilnius–Kaunas'],
    ['VNO', 'RIX', 4, 18, 'bus Vilnius–Riga'],
    ['KUN', 'RIX', 4, 18, 'bus Kaunas–Riga'],
    ['RIX', 'TLL', 4.5, 20, 'bus Riga–Tallinn'],
    ['TLL', 'HEL', 2.2, 30, 'ferry Tallinn–Helsinki'],
    ['CPH', 'MMX', 0.7, 12, 'train Copenhagen–Malmö'],
    ['CPH', 'GOT', 4, 30, 'train Copenhagen–Gothenburg'],
    ['GOT', 'OSL', 4, 30, 'bus Gothenburg–Oslo'],
    ['ARN', 'GOT', 3.2, 35, 'train Stockholm–Gothenburg'],
    ['TRF', 'OSL', 2, 20, 'train Sandefjord–Oslo'],
  ],
  // Extra per-person cost for airports far from the city they serve (ranking only).
  remoteAirportPenalty: { STN: 20, HHN: 30, BVA: 30, CRL: 15, NYO: 25, NRN: 20, WMI: 8, TRF: 25, VST: 20 },
};

(() => {
  const S = (window.TRIP_SEARCH = { status: 'running', results: [], cache: {}, nodes: 0, errors: 0 });
  const C = CONFIG;
  const HOME = new Set([...C.homeAirports, ...(C.homeCity ? [C.homeCity] : [])]);

  // ---------- helpers ----------
  const addDays = (d, n) => { const x = new Date(d + 'T12:00:00Z'); x.setUTCDate(x.getUTCDate() + n); return x.toISOString().slice(0, 10); };
  const hhmm = (s) => s.slice(11, 16);
  const hrs = (s) => new Date(s + 'Z').getTime() / 3.6e6;            // local wall-clock hours (consistent within one city)
  const iso = (h) => new Date(h * 3.6e6).toISOString().slice(0, 19);
  const countryOk = (c) => {
    const n = (c || '').toLowerCase();
    if (C.excludeCountries.some((x) => n.includes(x))) return false;
    return !C.includeCountries || C.includeCountries.some((x) => n.includes(x));
  };
  // Usable hours in a city between arrival and next departure, counting only 08:00–22:00,
  // minus ~1h after landing / ~2h before a flight (less for trains/buses).
  const wakingHours = (arr, dep, arrGround, depGround) => {
    const a = hrs(arr) + (arrGround ? 0.3 : 1), b = hrs(dep) - (depGround ? 0.5 : 2);
    let tot = 0;
    for (let d0 = Math.floor(a / 24) * 24; d0 < b; d0 += 24) {
      const s = Math.max(a, d0 + 8), e = Math.min(b, d0 + 22);
      if (e > s) tot += e - s;
    }
    return Math.max(0, tot);
  };

  // ---------- ground graph ----------
  const ground = {};
  for (const [a, b, h, p, label] of C.groundLinks) {
    const [mode, route] = [label.split(' ')[0], label.slice(label.indexOf(' ') + 1)];
    const [x, y] = route.split('–');
    (ground[a] ||= []).push({ to: b, h, p, label });
    (ground[b] ||= []).push({ to: a, h, p, label: `${mode} ${y}–${x}` });
  }
  const groundLegs = (city, date, time) => (ground[city] || []).map((g) => ({
    from: city, to: g.to, toName: g.label.split('–')[1], dep: `${date}T${time}:00`,
    arr: iso(hrs(`${date}T${time}:00`) + g.h), price: g.p, id: g.label, ground: true,
  }));

  // ---------- fare fetching (cached, rate-limited) ----------
  let active = 0; const queue = [];
  const limit = (fn) => new Promise((res, rej) => {
    const run = () => { active++; fn().then(res, rej).finally(() => { active--; if (queue.length) queue.shift()(); }); };
    active < C.concurrency ? run() : queue.push(run);
  });
  const flights = (ap, date) => {
    if (!/^[A-Z]{3}$/.test(ap) || (C.homeCity && ap === C.homeCity && !C.homeAirports.includes(ap))) return Promise.resolve([]);
    const key = ap + date;
    if (S.cache[key]) return S.cache[key];
    S.cache[key] = limit(async () => {
      // currency=EUR matters: without it prices come back in the departure country's currency (PLN, GBP, SEK, HUF...).
      const url = `/api/farfnd/v4/oneWayFares?departureAirportIataCode=${ap}&outboundDepartureDateFrom=${date}` +
        `&outboundDepartureDateTo=${date}&market=en-gb&adultPaxCount=1&currency=EUR`;
      for (let i = 0; i < 4; i++) {
        try {
          const r = await fetch(url); if (!r.ok) throw new Error(r.status);
          const j = await r.json();
          return (j.fares || []).map((f) => ({
            from: ap, to: f.outbound.arrivalAirport.iataCode, toName: f.outbound.arrivalAirport.city.name,
            country: f.outbound.arrivalAirport.countryName, dep: f.outbound.departureDate, arr: f.outbound.arrivalDate,
            price: f.outbound.price.value, id: f.outbound.flightNumber, ground: false,
          }));
        } catch (e) { await new Promise((r) => setTimeout(r, 2000)); }
      }
      S.errors++; return [];
    });
    return S.cache[key];
  };
  const options = async (city, date) => {
    const fl = (await flights(city, date)).filter((f) => HOME.has(f.to) || countryOk(f.country));
    return fl.concat(groundLegs(city, date, C.groundDeparture));
  };

  // ---------- search ----------
  const sameDayArrival = (l) => l.arr.slice(0, 10) === l.dep.slice(0, 10);
  const visitsRequired = (chain) => !C.requireAnyOf.length || chain.some((l) => C.requireAnyOf.includes(l.to));

  async function extend(chain, nightsLeft, endDate) {
    S.nodes++;
    const last = chain[chain.length - 1], city = last.to, entry = chain[0].to;
    const cost = chain.reduce((s, l) => s + l.price, 0);
    for (const n of C.nightsPerStop) {
      if (n > nightsLeft) continue;
      const date = addDays(last.arr.slice(0, 10), n);
      for (const f of await options(city, date)) {
        if (f.price > C.maxLegPrice || cost + f.price > C.maxTotalPrice) continue;
        if (!f.ground && hhmm(f.dep) < C.earliestCityDeparture) continue;
        if (wakingHours(last.arr, f.dep, last.ground, f.ground) < (C.minWakingHours[n] ?? 8)) continue;
        const toHome = HOME.has(f.to);
        if (!toHome) {
          if (f.to === city) continue;
          // No revisits, EXCEPT coming back to the entry city once (needed when only one city
          // connects to home, e.g. fly into Kraków, loop through Budapest, fly home from Kraków).
          const revisit = chain.some((l) => l.from === f.to);
          const entryLoop = f.to === entry && chain.length >= 2 && !chain.slice(1).some((l) => l.to === entry);
          if (revisit && !entryLoop) continue;
        }
        if (n === nightsLeft) {
          const arrOk = f.ground ? hhmm(f.arr) <= '23:00' : hhmm(f.arr) <= C.latestHomeArrival;
          const next = [...chain, f];
          if (toHome && arrOk && sameDayArrival(f) && date === endDate && visitsRequired(next)) {
            S.results.push({ legs: next, total: cost + f.price });
          }
        } else if (!toHome && sameDayArrival(f) && hhmm(f.arr) <= C.latestCityArrival && chain.length < C.maxLegs) {
          await extend([...chain, f], nightsLeft - n, endDate);
        }
      }
    }
  }

  (async () => {
    const lastStart = addDays(C.lastReturnDate, -C.nights);
    for (let d = C.firstDepartureDate; d <= lastStart; d = addDays(d, 1)) {
      const first = [];
      for (const h of C.homeAirports) {
        for (const f of await flights(h, d)) {
          if (!HOME.has(f.to) && countryOk(f.country) && f.price <= C.maxLegPrice && hhmm(f.dep) >= C.earliestHomeDeparture &&
              sameDayArrival(f) && hhmm(f.arr) <= '21:00') first.push(f);
        }
      }
      if (C.homeCity) first.push(...groundLegs(C.homeCity, d, C.homeGroundDeparture));
      await Promise.all(first.map((f) => extend([f], C.nights, addDays(d, C.nights))));
    }
    S.status = 'done';
    console.log(`Search done: ${S.results.length} itineraries, ${Object.keys(S.cache).length} fare lookups, ${S.errors} errors.`);
  })();

  // ---------- ranking & output ----------
  window.rankTrips = () => {
    const seen = new Set(), out = [];
    for (const r of S.results) {
      const groundHours = r.legs.filter((l) => l.ground).reduce((s, l) => s + hrs(l.arr) - hrs(l.dep), 0);
      const early = r.legs.filter((l) => !l.ground && hhmm(l.dep) < '08:30').length;
      const remote = r.legs.slice(0, -1).reduce((s, l) => s + (l.ground ? 0 : C.remoteAirportPenalty[l.to] || 0), 0);
      r.score = r.total + remote + 2 * groundHours + 8 * early;   // EUR-equivalent: cheap AND comfortable
    }
    S.results.sort((a, b) => a.score - b.score);
    for (const r of S.results) {
      const key = r.legs.slice(0, -1).map((l) => l.to).sort().join('-');   // one result per city set
      if (!seen.has(key)) { seen.add(key); out.push(r); }
    }
    return out;
  };
  window.printTrips = (n = 30) => rankTrips().slice(0, n).map((r) =>
    `score ${r.score.toFixed(0)} | €${r.total.toFixed(2)} pp | ` +
    r.legs.map((l) => `${l.from}>${l.to} ${l.dep.slice(5, 16).replace('T', ' ')}-${hhmm(l.arr)} €${l.price} ${l.id}`).join(' || ')
  ).join('\n');

  // Re-price one leg for the real passenger count. Returns per-person EUR price or null.
  // If null, open the booking page (bookingUrl) — the cheap fare may have only 1 seat left.
  window.repriceLeg = async (from, to, date, adults = 2) => {
    const url = `/api/farfnd/v4/oneWayFares?departureAirportIataCode=${from}&arrivalAirportIataCode=${to}` +
      `&outboundDepartureDateFrom=${date}&outboundDepartureDateTo=${date}&market=en-gb&adultPaxCount=${adults}&currency=EUR`;
    const j = await (await fetch(url)).json();
    const f = j.fares && j.fares[0];
    return f ? { flight: f.outbound.flightNumber, dep: hhmm(f.outbound.departureDate), arr: hhmm(f.outbound.arrivalDate), totalForAll: f.outbound.price.value } : null;
  };
  window.bookingUrl = (from, to, date, adults = 2) =>
    `https://www.ryanair.com/de/en/trip/flights/select?adults=${adults}&teens=0&children=0&infants=0&dateOut=${date}` +
    `&isConnectedFlight=false&isReturn=false&discount=0&originIata=${from}&destinationIata=${to}` +
    `&tpAdults=${adults}&tpTeens=0&tpChildren=0&tpInfants=0&tpStartDate=${date}&tpDiscount=0&tpOriginIata=${from}&tpDestinationIata=${to}`;
})();
