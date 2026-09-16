---
name: wp-search
description: Search bleikoya.net for content like bylaws (vedtekter), meeting notes (referater), rules, and documentation. Use when you need information from the website to inform development decisions.
---

# WordPress Content Search

Search the bleikoya.net production site for content and documentation.

## API Endpoint

Base URL: `https://bleikoya.net/wp-json/bleikoya/v1/search`

## Quick Examples

**Get dugnad rules:**
```bash
curl -s "https://bleikoya.net/wp-json/bleikoya/v1/search?type=category&category=dugnad" | jq '.category.documentation'
```

**Get vedtekter (bylaws):**
```bash
curl -s "https://bleikoya.net/wp-json/bleikoya/v1/search?type=category&category=vedtekter" | jq '.category.documentation'
```

**Search all content (posts, pages, and events):**
```bash
curl -s "https://bleikoya.net/wp-json/bleikoya/v1/search?q=gebyr" | jq '.'
```

**Search upcoming events:**
```bash
curl -s "https://bleikoya.net/wp-json/bleikoya/v1/search?type=events" | jq '.events[] | {title, start_date}'
```

**Search events by keyword:**
```bash
curl -s "https://bleikoya.net/wp-json/bleikoya/v1/search?type=events&q=dugnad" | jq '.'
```

**Search events in a date range (historical):**
```bash
curl -s "https://bleikoya.net/wp-json/bleikoya/v1/search?type=events&after=2024-01-01&before=2024-12-31" | jq '.events[] | {title, start_date}'
```

## Authentication (for private content)

Many posts (meeting minutes, board documents, innkallinger) are private. To include them, authenticate using credentials from `.env`:

```bash
export $(grep "^PRODUCTION_" .env | xargs)
curl -s -u "$PRODUCTION_USER:$PRODUCTION_APPLICATION_PASSWORD" "https://bleikoya.net/wp-json/bleikoya/v1/search?q=referat" | jq '.'
```

**Always authenticate** when searching for meeting minutes (referater), board documents, or other internal content. The `meta.includes_private` field in the response confirms whether private posts are included — if it's `false`, you need to authenticate.

## API Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query |
| `type` | string | `all`, `posts`, `categories`, `category`, or `events` |
| `category` | string | Category slug (when type=category) |
| `limit` | int | Max results (default 10, max 50) |
| `after` | string | Events ending after this date, Y-m-d (default: today for type=events) |
| `before` | string | Events starting before this date, Y-m-d |

## Key Categories

| Slug | Description |
|------|-------------|
| `dugnad` | Volunteer work rules (6t dugnad + 2t strandrydding) |
| `vedtekter` | Bylaws and regulations |
| `styret` | Board information |
| `generalforsamling` | Annual meeting documentation |
| `avfall` | Waste and recycling rules |
| `brannsikring` | Fire safety |

## Instructions

1. **Always authenticate** by loading credentials from `.env` before making requests:
   ```bash
   export $(grep "^PRODUCTION_" .env | xargs)
   ```
   Then add `-u "$PRODUCTION_USER:$PRODUCTION_APPLICATION_PASSWORD"` to all curl commands.
2. Start by searching for the relevant category if looking for rules
3. Use `type=category&category=<slug>` for full documentation
4. Use `q=<keyword>` to search across all content (posts, pages, and events)
5. Use `type=events` for dedicated event search with date filtering
6. Use `type=events&after=YYYY-01-01&before=YYYY-12-31` for historical events
7. Parse the JSON response and summarize relevant findings
8. Verify `meta.includes_private` is `true` — if not, authentication failed

## Response Format

**General search (`type=all`):**
```json
{
  "categories": [
    {
      "id": 56,
      "name": "Dugnad og Strandrydding",
      "slug": "dugnad",
      "documentation": "Full text content..."
    }
  ],
  "posts": [
    {
      "id": 123,
      "title": "Post title",
      "type": "post",
      "status": "publish",
      "excerpt": "...matched text...",
      "url": "https://...",
      "date": "2025-05-25 12:00:00"
    },
    {
      "id": 456,
      "title": "Generalforsamling",
      "type": "tribe_events",
      "status": "publish",
      "url": "https://...",
      "date": "2025-04-07 19:29:32",
      "start_date": "2025-05-25 12:00:00",
      "end_date": "2025-05-25 15:00:00",
      "venue": "Velhuset",
      "all_day": false
    }
  ],
  "meta": {
    "authenticated": false,
    "includes_private": false
  }
}
```

**Event search (`type=events`):**
```json
{
  "events": [
    {
      "id": 456,
      "title": "Generalforsamling",
      "type": "tribe_events",
      "status": "publish",
      "url": "https://...",
      "date": "2025-04-07 19:29:32",
      "start_date": "2025-05-25 12:00:00",
      "end_date": "2025-05-25 15:00:00",
      "venue": "Velhuset",
      "all_day": false
    }
  ],
  "meta": {
    "authenticated": false,
    "includes_private": false
  }
}
```
