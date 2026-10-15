# Rules on past bars, and causality

Read this when the idea is a rule on past bars (you are writing `rule.py`), when the user brings
their own list of events, or when the replay fails.

## The rule file

`declare.py init --kind rule` puts an empty `rule.py` in EXP. Edit two things only: `LOOKBACK` and
the body of `signal(window, params)`. Write it before the freeze: `declare.py check` refuses while
the file is still the empty template, and the freeze records its hash.

`rule.py` is ordinary Python. `declare.py check`, `events.py` and `sweep.py` run it on the user's
machine with the user's rights, and it is not sandboxed. Show the user the file before the first
`check`. Before running it the scripts read its text and refuse (exit code 2) anything at the top
level other than constants and functions, any import other than `math` and `statistics`, and the
names `open`, `exec`, `eval`, `compile`, `input` and `__import__`. That check stops accidents; it is
not a security boundary, so the user should still read the file.

- `window` holds the `LOOKBACK` most recent closed bars, oldest first, and nothing later:
  `window.ts`, `window.open`, `window.high`, `window.low`, `window.close`, `window.volume`, each
  exactly `LOOKBACK` numbers. `window.close[-1]` is the last closed bar's close.
- `params` is the dict declared under `idea.params`; a gridded parameter arrives with the value
  of the cell being run.
- Return +1 to enter long, -1 to enter short, 0 to do nothing. The entry is the open of the next
  bar, so a decision can never be filled inside the bar that produced it.
- Use nothing but the two arguments: no files, no module-level state, no clock, no random numbers.
  Read each `window` attribute once into a local name; every access builds a new tuple.

`idea.side` filters the returns: `long` takes only +1, `short` only -1, `both` takes either. A
signal that fires while a trade is open is skipped and counted. A decision whose lookback contains
a missing bar is skipped and counted (`skipped_gap_in_lookback`).

## Turning the user's words into `signal`

- Write the most literal reading. Add no filter, threshold, smoothing or confirmation the user did
  not state.
- Every number the user stated goes into `idea.params` under a plain name and is read from
  `params` in the code. Then it shows in the declarations, and it can be gridded if the user names
  several values.
- Where the words leave a number or a definition open, ask. Do not choose it.
- `LOOKBACK` is the largest number of past bars the rule needs. A value anchored to the day (a
  session high, a running average since midnight) is computed inside `signal` from the bars of
  that day in the window, so `LOOKBACK` must cover a full day of bars.
- A value from a longer bar than the data's is built inside `signal` from complete groups of
  closed bars only.
- Show the user `rule.py` together with the draft declarations. It is part of what they accept.

## The replay

`events.py` makes every decision once in sequence. It then picks the declared number of bars at
random with the declared seed, loads the rule file afresh for each, calls `signal` on that bar's
window alone, and requires the same answer. The `causality:` line reports the outcome.

- It catches hidden state: a counter, a cache, a module-level list, anything `signal` remembers
  from one call to the next. A failure prints `causality: FAIL` with the first three timestamps
  and exits 1.
- To fix it, make `signal` depend on its two arguments alone, record the edit with
  `declare.py amend --exp EXP --reason "..."` (the rule file is frozen, so `events.py` refuses an
  unrecorded edit; N rises by the cells already frozen), and run the steps again from `checkdata.py`. The
  decisions the rule makes must stay the user's; if removing the state changes what the rule
  means, ask them. Do not lower `replay_probes`, and do not edit the test.
- It cannot catch a fault on fewer bars than the sample finds, or a parameter value that was chosen
  by looking at the whole history. Say so under "What this does not show" when either may apply.

Look-ahead through the arguments is impossible by construction: `signal` is never handed the
current bar or a later one.

## Events supplied as a file

The file has a header `decision_ts,side`, with times in the same unit as the data; `side` may be
left out when `idea.side` is `long` or `short`. `decision_ts` is the moment the information was
known, not the bar it describes. The entry is the first bar opening at or after it, and that bar
must open less than one bar later, or the event is dropped and listed.

The scripts cannot see how those times were produced, so the `causality:` line reads `not verified
(events were supplied as a file)`. Such a test can still reach GO, with "causality of supplied
events not verified" on the verdict line. Ask the user how the list was made, go through the table
below with them, and record the answers under "Artifact checks done by hand".

## Where look-ahead comes from in a user's own code

| Source | Why it leaks | Fix |
|---|---|---|
| Full-sample normalisation (a z-score with the whole series' mean and deviation) | Every point knows the future range | Rolling or expanding window ending before the bar |
| Centred moving averages, two-sided filters | Half the window is future | Trailing windows only |
| Swing highs and lows, pivots, fractals | Confirmed only some bars later | Use the level only from its confirmation bar onward |
| Resampling with the wrong label or closed side | A bar stamped at its open but containing its close | Check one bar by hand against the raw data |
| Forward-fill across a merge | A later value fills an earlier row | Merge as-of with strict `<` on the timestamps |
| Day-anchored values (session high, a daily average price) | The finished day's value is used inside the day | Cumulative value up to the previous bar |
| A higher-timeframe bar used before it has closed | The bar opened at 13:00 on hourly data is known from 14:00 | Use it only from its close |
| Thresholds fitted on the whole sample | The threshold has seen out-of-sample | Fit on development only, apply unchanged |
| A list of instruments chosen today | The list was picked knowing what survived | The list as it stood on each date |

Two habits cover most rows: a value computed from a bar's close is acted on at the next bar's open
at the earliest, and every join between a signal and a price uses strict `<`, never `<=`.
