# Clock events

Read this when the idea is tied to a clock time or to a session open or close.

## Local time and zone, never a fixed UTC hour

Declare the event as a local `HH:MM` plus an IANA zone name, in the user's own terms. If they name a
session rather than a time, ask which local clock time, which city and which days they mean; do not
pick or list candidates for them. A fixed UTC hour is wrong for part of every year wherever clocks
change: 09:30 in New York was 13:30 UTC on 238 days of 2024 and 14:30 UTC on the other 128.
`events.py` converts each date and prints both on the `event in UTC:` line: quote it as printed.
One event time per experiment; the time cannot be gridded.

If Python has no time-zone database, `America/New_York` uses a built-in rule (valid from 2007) and
the output says `zone rule: built-in US fallback`; any other zone stops with exit code 2. Then run
where Python has zone data. Restating the event in another zone changes the idea: the user decides.

## Bars and the entry

- The entry is the open of the bar whose open time equals the event time. The bar size must
  therefore divide the clock time: `declare.py check` refuses 09:30 on bars of 3,600 seconds. Ask
  for finer bars; do not shift the event.
- When that bar does not exist on a date, the event is dropped and listed with its date: tell the
  user the dates. If the dropped share is above the declared limit, `events.py` exits 1.
- `days` is the user's: `"weekdays"`, `"all"`, or the weekday numbers they named.

## Holidays

No holiday calendar is computed. A weekday on which the user's market was closed still counts as an
event, unless the user supplies `skip_dates_file` (one `YYYY-MM-DD` local date per line) before the
freeze. Ask whether they have one. If not, say so under "What this does not show".

## Why the null is other times on the same days

For a clock idea the claim is that this time of day matters. A null drawn from the same hour on
other days would contain the effect it is meant to test, and a null drawn from other days at any
hour would mix in whatever those days did as a whole. So each draw keeps the day, the side, the
hold and the cost, and moves only the start time, to a time whose window does not overlap the
event's. What is left to differ is the clock time alone.

So the hold must be well under a day. With a hold near 24 hours no other window exists on the
same day and `effect.py` stops with `DEGENERATE NULL`: the idea cannot be tested here. Say so.
A session open is usually more volatile than the times it is compared with. The scripts allow for
that: the null p is the larger of the draw count and a p that uses the event days' own spread.

## The weekend placebo line

When the event is declared on weekdays and the data has weekend bars, `effect.py` also prints the
same clock rule on Saturdays and Sundays: gross mean and t, reported and never gated. A weekend
figure like the weekday one makes the named session an unlikely cause. Draw nothing else from it.

## Limits to state under "What this does not show"

- Other things happen at fixed times: a perpetual contract's funding settlement at fixed UTC hours,
  scheduled announcements at fixed local hours. As the event's UTC time moves with daylight saving,
  such a thing can be inside the window for part of the year. The test does not separate them, and
  no script checks a schedule: a time you recall is unverified, so say that and do not rule it out.
- For a few weeks each spring and autumn, regions change clocks on different dates. Those weeks
  are too few to test alone and are pooled with the rest.
