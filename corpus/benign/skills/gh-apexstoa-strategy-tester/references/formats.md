# Files, columns, keys and exit codes

Read this when a script exits 2, or when you need a file's columns or keys.

## Exit codes and messages

0 done; 1 done and a declared gate failed; 2 bad or missing input; 3 refused. `verdict.py` exits 0
whenever it writes a verdict. An error is three lines on stderr: `ERROR:`, `EXPECTED:`, `TRY:`.
`--json` on any script prints the result as JSON instead of text; `--help` lists its arguments.

## The user's files

- **Price bars**: a CSV with a header, one row per bar, oldest first. Any column names; the `data`
  block of `declarations.json` maps them.
- **Events file** (file kind): header `decision_ts` or `decision_ts,side`; `side` is `long`,
  `short`, `1` or `-1`; times in the same unit as the bars.
- **Skip dates** (clock kind, optional): one `YYYY-MM-DD` per line, the local date.

## The `data` block of `declarations.json`

| Key | Meaning |
|---|---|
| `path` | Absolute path of the price file |
| `columns` | Header names for `ts`, `open`, `high`, `low`, `close` and, if present, `volume` |
| `ts_unit` | `s`, `ms`, `us`, `ns` or `iso` |
| `ts_zone` | Zone of ISO times that carry no offset. `init` cannot know it: ask the user |
| `stamp` | `open` (a bar is stamped with its open time) or `close` |
| `bar_seconds` | Bar size in seconds |
| `first_utc`, `last_utc` | Optional inclusive bounds on the bars used: epoch seconds or `YYYY-MM-DD` |

`declare.py init` fills these from the header and the first 200 rows. Check them against what the
user said about the file. Common exit-2 causes and what to do:

- a mapped column is not in the header: correct `data.columns`;
- rows are newest-first: the user sorts the file ascending by time and gives the new path;
- ISO times without an offset and no `ts_zone`: ask which zone the file is in;
- the data file has moved: correct `data.path` (before the freeze) or put the file back (after);
- `costs.source` must begin with `measured` or `assumed`: ask the user which it is.

## The experiment folder

| File | Written by |
|---|---|
| `declarations.json` | `declare.py init`, then you (`declare.py set --exp EXP key=value ...`, or a file edit) |
| `STEP0_DECLARATIONS.md` | `declare.py show`, `freeze`, `amend` |
| `declarations.lock` | `declare.py freeze`, `amend` |
| `rule.py` | `declare.py init --kind rule`, then you with the user |
| `results/data_check.json`, `results/missing_bars.csv` | `checkdata.py` |
| `results/events_dev.csv`, `results/events.json` | `events.py` |
| `results/effect_dev.json`, `results/trades_raw_dev.csv` | `effect.py` |
| `results/grid.csv`, `results/grid_daily.csv`, `results/trades_c<i>_dev.csv`, `results/sweep.json` | `sweep.py` |
| `results/deflate.json` | `deflate.py --exp` |
| `results/events_oos.csv`, `results/trades_c<i>_oos.csv`, `results/oos.json` | `sweep.py --oos` |
| `results/verdict.json`, `FINDINGS.md` | `verdict.py` |
| `results_superseded_<k>/` | `declare.py amend` (earlier results, kept) |

Edit only `declarations.json`, `rule.py` and the prose sections of `FINDINGS.md` (`## Why`,
`## Artifact checks done by hand`, `## What this does not show`). Everything between
`<!-- generated:start -->` and `<!-- generated:end -->` belongs to `verdict.py`.

## Columns

- `events_*.csv`: `pset,segment,day,decision_ts,entry_ts,side` (`side` is 1 or -1).
- `trades_*.csv`: `cell,day,side,entry_ts,entry_px,exit_ts,exit_px,exit_reason,gross_bp,cost_bp,net_bp`.
  `exit_reason` is `time`, `stop`, `stop_gap`, `target` or `tie`; `cell` is `raw` in the raw file.
- `grid.csv`: `cell,pset,hold_minutes,stop_bp,target_bp,params,trades,event_days,gross_mean_bp,net_mean_bp,net_sd_bp,sharpe,t,ties,primary,chosen,flag`.
- `grid_daily.csv`: `day,c0,c1,...`, net basis points, blank where a cell has no trade that day.
- `missing_bars.csv`: `gap_start_utc,gap_end_utc,bars_missing`.

Timestamps are integer UTC epoch seconds, days are the entry's UTC date, returns are basis points.

## Keys

Every result JSON starts with `script`, `decl_sha256`, `created_utc`, `exit_code`.

| File | Keys you may need |
|---|---|
| `declarations.lock` | `decl_sha256`, `frozen_utc`, `data` (`bytes`, `sha256`, `first_utc`, `last_utc`), `split_utc`, `cells` (each `index`, `pset`, `hold_minutes`, `stop_bp`, `target_bp`, `params`), `primary_cell`, `cells_declared`, `variants_seen`, `amend_penalty`, `N`, `history`, `inputs` (path and hash of `rule.py`, the events file, the skip-dates file), `oos_opened_utc` (set by the one out-of-sample look), `cells_run_on_this_data` (frozen cells with results at the last amend, counted if the data changes), `frozen_declarations` (the declarations as frozen) |
| `data_check.json` | `rows`, `first_utc`, `last_utc`, `bar_seconds`, `missing_bars`, `largest_gap_bars`, `duplicates_identical`, `duplicates_conflicting`, `out_of_order`, `ohlc_violations`, `tie_rate`, `outliers`, `rows_by_year`, `fails`, `warns`, `result` |
| `events.json` | `kind`, `events`, `events_by_year`, `dropped_missing_entry`, `dropped_straddles_split`, `skipped_gap_in_lookback`, `dropped_share`, `causality`, `replay`, `by_pset`, `utc_time_summer`, `utc_time_winter`, `days_by_utc_time`, `zone_rule` |
| `effect_dev.json` | `events`, `trades`, `event_days`, `enough_days`, `gross`, `net` (`mean_bp`, `sd_bp`, `sharpe`, `t`, `psr0` at the declared cost), `hit_rate`, `tie_rate`, `cost_round_trip_bp`, `break_even_cost_bp`, `net_by_tier`, `by_year`, `null` (`pool`, `statistic_bp`, `null_mean_bp`, `null_sd_bp`, `excess_bp`, `z`, `p`, `days_excluded`), `placebo`, `flags`, `gate` |
| `sweep.json` | `cells_declared`, `cells_run`, `net_positive_cells`, `chosen_cell`, `grid_null` |
| `deflate.json` | `n`, `sharpe`, `t`, `skew`, `kurt`, `psr0`, `N`, `std_trials_used`, `emax_used`, `sr0`, `dsr`, `pass`, `days_needed`, `no_days_enough`, `days_needed_floor`, `warnings`, `flags` |
| `oos.json` | `cell`, `opened_utc`, `event_days`, `gross_mean_bp`, `break_even_cost_bp`, `net_mean_bp`, `sharpe`, `psr0`, `null`, `gate` |
| `verdict.json` | `verdict`, `row`, `deciding`, `qualifiers`, `gates`, `days_needed`, `history_event_days` |
