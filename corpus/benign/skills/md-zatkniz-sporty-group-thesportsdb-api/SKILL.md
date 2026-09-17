---
name: thesportsdb-api
description: Access TheSportsDB API for sports data including teams, players, leagues, schedules, livescores, and events. Use when users need sports-related information.
---

# TheSportsDB API

Access comprehensive sports data from TheSportsDB API covering teams, players, leagues, events, and livescores.

## Project Context

**This project primarily uses these V1 API endpoints:**
1. **All Leagues**: `/all_leagues.php` - Lists all available leagues
2. **Badge Lookup**: `/search_all_seasons.php?badge=1&id=<id>` - Gets league badges and seasons

API Key: `3` (free tier)

## When to Use

**DO USE** when:
- Need sports team information (details, logos, equipment)
- Looking up players and their stats
- Fetching league data and standings
- Getting match schedules (past, present, future)
- Searching for sports events
- Accessing livescores (Premium only)
- Retrieving event highlights (YouTube links)
- TV broadcast schedules

**DO NOT USE** when:
- Non-sports related data needed
- Real-time betting odds (not provided)
- Proprietary sports data

## API Versions

### V1 API (Used in this project)
- Simple authentication (API key in URL)
- Supports: Search, Lookup, List, Schedule, Video
- Free key: `3` (project default) or `123`
- Easy to test in browser
- **This is the version we use**

### V2 API (Not used in this project)
- Modern REST API
- Header-based authentication (`X-API-KEY`)
- More verbose and logical naming
- Includes livescores
- Premium only - not needed for current requirements

## Authentication

### V1 (URL-based) - PROJECT STANDARD
```
Development: https://www.thesportsdb.com/api/v1/json/3/{endpoint}
Alternative: https://www.thesportsdb.com/api/v1/json/123/{endpoint}
Premium: https://www.thesportsdb.com/api/v1/json/YOUR_API_KEY/{endpoint}
```

### V2 (Not used in this project)
```
Base URL: https://www.thesportsdb.com/api/v2/json
Header: X-API-KEY: YOUR_API_KEY
```

## Rate Limits

- **Free**: 30 requests/minute
- **Premium**: 100 requests/minute
- **Business**: 120 requests/minute
- HTTP 429 on limit breach

## Common Use Cases

### PRIMARY ENDPOINTS (PROJECT-SPECIFIC)

**Get All Leagues**
```typescript
// Returns all available leagues across all sports
GET https://www.thesportsdb.com/api/v1/json/3/all_leagues.php

Response:
{
  "leagues": [
    {
      "idLeague": "4328",
      "strLeague": "English Premier League",
      "strSport": "Soccer",
      "strLeagueAlternate": "Premier League"
    },
    // ... more leagues
  ]
}
```

**Get League Badge and Seasons**
```typescript
// Returns all seasons for a league with badge URL
GET https://www.thesportsdb.com/api/v1/json/3/search_all_seasons.php?badge=1&id=4328

Response:
{
  "seasons": [
    {
      "strSeason": "2023-2024",
      "strBadge": "https://www.thesportsdb.com/images/media/league/badge/..."
    },
    {
      "strSeason": "2022-2023",
      "strBadge": "https://www.thesportsdb.com/images/media/league/badge/..."
    },
    // ... more seasons
  ]
}

// Note: The badge parameter is required (badge=1) to include badge URL
// Without badge=1, you only get season names without badge images
```

### ADDITIONAL V1 ENDPOINTS

### Search Operations

**Search Teams**
```typescript
// V1
const teams = await $fetch('https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=Arsenal')

// V2 (Premium)
const teams = await $fetch('https://www.thesportsdb.com/api/v2/json/search/team/manchester_united', {
  headers: { 'X-API-KEY': runtimeConfig.theSportsDbApiKey }
})
```

**Search Players**
```typescript
const players = await $fetch('https://www.thesportsdb.com/api/v1/json/123/searchplayers.php?p=Danny_Welbeck')
```

**Search Events**
```typescript
const events = await $fetch('https://www.thesportsdb.com/api/v1/json/123/searchevents.php?e=Arsenal_vs_Chelsea')
const seasonEvents = await $fetch('https://www.thesportsdb.com/api/v1/json/123/searchevents.php?e=Arsenal_vs_Chelsea&s=2016-2017')
const dayEvents = await $fetch('https://www.thesportsdb.com/api/v1/json/123/searchevents.php?d=2015-04-26')
```

### Lookup by ID

**Lookup League**
```typescript
const league = await $fetch('https://www.thesportsdb.com/api/v1/json/123/lookupleague.php?id=4328')
```

**Lookup Team**
```typescript
const team = await $fetch('https://www.thesportsdb.com/api/v1/json/123/lookupteam.php?id=133604')
```

**Lookup Player**
```typescript
const player = await $fetch('https://www.thesportsdb.com/api/v1/json/123/lookupplayer.php?id=34145937')
```

