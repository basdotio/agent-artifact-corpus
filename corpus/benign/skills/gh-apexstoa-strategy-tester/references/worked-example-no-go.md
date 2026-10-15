# Worked example: an idea that tested as NO-GO

Read this when the user asks what a full test looks like in practice, never during a live test.

A real test from Apexstoa's own research archive, experiment 063, dated 2026-09-18. It is
shown because it ended NO-GO. Every figure below is quoted from that experiment's own
declarations and findings files. It is a record of one test, not a recommendation of any kind.

This record predates the scripts in this skill. It ran its declared grid in the same pass as the
characterisation instead of gating first, and it charged a maker fee on winning exits where the
scripts charge fee plus half-spread on every fill (063 did not run that stricter model, so no number
is put on the difference). Today `declare.py` would hold the declarations, `effect.py` the raw effect
and the null, `sweep.py` the grid, `deflate.py` the trial count and `verdict.py` the findings.

## Contents

- The idea, and what was declared before any result was looked at
- Characterise: is there a raw effect?
- Controls: does either condition select anything?
- Realistic fills
- Development against out-of-sample
- The grid, counted honestly
- The verdict that was written, and what to take from it

## The idea

A discretionary-style rule, supplied as a hunch:

> Go long BTC in the 19:00 to 21:00 window when a 15-minute candle closes green and above the
> day's VWAP. Put the stop at the last swing low. Take profit at a fixed multiple of the risk.

It sounds reasonable. That is exactly the kind of idea the method is for.

## What was declared before any result was looked at

- **Instrument and data.** BTC USDT-margined perpetual, 1-minute bars from 2020-01 to
  2026-05, resampled to 15-minute bars aligned to UTC.
- **Signal.** A 15m candle whose open time is in [19:00, 21:00) UTC, green (close above open)
  and closing above the UTC-day anchored VWAP, computed causally. First qualifying candle of
  the day only. Skip the day if a prior trade is still open.
- **Entry.** Long, taker, at the open of the first 1-minute bar after the signal candle
  closes. The signal uses the close, so the trade starts after it.
- **Stop.** The low of a red 15m candle immediately followed by a green one, confirmed at the
  green candle's close, most recent one within 96 bars, strictly below entry, and at least
  0.1 ATR(14) away. No valid swing, no trade.
- **Target.** Entry plus RR times the risk, with RR in {1, 1.5, 2, 3, 5}.
- **Exit resolution.** First touch on 1-minute bars. Stop and target in the same 1-minute
  bar counts as a loss. The stop is filled at the close of the 1-minute bar that crossed it.
  Time cap 24 hours.
- **Costs.** A winning trade pays taker in at 4bp and maker out at 1.5bp, 5.5bp in total. A
  losing or timed-out trade pays 8bp. Cost in R is the basis points divided by the trade's
  risk in basis points.
- **Controls.** The same rule in every 2-hour window of the day (24 hourly-start windows),
  because the timezone of "19:00" was never specified. The VWAP condition dropped. The green
  condition dropped. Any candle. A random candle in the window with the same stop logic.
  Development 2020-01 to 2023-12 against out-of-sample 2024-01 to 2026-05.
- **Grid.** 5 RR values x 24 windows x 5 versions of the rule = 600 cells, declared for deflation, with
  Bonferroni on the 5 primary-window RR cells (t of at least 2.6).
- **Gate.** Net R above zero with t of at least 2 in both development and out-of-sample at
  the same RR, AND the cell beats the drop-VWAP control and the median of the other 23
  windows at that RR.

Note what this buys. The timezone question, which could have been "fixed" later by quietly
picking the best window, was turned into a declared control before the first run.

## Characterise: is there a raw effect?

The primary cell produced 1,394 trades. 13 days were skipped for having no valid swing.

| RR | Win rate | Break-even win rate | Gross R (t) |
|---|---|---|---|
| 1 | 51.4% | 50.0% | +0.006 (0.2) |
| 1.5 | 41.5% | 40.0% | +0.029 (0.9) |
| 2 | 34.4% | 33.3% | +0.035 (0.9) |
| 3 | 25.9% | 25.0% | +0.057 (1.2) |
| 5 | 16.9% | 16.7% | +0.107 (1.7) |

The break-even column is the driftless barrier probability, 1 / (1 + RR). The win rate sits
about one percentage point above it at every RR. The findings put it in one line: the entry
has no directional information. Gross is positive but never reaches a t of 2.

