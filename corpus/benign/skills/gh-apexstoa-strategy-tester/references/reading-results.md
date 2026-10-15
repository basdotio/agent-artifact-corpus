# Reading the results

Read this before explaining the output of `effect.py`, `sweep.py` or `verdict.py`.

All returns are in basis points. Mean, deviation, t and Sharpe are taken over event-days: the sum
of the trades entered on one UTC day is one observation. A p-value from draws is
`(b + 1) / (m + 1)`, with b the draws at least as good as the real figure out of m, so it is never
zero. The null p a gate uses is the larger of that and a p adjusted for the event window's own
spread (`p_adjusted`), so a volatile event hour cannot pass by its volatility alone.

## The labelled lines

| Line | What it means | What to do |
|---|---|---|
| `DATA CHECK: PASS` or `FAIL (<n> problems)` | FAIL is a defect that would corrupt a result: unreadable rows, times out of order, conflicting duplicates, impossible bars, wrong bar size. Warnings (gaps, flat bars, outliers) are listed and nothing is altered | On FAIL show the list and stop. On PASS pass on the warnings |
| `event in UTC:` | The clock event's UTC time in summer and in winter | Tell the user |
| `causality:` | `by construction` (clock), `checked: 0 differences in <K> probes` (rule), `not verified` (file) or `FAIL` | Quote it; on FAIL fix the rule |
| `CHARACTERISATION GATE: PASS` or `FAIL (<reason>)` | Passes when the net mean at the declared cost is above zero and the random-entry null p is at or below the declared alpha | On FAIL go to `verdict.py` |
| `DEGENERATE NULL` | The null could not be built: its draws have no spread, or too many days have no alternative window. Usual causes are a hold close to a day long, or flat prices | Exit code 2. Tell the user the idea cannot be tested as declared; do not switch the pool |
| `SUSPICIOUS:` | A t beyond 20, a hit rate above 0.90 on 50 or more trades, a zero cost, or a Sharpe above 1 | The verdict is capped at INCONCLUSIVE. Reproduce three trades by hand; a clean result then needs a fresh declaration |
| `WARNING:` | Something that weakens a figure without failing it | Repeat it beside the figure it weakens, not in a list at the end |
| `Deflated Sharpe Ratio <d> (PASS at ...)` or `(not a pass at ...)` | The chosen cell against the luckiest of N | Quote with N |
| `VERDICT:` and `RESULT:` of `verdict.py` | The verdict, then the whole verdict line: deciding sentence, qualifiers and row | Paste the `RESULT:` text as printed; it is the `**Verdict:**` line of `FINDINGS.md` |

## The effect table

- **Gross** mean, median and t show the raw effect with the time exit only. The hit rate drops
  exact zeros from the raw returns first; the tie rate beside it says how many were dropped.
- **Net at three tiers** and the **break-even cost** show whether the verdict depends on the cost.
  The cost gate is one round trip because a raw effect smaller than that cannot be made positive
  on average by any arrangement of exits. A break-even below zero means a loss before any cost.
- **Net Sharpe per event day** with PSR(0) is one cell's figure. Quote that line when a Sharpe is
  asked for before the sweep; do not divide a t by a square root yourself. `sweep.py --oos` prints
  the out-of-sample gross mean and break-even cost in the same way.
- **Null**: `statistic` is the real figure, `null mean` what random entries earned, `excess` the
  difference and `z` the excess in null deviations. A positive null mean is drift: a long idea in
  a rising market earns it at random times too. Only the excess belongs to the event.
- Quote the null p as printed (`null p`, the larger of the two). When `p_adjusted` is the larger,
  the event window is more volatile than the times it was compared with: say that in one sentence.
- Lead with the `IN PLAIN WORDS:` lines. They name which finding a NO-GO is: lost before costs, no
  effect at all, or a real effect smaller than the cost. Do not reword them into something milder.
- The `same-year-any-time` pool lets random entries overlap each other and the real trades.
- **By year** rows are for diagnosis. Do not propose dropping a year.

## The grid

`sweep.py` runs every declared cell and prints how many are net-positive out of the cells declared.
The chosen cell is the one with the highest development net Sharpe among cells with enough event
days; a tie goes to the earlier cell. When reading `results/grid.csv`, look at the neighbours of
the chosen cell. A plateau, where neighbours agree, is reassuring. A single bright cell among dull
ones is the signature of noise. Say which it is in the "Why" section. The grid null compares the
best real cell with the best cell found on random entries. When `sweep.py` exits 1 on the grid null
its `NEXT:` still names `deflate.py`: the verdict needs the chosen cell's deflation.

The out-of-sample look runs the chosen cell once. It passes when the net mean is above zero, PSR
against zero meets the declared level and the null p meets alpha.

## The verdict rule in words

`verdict.py` computes nothing new. It refuses (exit code 3) if a result does not belong to the frozen
declarations and asks for a missing step (exit code 2). Then the first line that applies decides:

| What the results show | Verdict |
|---|---|
| Fewer development event days than the declared minimum | INCONCLUSIVE |
| Development net mean at or below zero: the raw effect does not cover the round-trip cost | NO-GO |
| The event did no better than random entries (excess at or below zero) | NO-GO |
| Excess positive but the null p above alpha | INCONCLUSIVE |
| The chosen cell is not net positive | NO-GO |
| The chosen cell's Sharpe is at or below what the luckiest of N unskilled cells would show, and the grid null does not put it above random entries | NO-GO |
| DSR below the declared level | INCONCLUSIVE |
| The best cell is no better than the best cell on random entries | NO-GO |
| Better than that, but the grid null p above alpha | INCONCLUSIVE |
| Fewer out-of-sample event days than the minimum | INCONCLUSIVE |
| Out-of-sample net mean or excess at or below zero: it did not hold on the unseen segment | NO-GO |
| Out-of-sample on the right side but PSR or null p short | INCONCLUSIVE |
| Any `SUSPICIOUS:` flag still standing | INCONCLUSIVE |
| None of the above | GO |

The pattern: an estimate on the wrong side with enough days is NO-GO; every estimate on the right
side with only a significance gate short is INCONCLUSIVE. When the first four lines decide, the
grid, deflation and out-of-sample sections read `not run`, and out-of-sample stays unopened.

- **INCONCLUSIVE** is not "nearly GO". Its line carries the event days that would be needed and
  `history in this file`, the days that exist. If the need exceeds what the history can supply,
  say so. More days means a new experiment on new data, not a rerun. The days figure takes the
  observed excess as real: an idea with nothing in it lands here about half the time when costs
  are close to zero, so a null p far above alpha is no reason to collect more data.
- **NO-GO** is reported as it stands, with the deciding number. Do not soften it.
- **GO** means the idea survived the declared tests; the next step is the declared one.
- Qualifiers on the verdict line (supplied events not verified, earlier variants in N, deviations
  after the freeze, half-spread assumed, gates weaker than the defaults) are part of the verdict.
  Repeat them, and after a NO-GO offer nothing: no cheaper venue, no other hold, no paper trading.
- Not run by the scripts: removing each condition of a rule in turn ("A and B" against A alone and
  B alone). Each reduced rule would be its own experiment; mention it only if asked what else exists.