**League Standings**
```typescript
// Soccer leagues only
const table = await $fetch('https://www.thesportsdb.com/api/v1/json/123/lookuptable.php?l=4328&s=2023-2024')
```

### List Operations

**All Sports**
```typescript
const sports = await $fetch('https://www.thesportsdb.com/api/v1/json/123/all_sports.php')
```

**All Leagues**
```typescript
const leagues = await $fetch('https://www.thesportsdb.com/api/v1/json/123/all_leagues.php')
```

**Teams in League**
```typescript
const teams = await $fetch('https://www.thesportsdb.com/api/v1/json/123/search_all_teams.php?l=English_Premier_League')
```

**Players in Team**
```typescript
const players = await $fetch('https://www.thesportsdb.com/api/v1/json/123/lookup_all_players.php?id=133604')
```

### Schedule Operations

**Next Events (Team)**
```typescript
const upcoming = await $fetch('https://www.thesportsdb.com/api/v1/json/123/eventsnext.php?id=133602')
```

**Previous Events (Team)**
```typescript
const past = await $fetch('https://www.thesportsdb.com/api/v1/json/123/eventslast.php?id=133602')
```

**Events by Date**
```typescript
const events = await $fetch('https://www.thesportsdb.com/api/v1/json/123/eventsday.php?d=2024-01-15&s=Soccer')
```

**Events by Season**
```typescript
const events = await $fetch('https://www.thesportsdb.com/api/v1/json/123/eventsseason.php?id=4328&s=2023-2024')
```

**TV Schedule**
```typescript
const tvEvents = await $fetch('https://www.thesportsdb.com/api/v1/json/123/eventstv.php?d=2024-07-07')
```

### Video & Highlights

**Event Highlights**
```typescript
const highlights = await $fetch('https://www.thesportsdb.com/api/v1/json/123/eventshighlights.php?d=2024-07-07&s=motorsport')
```

### Livescores (Premium V2 Only)

```typescript
const config = useRuntimeConfig()
const livescores = await $fetch('https://www.thesportsdb.com/api/v2/json/livescore/soccer', {
  headers: { 'X-API-KEY': config.theSportsDbApiKey }
})
```

## Images

All entities return image URLs. Images support size variants:

```typescript
// Original (720px)
https://r2.thesportsdb.com/images/media/league/fanart/xpwsrw1421853005.jpg

// Medium (500px)
https://r2.thesportsdb.com/images/media/league/fanart/xpwsrw1421853005.jpg/medium

// Small (250px)
https://r2.thesportsdb.com/images/media/league/fanart/xpwsrw1421853005.jpg/small

// Tiny (50px)
https://r2.thesportsdb.com/images/media/league/fanart/xpwsrw1421853005.jpg/tiny
```

Image types:
- **Fanart**: JPEG backgrounds
- **Badges/Logos**: Transparent PNG
- **Player photos**: JPEG
- **Equipment**: PNG kits/jerseys

## Popular League IDs

- English Premier League: `4328`
- La Liga: `4335`
- Serie A: `4332`
- Bundesliga: `4331`
- Ligue 1: `4334`
- UEFA Champions League: `4480`
- NBA: `4387`
- NFL: `4391`
- MLB: `4424`
- Formula 1: `4370`

## Error Handling

- **429**: Rate limit exceeded (wait 1 minute)
- **404**: Resource not found
- **401**: Invalid API key (V2)
- Empty arrays: No results found

## Best Practices

1. **Cache Results**: League/team data rarely changes
2. **Use IDs**: Lookups by ID are faster than searches
3. **Batch Requests**: Get season data once, not per event
4. **Free Key Limits**: Only 2 search results with free key
5. **Image Optimization**: Use size variants for performance
6. **Rate Limits**: Implement retry logic with backoff

## Common Patterns

### Get All Leagues and Display with Badges
```typescript
// 1. Fetch all leagues
const leagues = await $fetch('/api/leagues/all')

// 2. For each league, fetch badge and seasons
for (const league of leagues.leagues) {
  const badgeData = await $fetch(`/api/leagues/badges/${league.idLeague}`)
  const badge = badgeData.seasons[0]?.strBadge
  // Display league with badge
}
```

### Get League with Latest Season Badge
```typescript
const leagueId = '4328'
const { seasons } = await $fetch(`/api/leagues/badges/${leagueId}`)
const latestSeason = seasons[0] // Most recent season
const badge = latestSeason.strBadge
const seasonName = latestSeason.strSeason
```

### Filter Leagues by Sport
```typescript
const { leagues } = await $fetch('/api/leagues/all')
const soccerLeagues = leagues.filter(l => l.strSport === 'Soccer')
const basketballLeagues = leagues.filter(l => l.strSport === 'Basketball')
```

## Documentation Resources

- Official Docs: https://www.thesportsdb.com/documentation
- Readme.io (interactive): https://thedatadb.readme.io/