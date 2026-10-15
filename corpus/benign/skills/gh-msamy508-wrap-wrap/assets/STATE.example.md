# STATE

Read this first. It is the current state of the work, not its history.
Updated: 2026-03-14
Commit: 4e1c9a2 on feature/parquet-export

## Current focus

Moving the invoice export from CSV to Parquet without breaking the nightly report.

## Last completed

- 2026-03-14: `export/parquet_writer.py` writes the same 41 columns as the CSV path. [verified]
- 2026-03-13: Agreed the report keeps reading CSV until Parquet has run clean for 7 nights. [verified]
- 2026-03-13: The staging bucket has room for 90 days of Parquet files. [unverified]

## Next action

Run `make nightly-dry` against yesterday's data and compare row counts with the CSV output.

## Open decisions

- Keep the CSV export after the switch? · default if nobody answers: keep it for 30 days.

## Do not re-derive

- The `amount` column is stored in cents, not currency units. The old docs are wrong.
- `pyarrow` 17 changed the default timestamp unit; we pin `coerce_timestamps="ms"`.

## Failed approaches

- Writing Parquet with `pandas.to_parquet` directly: loses the decimal precision of `amount`. Use the pyarrow schema in `export/schema.py`.

## Verification

- `pytest tests/` · 2026-03-14: 212 passed
- `make nightly-dry` · not run yet

## Waiting

- Uncommitted: `export/parquet_writer.py`, `tests/test_parquet_writer.py` (from the repo root)
- For the user: approve the extra storage bucket in the cloud console.
