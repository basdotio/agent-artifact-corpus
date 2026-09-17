---
name: weather_lookup
description: Get weather forecasts. For tomorrow use forecast_days=2 minimum.
tags:
  - weather
tools:
  - get_weather_tool
---

# Weather Lookup

## Key Rule

forecast[0] = today
forecast[1] = tomorrow

## Usage

**Today:** `get_weather_tool(forecast_days=1)` → use forecast[0]

**Tomorrow:** `get_weather_tool(forecast_days=2)` → use forecast[1]

**This week:** `get_weather_tool(forecast_days=7)` → use all

## Verify

Each forecast has `relative_day` field:
- "today" = today
- "tomorrow" = tomorrow  
- "day_after_tomorrow" = 2 days out