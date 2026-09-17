---
name: weather-finder
description: Get current weather and forecasts for a location. Use when the user asks about weather, temperature, precipitation, wind, alerts, or forecasts for a city, address, or coordinates.
---

# Weather Finder

## Purpose
Provide reliable **current conditions** and **forecast** for a user-specified location, with units and time zone handled correctly.

## When to use
Use this skill when the user asks for:
- weather “now”, “today”, “tomorrow”, “this weekend”, “next week”
- temperature highs/lows, feels-like, humidity
- precipitation chance/amount, snow, radar-like summaries
- wind speed/gusts/direction
- severe weather alerts
- comparisons between locations

## Requirements / clarifying questions
Ask the minimum needed to disambiguate:
1. **Location**: city + region/country (e.g., “Paris, FR” vs “Paris, TX”), or ZIP/postal code, or lat/long.
2. **Timeframe**: current, hourly (next N hours), daily (next N days), specific date.
3. **Units**: use user preference if stated; otherwise infer from locale (US → °F/mph, most others → °C/km/h). Offer both if unsure.

If the user requests “weather” without timeframe, default to:
- current conditions
- today’s high/low
- next 24h precip chances (brief)

## Data source approach
Preferred: use a public weather API that does not require an API key for basic usage.
Recommended: **Open-Meteo** (https://open-meteo.com/) plus a geocoding step.

### Steps
1. **Geocode** the user location to coordinates and a canonical place name.
   - Use Open-Meteo Geocoding API:
     - `https://geocoding-api.open-meteo.com/v1/search?name={QUERY}&count=5&language=en&format=json`
   - If multiple plausible matches, present 2–5 options and ask the user to choose.

2. **Fetch weather** for the chosen coordinates.
   - Forecast endpoint (supports current + hourly + daily):
     - `https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m&hourly=temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,weather_code&timezone=auto`
   - Add unit parameters when needed:
     - `temperature_unit=fahrenheit`
     - `wind_speed_unit=mph`
     - `precipitation_unit=inch`

3. **Interpret weather codes** into human-readable conditions.
   - Use Open-Meteo WMO weather code table (link in response if needed).
   - Provide short text labels (e.g., “Light rain”, “Overcast”, “Snow showers”).

4. **Compose answer**
   - Start with the resolved location + local time.
   - Provide:
     - Current: temp, feels-like, condition, wind.
     - Today: high/low + precip chance/amount.
     - Short forecast: next 6–12h or next 3 days depending on request.
   - Include important caveats (e.g., uncertainty, rapidly changing conditions).

5. **Alerts (optional)**
   - If user asks for warnings/alerts, use Open-Meteo’s weather alerts endpoint where available, or direct them to the official meteorological service for their region.

## Output format (default)
- **Location** (resolved)
- **Now**: condition, temperature (and feels-like), wind
- **Today**: high/low, precipitation chance
- **Next**: brief hourly or daily bullets
- **Source**: “Open-Meteo”

## Tooling notes for this agent environment
- Use the `fetch_url` tool to call the geocoding and forecast URLs.
- If the environment has no internet, ask the user for their local forecast details or provide general guidance instead.

## Example
User: “What’s the weather in Berlin tomorrow?”
Assistant:
1) Geocode Berlin → choose Berlin, DE.
2) Fetch forecast with timezone=auto, daily for tomorrow.
3) Respond with tomorrow high/low, precip probability, wind, condition summary.
