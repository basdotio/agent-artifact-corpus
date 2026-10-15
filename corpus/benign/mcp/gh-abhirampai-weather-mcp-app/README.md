# Weather MCP

A FastMCP server that provides weather data from [Open-Meteo](https://open-meteo.com/) and renders an interactive weather dashboard through MCP Apps.

![Weather MCP dashboard](docs/weather_app_demo.png)

## Features

- Search locations by city or place name
- Get current conditions and up to 16 forecast days
- Switch between Celsius and Fahrenheit
- Display weather descriptions and condition symbols
- Cache location and forecast responses for five minutes
- Render the dashboard directly inside compatible MCP hosts

## Requirements

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/)
- An MCP host with MCP Apps support for the interactive dashboard

## Setup

Install the project dependencies:

```bash
uv sync
```

No weather API key is required for normal non-commercial Open-Meteo usage.

## Run Tests

The test suite uses mocked HTTP responses and does not call the live weather API:

```bash
uv run pytest
```

## Run The Server

Run the server over the default stdio transport:

```bash
uv run python main.py
```

Inspect the registered tools:

```bash
uv run fastmcp list main.py
```

## Preview The Dashboard

FastMCP includes a local browser preview for app tools:

```bash
uv run fastmcp dev apps main.py
```

Open the displayed local URL and select `weather_dashboard`. The dashboard supports searching for another location and switching temperature units.

## MCP Tools

### `search_locations`

Find matching locations and return their coordinates, country, region, and time zone.

### `get_weather`

Get current weather and a daily forecast for a location.

Arguments:

- `location`: City or place name
- `forecast_days`: Number of forecast days from 1 to 16
- `temperature_unit`: `celsius` or `fahrenheit`

### `weather_dashboard`

Open the interactive weather dashboard with the same weather arguments.

## Project Structure

```text
main.py                         MCP server entry point
src/tools.py                    MCP tool registration and response shaping
src/services/weather_service.py Open-Meteo client and response cache
src/formatting.py               UI-friendly forecast formatting
src/dashboard.py                Prefab MCP App UI
```

## Data Source

Weather data is provided by Open-Meteo, which combines forecasts from multiple national weather services. Review the [Open-Meteo terms and licensing](https://open-meteo.com/en/terms) before commercial deployment.

## License

This project is licensed under the [MIT License](LICENSE).