## Controls: does either condition select anything?

| Version of the rule, same window | n | Gross at RR 2 | Gross at RR 5 | Net at RR 2, 8bp |
|---|---|---|---|---|
| Green and above VWAP (primary) | 1,394 | +0.035 | +0.107 | -0.30 |
| Green only | 2,226 | +0.050 | +0.071 | -0.32 |
| Above VWAP only | 1,423 | +0.024 | +0.062 | -0.29 |
| Any candle | 2,193 | +0.028 | +0.000 | -0.36 |
| Random candle (null) | 2,068 | +0.007 | +0.059 | -0.39 |

Adding the VWAP condition to "green" changed gross by -0.015 to +0.036R. Adding "green" to
"VWAP" changed it by +0.01 to +0.05R. Both are within noise of the random-candle null.
Neither condition selects anything.

**The window.** 19:00 to 21:00 UTC ranked 4th of 24 by gross at RR 2 and 5th at RR 5. The
median of the other windows was +0.011 at RR 2 and +0.063 at RR 5. The strongest window in
the grid by t-statistic was a different one, and it was still net negative. Whatever timezone
19:00 was meant in, every window is in the same place.

## Realistic fills

Median risk, entry to swing low, was 33bp, or 0.89 ATR on the 15-minute bars. With a stop
that close, costs come to 0.24R per loss (8bp) and 0.17R per win (5.5bp, with a maker exit). The honest stop fill (the
close of the crossing 1-minute bar) averaged -1.06R, not -1.00R.

| RR | Net at 2bp (idealised) | Net at 7bp | Net at 8bp (declared) | Net at 10bp |
|---|---|---|---|---|
| 1 | -0.09 | -0.27 | -0.31 (t -9.8) | -0.47 |
| 1.5 | -0.07 | -0.25 | -0.30 (t -7.9) | -0.45 |
| 2 | -0.06 | -0.26 | -0.30 (t -7.1) | -0.44 |
| 3 | -0.04 | -0.24 | -0.29 (t -5.7) | -0.42 |
| 5 | +0.01 (t 0.2) | -0.20 | -0.25 (t -3.9) | -0.37 |

No gross figure in the study exceeds the cost. Even at a 2bp round trip the best primary cell
is +0.01R. This is the reason to report several cost levels: it shows the verdict does not
depend on which fee tier was assumed.

## Development against out-of-sample

Gross R by year:

| | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| RR 2 | +0.17 | -0.05 | +0.13 | +0.19 | -0.05 | -0.06 | -0.21 |
| RR 5 | +0.29 | +0.06 | +0.29 | +0.30 | -0.05 | -0.14 | -0.17 |

At RR 5, development (2020 to 2023) gross was +0.234 with a t of 2.8. Out-of-sample (2024 to
2026) was -0.104 with a t of -1.1. Someone who had stopped at the development segment, gross
of costs, would have had a result with a t of 2.8 to show. The declared gate asked for both
segments, net, and the rule fails it at every RR. Net is negative in every year at 8bp.

## The grid, counted honestly

600 cells were declared. 0 of 600 were net-positive. With no positive cell there is nothing
to deflate, so no Deflated Sharpe Ratio was needed. The count still did its job: the best
gross cell in the grid, t 3.4, has to be read as the best of 600, not as a single test.

## The verdict that was written

> NO-GO, 0/600 cells net-positive; the entry is a coin flip with a bull-era tilt and the
> swing-low stop makes the fee 17 to 24% of risk.

The three reasons recorded:

1. The entry is a coin flip: win rate equals the barrier probability plus about 1pp at every
   RR, and the controls are identical.
2. The gross tilt is 2020 to 2023 bull drift, and it reverses in 2024 to 2026. Long-only plus
   drift is market exposure, not a signal.
3. The swing-low stop is close (median 33bp, 0.89 ATR), so costs come to 0.24R per
   loss (8bp) and 0.17R per win (5.5bp). No gross in the study exceeds that.

Status: closed.

## What to take from it

- The idea was not foolish. It simply had nothing in it, and the test said so plainly.
- The declared controls did the work: the random-candle null, the two dropped conditions and
  the 24-window sweep each answered a question that would otherwise have become an excuse.
- The development segment alone, gross, looked like a result. The out-of-sample segment and
  the cost column are what made the answer honest.
- Cost in R, not in basis points, explained why: a tight stop made a small fee a quarter of
  every loss.
- The findings were written and the experiment closed. A NO-GO is a deliverable.
