# Standard library imports.
from json import dumps
from logging import getLogger
from os import environ, getenv

# Third party imports.
from fastmcp import FastMCP
from fastmcp.utilities.logging import configure_logging
from httpx import AsyncClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# Init a MCP server and set its logging level.
mcp = FastMCP(name="squidfall")
configure_logging(level="DEBUG")
logger = getLogger("squidfall")

GEOCODING_API_KEY = environ["GEOCODING_API_KEY"]


@mcp.custom_route("/api/v1/healthcheck", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse(dumps({"status": "ok"}))


@mcp.tool(description="Get the latitude and longitude for a location.")
async def get_coordinates(location: str) -> dict:
    """Get the latitude and longitude for a location.

    Args:
        location: A city name, address, or ZIP code (e.g. 'Pittsburgh, PA').

    Returns:
        A dict with 'lat' and 'lon' keys, or an error message under 'error'.
    """
    async with AsyncClient(verify=False) as client:
        response = await client.get(
            "https://geocode.maps.co/search",
            params={
                "q": location,
                "api_key": GEOCODING_API_KEY,
            },
            follow_redirects=True,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return {"error": f"No coordinates found for: {location}"}

        return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}


@mcp.tool(description="Get the current weather forecast for a coordinate pair.")
async def get_forecast(lat: float, lon: float) -> str:
    """Get the current weather forecast for a coordinate pair.

    Args:
        lat: Latitude.
        lon: Longitude.

    Returns:
        The current forecast period as a plain text string.
    """
    async with AsyncClient(verify=False) as client:
        points_response = await client.get(
            url=f"https://api.weather.gov/points/{lat},{lon}",
            headers={
                "User-Agent": "(squidfall, contact@example.com)",
                "Accept": "application/geo+json",
            },
            follow_redirects=True,
        )
        points_response.raise_for_status()
        forecast_url = points_response.json()["properties"]["forecast"]
        forecast_response = await client.get(forecast_url)
        forecast_response.raise_for_status()
        periods = forecast_response.json()["properties"]["periods"]
        current = periods[0]

        return f"{current['name']}: {current['detailedForecast']}"


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8002,
    )