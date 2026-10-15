# Contributing

Thanks for helping. Keep changes small and sourced.

## Detection patterns (`scripts/scan.py`)
1. Add or adjust the regex.
2. Add a case to `tests/fixtures/bad` that triggers it and, where relevant, a case to `tests/fixtures/good` that must not.
3. Run `python -m unittest discover -s tests`.

## Law references (`references/`)
- Link a primary source (statute, Gazette, regulator page or court judgment).
- Mark each line V (verified from the source) or K (known but not re-verified).
- State the date you checked.
- Do not copy long passages from third-party articles.

## Style
- Plain English. No legal advice wording. Keep the disclaimer.
- Python standard library only.
