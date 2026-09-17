---
name: scrape-routing
description: Route docs scraping tasks through the dedicated scraper subagent and shared scraper helpers.
---

## What I do

- Route `/scrape_docs` work to the `scraper` subagent.
- Ensure scraping tasks use the dedicated scraping model and helper-first implementation style.
- Keep command behavior aligned with `scripts/scrapes/scrape_docs.sh.ts` dispatch conventions.

## Required routing

1. Use the `scraper` subagent for docs scraping implementation and refresh tasks.
2. Keep scripts in `scripts/scrapes/` and shared logic in `scripts/helpers/`.
3. Run the target scraper command after edits and report pages/ok/failed.

## Return checklist

- Scraper script path(s) added or updated
- Helper path(s) added or updated
- Exact command used for validation run
- Capture totals and notable failures
