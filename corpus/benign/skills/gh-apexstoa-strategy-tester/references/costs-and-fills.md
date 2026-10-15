# Costs and fills

Read this when the user asks about fees, spread, stops or targets, or has no cost figures.

## The cost model

```
cost per fill = fee + half the quoted spread          (basis points of the traded value)
round trip    = 2 x (fee + half-spread)               charged on every trade, win or lose
cost in R     = round trip / stop distance            (both in basis points)
```

The mid price is not tradable: a market buy pays the ask, which is the mid plus half the spread,
and then the fee. Cost in R matters because a close stop turns a small fee into a large share of
each trade. Arithmetic only, not suggested values: a fee of 5 and a half-spread of 1 make 6 per
fill and 12 per round trip, which is 0.24 R against a 50 bp stop and 0.40 R against a 30 bp stop.
The calculator prints the same lines for the user's own figures:

```
python3 <skill>/scripts/fills.py --fee-bp F --half-spread-bp H [--stop-bp S] [--gross-bp G]
```

## Where the two figures come from

Both are the user's and both are required before the freeze. Entries are market orders, so the fee
is the taker fee of the user's own tier on the declared venue's published schedule. The half-spread
is half of `(ask - bid) / mid` in basis points, measured by the user from quotes at the hours the
trade happens; the median is the usual figure.

`costs.source` begins with `measured` when the figures come from the user's own quotes, statements
or fee schedule. With no quote data the user states a figure and the source begins with `assumed`;
the verdict line then says the half-spread was assumed, not measured, and the break-even cost is the
figure to lead with, because it does not depend on the assumption. `declare.py check` accepts no
other first word, and you never supply a cost figure yourself: if the user gave none, ask.

## Tiers and break-even

`effect.py` prints the net mean at each declared multiple of the cost. If the sign of the net
mean changes between tiers, say so plainly: the result is then a bet on execution quality.

The break-even cost is the gross mean per trade: the round-trip cost at which the net mean is
zero. It is always printed, and it is the honest answer to "would a cheaper venue fix it": the
user can compare it with any venue's cost themselves.

## Fill rules, exactly as the scripts apply them

- The entry price is the open of the entry bar.
- The time exit is the open of the bar whose open time is the entry time plus the hold, found by
  timestamp. If that bar does not exist the trade is dropped and counted; nothing is filled forward.
- With a stop or a target, each bar from the entry bar up to, not including, the exit bar is
  checked. For a long trade the first match on a bar wins:
  1. not the entry bar, and the open is at or below the stop: exit at the open (`stop_gap`);
  2. the low is at or below the stop and the high is above the target: exit at the lower of the
     stop and the close (`tie`). A tie is a loss;
  3. the low is at or below the stop: exit at the lower of the stop and the close (`stop`). A stop
     never fills better than its level;
  4. the high is strictly above the target: exit at the target (`target`). A resting order needs
     the price to trade through it; a touch is not a fill.
  A short trade is the mirror image. Bars missing inside the check are skipped. Otherwise the exit
  reason is `time`.
- One position at a time: an event that arrives before the previous trade has exited is skipped
  and counted. A stop, target or tie exit frees the position at the end of its bar.
- `effect.py` ignores the declared stop and target and uses the time exit alone, because it
  measures the raw effect. `sweep.py` applies them.

For intuition on stops and targets: a price with no directional information reaches a target RR
times as far away as the stop first with probability `1 / (1 + RR)`. The random-entry null with
the same exits measures that same thing, with costs and drift included.

## What is not modelled

Funding payments, borrow and roll costs, the price impact of size, limit or passive entries, maker
fees, trailing stops, partial exits, several legs and position sizing. If the idea depends on one
of them, say so and stop. If it only touches one (a hold that crosses a funding settlement, say),
name it under "What this does not show".
