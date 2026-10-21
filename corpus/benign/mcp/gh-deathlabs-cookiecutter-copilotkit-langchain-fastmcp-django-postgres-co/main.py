# Standard library imports.
from json import dumps
from logging import getLogger
from os import environ

# Exclude metrics scrapes and health checks from instrumentation.
environ["OTEL_PYTHON_STARLETTE_EXCLUDED_URLS"] = "/metrics,/api/v1/health/"

# Third party imports.
from fastmcp import FastMCP
from fastmcp.utilities.logging import configure_logging
from httpx import AsyncClient
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from uvicorn import run

# Constants.
GEOCODING_API_KEY = environ["GEOCODING_API_KEY"]

# Init a MCP server and set its logging level.
mcp = FastMCP(name="{{ cookiecutter.project_slug }}")
configure_logging(level="DEBUG")
logger = getLogger("{{ cookiecutter.project_slug }}")

# Export OpenTelemetry metrics through the Prometheus registry.
meter_provider = MeterProvider(
    metric_readers=[PrometheusMetricReader()],
)


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(request: Request) -> Response:
    return Response(
        content=generate_latest(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )


@mcp.custom_route("/api/v1/health/", methods=["GET"])
async def health(request: Request) -> PlainTextResponse:
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
                "User-Agent": "({{ cookiecutter.project_slug }}, https://github.com/{{ cookiecutter.github_repository }})",
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
    app = mcp.http_app(path="/mcp")

    # Collect HTTP metrics while excluding health checks and scrapes.
    StarletteInstrumentor.instrument_app(
        app,
        meter_provider=meter_provider,
    )

    try:
        run(app, host="0.0.0.0", port=8002)
    finally:
        meter_provider.shutdown()
