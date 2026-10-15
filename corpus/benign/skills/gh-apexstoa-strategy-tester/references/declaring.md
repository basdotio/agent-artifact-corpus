# Declaring, freezing and amending

Read this when the user questions or changes a `[default]` line, when `declare.py check` complains,
or when anything must change after the freeze.

In `EXP/declarations.json`, `idea` and `costs` are the user's and start as `null`, `data` is
pre-filled by `declare.py init` from the price file, and `method` holds the defaults. Fill keys with
`declare.py set --exp EXP key=value ...` (a value is JSON, or plain text) or with a file edit.

## Idea and cost keys

| Key | What goes in it | Needed |
|---|---|---|
| `idea.hypothesis` | What happens and in which direction, in the user's words | yes |
| `idea.reason` | Why it might happen. Leave `null` if they gave none; do not invent one | no |
| `idea.instrument`, `idea.venue` | What they would trade and where | yes |
| `idea.side` | `long` or `short`; `both` only for the rule and file kinds | yes |
| `idea.event` (clock) | `local_time` as `HH:MM`, `zone` as an IANA name, `days` as `"weekdays"`, `"all"` or a list of weekday numbers with Monday = 0; `skip_dates_file` optional | first three |
| `idea.event` (rule, file) | `rule_file`, or `events_file` | yes |
| `idea.trade.hold_minutes` | Minutes from entry to the time exit; a whole number of bars | yes |
| `idea.trade.stop_bp`, `target_bp` | Distance from the entry price in basis points, only if the user named one | no |
| `idea.params` | Named numbers the user's rule reads | no |
| `idea.grid` | Lists of values under `trade.hold_minutes`, `trade.stop_bp`, `trade.target_bp` or `params.<name>`. The base value of a gridded key must be in its own list. The event time cannot be gridded | no |
| `idea.prior_looks.text` | What they have already seen of this idea on this data, in a sentence | yes |
| `idea.prior_looks.variants_seen` | How many other versions they have looked at; 0 when this exact idea is the only one | yes |
| `costs.fee_bp_per_fill`, `costs.half_spread_bp_per_fill`, `costs.source` | Their figures. `source` begins with `measured` or `assumed`, then says where each came from | yes |

None of these is ever defaulted or supplied by you: not a fee, not a spread, not a weekday. If an
answer is missing, ask that one question again. With no grid from the user there is one cell.
`declare.py check` names one problem per line: a `null` key names the round-one question to ask
again, and a misfit (a hold that is not a whole number of bars, a clock time off a bar boundary, a
segment too short) is put to the user. Do not round or move a value yourself.

## Method defaults and the reason for each

| Key | Default | Reason |
|---|---|---|
| `split.dev_fraction` | 0.6667, chronological (`split.date_utc` overrides it with a date) | Out-of-sample must be later than every choice |
| `null.pool` | `same-day-other-times` for clock ideas, `same-year-any-time` for rule and file ideas | The null must keep everything except the thing the idea claims matters |
| `null.draws`, `null.seed` | 1000, 1 | Smallest reachable p is 1/1001; a fixed seed makes the run repeatable |
| `null.alpha` | 0.05 | One-sided, in the declared direction |
| `gates.dsr_min` | 0.95 | The published DSR convention; same level as the null |
| `gates.oos_psr_min` | 0.95 | One pre-specified confirmatory test at the same level |
| `gates.min_event_days` | 100 | A convention, not a derived number: below it only very large effects are detectable |
| `gates.max_dropped_event_share` | 0.02 | Dropped events are not random; beyond a few percent the sample is not the declared one |
| `cost_tiers` | 0.5, 1, 2 | Shows whether the verdict depends on the cost assumed |
| `replay_probes` | 200 | Finds a fault present on 1.5% of bars with 95% probability |
| `next_if_go`, `next_if_no_go` | Paper trading before capital; write the findings and close | The next step is fixed before the result can argue for another |

Before the freeze the user may change any of these; a changed line is rendered `[changed from
default: <default>]`. Limits: alpha at most 0.10, both confidence gates at least 0.90, at least 30
event days, and a clock idea keeps the `same-day-other-times` pool. A gate weaker than its default
is named on the verdict line. The rules under `## Fixed rules` are not settings.

## How N is counted

`cells declared` is the product of the grid's value counts, and 1 with no grid. The trial count is
`N = cells declared + variants already seen + amend penalty`: three holds and two stops are six
cells, and with four earlier versions looked at N is ten. N never shrinks.
Under `## Trial count` the rendered file prints `luckiest of N unskilled cells` and `development t
needed for DSR 0.95 at this N`, the least the chosen cell must clear: about 1.65 for N = 1, 2.21
for 2, 2.95 for 6 and 3.17 for 9. Point the user at both when they propose a grid. Every extra
cell raises the bar, and cells that differ in kind (a very short hold, a tight stop) raise it
further, because the spread of the cells' Sharpes sets the benchmark: a grid whose cells come out
far apart can leave a strong, real effect INCONCLUSIVE where the base trade declared alone would
have passed. The grid to declare is the one they would really trade; its values, and whether to
have one at all, are theirs to pick before the freeze. The grid is run only if the base trade
passes the characterisation gate, and its cells count in N either way.

## Freeze

`declare.py freeze` writes `declarations.lock`: a hash and a copy of the declarations, the size and
hash of the data file and of any rule, events or skip-dates file, the split time, the cell list and
N. Later scripts compare against it and refuse on a mismatch; the out-of-sample look is recorded in
it too. This is tamper-evident, not tamper-proof: deleting the lock and `results/` starts again
unnoticed. For stronger proof of the date, commit the folder or publish the hash before the first run.

## Amend

After the freeze, edit `declarations.json`, then run `declare.py amend --exp EXP --reason "TEXT"`. It:
- moves `results/` to `results_superseded_<k>/` (kept, not deleted) and records the reason;
- recomputes N. Added grid values count as cells. If the event, the side, a cost figure or an input
  file changed, every cell frozen before was a different trial already looked at: all are added to
  N. If the data changed (the file's bytes, the first or last date, the split, how columns or
  stamps are read), every cell already run is run again on another sample: those are added to N,
  the whole grid once `sweep.py` has run, even with another amend in between. Any other amend that
  adds no cell adds 1, as does a data repair before any cell was run;
- refuses a gate made weaker than the frozen one, a locked cell missing from the grid, a lower
  `variants_seen`, and anything once out-of-sample was opened. To add a value, keep the old cells.

Then run every step again from the data check. Each amend is printed under Deviations and counted
on the verdict line. An edit to `rule.py`, the events file, the skip-dates file or the data file
after the freeze needs an amend too: the scripts refuse (exit code 3) until then. A new idea that
came out of the results is not an amend: it is a new experiment with its own folder and
declarations, tested on data the old experiment did not use to suggest it.
