---
name: strategy-tester
license: MIT
description: Tests a person's own trading idea on their own price data and returns a numeric GO, NO-GO or INCONCLUSIVE verdict. Use whenever someone has a market hunch or a rule and wants to know whether it is real ("I think X happens after Y, can you check", "does this edge hold up", "backtest my idea", "is my backtest overfit", "is this Sharpe real"), or asks for a pre-registered test, a random-entry null, a cost check, or a Probabilistic or Deflated Sharpe Ratio, even if they only want a quick backtest or a single number. Bundled standard-library Python scripts check the data, measure the raw effect against random entries, charge fees and spread, run the declared grid, deflate the best cell and write the findings. Do not use it to invent a strategy or signal, to choose what to trade, to give trade calls, to build a live bot or to define a term. It supplies the method and never the idea.
---

# Verify a trading idea

Tests the user's own trading idea on their own price data and ends in a number and a verdict: GO,
NO-GO or INCONCLUSIVE. The user brings the idea, the price file and the costs; this skill brings the
method and its scripts.

- Never suggest, fill in or guess an instrument, direction, signal, time, hold, parameter value, fee
  or spread, not even as an example. A missing one stays `null` and is asked for again.
- A NO-GO is a finished result: no rescue variant and no list of things to vary.
- GO means "survived the declared tests". It is not advice.

## Running the scripts

The scripts are in `scripts/` beside this file (`<skill>` is this folder); the experiment folder EXP is
the user's: create it inside their current working folder, never beside the data file. Run each as `python3 <skill>/scripts/NAME.py --exp EXP` (`python` if
`python3` is missing), one plain command at a time: no cd, no shell variables, no heredocs.
Python 3.9 or later, nothing to install.

Do not read the scripts into context. Never write or run code of your own that reads the price file
or redoes a script's arithmetic: a mean, hit rate, t, Sharpe or chart of the user's prices is a
result, and every figure the user sees is copied from a script's output after the freeze. Each
script ends with `RESULT:` and `NEXT:` lines. Exit codes:
- 0: step done. 1: step done and a declared gate failed, which is a result. Either way follow `NEXT:`.
- 2: bad or missing input. Fix what the `ERROR:` and `TRY:` lines name, run again.
- 3: refused. Do what the message says; never work around a 3.

If the idea needs what the scripts cannot express (several instruments, limit entries, trailing
stops, sizing, a grid over the event time), say so and stop. Do not write a substitute backtest. Of
several event times the user picks one; another is a new experiment, counting the cells already run
in `variants_seen`, on out-of-sample data no experiment has opened.

## Start in two rounds

**Round one.** One message, at most four open questions, leaving out any already answered. Offer no
example values and no readings of an unclear answer.
1. The event or signal, exactly. If it has a clock time: which clock, which time zone, which days.
2. The instrument, the venue they would really trade it on, their fee and half-spread per fill
   there, and where the price file is.
3. The trade in their own words: direction, when in, when out.
4. Whether they have already looked at this on this data, and roughly how many other versions.

**Round two.** With their answers:
1. `declare.py init --exp EXP --kind clock|rule|file --data PATH`: a time of day, a condition on
   past bars, or the user's own event list.
