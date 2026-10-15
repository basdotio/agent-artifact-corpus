"""Open-Meteo client used by the MCP tools and app."""

import time
from copy import deepcopy
from typing import Any

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CONDITIONS = {
    0: ("Clear sky", "sun", "☀"),
    1: ("Mainly clear", "sun", "☀"),
    2: ("Partly cloudy", "cloud-sun", "◐"),
    3: ("Overcast", "cloud", "☁"),
    45: ("Fog", "cloud-fog", "≋"),
    48: ("Depositing rime fog", "cloud-fog", "≋"),
    51: ("Light drizzle", "cloud-drizzle", "☂"),
    53: ("Drizzle", "cloud-drizzle", "☂"),
    55: ("Heavy drizzle", "cloud-drizzle", "☂"),
    56: ("Light freezing drizzle", "cloud-drizzle", "☂"),
    57: ("Heavy freezing drizzle", "cloud-drizzle", "☂"),
    61: ("Light rain", "cloud-rain", "☂"),
    63: ("Rain", "cloud-rain", "☂"),
    65: ("Heavy rain", "cloud-rain", "☂"),
    66: ("Light freezing rain", "cloud-rain", "☂"),
    67: ("Heavy freezing rain", "cloud-rain", "☂"),
    71: ("Light snow", "cloud-snow", "❄"),
    73: ("Snow", "cloud-snow", "❄"),
    75: ("Heavy snow", "cloud-snow", "❄"),
    77: ("Snow grains", "cloud-snow", "❄"),
    80: ("Light rain showers", "cloud-rain", "☂"),
    81: ("Rain showers", "cloud-rain", "☂"),
    82: ("Heavy rain showers", "cloud-rain", "☂"),
    85: ("Light snow showers", "cloud-snow", "❄"),
    86: ("Heavy snow showers", "cloud-snow", "❄"),
    95: ("Thunderstorm", "cloud-lightning", "⚡"),
    96: ("Thunderstorm with light hail", "cloud-lightning", "⚡"),
    99: ("Thunderstorm with heavy hail", "cloud-lightning", "⚡"),
}


def describe_weather_code(code: int) -> dict[str, str]:
    """Return a human-readable description and Lucide icon for a WMO code."""
    description, icon, symbol = WEATHER_CONDITIONS.get(
        code, ("Unknown conditions", "cloud", "☁")
    )
    return {"description": description, "icon": icon, "symbol": symbol}


class WeatherServiceError(RuntimeError):
    """Raised when Open-Meteo cannot provide a valid response."""


class WeatherService:
    def __init__(self, timeout: float = 10.0, cache_ttl: float = 300.0) -> None:
        self._client = httpx.Client(timeout=timeout)
        self._cache_ttl = cache_ttl
        self._location_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._forecast_cache: dict[
            tuple[float, float, int, str], tuple[float, dict[str, Any]]
        ] = {}

    def close(self) -> None:
        self._client.close()

    def search_location(self, query: str) -> list[dict[str, Any]]:
        cached = self._location_cache.get(query.casefold())
        if cached and not self._expired(cached[0]):
            return deepcopy(cached[1])
        response = self._request(
            GEOCODING_URL,
            {"name": query, "count": 5, "language": "en", "format": "json"},
        )
        locations = response.get("results", [])
        self._location_cache[query.casefold()] = (time.monotonic(), locations)
        return deepcopy(locations)

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        *,
        forecast_days: int = 5,
        temperature_unit: str = "celsius",
    ) -> dict[str, Any]:
        if not 1 <= forecast_days <= 16:
            raise ValueError("forecast_days must be between 1 and 16")
        if temperature_unit not in {"celsius", "fahrenheit"}:
            raise ValueError("temperature_unit must be celsius or fahrenheit")
        cache_key = (
            round(latitude, 4),
            round(longitude, 4),
            forecast_days,
            temperature_unit,
        )
        cached = self._forecast_cache.get(cache_key)
        if cached and not self._expired(cached[0]):
            return deepcopy(cached[1])
        forecast = self._request(
            FORECAST_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
                "forecast_days": forecast_days,
                "temperature_unit": temperature_unit,
                "timezone": "auto",
            },
        )
        self._forecast_cache[cache_key] = (time.monotonic(), forecast)
        return deepcopy(forecast)

    def _expired(self, created_at: float) -> bool:
        return time.monotonic() - created_at >= self._cache_ttl

    def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WeatherServiceError("Unable to retrieve weather data") from exc
        if not isinstance(payload, dict):
            raise WeatherServiceError("Weather service returned an invalid response")
        return payload
