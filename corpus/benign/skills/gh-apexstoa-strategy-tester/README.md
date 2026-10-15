# strategy-tester

A Claude Skill that tests **your own** trading idea on **your own** price data and ends with a
numeric verdict: **GO**, **NO-GO** or **INCONCLUSIVE**.

You bring the idea and a price file. The skill brings the method: it writes the test down before
any result exists, runs it with small scripts, and reports what the numbers say, whichever way
they come out.

It contains no signals, no strategies and no trade calls. It never suggests what to trade.

## Install

Claude Code, for every project:

```
git clone https://github.com/apexstoa/strategy-tester ~/.claude/skills/strategy-tester
```

Or for one project only, clone into that project's `.claude/skills/` folder instead.

Requirements: Python 3.9 or later. Nothing else to install; the scripts use the standard library
only.

## Use

Start Claude Code and describe an idea in a sentence:

```
I think BTC tends to rise in the last hour before the US stock market closes. Help me test it.
```

1. **Four questions.** The exact event, the instrument and your costs, the trade in your own
   words, and whether you have already looked at it.
2. **A full draft to accept.** Claude writes the complete test plan and shows it to you. Lines it
   filled with a method default are marked `[default]`; you can change any of them. Your idea is
   never defaulted: no instrument, direction, time or parameter is suggested.
3. **Freeze, then run.** Once you accept, the plan is locked by a hash and the scripts run in
   order. Nothing is computed on your prices before that.

## What it does

| Step | Command | What it settles |
|---|---|---|
| Declare and freeze | `declare.py` | The idea, costs, grid and pass marks, fixed before any result |
| Check the data | `checkdata.py` | Gaps, duplicates, broken bars, missing event bars |
| Build the events | `events.py` | Local clock time to UTC per date, daylight saving included; a replay test for rule-based ideas |
| Measure the raw effect | `effect.py` | The effect before and after costs, against the same trade at random times |
| Run the declared grid | `sweep.py` | Every declared cell, all reported; one look at held-back data |
| Deflate | `deflate.py` | Probabilistic and Deflated Sharpe Ratio at the declared number of trials |
| Write the verdict | `verdict.py` | A decision table applied mechanically, and `FINDINGS.md` |

The scripts refuse to run out of order, refuse a cell that was not declared, and refuse a second
look at the held-back data. A change after the freeze is recorded and raises the number of trials
the result has to clear.

## What a verdict looks like

A real run, on three years of one-minute BTCUSDT perpetual bars:

> **In plain words**
> - No effect shows up before costs: the average was -2.33 bp per event day over 522 days, which
>   cannot be told apart from zero (t -0.92). Even the optimistic end of the estimate (+1.83 bp)
>   is below the 11 bp it costs to trade.
> - The average was at or below zero before any cost, so no level of cost makes it pay on this
>   sample.
> - This experiment is closed. To test a different version, start a new experiment folder and
>   count this one under 'variants already seen', so the next result is held to a higher bar.
>
> **Verdict:** NO-GO: development net mean -13.33 bp per event day: the raw effect -2.33 bp per
> trade does not cover the round-trip cost 11 bp.

Most honest tests end this way. A NO-GO with its reasons is a finished, useful result.

## How the verdict is reached

- **The day is the unit of evidence.** Statistics are taken over event days, and Sharpe is never
  annualised.
- **Costs on every fill.** Fee plus half-spread, entry and exit, at half, one and two times your
  figure. The break-even cost is always printed.
- **A random-entry baseline.** For a time-of-day idea, the same trade at other times on the same
  days. The p-value allows for an event hour that is more volatile than the rest of the day.
- **Deflation.** The best of several cells is biased upward by being chosen. The Deflated Sharpe
  Ratio (Bailey and Lopez de Prado) is computed at the number of cells you declared, and that
  number can only grow.
- **One look at held-back data.** The last third of the file is read once, for the chosen cell,
  and only after the first two thirds passed.
- **Too good is a flag, not a pass.** A result stronger than real markets normally give is
  reported as INCONCLUSIVE until it has been checked by hand.

Formulas, with a case worked by hand, are in `references/deflation.md`. A complete worked example
that ended NO-GO is in `references/worked-example-no-go.md`.

## What was measured about the skill itself

- On 1,050 synthetic datasets with no edge in them, the full pipeline returned GO **0 times** at
  the default pass marks.
- On synthetic data with a planted edge of twice the trading cost, one declared cell reached GO in
  55 of 60 runs. A larger grid reaches GO less often and returns INCONCLUSIVE instead; declaring
  fewer cells keeps more power.
- The Probabilistic and Deflated Sharpe figures reproduce the values printed in the original
  papers.

These are tests on synthetic data. They show the method does not manufacture results; they say
nothing about any market.

## Scope

One instrument, entry at the next bar's open, a fixed holding time with an optional fixed stop and
target, one position at a time. Three kinds of idea: a time of day, a rule on past bars that you
write in a small `rule.py`, or your own list of event times.

Not modelled: limit entries, trailing stops, position sizing, several instruments at once, funding
payments, and slippage beyond the half-spread. The skill says so in every result and refuses to
improvise them.

A `rule.py` is ordinary Python that runs on your machine. Read it before you run it.

## Your data

Any CSV with a header and one row per bar, oldest first: a timestamp plus open, high, low and
close. Epoch seconds or milliseconds and ISO times are all read. Your prices never leave your
machine: the scripts make no network calls.

## Tests

```
python3 scripts/run_tests.py
```

Ten test files, including the published PSR and DSR values and a full pipeline run on synthetic
data.

## Not advice

This is a research method. A GO means an idea survived the tests that were declared for it, on
past data, at the costs you stated. It is not a recommendation to trade and not a promise about
the future. Trading leveraged instruments can lose more than you deposit.

## Licence

MIT. See `LICENSE`.

Published by [Apexstoa](https://apexstoa.com).
