"""Transform weather responses into UI-friendly data."""

from typing import Any

from src.services.weather_service import describe_weather_code


def daily_rows(daily: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Open-Meteo's column-oriented daily response into UI rows."""
    return [
        {
            "date": daily["time"][i],
            "weather_code": daily["weather_code"][i],
            **describe_weather_code(daily["weather_code"][i]),
            "high": daily["temperature_2m_max"][i],
            "low": daily["temperature_2m_min"][i],
            "rain_chance": daily["precipitation_probability_max"][i],
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i],
        }
        for i in range(len(daily["time"]))
    ]