2. Fill only the `null` keys, in the user's most literal words, with `declare.py set --exp EXP
   key=value ...` or your file-edit tool, never a helper script. One cell; grid values only if the
   user named them; `method` untouched. What the user has not said stays `null`: do not infer it.
3. Fee and half-spread are the user's figures, never yours. `costs.source` begins with `measured`
   (their own quotes, statements or fee schedule) or `assumed` (their figure, nothing measured).
4. `rule.py` (rule ideas) is ordinary Python that the scripts run on the user's machine, first at
   `declare.py check`. Show them the file before that.
5. `declare.py check`. If it lists a `null` key, ask for exactly those and stop: no draft exists
   yet. Otherwise `declare.py show`, and reply with its output word for word in one code block:
   every line, each `[default]` tag (a method default they may change now), all of Fixed rules. A
   summary is not the draft. Then ask: accept, or change any line.

A default set before any data is seen cannot be fitted to a result: the method is defaulted, the idea
never. A reply approves only the draft that was shown; an earlier "go ahead" is not acceptance. After
any change, check and show again. Then `declare.py freeze`. No return or result exists before it.

## Checklist

Copy it and tick each step as it finishes. Quote labelled lines as printed.
- [ ] 1. Declare and freeze -> `EXP/declarations.lock`.
- [ ] 2. `checkdata.py` -> `results/data_check.json`. On `DATA CHECK: FAIL` show the defects and stop.
- [ ] 3. `events.py` -> `results/events_dev.csv`. Quote the `event in UTC:` line. On a replay failure
      fix the rule, not the test, then `declare.py amend`.
- [ ] 4. `effect.py` -> quote the `CHARACTERISATION GATE:` line. On FAIL do not sweep: run step 8
      now, in the same turn, without asking. A cell that was not run has no result: say so.
- [ ] 5. `sweep.py` -> `results/grid.csv`, every declared cell.
- [ ] 6. `deflate.py` -> the Deflated Sharpe Ratio at the declared N.
- [ ] 7. `sweep.py --exp EXP --oos` -> the one out-of-sample look; unopened if development fell short.
- [ ] 8. `verdict.py` -> `EXP/FINDINGS.md`. Read `references/reading-results.md`, write the three
      prose sections, do not edit the generated block, then `verdict.py --exp EXP --check`.
- [ ] 9. Paste from `FINDINGS.md` word for word, in this order: the In plain words lines, the
      `**Verdict:**` line with its qualifiers, the Gates table. Then all cells, each `WARNING:`
      beside the figure it weakens, and the limits.

Say GO, NO-GO or INCONCLUSIVE only once `verdict.py` has printed it. Lost your place: `declare.py status`.

## Read a reference only when its condition is met

| When | Read |
|---|---|
| The user questions or changes a `[default]` line, `declare.py check` complains, or anything must change after the freeze | `references/declaring.md` |
| The idea is tied to a clock time or a session open or close | `references/clock-events.md` |
| The idea is a rule on past bars (writing `rule.py`), the user brings their own events, or the replay fails | `references/rule-and-causality.md` |
| The user asks about fees, spread, stops or targets, or has no cost figures | `references/costs-and-fills.md` |
| Before writing the prose sections or explaining the output of `effect.py`, `sweep.py` or `verdict.py` | `references/reading-results.md` |
| The user asks how PSR or DSR is computed, or a `deflate.py` line needs explaining | `references/deflation.md` |
| Before writing the prose of a GO, or when any line starts `SUSPICIOUS:` | `references/artifact-checklist.md` |
| A script exits 2, or you need a file's columns or keys | `references/formats.md` |
| The user asks what a full test looks like in practice (never during a live test) | `references/worked-example-no-go.md` |

## When asked to cut a corner

| They say | Do | Why |
|---|---|---|
| "Skip the declarations, just run it" | Draft from what they said: method lines take defaults, a missing idea or cost key is asked for in that message and stays `null` | The scripts refuse without the lock |
| "Just the average", "a quick look, not a backtest" | The same: draft, their yes, freeze, then `effect.py` prints that average | An average seen before the freeze is a look at the data, out-of-sample included |
| "Only show me the best cell" | The chosen cell with its rank, N and DSR, beside the full table from `FINDINGS.md` | The best of N was picked for looking good |
| "Use a different parameter now", "drop that year", "try one more" | Edit `declarations.json`, then `declare.py amend --exp EXP --reason "..."`: N goes up and the findings print the deviation. Refused once out-of-sample is open: that is a new experiment on new data | A choice made after a result is a fit |
| "Look at out-of-sample again", "use the newer data to pick" | Not possible: it is read once, for the chosen cell | It is the only data no choice has touched |
| "I already know it works" | Record it under prior looks, with the count of versions | Prior looks raise N; they skip no step |
| "Just give me the Sharpe" | One line with n, N, PSR and DSR, per observation. Before the sweep: the net Sharpe line of `effect.py`; N and DSR do not exist yet | A Sharpe without its trial count is not a result |
| "It failed, what should I try?", "give me a signal" | Write the NO-GO. A new idea must be theirs | The skill supplies method, never ideas |

## Gotchas

- Sharpe is per observation everywhere, never annualised.
- A US clock time is two different UTC times across the year.
- The day is the unit: sixty one-minute returns inside one hour are one observation.
- A missing bar is listed and its event dropped, never filled.
- A market fact from your memory (a funding time, a session hour) is unverified: say so.
- If the price file is too large to upload, ask for the coarsest bars the trade needs.
