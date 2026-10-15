"""Open-Meteo adapter with fixed endpoints, bounded responses and short-lived caching."""

import asyncio
import json
import time
from copy import deepcopy
from datetime import UTC, datetime

import httpx


class WeatherClient:
    def __init__(self, transport=None):
        self.transport = transport
        self.cache = {}

    async def request(self, url, params):
        key = (url, tuple(sorted(params.items())))
        cached = self.cache.get(key)
        if cached and cached[0] > time.monotonic():
            return {**deepcopy(cached[1]), "cached": True}
        async with httpx.AsyncClient(
            transport=self.transport, timeout=10, follow_redirects=False, trust_env=False
        ) as client:
            for attempt in range(3):
                try:
                    async with client.stream("GET", url, params=params) as response:
                        if (
                            response.status_code == 429 or response.status_code >= 500
                        ) and attempt < 2:
                            await asyncio.sleep(0.1 * 2**attempt)
                            continue
                        response.raise_for_status()
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 1_000_000:
                                raise ValueError("weather response exceeded size limit")
                    data = json.loads(body)
                    if not isinstance(data, dict) or data.get("error"):
                        raise ValueError("weather provider returned invalid data")
                    data = {
                        "data": data,
                        "source": "Open-Meteo",
                        "source_url": url,
                        "fetched_at": datetime.now(UTC).isoformat(),
                        "cached": False,
                    }
                    if len(self.cache) >= 128:
                        self.cache.pop(next(iter(self.cache)))
                    self.cache[key] = (time.monotonic() + 300, deepcopy(data))
                    return data
                except httpx.HTTPStatusError as error:
                    raise ValueError(
                        f"weather provider HTTP {error.response.status_code}"
                    ) from error
                except (httpx.TimeoutException, httpx.TransportError) as error:
                    if attempt == 2:
                        raise ValueError("weather provider unavailable; try later") from error
                except (json.JSONDecodeError, UnicodeDecodeError) as error:
                    raise ValueError("weather provider returned invalid JSON") from error
        raise ValueError("weather provider unavailable")

    async def locations(self, name, country_code=None):
        if not 2 <= len(name.strip()) <= 100:
            raise ValueError("location name must contain 2..100 characters")
        params = {"name": name.strip(), "count": 5, "language": "en", "format": "json"}
        if country_code:
            if len(country_code) != 2 or not country_code.isascii() or not country_code.isalpha():
                raise ValueError("use a two-letter country code")
            params["countryCode"] = country_code.upper()
        return await self.request("https://geocoding-api.open-meteo.com/v1/search", params)

    async def forecast(self, latitude, longitude, days=3):
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("invalid coordinates")
        if not 1 <= days <= 7:
            raise ValueError("forecast days must be 1..7")
        return await self.request(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": latitude,
                "longitude": longitude,
                "forecast_days": days,
                "timezone": "auto",
                "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            },
        )
