from typing import Any

import httpx
import pytest
from fastmcp import FastMCP

from src.dashboard import build_dashboard
from src.services.weather_service import (
    WeatherService,
    WeatherServiceError,
    describe_weather_code,
)
from src.tools import register_tools


def _service(handler: Any) -> WeatherService:
    service = WeatherService()
    service.close()
    service._client = httpx.Client(transport=httpx.MockTransport(handler))
    return service


def _forecast_payload() -> dict[str, Any]:
    return {
        "timezone": "Asia/Kolkata",
        "current": {
            "weather_code": 1,
            "temperature_2m": 33.5,
            "apparent_temperature": 40.1,
            "relative_humidity_2m": 61,
            "wind_speed_10m": 2.8,
        },
        "daily": {
            "time": ["2026-08-19"],
            "weather_code": [61],
            "temperature_2m_max": [33.5],
            "temperature_2m_min": [26.8],
            "precipitation_probability_max": [61],
            "sunrise": ["2026-08-19T06:00"],
            "sunset": ["2026-08-19T18:30"],
        },
    }


def test_weather_code_has_description_and_symbol() -> None:
    assert describe_weather_code(0) == {
        "description": "Clear sky",
        "icon": "sun",
        "symbol": "☀",
    }
    assert describe_weather_code(999)["description"] == "Unknown conditions"


def test_location_search_is_cached() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path == "/v1/search"
        return httpx.Response(
            200,
            json={"results": [{"name": "Delhi", "latitude": 28.6, "longitude": 77.2}]},
        )

    service = _service(handler)
    assert service.search_location("Delhi")[0]["name"] == "Delhi"
    assert service.search_location("delhi")[0]["name"] == "Delhi"
    assert calls == 1


def test_forecast_cache_is_separate_per_unit() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/forecast"
        calls.append(request.url.params["temperature_unit"])
        return httpx.Response(200, json=_forecast_payload())

    service = _service(handler)
    kwargs = {"forecast_days": 1}
    service.get_forecast(28.6, 77.2, temperature_unit="celsius", **kwargs)
    service.get_forecast(28.6, 77.2, temperature_unit="fahrenheit", **kwargs)
    service.get_forecast(28.6, 77.2, temperature_unit="celsius", **kwargs)

    assert calls == ["celsius", "fahrenheit"]


@pytest.mark.parametrize(
    ("forecast_days", "temperature_unit"),
    [(0, "celsius"), (17, "celsius"), (1, "kelvin")],
)
def test_forecast_rejects_invalid_options(
    forecast_days: int, temperature_unit: str
) -> None:
    service = WeatherService()
    with pytest.raises(ValueError):
        service.get_forecast(
            28.6,
            77.2,
            forecast_days=forecast_days,
            temperature_unit=temperature_unit,
        )
    service.close()


def test_service_errors_are_normalized() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    service = _service(handler)
    with pytest.raises(WeatherServiceError, match="Unable to retrieve weather data"):
        service.search_location("Delhi")


def test_get_weather_shapes_conditions_and_daily_rows() -> None:
    class FakeWeather:
        def search_location(self, _: str) -> list[dict[str, Any]]:
            return [{"name": "Delhi", "country": "India", "latitude": 28.6, "longitude": 77.2}]

        def get_forecast(self, *_: Any, **__: Any) -> dict[str, Any]:
            return _forecast_payload()

    get_weather = register_tools(FastMCP("test"), FakeWeather())
    result = get_weather("Delhi", 1, "celsius")

    assert result["location"]["country"] == "India"
    assert result["current_condition"]["description"] == "Mainly clear"
    assert result["days"][0]["description"] == "Light rain"
    assert result["days"][0]["symbol"] == "☂"


def test_dashboard_serializes_reactive_weather_symbols() -> None:
    def get_weather(*_: Any) -> dict[str, Any]:
        return {
            "location": {"name": "Delhi", "country": "India"},
            "forecast": _forecast_payload(),
            "current_condition": describe_weather_code(1),
            "days": [
                {
                    "date": "2026-08-19",
                    "description": "Light rain",
                    "symbol": "☂",
                    "high": 33.5,
                    "low": 26.8,
                    "rain_chance": 61,
                }
            ],
        }

    payload = build_dashboard(get_weather, "Delhi", 1).to_json()
    assert payload["state"]["weather"]["current_condition"]["symbol"] == "☀"
    assert payload["state"]["weather"]["days"][0]["symbol"] == "☂"
