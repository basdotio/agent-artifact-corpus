"""Example MCP tool using external API - Weather lookup"""

from tools.base import tool


@tool(
    name="get_weather",
    description="Get current weather for a city using Open-Meteo API (free, no API key needed)",
    schema={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name to get weather for"}
        },
        "required": ["city"],
    },
)
def get_weather(city: str) -> str:
    """Get weather for a city using Open-Meteo geocoding + weather API."""
    import httpx
    import json

    try:
        geocode_url = (
            f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        )
        geo_response = httpx.get(geocode_url, timeout=10)
        geo_data = geo_response.json()

        if not geo_data.get("results"):
            return f"City '{city}' not found"

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        city_name = geo_data["results"][0]["name"]
        country = geo_data["results"][0].get("country", "Unknown")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
        weather_response = httpx.get(weather_url, timeout=10)
        weather_data = weather_response.json()

        current = weather_data["current"]
        temp = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind = current["wind_speed_10m"]
        code = current["weather_code"]

        weather_desc = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
        }.get(code, f"Weather code {code}")

        return json.dumps(
            {
                "city": city_name,
                "country": country,
                "temperature": f"{temp}°C",
                "humidity": f"{humidity}%",
                "wind": f"{wind} km/h",
                "description": weather_desc,
            },
            indent=2,
        )

    except httpx.Timeout:
        return "Error: Request timed out"
    except Exception as e:
        return f"Error: {e}"
