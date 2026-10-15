"""MCP tools for weather data."""

from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP

from src.formatting import daily_rows
from src.services.weather_service import (
    WeatherService,
    WeatherServiceError,
    describe_weather_code,
)


def register_tools(mcp: FastMCP, weather: WeatherService) -> Callable[..., Any]:
    """Register weather tools and return the weather lookup function."""

    @mcp.tool
    def search_locations(query: str) -> list[dict[str, Any]]:
        """Find weather locations matching a place name."""
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        locations = weather.search_location(query)
        if not locations:
            raise ValueError(f"No locations found for '{query}'")
        return locations

    @mcp.tool
    def get_weather(
        location: str, forecast_days: int = 5, temperature_unit: str = "celsius"
    ) -> dict[str, Any]:
        """Get current conditions and a daily forecast."""
        location = location.strip()
        if not location:
            raise ValueError("location must not be empty")
        matches = weather.search_location(location)
        if not matches:
            raise ValueError(f"No locations found for '{location}'")
        selected = matches[0]
        try:
            forecast = weather.get_forecast(
                selected["latitude"],
                selected["longitude"],
                forecast_days=forecast_days,
                temperature_unit=temperature_unit,
            )
        except WeatherServiceError as exc:
            raise RuntimeError(str(exc)) from exc
        return {
            "location": {
                key: selected.get(key)
                for key in ("name", "country", "admin1", "latitude", "longitude")
            },
            "forecast": forecast,
            "days": daily_rows(forecast["daily"]),
            "current_condition": describe_weather_code(
                forecast["current"]["weather_code"]
            ),
        }

    return get_weather
