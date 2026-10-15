# Artifact checklist

Read this before writing the prose of a GO, or when any line starts `SUSPICIOUS:`.

Seven ways a test shows a result that is not there. Give each one a state in the "Artifact checks
done by hand" section of `FINDINGS.md`: PASS, FAIL or NOT RUN, with one line of evidence. NOT RUN
never counts as a pass, and a GO with a NOT RUN line says so beside the verdict. When a result is
surprisingly good, suspect the test before crediting the idea.

| # | Artifact | Checked by |
|---|---|---|
| 1 | Intrabar sequencing on coarse bars | by hand |
| 2 | Ties in the hit rate | script: `tie_rate` and `hit_rate` in `results/effect_dev.json` |
| 3 | Same-timestamp joins in the user's own code | by hand |
| 4 | Survivorship | by hand |
| 5 | Suspicious cleanliness | script: `flags` in `results/effect_dev.json`, `SUSPICIOUS:` lines; then three trades by hand |
| 6 | Degenerate shuffles | script: `DEGENERATE NULL`, `null.days_excluded` and `null.null_sd_bp` in `results/effect_dev.json` |
| 7 | Best cell against random entries | script: `grid_null` in `results/sweep.json` |

The generated block of `FINDINGS.md` ends with its own table, "Artifact checks done by the
scripts", holding the script-checked states. Do not edit it; quote from it for rows 2, 5, 6 and 7.

## 1. Intrabar sequencing on coarse bars (by hand)

A bar gives open, high, low and close, not the order they happened in. When a stop and a target
both lie inside one bar, nothing in the bar says which was reached first. The scripts count that
bar as a loss, so they cannot manufacture a win, but a large share of such bars means the bars
are too coarse for the declared distances and the result leans on the tie rule.

Check: in `results/trades_c<i>_dev.csv` for the chosen cell, count the rows with `exit_reason`
`tie` and the rows that left on the entry bar itself (`stop` or `target` with `exit_ts` one bar
after `entry_ts`). Report both as a share of all trades. PASS when both are small enough that
resolving them the other way could not change the sign of the net mean; otherwise FAIL, and the
user needs finer bars in a new declaration.

## 2. Ties in the hit rate (script)

At short holds many returns are exactly zero. The known bug is to subtract the mean first and drop
zeros second: no value is zero any more, nothing is dropped, and the block of non-events is counted
as hits for one side. `effect.py` drops exact zeros from the raw gross returns and prints the tie
rate beside the hit rate. PASS when both are reported. A hit rate from the user's own code needs
the same order checked by hand.

## 3. Same-timestamp joins in the user's own code (by hand)

An event and the price update it caused can carry the same timestamp. Read with `<=`, the "state
before" is already the state after. This applies to events supplied as a file and to any series
the user built outside the scripts. The usual tell is a hit rate near 70 to 75% on a short hold.
Check: ask how each event time was produced and whether every comparison between an input and
the thing it predicts is strict `<`, on the venue's timestamps and not on arrival times. NOT RUN
when the user cannot say.

## 4. Survivorship (by hand)

Testing only what exists today leaves out what was delisted, mostly after falling. That flatters a
long test. It runs the other way for a short test, whose largest paper gains are in the missing
names, and that is not a margin to lean on, since many of those could not have been sold short at
the time. Check: ask where the instrument came from and why this one. An instrument chosen because
of how it moved over the test period is a selection on the outcome. State the direction of the
bias for the declared side. With one instrument the user had already settled on, PASS with that
sentence.

## 5. Suspicious cleanliness (script flags, then by hand)

Markets are noisy; a result with no noise in it is usually a statement about the code or the data.
The scripts flag a t beyond 20, a hit rate above 0.90 on 50 or more trades, a round-trip cost of
zero and a Sharpe above 1. Also treat as suspect: a statistic that is exactly zero or identical
across cells that should differ, perfect symmetry between the two sides, no losing year.

Check, owed on any flag and before any GO: reproduce three trades from the raw rows. Take the
first, the last and the largest absolute `gross_bp` from the chosen cell's trades file. For each,
find the entry and exit bars in the user's price file by timestamp, and work out gross, cost and
net with a calculator. PASS when all three match the file. Typical causes of a mismatch are a
stale price that never moves, duplicated rows, and a wrong column mapping.

## 6. Degenerate shuffles (script)

A null says something only if its draws differ from the real series in the one thing under test
and still vary among themselves. `effect.py` stops with `DEGENERATE NULL` when the draws have no
spread or when more than a twentieth of the days have no alternative window. PASS when the null
ran, `days_excluded` is small and `null_sd_bp` is above zero; quote both.

## 7. Best cell against random entries (script)

Any search over a grid returns a best cell, on real data or on noise. The best real cell means
something only if it beats the best cell the same search finds on random entries. `sweep.py`
does this as the grid null. PASS when its p is at or below alpha; FAIL when above. With a single
cell there is no search and nothing to compare: write NOT RUN, one cell.
