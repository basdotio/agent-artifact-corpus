---
name: apm-goods-query
description: Search and query 27K+ goods from APM Zoom Korean fashion e-commerce platform via REST API
command: apm-goods-query
metadata:
  openclaw:
    requires:
      bins:
        - curl
    primaryEnv: APM_REFRESH_TOKEN
  version: 0.4.0
  author: APM AI Team
  license: MIT
  tags:
    - e-commerce
    - fashion
    - korea
    - goods-search
    - api
---

# APM Zoom Goods Query

Search and query **27,000+ Korean fashion goods** from the APM Zoom e-commerce platform.

No dependencies required — just call the REST API at `https://skiil.apmzoom.ai`.

## Quick Start

Search goods:
```bash
curl -s "https://skiil.apmzoom.ai/api/goods?q=T恤&limit=5" | jq
```

Get goods detail:
```bash
curl -s "https://skiil.apmzoom.ai/api/goods/165177320329" | jq
```

List categories:
```bash
curl -s "https://skiil.apmzoom.ai/api/categories" | jq
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/goods?q=keyword&page=1&limit=20` | Search/list goods |
| GET | `/api/goods/:id` | Get goods detail by ID |
| GET | `/api/categories` | List all categories |
| GET | `/api/health` | Health check |

Base URL: `https://skiil.apmzoom.ai`

## Goods Search Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | `""` | Search keyword (e.g. "T恤", "夹克") |
| `page` | int | `1` | Page number |
| `limit` | int | `20` | Items per page (max 200) |
| `is_sell` | int | `-1` | Filter: 1=selling, 0=pending, -1=all |
| `goods_id` | int | — | Filter by specific goods ID |

## Response Format

### Goods List
```json
{
  "total": 27166,
  "page": 1,
  "limit": 3,
  "data": [
    {
      "goods_id": 165177320329,
      "goods_name": "东大门爆款上衣T恤",
      "goods_class_name": "T恤",
      "sale_price": 23000,
      "stock_count": 100,
      "store_name": "APM Store",
      "goods_thumb_img": "https://...",
      "goods_big_img": "https://...",
      "is_sell": 1
    }
  ]
}
```

### Categories
```json
[
  {
    "goods_class_id": 1,
    "goods_class_name": "女装",
    "ls_child": [...]
  }
]
```

## Use Cases

- **Product research**: Search Korean fashion goods by keyword, category, price
- **Inventory check**: Query stock levels and selling status
- **Market analysis**: Browse 27K+ goods across 5 major categories
- **Data integration**: Feed goods data into your application or workflow

## Installation

See [README.md](../README.md) for installation options:
- ClawHub: `clawhub install apm-goods-query`
- Claude Code: Copy to `~/.claude/skills/`
- MCP Server: See `install/mcp/`
- Direct API: No installation needed

## More

- [API Reference](reference.md) — Detailed endpoint documentation
- [Examples](examples.md) — Usage examples and recipes
