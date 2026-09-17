# Kalshi Market Data — OpenClaw Skill

## Overview

OpenClaw plugin that fetches live prediction market data from Kalshi.com
using the public REST API. No external dependencies — Python stdlib only.

## Exposed Functions

### `browse(url, max_markets)`

List markets from a Kalshi category or home page.

**Parameters:**
- `url` (str) — Kalshi page URL. Default: `https://kalshi.com`
- `max_markets` (int) — Max results. Default: `20`

**Returns:** List of `{"title": str, "url": str}`.

### `market(url)`

Fetch data for a single Kalshi market/event.

**Parameters:**
- `url` (str) — Full market URL or event ticker.

**Returns:**
```json
{
  "title": "...",
  "outcomes": [{"label": "Yes", "price_cents": 47, "raw": "47%"}],
  "status": "ok",
  "error": null
}
```

## Categories

- `https://kalshi.com`
- `https://kalshi.com/category/politics`
- `https://kalshi.com/category/economics`
- `https://kalshi.com/category/crypto`
- `https://kalshi.com/category/climate`
- `https://kalshi.com/category/culture`
- `https://kalshi.com/category/companies`
- `https://kalshi.com/category/financials`
- `https://kalshi.com/category/mentions`
- `https://kalshi.com/category/science`
- `https://kalshi.com/sports/all-sports`
