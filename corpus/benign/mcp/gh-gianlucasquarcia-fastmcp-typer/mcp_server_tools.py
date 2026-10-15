import asyncio

import requests
from fastmcp import Context, FastMCP
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from settings import settings

mcp = FastMCP("Tools")


@mcp.tool(
    title="Long Running Greet",
    description="Simulate a slow async task, then greet the given name.",
    tags={"demo", "greeting", "async"},
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def long_running_greet(name: str, ctx: Context) -> str:
    """
    Simulate a long-running task and return a greeting.

    Args:
        name (str): The name to greet.
        ctx (Context): FastMCP request context, used for progress reporting.

    Returns:
        str: A greeting message for the given name.
    """
    await ctx.report_progress(progress=0, total=1)
    await asyncio.sleep(
        settings.LONG_RUNNING_TASK_FAKE_DELAY
    )  # Simulate a long-running task
    await ctx.report_progress(progress=1, total=1)
    return f"Hello, {name}!"


@mcp.tool(
    title="Sort Numbers",
    description="Sort a list of numbers in ascending order.",
    tags={"demo", "sorting", "numbers"},
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
def sort_numbers(numbers: list[int]) -> list[int]:
    """
    Sort a list of numbers in ascending order.

    Args:
        numbers (list[int]): A list of numbers to be sorted.

    Returns:
        list[int]: The sorted list of numbers in ascending order.
    """
    return sorted(numbers)


@mcp.tool(
    title="Open-Meteo current forecast",
    description="Get the current temperature and wind speed for geographic coordinates.",
    tags={"weather", "forecast", "external-api"},
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
def open_meteo_current_forecast(latitude: float, longitude: float) -> dict:
    """
    Get the current weather forecast for a given latitude and longitude using the Open-Meteo API.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        dict: A dictionary containing the current weather forecast data.
    """

    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise ValueError(
            "Latitude must be between -90 and 90, and longitude must be between -180 and 180."
        )

    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    req = requests.Session()
    req.mount("https://", adapter)
    req.mount("http://", adapter)

    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m"
    response = req.get(
        url,
        verify=settings.HTTP_REQUEST_TLS_VERIFY,
        timeout=settings.HTTP_REQUEST_TIMEOUT,
    )
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()
